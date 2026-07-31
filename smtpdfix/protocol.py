# Copyright (c) 2026 James Warne (bebleo).
# Licensed under the MIT License. See LICENSE file in the project root
# for full license information.

import ssl
from asyncio import (AbstractEventLoop, CancelledError, Event, Protocol, Queue,
                     Task, TimeoutError, Transport, create_task,
                     get_event_loop, sleep, wait_for)
# from collections.abc import Awaitable, Callable
from email.message import EmailMessage
from enum import Enum, auto

from .log import log

# Type aliases for clarity
# RespCallback = Callable[[str], Awaitable[None]]

# Constants
BUFFERSIZE = 8192  # Default buffer size for incoming data
# Maximum number of recipients allowed per message. This is set to 300,
# which is greater than or equal to 100, as recommended by RFC 5321 section
# 4.5.3.1.8.
RCPTLIMIT = 300
MAXSIZE = 300 * 1024 * 1024  # Maximum size of the email payload (300 MB)


class AsyncTransport(Transport):
    """A custom transport class that extends asyncio's Transport to provide
    additional functionality or customization for the SMTP protocol.
    """
    def __init__(self, transport: Transport) -> None:
        super().__init__()
        self._transport = transport

    async def close(self) -> None:
        """Close the transport connection and wait for it to be fully
        closed.
        """
        if self._transport is not None:
            self._transport.close()
            await self._transport.wait_closed()

    def __getattr__(self, name: str):
        """Delegate attribute access to the underlying transport."""
        return getattr(self._transport, name)


class SMTPD_State(Enum):
    """Enum representing the state of the SMTPD protocol."""
    COMMAND = auto()  # Ready for a command from the client
    DATA = auto()     # Receiving data following a DATA command
    AUTH = auto()     # In the process of authenticating the client


class SMTPD_ProtocolError(Exception):
    """Custom exception for SMTPD protocol errors."""
    pass


class MaxSizeExceededError(SMTPD_ProtocolError):
    """Exception raised when the maximum allowed message size is exceeded."""
    pass


class SMTPD_Envelope:
    """A class representing the envelope of an SMTP message, including the
    sender and recipients.

    Attributes:
        sender (str): The email address of the sender.
        rcpts (list[str]): A list of recipient email addresses.
    """
    def __init__(self, sender: str, rcpts: list[str] | None = None) -> None:
        if sender is None:
            raise ValueError("Sender email address cannot be None")

        self.sender: str = sender
        self.rcpts: list[str] = []
        self.payload: bytearray = bytearray()  # Initialize an empty payload

        if rcpts is not None:
            self.add_recipients(rcpts)

    def add_recipients(self, rcpts: list[str] | str) -> None:
        """Add recipients to the envelope.

        Args:
            rcpts (list[str] | str): A list of recipient email addresses or
            a single recipient.
        """
        # If a string is provided, convert it to a list for uniform processing
        _rcpts = []
        if isinstance(rcpts, str):
            _rcpts.extend([r.strip() for r in rcpts.split(',') if r.strip()])
        else:
            _rcpts.extend(rcpts)

        if len(self.rcpts) + len(_rcpts) > RCPTLIMIT:
            log.debug("Recipient limit exceeded: current count %d, incoming "
                      "count %d, maximum allowed count %d",
                      len(self.rcpts),
                      len(rcpts),
                      RCPTLIMIT)
            raise SMTPD_ProtocolError("Too many recipients")

        self.rcpts.extend(_rcpts)

    def append_payload(self, data: bytes) -> None:
        """Append data to the payload of the envelope.

        Args:
            data (bytes): The data to append to the payload.
        """
        if len(self.payload) + len(data) > MAXSIZE:
            log.debug("Payload size exceeded: current size %d, incoming data "
                      "size %d, maximum allowed size %d",
                      len(self.payload),
                      len(data),
                      MAXSIZE)
            self.payload.clear()  # Clear the payload
            raise MaxSizeExceededError(f"Message payload exceeds maximum "
                                       f"allowed size of {MAXSIZE} bytes")

        # Append the data to the payload
        self.payload.extend(data)


class SMTPD_Protocol:
    """A class representing the SMTPD protocol, which handles the state and
    behavior of an SMTP server connection.

    Attributes:
        transport (AsyncTransport | None): The transport layer for sending and
            receiving data.
        hostname (str | None): The hostname of the server.
        _timeout (float | None): The timeout value for the connection in
            seconds.
        _loop (AbstractEventLoop): The event loop for asynchronous operations.
        _tls_context (ssl.SSLContext | None): The SSL context for TLS
            connections.
        _smtpd_state (SMTPD_State): The current state of the SMTPD protocol.
        _cancellation_token (Event): An event used to signal when the protocol
            should shut down.
        _timer (Task | None): A task for managing timeouts.
        _envelope (SMTPD_Envelope | None): The current email envelope being
            processed.
        _messages (list[EmailMessage]): A list of received email messages.
    """
    transport: AsyncTransport | None
    hostname: str | None
    _timeout: float | None
    _loop: AbstractEventLoop
    _tls_context: ssl.SSLContext | None
    _smtpd_state: SMTPD_State
    _cancellation_token: Event
    _timer: Task | None
    _envelope: SMTPD_Envelope | None
    _messages: list[EmailMessage]
    _peername: str | None


