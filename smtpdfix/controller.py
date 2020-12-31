import errno
import logging
import os
import ssl

from aiosmtpd.controller import Controller

from .handlers import AuthMessage
from .lazy import lazy_class
from .smtp import AuthSMTP

log = logging.getLogger(__name__)


@lazy_class
class AuthController(Controller):
    def __init__(self,
                 loop=None,
                 hostname=None,
                 port=None,
                 ready_timeout=1.0,
                 enable_SMTPUTF8=True,
                 config=None,
                 authenticator=None):
        self.use_starttls = config.SMTPD_USE_STARTTLS
        self.config = config

        self._messages = []
        handler = AuthMessage(messages=self._messages,
                              authenticator=authenticator)

        __ssl_context = None
        if config.SMTPD_USE_SSL or config.SMTPD_USE_TLS:
            __ssl_context = self._get_ssl_context()

        super().__init__(handler=handler,
                         hostname=hostname,
                         port=port,
                         ready_timeout=ready_timeout,
                         enable_SMTPUTF8=enable_SMTPUTF8,
                         ssl_context=__ssl_context)

        self._starttls_context = None
        if config.SMTPD_USE_STARTTLS:
            certs = self._get_ssl_context()
            self._starttls_context = certs

        log.info(f"SMTPD running on {self.hostname}:{self.port}")

    def factory(self):
        return AuthSMTP(handler=self.handler,
                        require_starttls=self.use_starttls,
                        tls_context=self._starttls_context)

    def _get_ssl_context(self):
        certs_path = self.config.SMTPD_SSL_CERTS_PATH
        cert_path = os.path.join(certs_path, 'cert.pem')
        key_path = os.path.join(certs_path, 'key.pem')

        for file_ in [cert_path, key_path]:
            if os.path.isfile(file_):
                log.debug(f"Found {os.path.abspath(file_)}")
                continue
            log.debug(f"File {os.path.abspath(file_)} not found")
            raise FileNotFoundError(errno.ENOENT,
                                    os.strerror(errno.ENOENT),
                                    os.path.abspath(file_))

        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(cert_path, key_path)

        return context

    @property
    def messages(self):
        return self._messages.copy()
