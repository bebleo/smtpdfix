from email.message import EmailMessage

import pytest

# Because we need to test the fixture we include the plugin here, but generally
# this is not necessary and the fixture is loaded automatically.
pytest_plugins = ["smtpdfix", "pytester"]


def pytest_collection_modifyitems(items):
    # Mark each test as timing out after 15 seconds to prevent the server
    # hanging on errors. Note that this can lead to the entire test run
    # failing.
    timeout_secs = 10
    for item in items:
        if item.get_closest_marker("timeout") is None:
            item.add_marker(pytest.mark.timeout(timeout_secs))


@pytest.fixture
def mock_smtpd_port(monkeypatch):
    monkeypatch.setenv("SMTPD_PORT", "5025")


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
