import os
from os import getenv, strerror
import errno
import ssl
from distutils.util import strtobool
import logging

from aiosmtpd.controller import Controller

from .smtp import AuthSMTP
from .handlers import AuthMessage
from .authenticator import Authenticator

log = logging.getLogger('mail.log')


def _strtobool(value):
    """Method to simplify calling boolean values from env variables."""
    if isinstance(value, bool):
        return value

    return bool(strtobool(value))


def _get_ssl_context(certs_path=None):
    if certs_path is None:
        current_dir = os.path.dirname(__file__)
        certs_path = getenv("SMTPD_CERTS_PATH",
                            os.path.join(current_dir, "certs"))
    cert_path = os.path.join(certs_path, 'cert.pem')
    key_path = os.path.join(certs_path, 'key.pem')

    for file_ in [cert_path, key_path]:
        if os.path.isfile(file_):
            log.debug(f"Found {os.path.abspath(file_)}")
            continue
        raise FileNotFoundError(errno.ENOENT, strerror(errno.ENOENT),
                                os.path.abspath(file_))

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(cert_path, key_path)

    return context


class AuthController(Controller):
    def __init__(self, hostname, port, authenticator=None):
        self.use_ssl = _strtobool(getenv("SMTPD_USE_SSL", False))
        self.ssl_context = _get_ssl_context() if self.use_ssl else None
        self.use_starttls = _strtobool(getenv("SMTPD_USE_STARTTLS", False))
        self.tls_context = None

        self._messages = []
        if authenticator is None:
            authenticator = Authenticator()

        self.handler = AuthMessage(messages=self._messages,
                                   authenticator=authenticator)

        super().__init__(handler=self.handler,
                         hostname=hostname,
                         port=port,
                         ssl_context=self.ssl_context)

    def factory(self):
        if self.use_starttls:
            self.tls_context = _get_ssl_context()

        return AuthSMTP(
            handler=self.handler,
            require_starttls=self.use_starttls,
            tls_context=self.tls_context
        )

    @property
    def messages(self):
        return self._messages.copy()
