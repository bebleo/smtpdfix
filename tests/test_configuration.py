import functools
from typing import Any, Generator, List

import pytest

from smtpdfix.configuration import Config, _strtobool
from smtpdfix.event_handler import EventHandler

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


class FakeHandler():
    def handle(self, result: Any) -> None:
        result.append(True)


@pytest.fixture
def handler() -> Generator[FakeHandler, None, None]:
    yield FakeHandler()


@pytest.mark.parametrize("val", ["y", "yes", "t", "true", "on", "1"])
def test_strtobool_true(val: str) -> None:
    assert _strtobool(val) is True


@pytest.mark.parametrize("val", ["n", "no", "f", "false", "off", "0"])
def test_strtobool_false(val: str) -> None:
    assert _strtobool(val) is False


@pytest.mark.parametrize("val", ["-1", "maybe", "error"])
def test_strtobool_error(val: str) -> None:
    with pytest.raises(ValueError):
        assert _strtobool(val) is False


def test_init() -> None:
    config = Config()
    assert isinstance(config, Config)


@pytest.mark.parametrize("attr, value, expected, type", values)
def test_set_values(attr: str, value: Any, expected: Any, type: Any) -> None:
    config = Config()
    setattr(config, attr, value)
    assert isinstance(getattr(config, attr), type)
    assert getattr(config, attr) == expected


@pytest.mark.parametrize("prop", props)
def test_event_handler_fires(prop: str, handler: FakeHandler) -> None:
    config = Config()
    result: List[Any] = []
    config.OnChanged += functools.partial(handler.handle, result)
    setattr(config, prop, 1)
    assert result.pop() is True


def test_unset_event_handler(handler: FakeHandler) -> None:
    config = Config()
    result: List[EventHandler] = []
    prop = "auth_require_tls"  # chosen because it is alphabetically mo. 1
    func = functools.partial(handler.handle, result)

    config.OnChanged += func
    setattr(config, prop, 1)
    assert result.pop() is True

    config.OnChanged -= func
    setattr(config, prop, 0)
    assert not result
