from email.message import EmailMessage
from pathlib import Path
from smtplib import SMTP
from typing import Any

from pytest import MonkeyPatch, TempPathFactory

from smtpdfix import SMTPDFix


def test_smtpdfix(msg: EmailMessage) -> None:
    with SMTPDFix() as server, SMTP(server.hostname, server.port) as client:
        client.send_message(msg)
        assert len(server.messages) == 1


def test_misconfigured_socket(monkeypatch: MonkeyPatch,
                              tmp_path_factory: TempPathFactory) -> None:
    # As reported in #195 a misconfigured system will raise an error if
    # the hostname won't resolve to an IP address
    def raise_GAIError(*args: Any) -> None:
        from socket import gaierror
        raise gaierror("[Errno 8] nodename nor servname "
                       "provided, or not known")
    monkeypatch.setattr("socket.gethostbyname", raise_GAIError)

    from smtpdfix.certs import _generate_certs
    path = tmp_path_factory.mktemp("certs")
    _generate_certs(path)

    assert Path.joinpath(path, "cert.pem").is_file()
