import asyncio
import logging

from aiosmtpd.smtp import SMTP, TLSSetupException, syntax

log = logging.getLogger(__name__)


class _SMTP(SMTP):
    """Patch for the SMTP protocol from aiosmtpd."""

    @syntax('STARTTLS', when='tls_context')
    async def smtp_STARTTLS(self, arg: str) -> None:
        """Process the STARTTLS command when received.

        Overrides the smtp_STARTTLS from aiosmtpd because that
        implementation fails on python 3.11"""
        if arg:
            log.info("Unexpected argument received with STARTTLS command")
            await self.push('501 Syntax: STARTTLS')
            return
        if not self.tls_context:
            log.info("STARTTLS received but TLS not configured")
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
            log.info("Connection upgraded to TLS after STARTTLS received")

        except asyncio.CancelledError:
            raise
        except Exception as error:
            raise TLSSetupException() from error
