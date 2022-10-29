import asyncio

from aiosmtpd.smtp import SMTP as _SMTP
from aiosmtpd.smtp import TLSSetupException, syntax


class SMTP(_SMTP):

    @syntax('STARTTLS', when='tls_context')
    async def smtp_STARTTLS(self, arg: str) -> None:
        if arg:
            await self.push('501 Syntax: STARTTLS')
            return
        if not self.tls_context:
            await self.push('454 TLS not available')
            return
        await self.push('220 Ready to start TLS')

        try:
            self._original_transport = self.transport
            new_transport = await self.loop.start_tls(
                                       transport=self.transport,
                                       protocol=self,
                                       sslcontext=self.tls_context,
                                       server_side=True,
                                       ssl_handshake_timeout=5.0)
            self._reader._transport = new_transport
            self._writer._transport = new_transport
            self._tls_protocol = new_transport.get_protocol()

        except asyncio.CancelledError:
            raise
        except Exception as error:
            raise TLSSetupException() from error
