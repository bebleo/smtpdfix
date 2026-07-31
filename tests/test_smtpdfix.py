import socket
from email.message import EmailMessage
from pathlib import Path
from smtplib import SMTP

from pytest import TempPathFactory

from smtpdfix import SMTPDFix
from smtpdfix.certs import _generate_certs


def test_smtpdfix(msg: EmailMessage) -> None:
    with SMTPDFix() as server, SMTP(server.hostname, server.port) as client:
        client.send_message(msg)
        assert len(server.messages) == 1


def test_smtpdfix_with_prebound_socket(msg: EmailMessage) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(5)

        with SMTPDFix(sock=sock) as server:
            with SMTP(server.hostname, server.port) as client:
                client.send_message(msg)

            assert len(server.messages) == 1


def test_generate_certs(tmp_path_factory: TempPathFactory) -> None:
    path = tmp_path_factory.mktemp("certs")
    _generate_certs(path)

    assert Path.joinpath(path, "cert.pem").is_file()


def test_generate_certs_with_separate_key(
    tmp_path_factory: TempPathFactory
) -> None:
    path = tmp_path_factory.mktemp("certs")
    _generate_certs(path, separate_key=True)

    assert Path.joinpath(path, "cert.pem").is_file()
    assert Path.joinpath(path, "key.pem").is_file()
