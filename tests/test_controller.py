import logging
import os
import ssl
from pathlib import Path
from smtplib import SMTP, SMTPSenderRefused

import pytest

from smtpdfix.certs import generate_certs
from smtpdfix.configuration import Config
from smtpdfix.controller import AuthController
from smtpdfix.fixture import _Authenticator

log = logging.getLogger(__name__)
pytestmark = pytest.mark.asyncio


async def test_missing_auth_handler(smtpd):
    smtpd.config.SMTPD_AUTH_REQUIRE_TLS = False
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.helo()
        code, resp = client.docmd("AUTH", "PSEUDOMECH")
        assert code != 235  # This should be 504


async def test_use_starttls(smtpd, msg):
    smtpd.config.SMTPD_USE_STARTTLS = True
    with SMTP(smtpd.hostname, smtpd.port) as client:
        with pytest.raises(SMTPSenderRefused) as error:
            code, resp = client.send_message(msg)

    assert error.type == SMTPSenderRefused


async def test_custom_ssl_context(request, tmp_path_factory, msg):
    if os.getenv("SMTPD_SSL_CERTS_PATH") is None:
        path = tmp_path_factory.mktemp("certs")
        generate_certs(path)
        os.environ["SMTPD_SSL_CERTS_PATH"] = str(path.resolve())

    _config = Config()
    certs_path = Path(_config.SMTPD_SSL_CERTS_PATH).resolve()
    cert_path = certs_path.joinpath("cert.pem").resolve()
    key_path = certs_path.joinpath("key.pem").resolve()

    _context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    _context.load_cert_chain(str(cert_path), str(key_path))

    server = AuthController(hostname=_config.SMTPD_HOST,
                            port=_config.SMTPD_PORT,
                            config=_config,
                            ssl_context=_context)
    request.addfinalizer(server.stop)
    server.config.SMTPD_USE_STARTTLS = True
    server.start()

    with SMTP(server.hostname, server.port) as client:
        client.starttls()
        client.send_message(msg)

    assert len(server.messages) == 1


async def test_missing_certs(request, msg):
    with pytest.raises(FileNotFoundError) as error:
        _config = Config()
        _config.SMTPD_USE_STARTTLS = True
        _config.SMTPD_SSL_CERTS_PATH = "."
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

    assert server.port == 5025

    os.environ.clear()
    os.environ.update(_original_env)


async def test_exception_handler(request, msg):
    def raise_error():
        raise Exception("Deliberately raised error.")

    server = AuthController()
    request.addfinalizer(server.stop)
    server.start()

    with pytest.raises(Exception):
        with SMTP(server.hostname, server.port) as client:
            client.ehlo()
            server.loop.call_soon_threadsafe(raise_error)
            client.send_message(msg)

        assert len(server.messages) == 1
