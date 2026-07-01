from concurrent.futures import TimeoutError as FuturesTimeoutError
from email.message import EmailMessage
from pathlib import Path
from smtplib import SMTP
from typing import Any

from pytest import MonkeyPatch, TempPathFactory

from smtpdfix import SMTPDFix
from smtpdfix.certs import _generate_certs


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

    path = tmp_path_factory.mktemp("certs")
    _generate_certs(path)

    assert Path.joinpath(path, "cert.pem").is_file()


def test_configured_socket(monkeypatch: MonkeyPatch,
                           tmp_path_factory: TempPathFactory) -> None:
    # Ensure that a properly configured socket still works
    import socket
    monkeypatch.setattr(socket, "gethostname", lambda: "127.0.0.1")

    path = tmp_path_factory.mktemp("certs")
    _generate_certs(path)

    assert Path.joinpath(path, "cert.pem").is_file()


def test_gethostbyname_timeout(monkeypatch: MonkeyPatch,
                               tmp_path_factory: TempPathFactory) -> None:
    # Simulate a system where the hostname lookup times out (e.g. macOS CI)
    # and verify that cert generation still succeeds without the host IP SAN.
    def timeout_gethostbyname(host: str) -> str:
        raise FuturesTimeoutError()

    monkeypatch.setattr("smtpdfix.certs.socket.gethostbyname",
                        timeout_gethostbyname)

    path = tmp_path_factory.mktemp("certs_timeout")
    _generate_certs(path)

    assert Path.joinpath(path, "cert.pem").is_file()
