import base64
import logging

from aiosmtpd.handlers import Message

log = logging.getLogger('mail.log')

AUTH_ALREADY_DONE = "530 Already authenticated."
AUTH_FAILED = "530 Authentication failed."
AUTH_REQUIRED = "530 SMTP authentication is required."
AUTH_UNRECOGNIZED = "504 Unrecognized authentication type."
AUTH_SUCCEEDED = "235 2.7.0 Authentication succeeded."


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


def authmechanism(text, requires_encryption=False):
    def decorator(f):
        f.__auth_method__ = text
        f.__requires_encryption__ = requires_encryption
        return f
    return decorator


class AuthMessage(Message):
    def __init__(self, messages, authenticator=None, enforce_auth=False):
        super().__init__()
        self._messages = messages
        self._authenticated = False
        self._authenticator = authenticator
        self._enforce_auth = enforce_auth

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

    @authmechanism("LOGIN", requires_encryption=True)
    async def auth_LOGIN(self, server, session, envelope, arg):
        log.debug("====> AUTH LOGIN received.")
        if session.ssl is None:
            return AUTH_UNRECOGNIZED

        args, login = arg.split(), []
        for n in range(1, len(args)):
            login.extend(_base64_decode(args[n]).split(maxsplit=1))

        while len(login) < 2:
            prompt = _base64_encode('Password') if len(login) >= 2 else ""
            response = await self._get_response(server, "334 " + prompt)
            response = _base64_decode(response)
            if response.startswith("*"):
                return AUTH_FAILED
            login.extend(response.split(maxsplit=1-len(login)))

        username = login[0]
        password = login[1]

        if self._authenticator.validate(username, password):
            self._authenticated = True
            return AUTH_SUCCEEDED
        return AUTH_FAILED

    @authmechanism("PLAIN", requires_encryption=True)
    async def auth_PLAIN(self, server, session, envelope, arg):
        log.error("====> AUTH PLAIN received.")
        if session.ssl is None:
            return AUTH_UNRECOGNIZED

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

    async def handle_DATA(self, server, session, envelope):
        if (self._enforce_auth is True and self._authenticated is False):
            return AUTH_REQUIRED

        return await super().handle_DATA(server, session, envelope)

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
        if self._authenticated:
            return AUTH_ALREADY_DONE
        _args = arg.split()
        _mechanism = _args[0].replace('-', '_')
        method = getattr(self, "auth_" + _mechanism, None)
        if method is None:
            return AUTH_UNRECOGNIZED
        return await method(server, session, envelope, arg)
