import asyncio
import logging
import socket
from ssl import SSLContext
from typing import Any, Dict, Iterable, Optional, Union

from aiosmtpd.smtp import (DATA_SIZE_DEFAULT, SMTP, AuthCallbackType,
                           AuthenticatorType, TLSSetupException, syntax)

log = logging.getLogger(__name__)


class _SMTP(SMTP):
    """Patch for the SMTP protocol from aiosmtpd."""
    def __init__(
            self,
            handler: Any,
            *args: Any,
            data_size_limit: int = DATA_SIZE_DEFAULT,
            enable_SMTPUTF8: bool = False,
            decode_data: bool = False,
            hostname: Optional[str] = None,
            ident: Optional[str] = None,
            tls_context: Optional[SSLContext] = None,
            require_starttls: bool = False,
            timeout: float = 300,
            auth_required: bool = False,
            auth_require_tls: bool = True,
            auth_exclude_mechanism: Optional[Iterable[str]] = None,
            auth_callback: Optional[AuthCallbackType] = None,
            command_call_limit: Union[int, Dict[str, int], None] = None,
            authenticator: Optional[AuthenticatorType] = None,
            proxy_protocol_timeout: Optional[Union[int, float]] = None,
            loop: Optional[asyncio.AbstractEventLoop] = None
    ):
        if hostname:  # pragma: no cover
            _hostname = hostname
        else:
            _hostname = socket.gethostname()

        super().__init__(
            handler=handler,
            *args,
            data_size_limit=data_size_limit,
            enable_SMTPUTF8=enable_SMTPUTF8,
            decode_data=decode_data,
            hostname=_hostname,
            ident=ident,
            tls_context=tls_context,
            require_starttls=require_starttls,
            timeout=timeout,
            auth_required=auth_required,
            auth_require_tls=auth_require_tls,
            auth_exclude_mechanism=auth_exclude_mechanism,
            auth_callback=auth_callback,
            command_call_limit=command_call_limit,
            authenticator=authenticator,
            proxy_protocol_timeout=proxy_protocol_timeout,
            loop=loop,
        )

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
