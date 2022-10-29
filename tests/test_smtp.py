import asyncio
from asyncio import CancelledError, Future
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest


@pytest.fixture
def future() -> Any:
    mock_loop = MagicMock()
    f: asyncio.Future[bool] = Future(loop=mock_loop)
    f.set_result(True)
    return f


@pytest.mark.parametrize("cmd", ["DATA", "MAIL", "RCPT"])
def test_auth_first(cmd: str, smtpd: Any) -> None:
    smtpd.config.enforce_auth = True
    from smtplib import SMTP
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.ehlo()
        code, repl = client.docmd(cmd, "")
        assert code == 530
        assert repl.startswith(b"5.7.0 Authentication required")


@pytest.mark.asyncio
@patch("smtpdfix.handlers.AuthMessage")
async def test_starttls_with_arg(mock_AuthMessage: Mock, future: Any) -> None:
    from smtpdfix.smtp import _SMTP
    smtpd: _SMTP = _SMTP(mock_AuthMessage)
    with patch.object(smtpd, "push", return_value=future) as mock_push:
        await smtpd.smtp_STARTTLS("arg")
        mock_push.assert_called_with("501 Syntax: STARTTLS")


@pytest.mark.asyncio
@patch("smtpdfix.handlers.AuthMessage")
async def test_starttls_no_context(mock_AuthMessage: Mock,
                                   future: Any) -> None:
    from smtpdfix.smtp import _SMTP
    smtpd: _SMTP = _SMTP(mock_AuthMessage)
    with patch.object(smtpd, "push", return_value=future) as mock_push:
        await smtpd.smtp_STARTTLS(None)
        mock_push.assert_called_with('454 TLS not available')


@pytest.mark.asyncio
@patch("ssl.SSLContext")
@patch("smtpdfix.handlers.AuthMessage")
async def test_starttls_CancelledError(mock_AuthMessage: Mock,
                                       mock_SSLContext: Mock,
                                       future: Any) -> None:
    from smtpdfix.smtp import _SMTP

    mock_loop = Mock()
    mock_loop.start_tls.side_effect = CancelledError()
    smtpd: _SMTP = _SMTP(mock_AuthMessage,
                         tls_context=mock_SSLContext,
                         loop=mock_loop)
    with patch.object(smtpd, "push", return_value=future) as mock_push:
        with pytest.raises(CancelledError):
            await smtpd.smtp_STARTTLS(None)
        mock_push.assert_called_once_with('220 Ready to start TLS')


@pytest.mark.asyncio
@patch("ssl.SSLContext")
@patch("smtpdfix.handlers.AuthMessage")
async def test_starttls_Exception(mock_AuthMessage: Mock,
                                  mock_SSLContext: Mock,
                                  future: Any) -> None:
    from aiosmtpd.smtp import TLSSetupException

    from smtpdfix.smtp import _SMTP

    mock_loop = Mock()
    mock_loop.start_tls.side_effect = Exception()
    smtpd: _SMTP = _SMTP(mock_AuthMessage,
                         tls_context=mock_SSLContext,
                         loop=mock_loop)
    with patch.object(smtpd, "push", return_value=future) as mock_push:
        with pytest.raises(TLSSetupException):
            await smtpd.smtp_STARTTLS(None)
        mock_push.assert_called_once_with('220 Ready to start TLS')
