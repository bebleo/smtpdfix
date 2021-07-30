import functools
import os
from pathlib import Path

import pytest

from smtpdfix.configuration import Config

values = [
    ("host", "mail.localhost", "mail.localhost", str),
    ("port", 5025, 5025, int),
    ("port", "5025", 5025, int),
    ("ready_timeout", 2.5, 2.5, float),
    ("ready_timeout", "2.5", 2.5, float),
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
    ("ssl_cert_files",
        ("./certs/cert.pem", "./certs/key.pem"),
        ("./certs/cert.pem", "./certs/key.pem"),
        tuple),
    ("ssl_cert_files",
        "./certs/key.pem",
        ("./certs/key.pem", None),
        tuple),
    ("use_starttls", False, False, bool),
    ("use_tls", True, True, bool),
    ("use_ssl", True, True, bool),
]
props = [p for p in dir(Config) if isinstance(getattr(Config, p), property)]


@pytest.fixture
def handler():
    class Handler():
        def handle(self, result):
            result.append(True)
    yield Handler()


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


@pytest.mark.parametrize("attr, value, expected, type", values)
def test_set_values(attr, value, expected, type):
    config = Config()
    setattr(config, attr, value)
    assert isinstance(getattr(config, attr), type)
    assert getattr(config, attr) == expected


@pytest.mark.parametrize("prop", props)
def test_event_handler_fires(prop, handler):
    config = Config()
    result = []
    config.OnChanged += functools.partial(handler.handle, result)
    setattr(config, prop, 1)
    assert result.pop() is True


def test_unset_event_handler(handler):
    config = Config()
    result = []
    prop = "auth_require_tls"  # chosen because it is alphabetically mo. 1
    func = functools.partial(handler.handle, result)

    config.OnChanged += func
    setattr(config, prop, 1)
    assert result.pop() is True

    config.OnChanged -= func
    setattr(config, prop, 0)
    assert not result
