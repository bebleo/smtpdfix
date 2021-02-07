from smtplib import SMTP

from smtpdfix import SMTPDFix


def test_smtpdfix(msg):
    hostname, port = "127.0.0.1", 8025

    with SMTPDFix(hostname, port) as smtpd:
        with SMTP(hostname, port) as client:
            from_addr = "foo@example.org"
            to_addrs = "bar@example.org"
            msg = (f"From: {from_addr}\r\n"
                   f"To: {to_addrs}\r\n"
                   f"Subject: Foo\r\n\r\n"
                   f"Foo bar")

            client.sendmail(from_addr, to_addrs, msg)

        assert len(smtpd.messages) == 1
