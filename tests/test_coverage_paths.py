import asyncio
import socket
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from smtpdfix.configuration import Config
from smtpdfix.controller import AuthController, _SMTPSession
from smtpdfix.fixture import _Authenticator
from smtpdfix.handlers import MISSING, AuthMessage
from smtpdfix.smtp import _SMTP, TLSSetupException


class _Reader:
    def __init__(self, lines: list[bytes]) -> None:
        self._lines = lines

    async def readline(self) -> bytes:
        if self._lines:
            return self._lines.pop(0)
        return b""


class _Writer:
    def __init__(self) -> None:
        self.transport = Mock()
        self._protocol = Mock()
        self.messages: list[bytes] = []

    def get_extra_info(self, key: str) -> object:
        if key == "peername":
            return ("127.0.0.1", 9999)
        return None

    def write(self, data: bytes) -> None:
        self.messages.append(data)

    async def drain(self) -> None:
        return None

    def close(self) -> None:
        return None

    async def wait_closed(self) -> None:
        return None


def _session(lines: list[bytes], auth: bool = True) -> _SMTPSession:
    config = Config()
    config.auth_require_tls = False
    config.use_starttls = False
    controller = SimpleNamespace(
        handler=AuthMessage([]),
        hostname="localhost",
        config=config,
        loop=asyncio.new_event_loop(),
        _authenticator=_Authenticator(config) if auth else None,
        _get_ssl_context=lambda: None,
    )
    return _SMTPSession(controller, _Reader(lines), _Writer())


@pytest.mark.asyncio
async def test_session_authenticator_missing() -> None:
    smtp = _session([], auth=False)
    with pytest.raises(RuntimeError):
        _ = smtp._authenticator


@pytest.mark.asyncio
async def test_session_challenge_auth_bad_base64() -> None:
    smtp = _session([b"a\r\n"])
    result = await smtp.challenge_auth("challenge")
    assert result is MISSING


@pytest.mark.asyncio
async def test_session_run_noop_and_quit() -> None:
    smtp = _session([b"\r\n", b"NOOP\r\n", b"QUIT\r\n"])
    await smtp.run()
    assert any(m.startswith(b"250 OK") for m in smtp.writer.messages)


@pytest.mark.asyncio
async def test_session_run_unknown_command() -> None:
    smtp = _session([b"WUT\r\n", b"QUIT\r\n"])
    await smtp.run()
    assert any(
        b"500 Error: command not recognized" in m for m in smtp.writer.messages
    )


@pytest.mark.asyncio
async def test_session_mail_and_rcpt_syntax_errors() -> None:
    smtp = _session([])
    await smtp._handle_mail("NOTFROM")
    await smtp._handle_rcpt("NOTTO")
    assert any(
        b"501 Syntax: MAIL FROM:<address>" in m for m in smtp.writer.messages
    )
    assert any(
        b"503 Error: need MAIL command" in m for m in smtp.writer.messages
    )


@pytest.mark.asyncio
async def test_session_rcpt_invalid_to() -> None:
    smtp = _session([])
    smtp.mail_from = "sender@example.com"
    await smtp._handle_rcpt("NOPE")
    assert any(
        b"501 Syntax: RCPT TO:<address>" in m for m in smtp.writer.messages
    )


@pytest.mark.asyncio
async def test_session_data_missing_mail_state() -> None:
    smtp = _session([])
    await smtp._handle_data()
    assert any(
        b"503 Error: need MAIL command" in m for m in smtp.writer.messages
    )


@pytest.mark.asyncio
async def test_session_data_eof_and_dot_stuffing() -> None:
    eof_smtp = _session([b""])
    eof_smtp.mail_from = "sender@example.com"
    eof_smtp.recipients = ["to@example.com"]
    await eof_smtp._handle_data()
    assert any(
        b"354 End data with <CR><LF>.<CR><LF>" in m
        for m in eof_smtp.writer.messages
    )

    data_smtp = _session([b"..body\r\n", b".\r\n"])
    data_smtp.mail_from = "sender@example.com"
    data_smtp.recipients = ["to@example.com"]
    await data_smtp._handle_data()
    assert any(m.startswith(b"250 OK") for m in data_smtp.writer.messages)


@pytest.mark.asyncio
async def test_session_starttls_error_paths() -> None:
    smtp = _session([])
    await smtp._handle_starttls("arg")
    smtp.controller.config.use_starttls = False
    await smtp._handle_starttls("")
    smtp.controller.config.use_starttls = True
    smtp._smtp.smtp_STARTTLS = AsyncMock(side_effect=TLSSetupException())
    await smtp._handle_starttls("")
    smtp._smtp.smtp_STARTTLS = AsyncMock(side_effect=asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):
        await smtp._handle_starttls("")


@pytest.mark.asyncio
async def test_session_auth_empty_arg() -> None:
    smtp = _session([])
    await smtp._handle_auth("")
    assert any(
        b"501 Syntax: AUTH mechanism [initial-response]" in m
        for m in smtp.writer.messages
    )


