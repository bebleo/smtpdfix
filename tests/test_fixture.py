import time
from os import getenv

from bebleo_smtpd_fixture import SMTPServerThread


def test_connect():
    messages = []
    thread = SMTPServerThread(messages)
    thread.start()
    elapsed_count = 0
    while thread.host_port is None and elapsed_count < 10:
        time.sleep(0.1)
        elapsed_count += 1
    assert thread.host_port[0] == getenv("SMTPD_HOST", "127.0.0.1")
    assert thread.host_port[1] == int(getenv("SMTPD_PORT", "8025"))
    assert len(thread.messages) == 0
    thread.close()
