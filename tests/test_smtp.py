from smtplib import SMTP

import pytest


@pytest.mark.parametrize("cmd", ["DATA", "MAIL", "RCPT"])
def test_auth_first(cmd, smtpd):
    smtpd.config.enforce_auth = True
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.ehlo()
        code, repl = client.docmd(cmd, "")
        assert code == 530
        assert repl.startswith(b"5.7.0 Authentication required")
