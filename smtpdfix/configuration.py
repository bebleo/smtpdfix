import os
from pathlib import Path
from typing import Any, Optional, Tuple, Union

import portpicker

from .event_handler import EventHandler
from .typing import PathType

_current_dir = Path(__file__).parent


def _strtobool(val: str) -> bool:
    """Convert a string representation of truth to true (1) or false (0).

    True values are "y", "yes", "t", "true", "on", and "1"; false values are
    "n", "no", "f", "false", "off", and "0".  Raises ValueError if "val" is
    anything else.
    """
    # Copied and updated from distutils.util in response to distutils removal
    # as of python 3.12
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError(f"invalid truth value {val}")


class Config():
    def __init__(self) -> None:

        self.OnChanged = EventHandler()

        self._host = os.getenv("SMTPD_HOST")
        self._port = int(
            os.getenv("SMTPD_PORT", portpicker.pick_unused_port())
        )
        self._ready_timeout = float(os.getenv("SMTPD_READY_TIMEOUT", 10.0))
        self._login_username = os.getenv("SMTPD_LOGIN_NAME", "user")
        self._login_password = os.getenv("SMTPD_LOGIN_PASSWORD", "password")
        self._enforce_auth = _strtobool(os.getenv("SMTPD_ENFORCE_AUTH",
                                                  "False"))
        self._auth_require_tls = _strtobool(os.getenv("SMTPD_AUTH_REQUIRE_TLS",
                                                      "True"))
        self._ssl_cert_path: PathType = os.getenv(
            "SMTPD_SSL_CERTS_PATH",
            _current_dir.joinpath("certs"))
        self._ssl_cert_files = (
            os.getenv("SMTPD_SSL_CERTIFICATE_FILE", "./cert.pem"),
            os.getenv("SMTPD_SSL_KEY_FILE"))
        self._use_starttls = _strtobool(os.getenv("SMTPD_USE_STARTTLS",
                                                  "False"))
        self._use_ssl = (_strtobool(os.getenv("SMTPD_USE_SSL", "False"))
                         or _strtobool(os.getenv("SMTPD_USE_TLS", "False")))

    def convert_to_bool(self, value: Any) -> bool:
        """Consistently convert to bool."""
        if isinstance(value, str):
            return bool(_strtobool(value))
        return bool(value)

    @property
    def host(self) -> Optional[str]:
        return self._host

    @host.setter
    def host(self, value: Optional[str]) -> None:
        self._host = value
        self.OnChanged()

    @property
    def port(self) -> int:
        return self._port

    @port.setter
    def port(self, value: int) -> None:
        self._port = int(value)
        self.OnChanged()

    @property
    def ready_timeout(self) -> float:
        return self._ready_timeout

    @ready_timeout.setter
    def ready_timeout(self, value: float) -> None:
        self._ready_timeout = float(value)
        self.OnChanged()

    @property
    def login_username(self) -> str:
        return self._login_username

    @login_username.setter
    def login_username(self, value: str) -> None:
        self._login_username = value
        self.OnChanged()

    @property
    def login_password(self) -> str:
        return self._login_password

    @login_password.setter
    def login_password(self, value: str) -> None:
        self._login_password = value
        self.OnChanged()

    @property
    def enforce_auth(self) -> bool:
        return self._enforce_auth

    @enforce_auth.setter
    def enforce_auth(self, value: bool) -> None:
        self._enforce_auth = self.convert_to_bool(value)
        self.OnChanged()

    @property
    def auth_require_tls(self) -> bool:
        return self._auth_require_tls

    @auth_require_tls.setter
    def auth_require_tls(self, value: bool) -> None:
        self._auth_require_tls = self.convert_to_bool(value)
        self.OnChanged()

    @property
    def ssl_certs_path(self) -> PathType:
        return self._ssl_cert_path

    @ssl_certs_path.setter
    def ssl_certs_path(self, value: PathType) -> None:
        self._ssl_cert_path = value
        self.OnChanged()

    @property
    def ssl_cert_files(self) -> Tuple[str, Optional[str]]:
        return self._ssl_cert_files

    @ssl_cert_files.setter
    def ssl_cert_files(self,
                       value: Union[str, Tuple[str, Optional[str]]]) -> None:
        if isinstance(value, tuple):
            self._ssl_cert_files = (value[0], value[1])
        else:
            self._ssl_cert_files = (value, None)
        self.OnChanged()

    @property
    def use_starttls(self) -> bool:
        return self._use_starttls

    @use_starttls.setter
    def use_starttls(self, value: Any) -> None:
        self._use_starttls = self.convert_to_bool(value)
        self.OnChanged()

    @property
    def use_ssl(self) -> bool:
        return self._use_ssl

    @use_ssl.setter
    def use_ssl(self, value: Any) -> None:
        self._use_ssl = self.convert_to_bool(value)
        self.OnChanged()
