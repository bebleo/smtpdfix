import logging
import os
from typing import Any, Generator, Optional

import pytest

from .authenticator import Authenticator
from .certs import _generate_certs
from .configuration import Config
from .controller import AuthController
from .typing import TempPathFactory

log = logging.getLogger(__name__)


class _Authenticator(Authenticator):
    def __init__(self, config: Config) -> None:
        self.config = config

    def validate(self, username: str, password: str) -> bool:
        if (
            username == self.config.login_username
            and password == self.config.login_password
        ):
            log.debug("Validating username and password for succeeded")
            return True

        log.debug("Validating username and password failed")
        return False

    def get_password(self, username: Optional[str]) -> str:
        return self.config.login_password


class SMTPDFix():
    def __init__(self,
                 hostname: Optional[str] = None,
                 port: int = 8025,
                 config: Optional[Config] = None) -> None:
        self.hostname = hostname
        self.port = int(port) if port is not None else 8025
        self.config = config or Config()

    def __enter__(self) -> AuthController:
        self.controller = AuthController(
            hostname=self.hostname,
            port=self.port,
            config=self.config,
            authenticator=_Authenticator(self.config)
        )
        self.controller.start()
        return self.controller

    def __exit__(self, type: Any, value: Any, traceback: Any) -> None:
        self.controller.stop()


@pytest.fixture
def smtpd(
    tmp_path_factory: TempPathFactory
) -> Generator[AuthController, None, None]:
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
    if os.getenv("SMTPD_SSL_CERTS_PATH") is None:
        path = tmp_path_factory.mktemp("certs")
        _generate_certs(path)
        os.environ["SMTPD_SSL_CERTS_PATH"] = str(path.resolve())

    with SMTPDFix() as fixture:
        yield fixture