@pytest.mark.asyncio
async def test_handlers_uncovered_paths() -> None:
    auth = AuthMessage([])
    server = SimpleNamespace(
        hostname="localhost",
        _authenticator=SimpleNamespace(
            get_password=lambda _u: "secret",
            validate=lambda _u, _p: True,
        ),
        challenge_auth=AsyncMock(return_value=MISSING),
    )
    res = await auth.auth_CRAM_MD5(server, ["CRAM-MD5"])
    assert res.handled and not res.success

    server.challenge_auth = AsyncMock(return_value=b"singlepart")
    res = await auth.auth_CRAM_MD5(server, ["CRAM-MD5"])
    assert not res.handled and not res.success

    bad_login = "a"
    server.challenge_auth = AsyncMock(return_value=MISSING)
    res = await auth.auth_LOGIN(server, ["LOGIN", bad_login])
    assert res.handled and not res.success

    res = await auth.auth_PLAIN(server, ["PLAIN", bad_login])
    assert not res.handled and not res.success

    res = await auth.auth_PLAIN(server, ["PLAIN"])
    assert res.handled and not res.success


@pytest.mark.asyncio
async def test_smtp_uncovered_paths() -> None:
    smtp = _SMTP(Mock())
    await smtp.push("noop")

    smtp = _SMTP(Mock(), tls_context=Mock(), loop=Mock())
    with patch.object(
        smtp, "push", return_value=asyncio.Future()
    ) as mock_push:
        mock_push.return_value.set_result(True)
        with pytest.raises(TLSSetupException):
            await smtp.smtp_STARTTLS(None)

    loop = Mock()
    loop.start_tls = AsyncMock(return_value=None)
    smtp = _SMTP(Mock(), tls_context=Mock(), loop=loop)
    smtp.transport = Mock()
    smtp.protocol = Mock()
    with patch.object(
        smtp, "push", return_value=asyncio.Future()
    ) as mock_push:
        mock_push.return_value.set_result(True)
        with pytest.raises(TLSSetupException):
            await smtp.smtp_STARTTLS(None)

    loop = Mock()
    loop.start_tls = AsyncMock(return_value=Mock())
    smtp = _SMTP(Mock(), tls_context=Mock(), loop=loop)
    smtp.transport = Mock()
    smtp.protocol = Mock()
    with patch.object(
        smtp, "push", return_value=asyncio.Future()
    ) as mock_push:
        mock_push.return_value.set_result(True)
        assert await smtp.smtp_STARTTLS(None) is not None


def test_controller_init_sock_conflicts() -> None:
    with pytest.raises(ValueError):
        AuthController(sock=socket.socket(), hostname="localhost")


def test_controller_init_sock_getsockname_oserror() -> None:
    bad_sock = Mock()
    bad_sock.getsockname.side_effect = OSError()
    controller = AuthController(sock=bad_sock)
    assert controller.hostname


@pytest.mark.asyncio
async def test_controller_start_async_and_stop_async_branches() -> None:
    controller = AuthController()
    mock_server = Mock()
    mock_server.sockets = []
    with patch("asyncio.start_server", AsyncMock(return_value=mock_server)):
        await controller._start_async()

    mock_server.sockets = [Mock(getsockname=Mock(return_value="invalid"))]
    with patch("asyncio.start_server", AsyncMock(return_value=mock_server)):
        await controller._start_async()

    writer = _Writer()
    writer.wait_closed = AsyncMock(side_effect=Exception("boom"))
    controller._clients.add(writer)
    controller.server = mock_server
    mock_server.wait_closed = AsyncMock()
    await controller._stop_async()
    assert controller.server is None

    controller.server = None
    await controller._stop_async()


def test_controller_run_sets_thread_exception() -> None:
    controller = AuthController()
    controller._start_async = AsyncMock(side_effect=RuntimeError("boom"))
    ready = threading.Event()
    controller._run(ready)
    assert ready.is_set()
    assert isinstance(controller._thread_exception, RuntimeError)


def test_controller_start_and_stop_edge_paths() -> None:
    controller = AuthController()
    controller._started = True
    controller.start()

    controller = AuthController()
    with patch("smtpdfix.controller.threading.Thread") as thread_cls:
        thread = Mock()
        thread_cls.return_value = thread
        with patch(
            "smtpdfix.controller.threading.Event.wait", return_value=False
        ):
            with pytest.raises(TimeoutError):
                controller.start()

    controller = AuthController()
    controller._thread_exception = RuntimeError("thread failed")
    with patch("smtpdfix.controller.threading.Thread") as thread_cls:
        thread = Mock()
        thread_cls.return_value = thread
        with patch(
            "smtpdfix.controller.threading.Event.wait", return_value=True
        ):
            with pytest.raises(RuntimeError):
                controller.start()

    controller = AuthController()
    controller.stop(no_assert=True)
    with pytest.raises(AssertionError):
        controller.stop()

    controller = AuthController()
    controller._started = True
    controller.loop.close()
    controller.stop()
    assert not controller._started

    controller = AuthController()
    controller._started = True
    controller.thread = Mock(is_alive=Mock(return_value=False))
    controller.stop()
    assert not controller._started


def test_controller_reset_and_exception_handler_paths() -> None:
    controller = AuthController()
    controller._messages.extend(["a"])
    controller.reset(persist_messages=False)
    assert controller.messages == []

    writer = _Writer()
    writer.transport = None
    controller._clients.add(writer)
    controller.server = None
    controller._handle_exception(
        controller.loop, {"message": "ignored by default handler"}
    )


def test_controller_init_sock_name_without_port() -> None:
    odd_sock = Mock()
    odd_sock.getsockname.return_value = ("127.0.0.1",)
    controller = AuthController(sock=odd_sock)
    assert controller.port == int(controller.config.port)
