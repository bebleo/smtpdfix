import asyncio
import errno
import logging
from contextlib import ExitStack
from os import strerror
from pathlib import Path
from socket import create_connection
from ssl import CERT_OPTIONAL, Purpose, SSLContext, create_default_context
from typing import Any, List, Optional

from aiosmtpd.controller import Controller, get_localhost

from .authenticator import Authenticator
from .configuration import Config
from .handlers import AuthMessage
from .smtp import _SMTP
from .typing import AsyncServer, PathType, ServerCoroutine

log = logging.getLogger(__name__)


class AuthController(Controller):
    def __init__(self,
                 loop: Optional[asyncio.AbstractEventLoop] = None,
                 hostname: Optional[str] = None,
                 port: Optional[int] = None,
                 ready_timeout: Optional[float] = None,
                 ssl_context: Optional[SSLContext] = None,
                 config: Optional[Config] = None,
                 authenticator: Optional[Authenticator] = None,
                 **kwargs: Any) -> None:
        self.config = config or Config()
        self._messages = kwargs.get("messages") or []
        self._ssl_context = ssl_context
        self._authenticator = authenticator

        _handler = AuthMessage(messages=self._messages)
        _hostname = hostname or self.config.host
        _port = int(port or self.config.port)
        _ready_timeout = float(ready_timeout or self.config.ready_timeout)
        _loop = loop or asyncio.new_event_loop()
        _loop.set_exception_handler(self._handle_exception)

        def context_or_none() -> Optional[SSLContext]:
            # Determines whether to return a sslContext or None to avoid a
            # situation where both could be used. Prefers STARTTLS to TLS.
            if (self.config.use_ssl and not self.config.use_starttls):
                context = ssl_context or self._get_ssl_context()
                context.verify_mode = CERT_OPTIONAL
                return context

            return None

        super().__init__(handler=_handler,
                         hostname=_hostname,
                         port=_port,
                         loop=_loop,
                         ready_timeout=_ready_timeout,
                         ssl_context=context_or_none(),
                         authenticator=self._authenticator,
                         **kwargs)

        # The event handler for changes to the config goes here to prevent it
        # firing when the obkect is initialized.
        self.config.host = _hostname
        if port is not None:
            self.config.port = port
        self.config.OnChanged += self.reset
        log.info(f"SMTPDFix running on {self.hostname}:{self.port}")

    def factory(self) -> _SMTP:
        use_starttls = self.config.use_starttls
        context = self._get_ssl_context() if use_starttls else None

        return _SMTP(handler=self.handler,
                     require_starttls=self.config.use_starttls,
                     auth_required=self.config.enforce_auth,
                     auth_require_tls=self.config.auth_require_tls,
                     tls_context=context,
                     authenticator=self._authenticator)

    def _get_ssl_context(self) -> SSLContext:
        if self._ssl_context is not None:
            return self._ssl_context

        certs_path = Path(self.config.ssl_certs_path).resolve()
        cert_file, key_file = self.config.ssl_cert_files

        def _resolve_file(basepath: Path, file_: PathType) -> str:
            # Resolve the file paths in order:
            #   1. if the file exists return the path as string
            #   2. try to combine basepath and the filename and if that exists
            #      return as a string.
            # NB: the paths are returned as strings becuase PYPY3 doesn't
            # support paths in sslcontext.load_cert_chain()
            if Path(file_).is_file():
                return str(Path(file_))
            elif basepath.joinpath(file_).resolve().is_file():
                return str(basepath.joinpath(file_).resolve())

            raise FileNotFoundError(errno.ENOENT,
                                    strerror(errno.ENOENT),
                                    file_)

        cert_path = _resolve_file(certs_path, cert_file)
        key_path = _resolve_file(certs_path, key_file) if key_file else None

        context = create_default_context(Purpose.CLIENT_AUTH)
        context.check_hostname = False
        context.load_verify_locations(cert_path)
        context.load_cert_chain(cert_path, keyfile=key_path)
        return context

    def _handle_exception(self, loop: Any, context: Any) -> None:
        loop.default_exception_handler(context)

        status = "421 Service not available. Closing connection."
        asyncio.ensure_future(self.smtpd.push(status))
        self.smtpd.transport.close()
        self.server.close()

    def _run(self, ready_event: Any) -> None:
        asyncio.set_event_loop(self.loop)
        try:
            # Need to do two-step assignments here to ensure IDEs can properly
            # detect the types of the vars. Cannot use `assert isinstance`,
            # because Python 3.6 in asyncio debug mode has a bug wherein
            # CoroWrapper is not an instance of Coroutine
            coro_kwargs = {}
            if self.ssl_context:
                coro_kwargs["ssl_handshake_timeout"] = 5.0

            srv_coro: ServerCoroutine = self.loop.create_server(
                self._factory_invoker,
                host=self.hostname,
                port=self.port,
                ssl=self.ssl_context,
                **coro_kwargs
            )
            self.server_coro = srv_coro
            srv: AsyncServer = self.loop.run_until_complete(srv_coro)
            self.server = srv
        except Exception as error:  # pragma: on-wsl; # pragma: no cover
            # Usually will enter this part only if create_server() cannot bind
            # to the specified host:port.
            #
            # Somehow WSL 1.0 (Windows Subsystem for Linux) allows multiple
            # listeners on one port?!
            # That is why we add "pragma: on-wsl" there, so this block will not
            # affect coverage on WSL 1.0.
            self._thread_exception = error
            return
        self.loop.call_soon(ready_event.set)
        self.loop.run_forever()
        self.server.close()
        self.loop.run_until_complete(self.server.wait_closed())
        self.loop.close()
        # This done this way to accomodate type checking. Was originally the
        # more sensible self.server = None
        setattr(self, "server", None)

    def reset(self, persist_messages: bool = True) -> None:
        _running = False
        try:
            self.stop()
            _running = True
        except AssertionError:
            pass

        # Remove the handler to avoid recursion
        self.config.OnChanged -= self.reset

        # Ignoring this for the purposes of type checking on the grounds that
        # this works and can't be replaced for now.
        self.__init__(  # type: ignore
            loop=None if self.loop.is_closed() else self.loop,
            hostname=self.config.host,
            port=self.config.port,
            ssl_context=self._ssl_context,
            config=self.config,
            authenticator=self._authenticator,
            messages=self._messages if persist_messages else None
        )

        if _running:
            self.start()

    def _trigger_server(self) -> None:
        hostname = self.hostname or get_localhost()
        with ExitStack() as stk:
            conn = create_connection((hostname, self.port), 1.0)
            s = stk.enter_context(conn)
            # connecting using the ssl_context removed as this fails under
            # python 3.10 when using opportunistic SSL
            _ = s.recv(1024)

    @property
    def messages(self) -> List[Any]:
        return self._messages.copy()
