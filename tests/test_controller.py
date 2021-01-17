import logging
import os
from pathlib import Path
from smtplib import SMTP, SMTPSenderRefused

import pytest
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Sink

from smtpdfix.config import Config
from smtpdfix.controller import AuthController
from smtpdfix.fixture import _Authenticator
from smtpdfix.smtp import AuthSMTP

log = logging.getLogger(__name__)
pytestmark = pytest.mark.asyncio


@pytest.fixture
async def no_auth(request):
    class PseudoController(Controller):
        def factory(self):
            return AuthSMTP(self.handler)

    controller = PseudoController(Sink(), hostname="127.0.0.1", port="8025")
    request.addfinalizer(controller.stop)
    controller.start()
    return controller


@pytest.fixture
async def mock_certs(monkeypatch):
    monkeypatch.setenv("SMTPD_USE_STARTTLS", "True")
    monkeypatch.setenv("SMTPD_SSL_CERTS_PATH", ".")


async def test_missing_auth_handler(no_auth):
    with SMTP(no_auth.hostname, no_auth.port) as client:
        client.helo()
        code, resp = client.docmd("AUTH", "PSEUDOMECH")
        assert code == 502


async def test_use_starttls(mock_smtpd_use_starttls, smtpd, msg):
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
