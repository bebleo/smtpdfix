import logging
import os
import ssl
import sys
from pathlib import Path
from smtplib import SMTP, SMTP_SSL, SMTPSenderRefused, SMTPServerDisconnected

import pytest

from smtpdfix.certs import _generate_certs
from smtpdfix.configuration import Config
from smtpdfix.controller import AuthController
from smtpdfix.fixture import _Authenticator

log = logging.getLogger(__name__)
pytestmark = pytest.mark.asyncio


async def test_missing_auth_handler(smtpd):
    smtpd.config.auth_require_tls = False
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.helo()
        code, resp = client.docmd("AUTH", "PSEUDOMECH")
        assert code != 235  # This should be 504


async def test_use_starttls(smtpd, msg):
    smtpd.config.use_starttls = True
    with SMTP(smtpd.hostname, smtpd.port) as client:
        with pytest.raises(SMTPSenderRefused) as error:
            code, resp = client.send_message(msg)

    assert error.type == SMTPSenderRefused


async def test_custom_ssl_context(request, tmp_path_factory, msg):
    path = tmp_path_factory.mktemp("certs")
    _generate_certs(path, separate_key=True)

    cert_path = path.joinpath("cert.pem").resolve()
    key_path = path.joinpath("key.pem").resolve()

    _context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    _context.load_cert_chain(str(cert_path), str(key_path))

    server = AuthController(ssl_context=_context)
    request.addfinalizer(server.stop)
    server.config.use_starttls = True
    server.start()

    with SMTP(server.hostname, server.port) as client:
        client.starttls()
        client.send_message(msg)

    assert len(server.messages) == 1


async def test_missing_certs(request, msg):
    with pytest.raises(FileNotFoundError) as error:
        _config = Config()
        _config.use_starttls = True
        _config.ssl_certs_path = "."
        _authenticator = _Authenticator(config=_config)
        server = AuthController(hostname=_config.host,
                                port=_config.port,
                                config=_config,
                                authenticator=_authenticator)
        request.addfinalizer(server.stop)
        server.start()

        with SMTP(server.hostname, server.port) as client:
            client.send_message(msg)

    assert error.type == FileNotFoundError


async def test_custom_cert_and_key(request, tmp_path_factory, msg):
    path = tmp_path_factory.mktemp("certs")
    _generate_certs(path, separate_key=True)
    _config = Config()
    _config.use_ssl = True
    _config.ssl_cert_files = (path.joinpath("cert.pem"),
                              path.joinpath("key.pem"))

    server = AuthController(config=_config)
    request.addfinalizer(server.stop)
    server.start()

    with SMTP_SSL(server.hostname, server.port) as client:
        client.send_message(msg)

    assert len(server.messages) == 1


@pytest.mark.skipif(sys.version_info < (3, 7),
                    reason="No timeout of SSL handshake possible")
async def test_TLS_not_supported(request, tmp_path_factory, msg, user):
    path = tmp_path_factory.mktemp("certs")
    _generate_certs(path)
    ssl_cert_files = str(path.joinpath("cert.pem"))
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(ssl_cert_files)

    config = Config()
    config.enforce_auth = True
    config.use_ssl = True
    server = AuthController(config=config,
                            authenticator=_Authenticator(config),
                            ssl_context=context)
    request.addfinalizer(server.stop)
    server.start()

    with pytest.raises(SMTPServerDisconnected):
        with SMTP(server.hostname, server.port) as client:
            # this should return a 523 Encryption required error
            # but instead returns an SMTPServerDisconnected Error on
            # Python 3.7 or later.
            # Python 3.6 just hangs without timing out.
            client.send_message(msg)
            assert len(server.messages) == 1


async def test_config_file(request, msg):
    _original_env = os.environ.copy()
    config_file = Path(__file__).parent.joinpath("assets/.test.env")
    _config = Config(filename=config_file, override=True)
    server = AuthController(hostname=_config.host,
                            port=_config.port,
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
