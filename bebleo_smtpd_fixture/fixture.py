import asyncore
import time
from collections import namedtuple
from smtpd import SMTPServer
from threading import Thread
from os import getenv

import pytest

RecordedMessage = namedtuple(
    'RecordedMessage',
    'peer, mailfrom, rcpttos, data, mail_options, rcpt_options'
)


class _SMTPServer(SMTPServer):
    def __init__(self, host, messages):
        super().__init__(host, None)
        self._messages = messages

    def process_message(
        self, peer, mailfrom, rcpttos, data, mail_options, rcpt_options
    ):
        msg = RecordedMessage(
            peer, mailfrom, rcpttos, data, mail_options, rcpt_options
        )
        self._messages.append(msg)


class SMTPServerThread(Thread):
    def __init__(self, messages):
        super().__init__()
        self.messages = messages
        self.host_port = None

    def run(self):
        host = getenv("SMTPD_HOST", "127.0.0.1")
        port = int(getenv("SMTPD_PORT", "8025"))

        self.smtp = _SMTPServer((host, port), self.messages)
        self.host_port = self.smtp.socket.getsockname()
        asyncore.loop(timeout=0.1)

    def close(self):
        self.smtp.close()


class SMTPFixture():
    def __init__(self):
        self._messages = []
        self._thread = SMTPServerThread(self._messages)
        self._thread.start()

    @property
    def host_port(self):
        while self._thread.host_port is None:
            time.sleep(0.1)
        return self._thread.host_port

    @property
    def host(self):
        return self.host_port[0]

    @property
    def port(self):
        return self.host_port[1]

    @property
    def messages(self):
        return self._messages.copy()

    def close(self):
        self._thread.close()
        self._thread.join(timeout=5)
        if self._thread.is_alive():  # pragma: no coverage
            raise RuntimeError("Server has not shut down after 5 seconds")


@pytest.fixture
def smtpd(request):
    fixture = SMTPFixture()
    request.addfinalizer(fixture.close)
    return fixture
