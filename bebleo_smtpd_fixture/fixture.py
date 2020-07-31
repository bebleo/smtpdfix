import logging
# import os

import pytest

from .authenticator import Authenticator
from .config import Config
from .controller import AuthController


log = logging.getLogger(__name__)


class _Authenticator(Authenticator):
    def __init__(self, config=Config()):
        self.config = config

    def validate(self, username, password):
        if (
            username == self.config.SMTPD_LOGIN_NAME and
            password == self.config.SMTPD_LOGIN_PASSWORD
        ):
            log.debug((f"Validating username and password for {username} "
                       "succeeded."))
            return True

        log.debug(f'Validating username and password for {username} failed.')
        return False

    def get_password(self, username):
        log.debug(f"Password retrieved for {username}.")
        return self.config.SMTPD_LOGIN_PASSWORD


@pytest.fixture
def smtpd(request):
    """A small SMTP server for use when testing applications that send email
    messages. To access the messages call `smtpd.messages` which returns a copy
    of the list of messages sent to the server.

    Example:
        def test_mail(smtpd):
            from smtplib import SMTP
            with SMTP(smtpd.hostname, smtpd.port) as client:
                code, resp = client.noop()
                assert code == 250

    """
    config = Config()

    fixture = AuthController(
        hostname=config.SMTPD_HOST,
        port=int(config.SMTPD_PORT),
        config=config,
        authenticator=_Authenticator(config)
    )
    request.addfinalizer(fixture.stop)
    fixture.start()
    return fixture
