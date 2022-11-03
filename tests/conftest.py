import os
from email.message import EmailMessage
from typing import List, NamedTuple

import pytest

# Because we need to test the fixture we include the plugin here, but generally
# this is not necessary and the fixture is loaded automatically.
pytest_plugins = ["smtpdfix", "pytester"]


class User(NamedTuple):
    username: str
    password: str


def pytest_collection_modifyitems(items: List[pytest.Item]) -> None:
    # Mark each test as timing out after 10 seconds to prevent the server
    # hanging on errors. Note that this can lead to the entire test run
    # failing.
    timeout_secs = 10
    for item in items:
        if item.get_closest_marker("timeout") is None:
            item.add_marker(pytest.mark.timeout(timeout_secs))


@pytest.fixture
def msg() -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = "Foo"
    msg["Sender"] = "from.addr@example.org"
    msg["To"] = "to.addr@example.org"
    msg.set_content("foo bar")
    return msg


@pytest.fixture
def user() -> User:
    username = os.getenv("SMTPD_USERNAME", "user")
    password = os.getenv("SMTPD_PASSWORD", "password")
    return User(username, password)
