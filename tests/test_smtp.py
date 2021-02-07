from smtplib import SMTP

import pytest


@pytest.mark.parametrize("cmd", ["DATA", "MAIL", "RCPT"])
def test_auth_first(cmd, monkeypatch, smtpd):
    monkeypatch.setenv("SMTPD_ENFORCE_AUTH", "True")
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.ehlo()
        code, repl = client.docmd(cmd, "")
        assert code == 530
        assert repl.startswith(b"5.7.0 Authentication required")
