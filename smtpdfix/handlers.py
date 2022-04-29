import base64
import hmac
import logging
import secrets
from datetime import datetime
from email.message import Message as EmailMessage
from typing import List

from aiosmtpd.handlers import Message
from aiosmtpd.smtp import MISSING, SMTP, AuthResult, auth_mechanism

log = logging.getLogger(__name__)


class AuthMessage(Message):
    def __init__(self, messages: List[EmailMessage]) -> None:
        super().__init__()
        self._messages = messages

    @auth_mechanism("CRAM-MD5")
    async def auth_CRAM_MD5(self, server: SMTP, args: List[str]) -> AuthResult:
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

    async def auth_LOGIN(self, server: SMTP, args: List[str]) -> AuthResult:
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

    async def auth_PLAIN(self, server: SMTP, args: List[str]) -> AuthResult:
        log.debug("AUTH PLAIN received")

        response = b""
        if len(args) >= 2:
            response = base64.b64decode(args[1])
        else:
            response = await server.challenge_auth("")
        decoded_resp = response.decode()
        split_resp: List[str] = decoded_resp.split()
        if len(split_resp) < 2:
            return AuthResult(success=False, handled=False)
        if (
            len(split_resp) >= 2
            and server._authenticator.validate(split_resp[0], split_resp[-1])
        ):
            log.debug("AUTH PLAIN succeeded")
            return AuthResult(success=True, handled=True)

        log.debug("AUTH PLAIN failed")
        return AuthResult(success=False, handled=False)

    def handle_message(self, message: EmailMessage) -> None:
        self._messages.append(message)
