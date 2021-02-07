import errno
import logging
import ssl
from os import strerror
from pathlib import Path

from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP

from .config import Config
from .handlers import AuthMessage

log = logging.getLogger(__name__)


class AuthController(Controller):
    def __init__(self,
                 loop=None,
                 hostname=None,
                 port=8025,
                 ready_timeout=1.0,
                 ssl_context=None,
                 config=None,
                 authenticator=None):
        self.config = config or Config()
        self._messages = []
        self._ssl_context = ssl_context

        handler = AuthMessage(messages=self._messages,
                              authenticator=authenticator)

        def context_or_none():
            # Determines whether to return a sslContext or None to avoid a
            # situation where both could be used. Prefers STARTTLS to TLS.
            if (
                (self.config.SMTPD_USE_TLS or
                 self.config.SMTPD_USE_SSL) and
                not self.config.SMTPD_USE_STARTTLS
            ):
                return ssl_context or self._get_ssl_context()
            return None

        super().__init__(handler=handler,
                         hostname=hostname,
                         port=port,
                         loop=loop,
                         ready_timeout=ready_timeout,
                         ssl_context=context_or_none())

        log.info(f"SMTPDFix running on {self.hostname}:{self.port}")

    def factory(self):
        auth_required = self.config.SMTPD_ENFORCE_AUTH
        auth_require_tls = self.config.SMTPD_AUTH_REQUIRE_TLS
        use_starttls = self.config.SMTPD_USE_STARTTLS
        certs = self._get_ssl_context() if use_starttls else None

        return SMTP(handler=self.handler,
                    require_starttls=use_starttls,
                    auth_required=auth_required,
                    auth_require_tls=auth_require_tls,
                    tls_context=certs)

    def _get_ssl_context(self):
        if self._ssl_context is not None:
            return self._ssl_context

        certs_path = Path(self.config.SMTPD_SSL_CERTS_PATH).resolve()
        cert_path = certs_path.joinpath("cert.pem")
        key_path = certs_path.joinpath("key.pem")

        for file_ in [cert_path, key_path]:
            if file_.is_file():
                continue
            log.debug(f"File {str(file_)} not found")
            raise FileNotFoundError(errno.ENOENT,
                                    strerror(errno.ENOENT),
                                    file_)

        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(cert_path, key_path)

        return context

    @property
    def messages(self):
        return self._messages.copy()
