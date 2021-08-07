import base64
import hmac
import logging
import secrets
from datetime import datetime

from aiosmtpd.handlers import Message
from aiosmtpd.smtp import MISSING, AuthResult, auth_mechanism

log = logging.getLogger(__name__)


class AuthMessage(Message):
    def __init__(self, messages):
        super().__init__()
        self._messages = messages

    @auth_mechanism("CRAM-MD5")
    async def auth_CRAM_MD5(self, server, args):
        log.debug("AUTH CRAM-MD5 received")

        # Generate challenge
        secret = secrets.token_hex(8)
        ts = datetime.now().timestamp()
        hostname = server.hostname
        challenge = f"<{secret}{ts}@{hostname}>"
        response = await server.challenge_auth(challenge)
        user, received = response.split()
        password = server._authenticator.get_password(user.decode())

        # Verify
        mac = hmac.HMAC(password.encode(),
                        challenge.encode(),
                        "md5")
        expected = mac.hexdigest().encode()
        if hmac.compare_digest(expected, received):
            log.debug("AUTH CARM-MD5 succeeded")
            return AuthResult(success=True, handled=True, auth_data=user)
        log.debug("AUTH CRAM-MD5 failed")
        return AuthResult(success=False, handled=False)

    async def auth_LOGIN(self, server, args):
        log.info("AUTH LOGIN received")

        login = []
        for n in range(1, len(args)):
            arg = base64.b64decode(args[n]).decode()
            login.extend(arg.split(maxsplit=1))

        while len(login) < 2:
            prompt = "Password" if len(login) >= 1 else ""
            response = await server.challenge_auth(prompt)
            if response is MISSING:
                return AuthResult(success=False, handled=True)
            response = response.decode()
            login.extend(response.split(maxsplit=1 - len(login)))

        username = login[0]
        password = login[1]

        if server._authenticator.validate(username, password):
            log.info("AUTH LOGIN succeeded.")
            return AuthResult(success=True, handled=True, auth_data=username)
        log.info("AUTH LOGIN failed.")
        return AuthResult(success=False, handled=False)

    async def auth_PLAIN(self, server, args):
        log.debug("AUTH PLAIN received")

        response = None
        if len(args) >= 2:
            response = base64.b64decode(args[1])
        else:
            response = await server.challenge_auth("")
        response = response.decode()
        response = response.split()
        if len(response) < 2:
            return AuthResult(success=False, handled=False)
        if (
            len(response) >= 2 and
            server._authenticator.validate(response[0], response[-1])
        ):
            log.debug("AUTH PLAIN succeeded")
            return AuthResult(success=True, handled=True)

        log.debug("AUTH PLAIN failed")
        return AuthResult(success=False, handled=False)

    def handle_message(self, message):
        self._messages.append(message)