class SMTPD_CommandsMixin:
    """A mixin class that provides methods for handling SMTP commands. This
    class is intended to be used with the SMTPD_ProtocolServer class to handle
    specific SMTP commands such as HELO, MAIL, RCPT, DATA, and QUIT.
    """
    async def smtp_HELO(self: SMTPD_Protocol, arg: str | None) -> None:
        log.debug(f"Received HELO command from {self._peername}")
        if arg is None:
            return await self.write("501 Syntax: HELO hostname")
        await self.write(f"250 Hello {arg}, pleased to meet you")

    async def smtp_EHLO(self: SMTPD_Protocol, arg: str | None) -> None:
        log.debug(f"Received EHLO command from {self._peername}")
        if arg is None:
            return await self.write("501 Syntax: EHLO hostname")

        _queue: Queue[str] = Queue()
        await _queue.put(f"Hello {arg}, pleased to meet you")
        await _queue.put("SIZE 35882577")  # Example size limit
        await _queue.put("8BITMIME")
        await _queue.put("UTF8")
        await _queue.put("ENHANCEDSTATUSCODES")

        if self._tls_context is not None and \
                self.transport is not None and \
                self.transport.get_extra_info('sslcontext') is None:
            await _queue.put("STARTTLS")

        await _queue.put("PIPELINING")

        while not _queue.empty():
            _line = await _queue.get()
            # If there are more lines to send, use the "250-" prefix;
            # otherwise, use "250 " to signal the end of the EHLO response.
            _prefix = "250-" if not _queue.empty() else "250 "
            await self.write(f"{_prefix}{_line}")
            _queue.task_done()

    async def smtp_QUIT(self: SMTPD_Protocol, arg: str | None) -> None:
        log.debug(f"Received QUIT command from {self._peername}")
        await self.write("221 Bye")
        await self.cancellation_token.set()  # Set token to initiate shutdown

    async def smtp_NOOP(self: SMTPD_Protocol, arg: str | None) -> None:
        log.debug(f"Received NOOP command from {self._peername}")
        await self.write("250 OK")

    async def smtp_RSET(self: SMTPD_Protocol, arg: str | None) -> None:
        log.debug(f"Received RSET command from {self._peername}")
        self._envelope = None
        await self.write("250 OK")

    async def smtp_VRFY(self: SMTPD_Protocol, arg: str | None) -> None:
        """Implement the VRFY command handling logic.

        The VRFY command is used to verify if a user exists on the server.
        However, for security reasons, many servers do not implement this
        command and will respond with a generic message.
        """
        log.debug(f"Received VRFY command from {self._peername}")
        await self.write("252 Cannot VRFY user, but will accept "
                         "message and attempt delivery")

    async def smtp_MAIL(self: SMTPD_Protocol, arg: str | None) -> None:
        if arg is None or not arg.upper().startswith("FROM:"):
            log.debug(f"Received invalid MAIL command syntax "
                      f"from {self._peername}")
            return await self.write("501 Syntax: MAIL FROM:<address>")

        log.debug(f"Received valid MAIL command from {self._peername}")
        # Extract the email address from the argument
        email_address = arg[5:].strip()
        self._envelope = SMTPD_Envelope(sender=email_address)
        await self.write("250 OK")

    async def smtp_RCPT(self: SMTPD_Protocol, arg: str | None) -> None:
        """ Handles the RCPT command, which specifies a recipient for the email
        being sent. It checks for proper syntax, ensures that a MAIL
        command has been received first, and manages the list of
        recipients. If the number of recipients exceeds the defined limit
        (RCPTLIMIT), it responds with an error. Otherwise, it adds the
        recipient to the email message and acknowledges with a success
        response.

        Possible recipient formats include:
        - `RCPT TO:<address>`
        - `RCPT TO:<address1>,<address2>,...`
        - `RCPT TO:<address1>,<address2>,...,<addressN>`
        - `RCPT CC:<address>`
        - `RCPT BCC:<address>`
        - Etc.
        """
        log.debug(f"Received RCPT command from {self._peername}")
        if self._envelope is None:
            await self.write("503 Need MAIL command first")
            return

        if arg is None or not arg.upper().startswith("TO:"):
            return await self.write("501 Syntax: RCPT TO:<address>")
        # Extract the email address from the argument
        email_address = arg[3:].strip()

        try:
            await self._envelope.add_recipients(email_address)
        except SMTPD_ProtocolError as e:
            log.warning(f"Too many recipients: {str(e)}")
            await self.write("552 Too many recipients")
            return

        await self.write("250 OK")

    async def smtp_DATA(self: SMTPD_Protocol, arg: str | None) -> None:
        log.debug(f"Handling DATA command with arg: {arg}")
        if self._envelope is None:
            return await self.write("503 Need MAIL command first")
        self._smtpd_state = SMTPD_State.DATA
        await self.write("354 End data with <CR><LF>.<CR><LF>")
        # The actual message data will be received in subsequent
        # calls to data_received.

    async def smtp_STARTTLS(self: SMTPD_Protocol, arg: str | None) -> None:
        """Handles the STARTTLS command, which initiates a transition to a
        secure TLS connection.

        This method checks for unexpected arguments, verifies that TLS is
        configured, and then attempts to upgrade the connection. If the upgrade
        is successful, it updates the transport and protocol to use the new TLS
        transport. If any errors occurd during the process, it logs the error
        and raises a TLSSetupException.

        Args:
            arg (str | None): The argument provided with the STARTTLS command.
        """
        if arg:
            log.info("Unexpected argument received with STARTTLS command")
            return await self.write("501 Syntax: STARTTLS")

        if self.transport is None:
            log.warning("STARTTLS requested without active transport")
            await self.write("454 TLS not available due to temporary reason")
            return
        if self._tls_context is None:
            log.info("STARTTLS requested but TLS context is not configured")
            await self.write("454 TLS not available due to temporary reason")
            return
        if self.transport.get_extra_info('sslcontext') is not None:
            log.info("STARTTLS requested on an already TLS-secured connection")
            await self.write("503 Bad sequence of commands")
            return

        log.debug("Handling STARTTLS command")
        await self.write("220 Ready to start TLS")
        try:
            # Upgrade the existing transport to a TLS transport using the
            # provided SSL context.
            tls_transport = await self._loop.start_tls(
                self.transport,
                self,
                self._tls_context,
                server_side=True,
            )

            # Swap the transport to the new TLS transport and close the old one
            _transport = self.transport
            self.transport = AsyncTransport(tls_transport)
            # Pause reading on the old transport to ensure no more data
            # is received while we close it
            _transport.pause_reading()
            while _transport.is_reading():
                await sleep(0)
            if _transport is not None:
                await _transport.close()

            self._smtpd_state = SMTPD_State.COMMAND
            log.debug("Connection upgraded to TLS successfully")

        except Exception as exc:
            log.exception("Failed to upgrade connection to TLS", exc)
            if self.transport is not None:
                await self.transport.close()
            return

        if tls_transport is None:
            log.error("TLS upgrade failed; closing connection")
            if self.transport is not None:
                await self.transport.close()
            return

        self.transport = tls_transport
        self._smtpd_state = SMTPD_State.COMMAND
        self._envelope = None
        log.debug("Connection upgraded to TLS successfully")


