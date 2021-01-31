import logging
import os
from pathlib import Path
from smtplib import SMTP, SMTPSenderRefused

import pytest

from smtpdfix.config import Config
from smtpdfix.controller import AuthController
from smtpdfix.fixture import _Authenticator

log = logging.getLogger(__name__)
pytestmark = pytest.mark.asyncio


@pytest.fixture
async def mock_certs(monkeypatch):
    monkeypatch.setenv("SMTPD_USE_STARTTLS", "True")
    monkeypatch.setenv("SMTPD_SSL_CERTS_PATH", ".")


async def test_missing_auth_handler(monkeypatch, smtpd):
    monkeypatch.setenv("SMTPD_AUTH_REQUIRE_TLS", "False")
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.helo()
        code, resp = client.docmd("AUTH", "PSEUDOMECH")
        assert code != 235  # This should be 504


async def test_use_starttls(monkeypatch, smtpd, msg):
    monkeypatch.setenv("SMTPD_USE_STARTTLS", "True")
    with SMTP(smtpd.hostname, smtpd.port) as client:
        with pytest.raises(SMTPSenderRefused) as error:
            code, resp = client.send_message(msg)

    assert error.type == SMTPSenderRefused


async def test_missing_certs(mock_certs, request, msg):
    with pytest.raises(FileNotFoundError) as error:
        _config = Config()
        _authenticator = _Authenticator(config=_config)
        server = AuthController(hostname=_config.SMTPD_HOST,
                                port=_config.SMTPD_PORT,
                                config=_config,
                                authenticator=_authenticator)
        request.addfinalizer(server.stop)
        server.start()

        with SMTP(server.hostname, server.port) as client:
            client.send_message(msg)

    assert error.type == FileNotFoundError


async def test_config_file(request, msg):
    _original_env = os.environ.copy()
    config_file = Path(__file__).parent.joinpath("assets/.test.env")
    _config = Config(filename=config_file, override=True)
    server = AuthController(hostname=_config.SMTPD_HOST,
                            port=_config.SMTPD_PORT,
                            config=_config)
    request.addfinalizer(server.stop)
    server.start()

    with SMTP(server.hostname, server.port) as client:
        client.send_message(msg)

    assert server.port == "5025"

    os.environ.clear()
    os.environ.update(_original_env)
