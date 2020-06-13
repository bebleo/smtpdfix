from os import getenv

import pytest

from .controller import AuthController
from .authenticator import Authenticator


class _Authenticator(Authenticator):
    def validate(self, username, password):
        return (
            username == getenv("SMPTD_LOGINNAME", "user") and
            password == getenv("SMPTD_LOGIN_PASSWORD", "password")
        )


@pytest.fixture
def smtpd(request):
    fixture = AuthController(
        hostname=getenv("SMTPD_HOST", "127.0.0.1"),
        port=int(getenv("SMTPD_PORT", "8025")),
        authenticator=_Authenticator()
    )
    request.addfinalizer(fixture.stop)
    fixture.start()
    return fixture
