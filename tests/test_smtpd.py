from email.message import EmailMessage
from os import getenv

import pytest  # noqa: F401
from smtplib import SMTP


def test_init(smtpd):
    host = getenv("SMTPD_HOST", "127.0.0.1")
    port = int(getenv("SMTPD_PORT", "8025"))
    assert smtpd.hostname == host
    assert smtpd.port == port


def test_alt_port(mock_smtpd_port, smtpd):
    assert smtpd.port == 5025


def test_no_messages(smtpd):
    assert len(smtpd.messages) == 0


def test_send_message(smtpd):
    msg = EmailMessage()
    msg["Subject"] = "Foo"
    msg["Sender"] = "from.addr@example.org"
    msg["To"] = "to.addr@example.org"
    msg.set_content("foo bar")

    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.send_message(msg)

    assert len(smtpd.messages) == 1


def test_sendmail(smtpd):
    from_addr = "from.addr@example.org"
    to_addr = "to.addr@example.org"
    msg = f"From: {from_addr}\r\nTo: {to_addr}\r\nSubject: Foo\r\n\r\nFoo bar"

    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.sendmail(from_addr, to_addr, msg)

    assert len(smtpd.messages) == 1
