import asyncio
import logging
import socket
from ssl import SSLContext
from typing import Any, cast

log = logging.getLogger(__name__)


class TLSSetupException(Exception):
    """Raised when upgrading an SMTP connection to TLS fails."""


class _SMTP:
    """Small SMTP session helper focused on STARTTLS handling."""

    def __init__(
        self,
        handler: Any,
        *args: Any,
        hostname: str | None = None,
        tls_context: SSLContext | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
        transport: asyncio.BaseTransport | None = None,
        protocol: asyncio.BaseProtocol | None = None,
        reader: Any = None,
        writer: Any = None,
        **kwargs: Any,
    ) -> None:
        del args, kwargs, handler
        self.hostname = hostname or socket.gethostname()
        self.tls_context = tls_context
        self.loop = loop or asyncio.get_event_loop()
        self.transport = transport
        self.protocol = protocol
        self._reader = reader
        self._writer = writer

    async def push(self, status: str) -> None:
        if self._writer is None:
            return
        self._writer.write(f"{status}\r\n".encode("ascii"))
        await self._writer.drain()

    async def smtp_STARTTLS(
        self, arg: str | None
    ) -> asyncio.Transport | None:
        """Process the STARTTLS command and upgrade the client transport."""
        if arg:
            log.info("Unexpected argument received with STARTTLS command")
            await self.push("501 Syntax: STARTTLS")
            return cast(asyncio.Transport | None, self.transport)
        if not self.tls_context:
            log.info("STARTTLS received but TLS not configured")
            await self.push("454 TLS not available")
            return cast(asyncio.Transport | None, self.transport)

        await self.push("220 Ready to start TLS")
        if self.transport is None or self.protocol is None:
            raise TLSSetupException()

        try:
            new_transport = await self.loop.start_tls(
                transport=self.transport,
                protocol=self.protocol,
                sslcontext=self.tls_context,
                server_side=True,
                ssl_handshake_timeout=5.0,
            )
            if new_transport is None:
                raise TLSSetupException()
            self.transport = new_transport

            # Streams currently expose transport via private attributes.
            if (
                self._reader is not None
                and hasattr(self._reader, "_transport")
            ):
                self._reader._transport = new_transport
            if (
                self._writer is not None
                and hasattr(self._writer, "_transport")
            ):
                self._writer._transport = new_transport
            return new_transport
        except asyncio.CancelledError:
            raise
        except Exception as error:
            raise TLSSetupException() from error
