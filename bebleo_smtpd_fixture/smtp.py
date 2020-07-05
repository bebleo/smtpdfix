import logging

from aiosmtpd.smtp import MISSING, SMTP, syntax

log = logging.getLogger('mail.log')


class AuthSMTP(SMTP):
    @syntax('AUTH [args]')
    async def smtp_AUTH(self, arg):
        log.debug("===> AUTH command received.")
        status = await self._call_handler_hook("AUTH", arg)
        if status is MISSING:
            status = "502 Command not implemented"
        await self.push(status)
