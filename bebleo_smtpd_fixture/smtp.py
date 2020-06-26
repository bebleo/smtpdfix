import logging

from aiosmtpd.smtp import MISSING, SMTP, syntax

log = logging.getLogger('mail.log')


class AuthSMTP(SMTP):
    @syntax('AUTH [args]')
    async def smtp_AUTH(self, arg):
        log.debug("===> AUTH command received.")
        if self.require_starttls and not self._tls_protocol:
            await self.push('530 Must issue a STARTTLS command first')
            return
        # if not (self.session.ssl or self._tls_protocol):
        #     await self.push('538 5.7.11 Encrytion required for login')
        #     return

        status = await self._call_handler_hook("AUTH", arg)
        if status is MISSING:
            status = "235 2.7.0 Authentication successful"
        await self.push(status)
