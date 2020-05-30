import base64
import errno
import logging
import ssl
from distutils.util import strtobool
from os import getenv, path, strerror

import pytest
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Message

from .authenticator import Authenticator
from .authsmtp import AuthSMTP

# Use the same log as aiosmtpd
log = logging.getLogger('mail.log')

AUTH_FAILED = "530 Authentication failed."
AUTH_SUCCEEDED = "235 2.7.0 Authentication succeeded."


def _strtobool(value):
    """Method to simplify calling boolean values from env variables."""
    if isinstance(value, bool):
        return value

    return bool(strtobool(value))


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


def _base64_decode(base64_message):
    base64_bytes = base64_message
    if not isinstance(base64_message, bytes):
        base64_bytes = base64_message.encode('ASCII')
    message_bytes = base64.b64decode(base64_bytes)
    message = message_bytes.decode('ASCII')
    return message


def _base64_encode(message):
    message_bytes = message.encode('ASCII')
    base64_bytes = base64.b64encode(message_bytes)
    base64_message = base64_bytes.decode('ASCII')
    return base64_message


def authmechanism(text, requires_tls=False):
    def decorator(f):
        f.__auth_method__ = text
        # Requires TLS included for future development
        f.__requires_tls__ = requires_tls  # pragma: no coverage
        return f
    return decorator


class _Authenticator(Authenticator):
    def validate(self, username, password):
        if (
            username == getenv("SMPTD_LOGINNAME", "user") and
            password == getenv("SMPTD_LOGIN_PASSWORD", "password")
        ):
            return True
        return False


class MessageHandler(Message):
    def __init__(self, messages, authenticator=None):
        super().__init__()
        self._messages = messages
        self._authenticated = False
        self._authenticator = authenticator

    def _is_authmechanism(self, method):
        if getattr(method, '__auth_method__', None) is None:
            return False
        return True

    # def _get_auth_mechanisms(self):
    #     for name in dir(self):
    #         if not name.startswith('auth_'):
    #             continue
    #         method = getattr(self, name)

    async def _get_response(self, server, message):
        await server.push(message)
        response = await server._reader.readline()
        return response.rstrip()

    @authmechanism("LOGIN")
    async def auth_LOGIN(self, server, session, envelope, arg):
        log.debug("====> AUTH LOGIN received.")
        args = arg.split()
        while len(args) < 1:
            response = await self._get_response(server, "334 ")
            if response.startswith("*"):
                return AUTH_FAILED
            args.append(response)
        decoded = _base64_decode(args[1])

        login = decoded.split()
        while len(login) < 2:
            response = await self._get_response(
                server,
                "334 " + _base64_encode('Password')
            )
            response = _base64_decode(response)
            if response.startswith("*"):
                return AUTH_FAILED
            login.append(response)

        if self._authenticator.validate(
            login[0], login[1]
        ):
            self._authenticated = True
            return AUTH_SUCCEEDED
        return AUTH_FAILED

    @authmechanism("PLAIN")
    async def auth_PLAIN(self, server, session, envelope, arg):
        log.debug("====> AUTH PLAIN received.")
        args = arg.split()
        response = args[1] if len(args) >= 2 else None
        if response is None:
            response = await self._get_response(server, "334 ")
        response = _base64_decode(response).rstrip()
        response = response.split()
        if len(response) < 2:
            return AUTH_FAILED
        if (
            len(response) >= 2 and
            self._authenticator.validate(response[0], response[-1])
        ):
            self._authenticated = True
            return AUTH_SUCCEEDED
        return AUTH_FAILED

    def handle_message(self, message):
        self._messages.append(message)

    async def handle_EHLO(self, server, session, envelope, hostname):
        session.host_name = hostname
        await server.push("250-AUTH PLAIN LOGIN")
        return "250 HELP"

    async def handle_HELO(self, server, session, envelope, hostname):
        session.host_name = hostname
        await server.push("250-AUTH PLAIN")
        return "250 %s" % server.hostname

    async def handle_AUTH(self, server, session, envelope, arg):
        if self._authenticated:
            return "530 Already authenticated"
        _args = arg.split()
        _mechanism = _args[0].replace('-', '_')
        method = getattr(self, "auth_" + _mechanism, None)
        if method is None:
            return "504 Unrecognized authentication type."
        return await method(server, session, envelope, arg)


class AuthController(Controller):
    def __init__(self, hostname, port, authenticator=None):
        self.use_ssl = _strtobool(getenv("SMTPD_USE_SSL", False))
        self.ssl_context = _get_ssl_context() if self.use_ssl else None
        self.use_starttls = _strtobool(getenv("SMTPD_USE_STARTTLS", False))
        self.tls_context = None

        self._messages = []
        self._authenticator = authenticator
        if self._authenticator is None:
            self._authenticator = _Authenticator()

        self.handler = MessageHandler(self._messages,
                                      authenticator=authenticator)

        super().__init__(self.handler, hostname=hostname, port=port,
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


@pytest.fixture
def smtpd(request):
    fixture = AuthController(
        hostname=getenv("SMTPD_HOST", "127.0.0.1"),
        port=int(getenv("SMTPD_PORT", "8025")),
        authenticator=_Authenticator()
    )
    request.addfinalizer(fixture.stop)
    fixture.start()
    return fixture
