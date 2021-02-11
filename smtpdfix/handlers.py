import base64
import hmac
import logging
import secrets
from datetime import datetime

from aiosmtpd.handlers import Message
from aiosmtpd.smtp import MISSING, AuthResult, auth_mechanism

from .config import Config

log = logging.getLogger(__name__)

AUTH_CANCELLED = "501 Syntax error in parameters or arguments"
AUTH_VERIFIED = ("252 Cannot VRFY user, but will accept message "
                 "and attempt delivery")
AUTH_UNVERIFIED = "502 Could not VRFY"


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


class AuthMessage(Message):
    def __init__(self, messages, authenticator=None, enforce_auth=None):
        super().__init__()
        self._messages = messages
        self._authenticator = authenticator
        self._enforce_auth = enforce_auth
        if authenticator is not None and self._enforce_auth is None:
            config = Config()
            self._enforce_auth = config.SMTPD_ENFORCE_AUTH

    async def _get_response(self, server, message):
        await server.push(message)
        response = await server._reader.readline()
        return response.rstrip()

    @auth_mechanism("CRAM-MD5")
    async def auth_CRAM_MD5(self, server, arg):
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
            return MISSING
        user, received = response.split()
        password = self._authenticator.get_password(user)

        # Verify
        mac = hmac.HMAC(password.encode('ascii'),
                        challenge.encode('ascii'),
                        'md5')
        expected = mac.hexdigest().encode('ascii')
        if hmac.compare_digest(expected, received):
            log.debug("CRAM MD5 successful")
            return AuthResult(success=True, handled=True, auth_data=user)
        log.debug("CRAM MD5 unsuccessful, returning false")
        return MISSING

    async def auth_LOGIN(self, server, args):
        log.info("AUTH LOGIN received")

        login = []
        for n in range(1, len(args)):
            login.extend(_base64_decode(args[n]).split(maxsplit=1))

        while len(login) < 2:
            prompt = _base64_encode('Password') if len(login) >= 1 else ""
            response = await self._get_response(server, "334 " + prompt)
            if response.startswith(b'*'):
                log.info(("Client cancelled authentication "
                          "process by sending *"))
                await server.push(AUTH_CANCELLED)
                return
            response = _base64_decode(response)
            login.extend(response.split(maxsplit=1 - len(login)))

        username = login[0]
        password = login[1]

        if self._authenticator.validate(username, password):
            log.info(f'AUTH LOGIN for {username} succeeded.')
            return AuthResult(success=True, handled=True, auth_data=username)
        log.info(f'AUTH LOGIN for {username} failed.')
        return MISSING

    async def auth_PLAIN(self, server, args):
        log.debug("AUTH PLAIN received")

        response = args[1] if len(args) >= 2 else None
        if response is None:
            response = await self._get_response(server, "334 ")
        response = _base64_decode(response).rstrip()
        response = response.split()
        if len(response) < 2:
            return MISSING
        if (
            len(response) >= 2 and
            self._authenticator.validate(response[0], response[-1])
        ):
            return AuthResult(success=True, handled=True)
        return MISSING

    def handle_message(self, message):
        self._messages.append(message)

    async def handle_VRFY(self, server, session, envelope, address):
        # no handler for VRFY exists in aiosmtpd.handlers.Message so this must
        # return a 252 status upon success.
        if self._authenticator.verify(address):
            return AUTH_VERIFIED

        return ' '.join([AUTH_UNVERIFIED, address])
