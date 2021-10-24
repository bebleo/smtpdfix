import ssl
from smtplib import SMTP, SMTP_SSL

import pytest
import trustme
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Sink


@pytest.mark.parametrize("cmd", ["DATA", "MAIL", "RCPT"])
def test_auth_first(cmd, smtpd):
    smtpd.config.enforce_auth = True
    with SMTP(smtpd.hostname, smtpd.port) as client:
        client.ehlo()
        code, repl = client.docmd(cmd, "")
        assert code == 530
        assert repl.startswith(b"5.7.0 Authentication required")


def test_trustme_ssl(request, msg):
    ca = trustme.CA()
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

    server_cert = ca.issue_cert("localhost")
    server_cert.configure_cert(context)
    ca.configure_trust(context)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_OPTIONAL

    handler = Sink()
    controller = Controller(handler, ssl_context=context)
    request.addfinalizer(controller.stop)
    controller.start()

    with SMTP_SSL(controller.hostname,
                  controller.port) as client:
        client.send_message(msg)

    assert client
