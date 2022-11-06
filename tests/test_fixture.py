from base64 import b64encode
from email.message import EmailMessage
from smtplib import (SMTP, SMTP_SSL, SMTPAuthenticationError,
                     SMTPResponseException)
from unittest import mock

from pytest import MonkeyPatch, raises

from smtpdfix import Config
from smtpdfix.controller import AuthController
from smtpdfix.fixture import _Authenticator
from tests.conftest import User


def encode(message: str) -> str:
    message_bytes = message.encode()
    base64_bytes = b64encode(message_bytes)
    base64_message = base64_bytes.decode()
    return base64_message


def test_init(smtpd: AuthController) -> None:
    assert smtpd
    assert len(smtpd.messages) == 0


def test_init_ssl(smtpd: AuthController, msg: EmailMessage) -> None:
    smtpd.config.use_ssl = True
    with SMTP_SSL(smtpd.hostname, smtpd.port) as client:
        client.send_message(msg)

    assert len(smtpd.messages) == 1


def test_AUTH_unknown_mechanism(smtpd: AuthController) -> None:
    smtpd.config.use_starttls = True
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.starttls()
        client.ehlo()
        code, response = client.docmd("AUTH", args="FAKEMECH")
        assert code == 504


def test_AUTH_LOGIN_abort(smtpd: AuthController, user: User) -> None:
    smtpd.config.use_starttls = True
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.starttls()
        client.ehlo()
        code, resp = client.docmd("AUTH", f"LOGIN {encode(user.username)}")
        assert code == 334
        code, resp = client.docmd("*")
        assert code == 501


def test_AUTH_LOGIN_success(smtpd: AuthController, user: User) -> None:
    smtpd.config.use_starttls = True
    username = encode(user.username)
    password = encode(user.password)
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.starttls()
        client.ehlo()
        code, resp = client.docmd("AUTH", f"LOGIN {username}")
        assert code == 334
        assert resp == bytes(encode("Password"), "ascii")
        code, resp = client.docmd(f"{password}")
        assert code == 235


def test_AUTH_PLAIN(smtpd: AuthController, user: User) -> None:
    smtpd.config.use_starttls = True
    enc = encode(f"{user.username} {user.password}")
    cmd_text = f"PLAIN {enc}"
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.starttls()
        client.ehlo()
        (code, resp) = client.docmd("AUTH", args=cmd_text)
        assert code == 235


def test_AUTH_PLAIN_no_encryption(smtpd: AuthController, user: User) -> None:
    enc = encode(f"{user.username} {user.password}")
    cmd_text = f"PLAIN {enc}"
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.ehlo()
        (code, resp) = client.docmd("AUTH", args=cmd_text)
        assert code == 538


def test_AUTH_PLAIN_two_parts(smtpd: AuthController, user: User) -> None:
    smtpd.config.use_starttls = True
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.starttls()
        client.ehlo()
        code, resp = client.docmd("AUTH", "PLAIN")
        assert (code, resp) == (334, b"")
        enc = encode(f"{user.username} {user.password}")
        code, resp = client.docmd(enc)
        assert code == 235


def test_AUTH_PLAIN_failure(smtpd: AuthController, user: User) -> None:
    smtpd.config.use_starttls = True
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.starttls()
        client.ehlo()
        enc = encode(f"{user.username} {user.password[:0:-1]}")
        code, resp = client.docmd("AUTH", f"PLAIN {enc}")
        assert code == 535
        assert resp == b"5.7.8 Authentication credentials invalid"


def test_alt_port(smtpd: AuthController) -> None:
    smtpd.config.port = 5025
    assert smtpd.port == 5025


def test_login(smtpd: AuthController, user: User) -> None:
    smtpd.config.use_starttls = True
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.starttls()
        assert client.login(user.username, user.password)


def test_login_fail(smtpd: AuthController, user: User) -> None:
    smtpd.config.use_starttls = True
    with raises(SMTPAuthenticationError) as ex:
        with SMTP(smtpd.hostname, smtpd.port) as client:
            client.starttls()
            client.login(user.username, user.password[:0:-1])

    assert ex.type is SMTPAuthenticationError


def test_login_no_tls(smtpd: AuthController, user: User) -> None:
    smtpd.config.auth_require_tls = False
    with SMTP(smtpd.hostname, smtpd.port) as client:
        assert client.login(user.username, user.password)


def test_login_already_done(smtpd: AuthController, user: User) -> None:
    smtpd.config.enforce_auth = True
    smtpd.config.use_starttls = True
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.starttls()
        client.login(user.username, user.password)
        # we need to explicitly get the response from the the second AUTH
        # command because smtplib doesn't treat it as an error.
        code, resp = client.docmd("AUTH", "LOGIN")
        assert code == 503
        assert resp == b"Already authenticated"


def test_no_messages(smtpd: AuthController) -> None:
    assert len(smtpd.messages) == 0


def test_send_message(smtpd: AuthController, msg: EmailMessage) -> None:
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.send_message(msg)

    assert len(smtpd.messages) == 1


def test_send_message_logged_in(smtpd: AuthController,
                                user: User,
                                msg: EmailMessage) -> None:
    smtpd.config.use_starttls = True
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.starttls()
        client.login(user.username, user.password)
        client.send_message(msg)

    assert len(smtpd.messages) == 1


def test_send_message_auth_not_complete(smtpd: AuthController,
                                        msg: EmailMessage) -> None:
    smtpd.config.enforce_auth = True
    with raises(SMTPResponseException) as er:
        with SMTP(smtpd.hostname, smtpd.port) as client:
            client.send_message(msg)
    assert er.match(r"^\(530")


def test_sendmail(smtpd: AuthController) -> None:
    from_addr = "from.addr@example.org"
    to_addr = "to.addr@example.org"
    msg = (f"From: {from_addr}\r\n"
           f"To: {to_addr}\r\n"
           f"Subject: Foo\r\n\r\n"
           f"Foo bar")

    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.sendmail(from_addr, to_addr, msg)

    assert len(smtpd.messages) == 1


@mock.patch.object(Config, "enforce_auth", True)
def test_mock_patch(smtpd: AuthController) -> None:
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.helo()
        code, repl = client.docmd("DATA", "")
        assert code == 530
        assert repl.startswith(b"5.7.0 Authentication required")


def test_monkeypatch(monkeypatch: MonkeyPatch, smtpd: AuthController) -> None:
    monkeypatch.setattr(smtpd.config, "enforce_auth", True)
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.helo()
        code, repl = client.docmd("DATA", "")
        assert code == 530
        assert repl.startswith(b"5.7.0 Authentication required")


class TestDefaultAuthenticator:
    _config = Config()
    _auth = _Authenticator(_config)

    def test_validate(cls, user: User) -> None:
        assert cls._auth.validate(user.username, user.password)

    def test_verify(cls, user: User) -> None:
        with raises(NotImplementedError):
            cls._auth.verify(user.username)

    def test_get_password(cls, user: User) -> None:
        password = cls._auth.get_password(user.username)
        assert password == user.password
