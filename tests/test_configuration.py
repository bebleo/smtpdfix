import os
from pathlib import Path

import pytest

from smtpdfix.configuration import Config

values = [
    ("host", "mail.localhost", "mail.localhost", str),
    ("port", 5025, 5025, int),
    ("port", "5025", 5025, int),
    ("login_name", "name", "name", str),
    ("login_password", "word", "word", str),
    ("enforce_auth", "True", True, bool),
    ("enforce_auth", True, True, bool),
    ("enforce_auth", 1, True, bool),
    ("auth_require_tls", 0, False, bool),
    ("auth_require_tls", "0", False, bool),
    ("auth_require_tls", False, False, bool),
    ("auth_require_tls", "False", False, bool),
    ("ssl_certs_path", "./certs", "./certs", str),
    ("use_starttls", False, False, bool),
    ("use_tls", True, True, bool),
    ("use_ssl", True, True, bool),
]


def test_init():
    config = Config()
    assert isinstance(config, Config)


def test_init_envfile():
    original_env = os.environ.copy()
    config_file = Path(__file__).parent.joinpath("assets/.test.env")
    config = Config(filename=config_file, override=True)

    assert config.port == 5025

    os.environ.clear()
    os.environ.update(original_env)


@pytest.mark.parametrize("attr,value,expected,type", values)
def test_set_values(attr, value, expected, type):
    config = Config()
    setattr(config, attr, value)
    assert isinstance(getattr(config, attr), type)
    assert getattr(config, attr) == expected
