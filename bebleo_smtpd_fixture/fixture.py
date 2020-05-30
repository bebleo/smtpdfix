import logging
from os import getenv

import pytest

from .controller import AuthController
from .authenticator import Authenticator

# Use the same log as aiosmtpd
log = logging.getLogger('mail.log')


class _Authenticator(Authenticator):
    def validate(self, username, password):
        if (
            username == getenv("SMPTD_LOGINNAME", "user") and
            password == getenv("SMPTD_LOGIN_PASSWORD", "password")
        ):
            return True
        return False


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
