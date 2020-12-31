from smtplib import SMTP

import pytest


@pytest.mark.parametrize("cmd", ["AUTH", "DATA", "MAIL", "RCPT"])
def test_helo_first(cmd, smtpd):
    with SMTP(smtpd.hostname, smtpd.port) as client:
        code, repl = client.docmd(cmd, "")
        assert code == 503
        assert repl.startswith(b"Error: send HELO first")


@pytest.mark.parametrize("cmd", ["DATA", "MAIL", "RCPT"])
def test_auth_first(cmd, monkeypatch, smtpd):
    monkeypatch.setenv("SMTPD_ENFORCE_AUTH", "True")
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.helo()
        code, repl = client.docmd(cmd, "")
        assert code == 530
        assert repl.startswith(b"SMTP authentication is required")
