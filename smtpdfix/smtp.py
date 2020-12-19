import logging

from aiosmtpd.smtp import MISSING, SMTP, Session, syntax

from .config import Config
from .handlers import AUTH_REQUIRED

log = logging.getLogger(__name__)


class AuthSession(Session):
    def __init__(self, loop):
        super().__init__(loop)
        self.authenticated = False


class AuthSMTP(SMTP):
    def _create_session(self):
        # Override the _create_session method to return an AuthSession object.
        return AuthSession(self.loop)

    def _set_rset_state(self):
        super()._set_rset_state()
        # Set the authenticated state on the session to be False if it exists
        if self.session:
            self.session.authenticated = False

    @syntax('AUTH <mechanism> [args]')
    async def smtp_AUTH(self, arg):
        if not self.session.host_name:
            await self.push('503 Error: send HELO first')
            return
        log.debug("===> AUTH command received.")
        status = await self._call_handler_hook("AUTH", arg)
        if status is MISSING:
            status = "502 Command not implemented"
        await self.push(status)

    async def smtp_DATA(self, arg):
        if not self.session.host_name:
            await self.push('503 Error: send HELO first')
            return
        config = Config()
        if not self.session.authenticated and config.SMTPD_ENFORCE_AUTH:
            log.debug("Successful authentication required before DATA command")
            await self.push(AUTH_REQUIRED)
            return
        return await super().smtp_DATA(arg)

    async def smtp_MAIL(self, arg):
        if not self.session.host_name:
            await self.push('503 Error: send HELO first')
            return
        config = Config()
        if not self.session.authenticated and config.SMTPD_ENFORCE_AUTH:
            log.debug("Successful authentication required before MAIL command")
            await self.push(AUTH_REQUIRED)
            return
        return await super().smtp_MAIL(arg)

    async def smtp_RCPT(self, arg):
        if not self.session.host_name:
            await self.push('503 Error: send HELO first')
            return
        config = Config()
        if not self.session.authenticated and config.SMTPD_ENFORCE_AUTH:
            log.debug("Successful authentication required before RCPT command")
            await self.push(AUTH_REQUIRED)
            return
        return await super().smtp_RCPT(arg)
