from smtplib import SMTP

from smtpdfix import SMTPDFix


def test_smtpdfix(msg):
    with SMTPDFix() as server, SMTP(server.hostname, server.port) as client:
        client.send_message(msg)
        assert len(server.messages) == 1
