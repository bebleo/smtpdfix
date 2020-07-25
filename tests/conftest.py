from email.message import EmailMessage

import pytest

from bebleo_smtpd_fixture import smtpd  # noqa: F401


@pytest.fixture
def mock_smtpd_port(monkeypatch):
    monkeypatch.setenv("SMTPD_PORT", "5025")


@pytest.fixture
def mock_smtpd_use_starttls(monkeypatch):
    monkeypatch.setenv("SMTPD_USE_STARTTLS", "True")


@pytest.fixture
def mock_smtpd_use_ssl(monkeypatch):
    monkeypatch.setenv("SMTPD_USE_SSL", "True")


@pytest.fixture
def msg():
    msg = EmailMessage()
    msg["Subject"] = "Foo"
    msg["Sender"] = "from.addr@example.org"
    msg["To"] = "to.addr@example.org"
    msg.set_content("foo bar")
    return msg
