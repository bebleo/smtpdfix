import base64
import hmac
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime
from email.message import Message as EmailMessage
from typing import Any

log = logging.getLogger(__name__)

MISSING = object()


@dataclass
class AuthResult:
    success: bool
    handled: bool
    auth_data: str | None = None


class AuthMessage:
    def __init__(self, messages: list[EmailMessage]) -> None:
        self._messages = messages

    async def auth_CRAM_MD5(self, server: Any, args: list[str]) -> AuthResult:
        log.debug("AUTH CRAM-MD5 received")

        secret = secrets.token_hex(8)
        ts = datetime.now().timestamp()
        hostname = server.hostname
        challenge = f"<{secret}{ts}@{hostname}>"
        response = await server.challenge_auth(challenge)
        if response is MISSING:
            return AuthResult(success=False, handled=True)

        try:
            user, received = response.split()
            username = user.decode("ascii")
        except ValueError:
            return AuthResult(success=False, handled=False)

        password = server._authenticator.get_password(username)

        mac = hmac.HMAC(
            password.encode("utf-8"), challenge.encode("ascii"), "md5"
        )
        expected = mac.hexdigest().encode("ascii")
        if hmac.compare_digest(expected, received):
            log.debug("AUTH CARM-MD5 succeeded")
            return AuthResult(success=True, handled=True, auth_data=username)
        log.debug("AUTH CRAM-MD5 failed")
        return AuthResult(success=False, handled=False)

    async def auth_LOGIN(self, server: Any, args: list[str]) -> AuthResult:
        log.info("AUTH LOGIN received")

        login: list[str] = []
        for arg in args[1:]:
            try:
                decoded = base64.b64decode(arg).decode("utf-8")
            except Exception:
                continue
            login.extend(decoded.split(maxsplit=1))

        while len(login) < 2:
            prompt = "Password" if len(login) >= 1 else ""
            response = await server.challenge_auth(prompt)
            if response is MISSING:
                return AuthResult(success=False, handled=True)
            decoded = response.decode("utf-8")
            login.extend(decoded.split(maxsplit=1 - len(login)))

        username = login[0]
        password = login[1]

        if server._authenticator.validate(username, password):
            log.info("AUTH LOGIN succeeded.")
            return AuthResult(success=True, handled=True, auth_data=username)
        log.info("AUTH LOGIN failed.")
        return AuthResult(success=False, handled=False)

    async def auth_PLAIN(self, server: Any, args: list[str]) -> AuthResult:
        log.debug("AUTH PLAIN received")

        if len(args) >= 2:
            try:
                response = base64.b64decode(args[1])
            except Exception:
                return AuthResult(success=False, handled=False)
        else:
            response = await server.challenge_auth("")
            if response is MISSING:
                return AuthResult(success=False, handled=True)

        split_resp = response.decode("utf-8").split()
        if len(split_resp) < 2:
            return AuthResult(success=False, handled=False)

        if server._authenticator.validate(split_resp[0], split_resp[-1]):
            log.debug("AUTH PLAIN succeeded")
            return AuthResult(
                success=True, handled=True, auth_data=split_resp[0]
            )

        log.debug("AUTH PLAIN failed")
        return AuthResult(success=False, handled=False)

    def handle_message(self, message: EmailMessage) -> None:
        self._messages.append(message)
