import os
from pathlib import Path

import pytest

from smtpdfix.configuration import Config

values = [
    ("SMTPD_HOST", "mail.localhost", "mail.localhost", str),
    ("SMTPD_PORT", 5025, 5025, int),
    ("SMTPD_PORT", "5025", 5025, int),
    ("SMTPD_LOGIN_NAME", "name", "name", str),
    ("SMTPD_LOGIN_PASSWORD", "word", "word", str),
    ("SMTPD_ENFORCE_AUTH", "True", True, bool),
    ("SMTPD_ENFORCE_AUTH", True, True, bool),
    ("SMTPD_ENFORCE_AUTH", 1, True, bool),
    ("SMTPD_AUTH_REQUIRE_TLS", "False", False, bool),
    ("SMTPD_AUTH_REQUIRE_TLS", False, False, bool),
    ("SMTPD_AUTH_REQUIRE_TLS", 0, False, bool),
    ("SMTPD_AUTH_REQUIRE_TLS", "0", False, bool),
    ("SMTPD_SSL_CERTS_PATH", "./certs", "./certs", str),
    ("SMTPD_USE_STARTTLS", False, False, bool),
    ("SMTPD_USE_TLS", True, True, bool),
    ("SMTPD_USE_SSL", True, True, bool),
]


def test_init():
    config = Config()
    assert isinstance(config, Config)


def test_init_envfile():
    original_env = os.environ.copy()
    config_file = Path(__file__).parent.joinpath("assets/.test.env")
    config = Config(filename=config_file, override=True)

    assert config.SMTPD_PORT == 5025

    os.environ.clear()
    os.environ.update(original_env)


@pytest.mark.parametrize("attr,value,expected,type", values)
def test_set_values(attr, value, expected, type):
    config = Config()
    setattr(config, attr, value)
    assert isinstance(getattr(config, attr), type)
    assert getattr(config, attr) == expected