class SMTPD_ProtocolServer(SMTPD_CommandsMixin, Protocol):
    """A custom asyncio protocol for handling SMTP connections. It extends
    Protocol to manage the transport layer and maintain
    connection state.

    Args:
        loop (AbstractEventLoop | None): The event loop to use for asynchronous
            operations. If None, the default event loop is used.
        timeout (float): The timeout value for the connection in seconds.

    Calls arrive in the following sequence:
    1. connection_made: Called when a connection is established. The
       transport object is provided, which can be used to send data back to
       the client.
    2. data_received: Called when data is received from the client. The
       protocol can process the data and respond accordingly.
    3. eof_received: Called when the end of the data stream is reached. This
       is typically when the client has finished sending data. The protocol
       can respond accordingly, such as sending a final response or closing
       the connection.
    4. connection_lost: Called when the connection is closed or lost. An
       exception may be provided if the connection was lost due to an error.
    """
    def __init__(self,
                 loop: AbstractEventLoop | None = None,
                 timeout: float | None = 5.0,
                 tls_context: ssl.SSLContext | None = None) -> None:
        self.transport: AsyncTransport | None = None
        self.hostname: str | None = None
        self._timeout: float | None = timeout
        self._loop: AbstractEventLoop = loop or get_event_loop()
        self._tls_context: ssl.SSLContext | None = tls_context

        self._smtpd_state: SMTPD_State = SMTPD_State.COMMAND
        self._cancellation_token: Event = Event()
        self._timer: Task | None = None

        self._envelope: SMTPD_Envelope | None = None
        self._messages: list[EmailMessage] = []

    @property
    def messages(self) -> list[EmailMessage]:
        return self._messages

    @property
    def cancellation_token(self) -> Event:
        """Returns the cancellation token event, which can be used to signal
        when the protocol should shut down.
        """
        return self._cancellation_token

    async def set_timeout(self, timeout: float | None = 5.0) -> None:
        """Start the SMTPD protocol. This method can be used to perform any
        necessary initialization or setup before the protocol begins
        handling connections.
        """
        log.debug("SMTPDProtocol started with timeout: %s",
                  self._timeout or timeout)
        # Additional startup logic can be added here if needed.
        if self._timer:
            self._timer.cancel()
            self._timer = None

        if timeout is None:
            log.debug("Timeout is disabled")
            self._timer = create_task(self._cancellation_token.wait())
            _future: Task = create_task(self.shutdown())
            self._timer.add_done_callback(_future)
            await self._timer
            return

        try:
            self._timer = create_task(
                wait_for(self._cancellation_token.wait(),
                         timeout=self._timeout or timeout))
        except TimeoutError:
            # The connection has timed out and should now be closed.
            # This will trigger the connection_lost method.
            log.info("Connection timed out after %s seconds",
                     self._timeout or timeout)
        except CancelledError:
            # We cancelled the timeout task, likely because the connection
            # was closed or received data successfully and reset
            # the timeout timer. No further action is needed.
            pass

        if self._cancellation_token.is_set():
            await self.shutdown()

    async def connection_made(self, transport: Transport) -> None:
        """Called when a connection is established. The transport object is
        provided, which can be used to send data back to the client.
        """
        # Wrap the transport in AsyncTransport for additional functionality
        self.transport = AsyncTransport(transport)
        self._peername = transport.get_extra_info('peername')[0]
        log.debug(f"Connection made with {self._peername}")

    async def data_received(self, data: bytes) -> None:
        if self.transport.is_closing():
            log.warning("Data received on a closing transport; ignoring")
            return

        await self.set_timeout()  # Reset the timeout timer on data received

        if self._smtpd_state == SMTPD_State.COMMAND:
            rcvd: str = data.decode('utf-8').strip()
            if not rcvd:
                log.debug("Received empty message, ignoring")
                return

            cmd, arg = rcvd.split(' ', 1) if ' ' in rcvd else (rcvd, None)

            log.debug(f"Received command: {cmd}")

            # Find the handler method for the received command
            # This is the same method used in the original smtpd.py to dispatch
            # commands to their handlers and was copied into aiosmtd.
            handler_name = f"smtp_{cmd.upper()}"
            handler = getattr(self, handler_name, None)
            if handler is None:
                log.info(f"Unknown command received: {cmd}")
                await self.write("500 Command not recognized")
                return

            await handler(arg)

        elif self._smtpd_state == SMTPD_State.DATA:
            # Process message data
            if data == b"\r\n.\r\n":
                self._smtpd_state = SMTPD_State.COMMAND
                # finalize the envelope and store the message
                return

            # Append data to the current email message
            if self._email is not None:
                try:
                    await self.append_payload(data)
                    log.debug(f"Appended data to email: {self._email}")
                except MaxSizeExceededError as e:
                    log.warning(str(e))
                    await self.write("552 Message size exceeds fixed "
                                     "maximum message size")
                    self._email = None
                    self._smtpd_state = SMTPD_State.COMMAND
            else:
                log.warning("Received DATA without an active email "
                            "message")
                await self.write("503 Need MAIL command first")

    async def write(self, msg: str) -> None:
        """Send a message to the client."""
        log.debug(f"Sending message to client: {msg}")
        if self.transport is not None:
            self.transport.write((msg + "\r\n").encode('ascii'))
        else:
            log.warning("No connected write socket, cannot send message.")

    async def shutdown(self) -> None:
        """Shut down the protocol, closing the transport and cleaning up."""
        log.debug("Shutting down SMTPD protocol")

        if self.transport is not None:
            self.transport.write(b"221 Bye\r\n")
            await self.transport.close()

        if self._timer:
            self._timer.cancel()

        log.debug("SMTPD protocol shutdown complete")

    async def eof_received(self) -> None:
        # Called when the end of the data stream is reached. This is typically
        # when the client has finished sending data. The protocol can respond
        # accordingly, such as sending a final response or closing the
        # connection.
        log.debug("EOF received")

        if self._smtpd_state == SMTPD_State.DATA:
            # If we were in the middle of receiving data, abort the message
            log.warning("EOF received while in DATA state; aborting message")

            await self.write("250 OK")
        await self.shutdown()

    async def connection_lost(self, exc: Exception | None) -> None:
        if exc:
            log.debug(f"Connection lost with exception: {exc}")
        else:
            log.debug("Connection closed")

        await self.shutdown()
