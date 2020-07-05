from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Sink
from bebleo_smtpd_fixture.smtp import AuthSMTP
from bebleo_smtpd_fixture.controller import _get_ssl_context
from smtplib import SMTP

import pytest


@pytest.fixture
def no_auth(request):
    class PseudoController(Controller):
        def factory(self):
            return AuthSMTP(self.handler)

    controller = PseudoController(Sink(), hostname="127.0.0.1", port="8025")
    request.addfinalizer(controller.stop)
    controller.start()
    return controller


@pytest.fixture
def require_starttls(request):
    class StartTLSController(Controller):
        def factory(self):
            return AuthSMTP(self.handler,
                            require_starttls=True,
                            tls_context=_get_ssl_context)

    controller = StartTLSController(Sink(), hostname="127.0.0.1", port="8025")
    request.addfinalizer(controller.stop)
    controller.start()
    return controller


def test_missing_auth_handler(no_auth):
    with SMTP(no_auth.hostname, no_auth.port) as client:
        code, message = client.docmd('AUTH')
    assert code == 502


def test_require_starttls(require_starttls):
    with SMTP(require_starttls.hostname, require_starttls.port) as client:
        code, message = client.docmd("AUTH")
    assert code == 530
