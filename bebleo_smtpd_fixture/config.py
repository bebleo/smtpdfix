import os
from distutils.util import strtobool

_current_dir = os.path.dirname(__file__)


class Config():
    def __init__(self):
        pass

    def _strtobool(self, value):
        """Method to simplify calling boolean values from env variables."""
        if isinstance(value, bool):
            return value

        return bool(strtobool(value))

    @property
    def SMTPD_HOST(self):
        return os.getenv("SMTPD_HOST", "127.0.0.1")

    @property
    def SMTPD_PORT(self):
        return os.getenv("SMTPD_PORT", 8025)

    @property
    def SMTPD_LOGIN_NAME(self):
        return os.getenv("SMTPD_LOGIN_NAME", "user")

    @property
    def SMTPD_LOGIN_PASSWORD(self):
        return os.getenv("SMTPD_LOGIN_PASSWORD", "password")

    @property
    def SMTPD_SSL_CERTS_PATH(self):
        return os.getenv("SMTPD_SSL_CERTS_PATH",
                         os.path.join(_current_dir, "certs"))

    @property
    def SMTPD_USE_STARTTLS(self):
        return self._strtobool(os.getenv("SMTPD_USE_STARTTLS", False))

    @property
    def SMTPD_USE_TLS(self):
        return self._strtobool(os.getenv("SMTPD_USE_TLS", False))

    @property
    def SMTPD_USE_SSL(self):
        return self._strtobool(os.getenv("SMTPD_USE_SSL", False))
