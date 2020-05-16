import errno
import ssl
import logging
from os import getenv, path, strerror
from distutils.util import strtobool

import pytest
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Message
from aiosmtpd.smtp import SMTP

log = logging.getLogger(__name__)


def _strtobool(str):
    """Method to simplify calling boolean values from env variables."""
    if isinstance(str, bool):
        return str

    return bool(strtobool(str))


def _get_ssl_context():
    current_dir = path.dirname(__file__)
    certs_path = getenv("SMTPD_CERTS_PATH", path.join(current_dir, "certs"))
    cert_path = path.join(certs_path, 'cert.pem')
    key_path = path.join(certs_path, 'key.pem')

    for file_ in [cert_path, key_path]:
        if path.isfile(file_):
            log.debug(f"Found {path.abspath(file_)}")
            continue
        raise FileNotFoundError(errno.ENOENT, strerror(errno.ENOENT),
                                path.abspath(file_))

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(cert_path, key_path)

    return context


class MessageHandler(Message):
    def __init__(self, messages):
        super().__init__()
        self._messages = messages

    def handle_message(self, message):
        self._messages.append(message)


class _Controller(Controller):
    def __init__(self, hostname, port):
        self.use_ssl = _strtobool(getenv("SMTPD_USE_SSL", False))
        self.ssl_context = None
        if self.use_ssl:
            self.ssl_context = _get_ssl_context()

        self.use_starttls = _strtobool(getenv("SMTPD_USE_STARTTLS", False))
        self.tls_context = None

        self._messages = []
        self.handler = MessageHandler(self._messages)

        super().__init__(self.handler, hostname=hostname, port=port,
                         ssl_context=self.ssl_context)

    def factory(self):
        if self.use_starttls:
            self.tls_context = _get_ssl_context()

        return SMTP(
            handler=self.handler,
            require_starttls=self.use_starttls,
            tls_context=self.tls_context
        )

    @property
    def messages(self):
        return self._messages.copy()


@pytest.fixture
def smtpd(request):
    hostname = getenv("SMTPD_HOST", "127.0.0.1")
    port = int(getenv("SMTPD_PORT", "8025"))

    fixture = _Controller(hostname, port)
    request.addfinalizer(fixture.stop)
    fixture.start()
    return fixture
