import errno
import logging
import os
import ssl
from distutils.util import strtobool

from aiosmtpd.controller import Controller

from .handlers import AuthMessage
from .smtp import AuthSMTP

log = logging.getLogger('mail.log')


def _strtobool(value):
    """Method to simplify calling boolean values from env variables."""
    if isinstance(value, bool):
        return value

    return bool(strtobool(value))


def _get_ssl_context(certs_path=None):
    if certs_path is None:
        current_dir = os.path.dirname(__file__)
        certs_path = os.getenv("SMTPD_CERTS_PATH",
                               os.path.join(current_dir, "certs"))
    cert_path = os.path.join(certs_path, 'cert.pem')
    key_path = os.path.join(certs_path, 'key.pem')

    for file_ in [cert_path, key_path]:
        if os.path.isfile(file_):
            log.debug(f"Found {os.path.abspath(file_)}")
            continue
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT),
                                os.path.abspath(file_))

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(cert_path, key_path)

    return context


class AuthController(Controller):
    def __init__(self, loop=None, hostname=None, port=None,
                 ready_timeout=1.0, enable_SMTPUTF8=True,
                 authenticator=None):
        self.use_starttls = _strtobool(os.getenv("SMTPD_USE_STARTTLS", False))

        self._messages = []
        handler = AuthMessage(messages=self._messages,
                              authenticator=authenticator)

        __ssl_context = None
        print(f"SMTPD_USE_SSL is {os.getenv('SMTPD_USE_SSL', False)}")
        if _strtobool(os.getenv("SMTPD_USE_SSL", False)):
            __ssl_context = _get_ssl_context()

        super().__init__(handler=handler,
                         hostname=hostname,
                         port=port,
                         ready_timeout=ready_timeout,
                         enable_SMTPUTF8=enable_SMTPUTF8,
                         ssl_context=__ssl_context)

    def factory(self):
        tls_context = None
        if self.use_starttls:
            tls_context = _get_ssl_context()

        return AuthSMTP(
            handler=self.handler,
            require_starttls=self.use_starttls,
            tls_context=tls_context
        )

    @property
    def messages(self):
        return self._messages.copy()
