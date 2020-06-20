import os
from collections import namedtuple
from email.message import EmailMessage
from smtplib import SMTP, SMTPAuthenticationError

import pytest

from bebleo_smtpd_fixture.handlers import _base64_encode as encode


@pytest.fixture
def msg():
    msg = EmailMessage()
    msg["Subject"] = "Foo"
    msg["Sender"] = "from.addr@example.org"
    msg["To"] = "to.addr@example.org"
    msg.set_content("foo bar")
    return msg


@pytest.fixture
def user():
    user = namedtuple("User", "username, password")
    user.username = os.getenv("SMTPD_USERNAME", "user")
    user.password = os.getenv("SMTPD_PASSWORD", "password")
    return user


def test_init(smtpd):
    host = os.getenv("SMTPD_HOST", "127.0.0.1")
    port = int(os.getenv("SMTPD_PORT", "8025"))
    assert smtpd.hostname == host
    assert smtpd.port == port


def test_init_ssl(mock_smtpd_use_ssl, smtpd):
    assert bool(os.getenv("SMTPD_USE_SSL", "False")) is True
    assert smtpd.ssl_context is not None


def test_init_starttls(mock_smtpd_use_starttls, smtpd):
    assert bool(os.getenv("SMTPD_USE_STARTTLS", "False")) is True
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.starttls()

    assert smtpd.tls_context is not None


def test_HELO(smtpd):
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.helo()
        helo = client.helo_resp
        assert helo.startswith(b'AUTH\n')


def test_AUTH_unknown_mechanism(mock_smtpd_use_starttls, smtpd):
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.starttls()
        code, response = client.docmd('AUTH', args='FAKEMECH')
        assert code == 504


def test_alt_port(mock_smtpd_port, smtpd):
    assert smtpd.port == 5025


def test_init_login(mock_smtpd_use_starttls, smtpd, user):
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.starttls()
        assert client.login(user.username, user.password)


def test_init_login_fail(mock_smtpd_use_starttls, smtpd, user):
    with pytest.raises(SMTPAuthenticationError) as ex:
        with SMTP(smtpd.hostname, smtpd.port) as client:
            client.starttls()
            assert client.login(user.username, user.password[:0:-1])

    assert ex.type is SMTPAuthenticationError


def test_no_messages(smtpd):
    assert len(smtpd.messages) == 0


def test_send_message(smtpd, msg):
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.send_message(msg)

    assert len(smtpd.messages) == 1


def test_send_message_logged_in(mock_smtpd_use_starttls, smtpd, user, msg):
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.starttls()
        client.login(user.username, user.password)
        client.send_message(msg)

    assert len(smtpd.messages) == 1


def test_sendmail(smtpd):
    from_addr = "from.addr@example.org"
    to_addr = "to.addr@example.org"
    msg = f"From: {from_addr}\r\nTo: {to_addr}\r\nSubject: Foo\r\n\r\nFoo bar"

    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.sendmail(from_addr, to_addr, msg)

    assert len(smtpd.messages) == 1
