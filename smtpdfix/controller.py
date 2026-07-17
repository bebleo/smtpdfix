import asyncio
import base64
import errno
import logging
import socket
import threading
from email.parser import BytesParser
from os import strerror
from pathlib import Path
from socket import create_connection
from ssl import (CERT_NONE, CERT_OPTIONAL, Purpose, SSLContext,
                 create_default_context)
from typing import Any

from .authenticator import Authenticator
from .configuration import Config
from .handlers import MISSING, AuthMessage
from .smtp import _SMTP, TLSSetupException

log = logging.getLogger(__name__)


class _SMTPSession:
    def __init__(
        self,
        controller: "AuthController",
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        self.controller = controller
        self.reader = reader
        self.writer = writer
        self.authenticated = False
        self.encrypted = bool(writer.get_extra_info("ssl_object"))
        self.mail_from: str | None = None
        self.recipients: list[str] = []
        self.peer = writer.get_extra_info("peername")
        self._smtp = _SMTP(
            controller.handler,
            hostname=controller.hostname,
            tls_context=(
                controller._get_ssl_context()
                if controller.config.use_starttls
                else None
            ),
            loop=controller.loop,
            transport=writer.transport,
            protocol=getattr(writer, "_protocol", None),
            reader=reader,
            writer=writer,
        )

    @property
    def hostname(self) -> str:
        return self.controller.hostname or socket.gethostname()

    @property
    def _authenticator(self) -> Authenticator:
        authenticator = self.controller._authenticator
        if authenticator is None:
            raise RuntimeError("No authenticator configured")
        return authenticator

    async def push(self, message: str) -> None:
        self.writer.write(f"{message}\r\n".encode("ascii"))
        await self.writer.drain()

    async def challenge_auth(self, challenge: str) -> Any:
        if challenge:
            prompt = base64.b64encode(challenge.encode("utf-8")).decode(
                "ascii"
            )
            await self.push(f"334 {prompt}")
        else:
            await self.push("334")

        line = await self._readline()
        if line is None or line == "*":
            await self.push("501 Authentication aborted")
            return MISSING

        try:
            return base64.b64decode(line)
        except Exception:
            return MISSING

    async def _readline(self) -> str | None:
        data = await self.reader.readline()
        if not data:
            return None
        return data.decode("utf-8", errors="replace").strip("\r\n")

    async def run(self) -> None:
        await self.push(f"220 {self.hostname} SMTPDFix ready")
        while True:
            line = await self._readline()
            if line is None:
                return
            if not line:
                continue

            parts = line.split(" ", 1)
            command = parts[0].upper()
            arg = parts[1] if len(parts) > 1 else ""

            if command in {"EHLO", "HELO"}:
                await self._handle_helo(command)
            elif command == "NOOP":
                await self.push("250 OK")
            elif command == "RSET":
                self.mail_from = None
                self.recipients.clear()
                await self.push("250 OK")
            elif command == "QUIT":
                await self.push("221 Bye")
                return
            elif command == "STARTTLS":
                await self._handle_starttls(arg)
            elif command == "AUTH":
                await self._handle_auth(arg)
            elif command == "MAIL":
                await self._handle_mail(arg)
            elif command == "RCPT":
                await self._handle_rcpt(arg)
            elif command == "DATA":
                await self._handle_data()
            else:
                await self.push("500 Error: command not recognized")

    async def _handle_helo(self, command: str) -> None:
        if command == "HELO":
            await self.push(f"250 {self.hostname}")
            return

        lines = [f"250-{self.hostname}"]
        if self.controller.config.use_starttls and not self.encrypted:
            lines.append("250-STARTTLS")

        auth_mechs: list[str] = []
        if not self.controller.config.auth_require_tls or self.encrypted:
            auth_mechs = ["PLAIN", "LOGIN", "CRAM-MD5"]

        if auth_mechs:
            lines.append(f"250-AUTH {' '.join(auth_mechs)}")

        lines.append("250 HELP")
        for line in lines:
            await self.push(line)

    def _auth_required_block(self) -> str | None:
        if self.controller.config.enforce_auth and not self.authenticated:
            return "530 5.7.0 Authentication required"
        if self.controller.config.use_starttls and not self.encrypted:
            return "530 Must issue STARTTLS first"
        return None

    async def _handle_mail(self, arg: str) -> None:
        blocked = self._auth_required_block()
        if blocked:
            await self.push(blocked)
            return
        if not arg.upper().startswith("FROM:"):
            await self.push("501 Syntax: MAIL FROM:<address>")
            return
        self.mail_from = arg[5:].strip()
        self.recipients.clear()
        await self.push("250 OK")

    async def _handle_rcpt(self, arg: str) -> None:
        blocked = self._auth_required_block()
        if blocked:
            await self.push(blocked)
            return
        if self.mail_from is None:
            await self.push("503 Error: need MAIL command")
            return
        if not arg.upper().startswith("TO:"):
            await self.push("501 Syntax: RCPT TO:<address>")
            return
        self.recipients.append(arg[3:].strip())
        await self.push("250 OK")

    async def _handle_data(self) -> None:
        blocked = self._auth_required_block()
        if blocked:
            await self.push(blocked)
            return
        if self.mail_from is None or not self.recipients:
            await self.push("503 Error: need MAIL command")
            return

        await self.push("354 End data with <CR><LF>.<CR><LF>")
        lines: list[bytes] = []
        while True:
            data = await self.reader.readline()
            if not data:
                return
            if data in (b".\r\n", b".\n"):
                break
            if data.startswith(b".."):
                data = data[1:]
            lines.append(data)

        parser = BytesParser()
        message = parser.parsebytes(b"".join(lines))
        self.controller.handler.handle_message(message)
        await self.push("250 OK")

    async def _handle_starttls(self, arg: str) -> None:
        if arg:
            await self.push("501 Syntax: STARTTLS")
            return
        if not self.controller.config.use_starttls:
            await self.push("454 TLS not available")
            return

        try:
            await self._smtp.smtp_STARTTLS(arg or None)
        except TLSSetupException:
            await self.push("454 TLS not available")
            return
        except asyncio.CancelledError:
            raise

        self.encrypted = True
        self.authenticated = False
        self.mail_from = None
        self.recipients.clear()

    async def _handle_auth(self, arg: str) -> None:
        if self.authenticated:
            await self.push("503 Already authenticated")
            return
        if self.controller.config.auth_require_tls and not self.encrypted:
            await self.push(
                "538 5.7.11 Encryption required for requested "
                "authentication mechanism"
            )
            return

        if not arg:
            await self.push("501 Syntax: AUTH mechanism [initial-response]")
            return

        parts = arg.split()
        mechanism = parts[0].upper()

        handler_name = f"auth_{mechanism.replace('-', '_')}"
        if not hasattr(self.controller.handler, handler_name):
            await self.push("504 5.5.4 Unrecognized authentication type")
            return

        result = await getattr(self.controller.handler, handler_name)(
            self, [mechanism, *parts[1:]]
        )
        if result.success:
            self.authenticated = True
            await self.push("235 2.7.0 Authentication successful")
            return
        if result.handled:
            return
        await self.push("535 5.7.8 Authentication credentials invalid")


class AuthController:
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop | None = None,
        hostname: str | None = None,
        port: int | None = None,
        ready_timeout: float | None = None,
        ssl_context: SSLContext | None = None,
        config: Config | None = None,
        authenticator: Authenticator | None = None,
        sock: socket.socket | None = None,
        **kwargs: Any,
    ) -> None:
        if sock is not None and (hostname is not None or port is not None):
            raise ValueError("Cannot pass host/port together with sock")

        self.config = config or Config()
        self._messages = kwargs.get("messages") or []
        self._ssl_context = ssl_context
        self._authenticator = authenticator
        self._sock = sock

        self.handler = AuthMessage(messages=self._messages)

        _hostname = hostname or self.config.host
        _port = int(port or self.config.port)
        if self._sock is not None:
            try:
                sock_name = self._sock.getsockname()
                if isinstance(sock_name, tuple) and len(sock_name) >= 2:
                    _hostname = sock_name[0]
                    _port = int(sock_name[1])
            except OSError:
                pass

        self.hostname = _hostname
        self.port = _port
        self.ready_timeout = float(ready_timeout or self.config.ready_timeout)
        self.loop = loop or asyncio.new_event_loop()
        self.loop.set_exception_handler(self._handle_exception)

        self.server: asyncio.AbstractServer | None = None
        self.thread: threading.Thread | None = None
        self._thread_exception: Exception | None = None
        self._started = False
        self._clients: set[asyncio.StreamWriter] = set()

        self.config.host = self.hostname
        if port is not None:
            self.config.port = port
        self.config.OnChanged += self.reset
        log.info(f"SMTPDFix running on {self.hostname}:{self.port}")

    def _get_ssl_context(self) -> SSLContext:
        if self._ssl_context is not None:
            return self._ssl_context

        cert_file, key_file = self.config.ssl_cert_files

        def _resolve_file(file_: str | None) -> str:
            if file_ and Path(file_).is_file():
                return str(Path(file_))
            raise FileNotFoundError(
                errno.ENOENT, strerror(errno.ENOENT), file_
            )

        cert_path = _resolve_file(cert_file)
        key_path = _resolve_file(key_file) if key_file else None

        context = create_default_context(Purpose.CLIENT_AUTH)
        context.check_hostname = False
        context.load_verify_locations(cert_path)
        context.load_cert_chain(cert_path, keyfile=key_path)
        return context

    @property
    def ssl_context(self) -> SSLContext | None:
        if self.config.use_ssl and not self.config.use_starttls:
            context = self._get_ssl_context()
            context.verify_mode = CERT_OPTIONAL
            return context
        return None

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        self._clients.add(writer)
        try:
            session = _SMTPSession(self, reader, writer)
            await session.run()
        finally:
            self._clients.discard(writer)
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _start_async(self) -> None:
        server_kwargs: dict[str, Any] = {}
        if self.ssl_context:
            server_kwargs["ssl"] = self.ssl_context
            server_kwargs["ssl_handshake_timeout"] = 5.0

        if self._sock is not None:
            self.server = await asyncio.start_server(
                self._handle_client,
                sock=self._sock,
                **server_kwargs,
            )
        else:
            self.server = await asyncio.start_server(
                self._handle_client,
                host=self.hostname,
                port=self.port,
                **server_kwargs,
            )

        sockets: list[Any] = list(self.server.sockets or [])
        if sockets:
            sock_name = sockets[0].getsockname()
            if isinstance(sock_name, tuple) and len(sock_name) >= 2:
                self.hostname = str(sock_name[0])
                self.port = int(sock_name[1])

    async def _stop_async(self) -> None:
        for writer in list(self._clients):
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
        self._clients.clear()

        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()
            self.server = None

    def _run(self, ready_event: threading.Event) -> None:
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._start_async())
        except Exception as error:
            self._thread_exception = error
            ready_event.set()
            return

        ready_event.set()
        self.loop.run_forever()

        self.loop.run_until_complete(self._stop_async())
        self.loop.close()

    def _trigger_server(self) -> None:
        if self._sock is not None:
            return

        hostname = self.hostname or "localhost"
        with create_connection((hostname, self.port), 1.0) as conn:
            s: Any = conn
            if self.config.use_ssl and not self.config.use_starttls:
                client_context = create_default_context(Purpose.SERVER_AUTH)
                client_context.check_hostname = False
                client_context.verify_mode = CERT_NONE
                s = client_context.wrap_socket(s, server_hostname=hostname)
            _ = s.recv(1024)

    def start(self) -> None:
        if self._started:
            return

        if self.config.use_starttls or self.config.use_ssl:
            # Validate certs early so start() fails fast.
            self._get_ssl_context()

        ready_event = threading.Event()
        self.thread = threading.Thread(
            target=self._run, args=(ready_event,), daemon=True
        )
        self.thread.start()

        if not ready_event.wait(self.ready_timeout):
            raise TimeoutError("SMTP server startup timed out")

        if self._thread_exception is not None:
            raise self._thread_exception

        self._trigger_server()
        self._started = True

    def stop(self, no_assert: bool = False) -> None:
        if not self._started:
            if no_assert:
                return
            raise AssertionError("SMTP server is not running")

        if self.loop.is_closed():
            self._started = False
            return

        self.loop.call_soon_threadsafe(self.loop.stop)

        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=self.ready_timeout)

        self._close_loop()

        self._started = False

    def _close_loop(self) -> None:
        if self.loop.is_closed() or self.loop.is_running():
            return

        try:
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
        except Exception:
            pass

        try:
            self.loop.run_until_complete(self.loop.shutdown_default_executor())
        except Exception:
            pass

        self.loop.close()

    def reset(self, persist_messages: bool = True) -> None:
        was_running = self._started
        if was_running:
            self.stop()
        else:
            self._close_loop()

        self.config.OnChanged -= self.reset
        if not persist_messages:
            self._messages.clear()

        self.hostname = self.config.host
        self.port = int(self.config.port)

        self.loop = asyncio.new_event_loop()
        self.loop.set_exception_handler(self._handle_exception)

        self.config.OnChanged += self.reset

        if was_running:
            self.start()

    def _handle_exception(
        self, loop: asyncio.AbstractEventLoop, context: Any
    ) -> None:
        loop.default_exception_handler(context)
        for writer in list(self._clients):
            transport = writer.transport
            if transport is not None:
                transport.close()
        if self.server is not None:
            self.server.close()

    @property
    def messages(self) -> list[Any]:
        return self._messages.copy()
