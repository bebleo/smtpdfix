import pytest

from bebleo_smtpd_fixture import smtpd  # noqa: F401


@pytest.fixture
def mock_smtpd_port(monkeypatch):
    monkeypatch.setenv("SMTPD_PORT", "5025")
