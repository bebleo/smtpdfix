from os import getenv

import pytest
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Message


class MessageHandler(Message):
    def __init__(self, messages):
        super().__init__()
        self._messages = messages

    def handle_message(self, message):
        self._messages.append(message)


class _Controller(Controller):
    def __init__(self, hostname, port):
        self._messages = []
        self._handler = MessageHandler(self._messages)
        super().__init__(self._handler, hostname=hostname, port=port)

    @property
    def messages(self):
        return self._messages.copy()


@pytest.fixture
def smtpd(request):
    host = getenv("SMTPD_HOST", "127.0.0.1")
    port = int(getenv("SMTPD_PORT", "8025"))
    fixture = _Controller(hostname=host, port=port)
    request.addfinalizer(fixture.stop)
    fixture.start()
    return fixture
