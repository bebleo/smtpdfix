import os

import pytest

from bebleo_smtpd_fixture import AuthController


def test_bad_certs_path(monkeypatch):
    monkeypatch.setenv("SMTPD_USE_SSL", "True")
    monkeypatch.setenv("SMTPD_CERTS_PATH", "")

    with pytest.raises(FileNotFoundError):
        hostname = os.getenv("SMTPD_HOST", "127.0.0.1")
        port = os.getenv("SMPTD_PORT", "8025")
        with AuthController(hostname, port) as controller:
            assert controller.ssl_context is None
