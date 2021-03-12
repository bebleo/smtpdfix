import asyncio
import errno
import logging
import ssl
from os import strerror
from pathlib import Path

from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP

from .configuration import Config
from .handlers import AuthMessage

log = logging.getLogger(__name__)


class AuthController(Controller):
    def __init__(self,
                 loop=None,
                 hostname=None,
                 port=None,
                 ready_timeout=1.0,
                 ssl_context=None,
                 config=None,
                 authenticator=None,
                 **kwargs):
        self.config = config or Config()
        self._messages = kwargs.get("messages") or []
        self._ssl_context = ssl_context
        self._authenticator = authenticator

        _handler = AuthMessage(messages=self._messages)
        _hostname = hostname or self.config.host
        _port = int(port or self.config.port)
        _loop = loop or asyncio.new_event_loop()
        _loop.set_exception_handler(self.handle_exception)

        def context_or_none():
            # Determines whether to return a sslContext or None to avoid a
            # situation where both could be used. Prefers STARTTLS to TLS.
            if (
                (self.config.use_tls or
                 self.config.use_ssl) and
                not self.config.use_starttls
            ):
                return ssl_context or self._get_ssl_context()
            return None

        super().__init__(handler=_handler,
                         hostname=_hostname,
                         port=_port,
                         loop=_loop,
                         ready_timeout=ready_timeout,
                         ssl_context=context_or_none(),
                         authenticator=self._authenticator)

        # The event handler for changes to the config goes here to prevent it
        # firing when the obkect is initialized.
        if hostname is not None:
            self.config.host = hostname
        if port is not None:
            self.config.port = port
        self.config.OnChanged += self.reset
        log.info(f"SMTPDFix running on {self.hostname}:{self.port}")

    def factory(self):
        use_starttls = self.config.use_starttls
        certs = self._get_ssl_context() if use_starttls else None

        return SMTP(handler=self.handler,
                    require_starttls=self.config.use_starttls,
                    auth_required=self.config.enforce_auth,
                    auth_require_tls=self.config.auth_require_tls,
                    tls_context=certs,
                    authenticator=self._authenticator)

    def _get_ssl_context(self):
        if self._ssl_context is not None:
            return self._ssl_context

        certs_path = Path(self.config.ssl_certs_path).resolve()
        cert_path = certs_path.joinpath("cert.pem").resolve()
        key_path = certs_path.joinpath("key.pem").resolve()

        for file_ in [cert_path, key_path]:
            if file_.is_file():
                continue
            log.debug(f"File {str(file_)} not found")
            raise FileNotFoundError(errno.ENOENT,
                                    strerror(errno.ENOENT),
                                    file_)

        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

        # Becuase PYPY3 doesn't support Path objects when loading the
        # certificate and keys we cast them to a string.
        context.load_cert_chain(str(cert_path), keyfile=str(key_path))

        return context

    def handle_exception(self, loop, context):
        loop.default_exception_handler(context)

        status = "421 Service not available. Closing connection."
        asyncio.ensure_future(self.smtpd.push(status))
        self.smtpd.transport.close()
        self.server.close()

    def reset(self, persist_messages=True):
        _running = False
        try:
            self.stop()
            _running = True
        except AssertionError:
            pass

        # Remove the handler to avoid recursion
        self.config.OnChanged -= self.reset

        self.__init__(
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

    @property
    def messages(self):
        return self._messages.copy()
