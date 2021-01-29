from email.message import EmailMessage

import pytest

# Because we need to test the fixture we include the plugin here, but generally
# this is not necessary and the fixture is loaded automatically.
pytest_plugins = "smtpdfix"


def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.timeout(5))


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
