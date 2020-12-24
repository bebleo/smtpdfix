import base64
import hmac
import logging
import secrets
from datetime import datetime

from aiosmtpd.handlers import Message

from .config import Config

log = logging.getLogger(__name__)

AUTH_ALREADY_DONE = "503 Already authenticated"
AUTH_CANCELLED = "501 Syntax error in parameters or arguments"
AUTH_ENCRYPTION_REQUIRED = ("538 Encryption required for requested "
                            "authentication mechanism")
AUTH_FAILED = "530 Authentication failed"
AUTH_REQUIRED = "530 SMTP authentication is required"
AUTH_UNRECOGNIZED = "504 Unrecognized authentication type"
AUTH_SUCCEEDED = "235 2.7.0 Authentication succeeded"
AUTH_VERIFIED = ("252 Cannot VRFY user, but will accept message "
                 "and attempt delivery")
AUTH_UNVERIFIED = "502 Could not VRFY"
SMTP_STARTTLS_REQUIRED = "530 5.7.0 Must issue a STARTTLS command first"


def _base64_decode(base64_message):
    base64_bytes = base64_message
    if not isinstance(base64_message, bytes):
        base64_bytes = base64_message.encode('ascii')
    message_bytes = base64.b64decode(base64_bytes)
    message = message_bytes.decode('ascii')
    return message


def _base64_encode(message):
    message_bytes = message.encode('ascii')
    base64_bytes = base64.b64encode(message_bytes)
    base64_message = base64_bytes.decode('ascii')
    return base64_message


def authmechanism(text, requires_encryption=False):
    def decorator(func):
        func.__auth_method__ = text
        func.__requires_encryption__ = requires_encryption
        return func
    return decorator


class AuthMessage(Message):
    def __init__(self, messages, authenticator=None, enforce_auth=None):
        super().__init__()
        self._messages = messages
        self._authenticator = authenticator
        self._enforce_auth = enforce_auth
        if authenticator is not None and self._enforce_auth is None:
            config = Config()
            self._enforce_auth = config.SMTPD_ENFORCE_AUTH

    def _is_authmechanism(self, method):
        if getattr(method, '__auth_method__', None) is None:
            return False
        return True

    def _get_authmechanisms(self, server, session):
        mechanisms = []
        encrypted = session.ssl is not None
        for name in [n for n in dir(self) if n.startswith('auth_')]:
            method = getattr(self, name, None)
            if self._is_authmechanism(method):
                if method.__requires_encryption__ and encrypted is False:
                    continue
                mechanisms.append(method.__auth_method__)
        return mechanisms

    async def _get_response(self, server, message):
        await server.push(message)
        response = await server._reader.readline()
        return response.rstrip()

    @authmechanism("CRAM-MD5", requires_encryption=False)
    async def auth_CRAM_MD5(self, server, session, envelope, arg):
        log.debug("AUTH CRAM-MD5 received")

        # Generate challenge
        secret = secrets.token_hex(8)
        ts = datetime.now().timestamp()
        hostname = server.hostname
        challenge = f"<{secret}{ts}@{hostname}>"
        challenge_b64 = _base64_encode(challenge)

        # Send and get response
        response = await self._get_response(server, "334 " + challenge_b64)
        response = base64.decodebytes(response)
        if len(response.split()) < 2:
            return AUTH_FAILED
        user, received = response.split()
        password = self._authenticator.get_password(user)

        # Verify
        mac = hmac.HMAC(password.encode('ascii'),
                        challenge.encode('ascii'),
                        'md5')
        expected = mac.hexdigest().encode('ascii')
        if hmac.compare_digest(expected, received):
            session.authenticated = True
            return AUTH_SUCCEEDED
        return AUTH_FAILED

    @authmechanism("LOGIN", requires_encryption=True)
    async def auth_LOGIN(self, server, session, envelope, arg):
        log.info("AUTH LOGIN received")

        args, login = arg.split(), []
        for n in range(1, len(args)):
            login.extend(_base64_decode(args[n]).split(maxsplit=1))

        while len(login) < 2:
            prompt = _base64_encode('Password') if len(login) >= 1 else ""
            response = await self._get_response(server, "334 " + prompt)
            if response.startswith(b'*'):
                log.info(("Client cancelled authentication "
                          "process by sending *"))
                return AUTH_CANCELLED
            response = _base64_decode(response)
            login.extend(response.split(maxsplit=1 - len(login)))

        username = login[0]
        password = login[1]

        if self._authenticator.validate(username, password):
            session.authenticated = True
            log.info(f'AUTH LOGIN for {username} succeeded.')
            return AUTH_SUCCEEDED
        log.info(f'AUTH LOGIN for {username} failed.')
        return AUTH_FAILED

    @authmechanism("PLAIN", requires_encryption=True)
    async def auth_PLAIN(self, server, session, envelope, arg):
        log.debug("AUTH PLAIN received")

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
            session.authenticated = True
            return AUTH_SUCCEEDED
        return AUTH_FAILED

    def handle_message(self, message):
        self._messages.append(message)

    async def handle_VRFY(self, server, session, envelope, address):
        # no handler for VRFY exists in aiosmtpd.handlers.Message so this must
        # return a 252 status upon success.
        if self._authenticator.verify(address):
            return AUTH_VERIFIED

        return ' '.join([AUTH_UNVERIFIED, address])

    async def handle_EHLO(self, server, session, envelope, hostname):
        session.host_name = hostname
        mechanisms = self._get_authmechanisms(server=server, session=session)
        await server.push(f"250-AUTH {' '.join(mechanisms)}")
        return "250 HELP"

    async def handle_HELO(self, server, session, envelope, hostname):
        session.host_name = hostname
        mechanisms = self._get_authmechanisms(server=server, session=session)
        await server.push(f"250-AUTH {' '.join(mechanisms)}")
        return f"250 {server.hostname}"

    async def handle_AUTH(self, server, session, envelope, arg):
        if session.authenticated:
            return AUTH_ALREADY_DONE
        _args = arg.split()
        _mechanism = _args[0].replace('-', '_')
        method = getattr(self, "auth_" + _mechanism, None)
        if method is None:
            return AUTH_UNRECOGNIZED
        # session.ssl cna detect when there isn't an SSL connection, but fails
        # in cases where there is. Currently this causes fallback to CRAM_MD5
        # for authentication.
        if (method.__requires_encryption__ and session.ssl is None):
            return AUTH_ENCRYPTION_REQUIRED
        return await method(server, session, envelope, arg)
