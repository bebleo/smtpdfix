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
