import pytest
from os import getenv
from smtplib import SMTP
from bebleo_smtpd_fixture import smtpd  # noqa: F401


@pytest.fixture
def mock_smtpd_port(monkeypatch):
    monkeypatch.setenv("SMTPD_PORT", "5025")


@pytest.fixture
def client(request):
    host = getenv("SMTPD_HOST", "127.0.0.1")
    port = int(getenv("SMTPD_PORT", "8025"))
    smtp = SMTP(host=host, port=port)
    request.addfinalizer(smtp.close)
    return smtp
