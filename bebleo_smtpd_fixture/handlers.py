import base64
import logging

from aiosmtpd.handlers import Message

log = logging.getLogger('mail.log')

AUTH_FAILED = "530 Authentication failed."
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


def authmechanism(text, requires_tls=False):
    def decorator(f):
        f.__auth_method__ = text
        # Requires TLS included for future development
        f.__requires_tls__ = requires_tls  # pragma: no coverage
        return f
    return decorator


class AuthMessage(Message):
    def __init__(self, messages, authenticator=None):
        super().__init__()
        self._messages = messages
        self._authenticated = False
        self._authenticator = authenticator

    def _is_authmechanism(self, method):
        if getattr(method, '__auth_method__', None) is None:
            return False
        return True

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

        if self._authenticator.validate(login[0], login[1]):
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
