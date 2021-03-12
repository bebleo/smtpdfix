import os
from distutils.util import strtobool

from dotenv import load_dotenv

from smtpdfix.event_handler import EventHandler

_current_dir = os.path.dirname(__file__)
load_dotenv()


class Config():
    def __init__(self, filename=None, override=False, *args, **kwargs):
        if filename:
            load_dotenv(filename, override=override)

        self.OnChanged = EventHandler()

        self._host = os.getenv("SMTPD_HOST")
        self._port = int(os.getenv("SMTPD_PORT", 8025))
        self._login_name = os.getenv("SMTPD_LOGIN_NAME", "user")
        self._login_password = os.getenv("SMTPD_LOGIN_PASSWORD", "password")
        self._enforce_auth = strtobool(os.getenv("SMTPD_ENFORCE_AUTH",
                                                 "False"))
        self._auth_require_tls = strtobool(os.getenv("SMTPD_AUTH_REQUIRE_TLS",
                                                     "True"))
        self._ssl_certs_path = os.getenv("SMTPD_SSL_CERTS_PATH",
                                         os.path.join(_current_dir, "certs"))
        self._use_starttls = strtobool(os.getenv("SMTPD_USE_STARTTLS",
                                                 "False"))
        self._use_tls = strtobool(os.getenv("SMTPD_USE_TLS", "False"))
        self._use_ssl = strtobool(os.getenv("SMTPD_USE_SSL", "False"))

    def convert_to_bool(self, value):
        """Consistently convert to bool."""
        if isinstance(value, str):
            return bool(strtobool(value))
        return bool(value)

    @property
    def SMTPD_HOST(self):
        return self._host

    @SMTPD_HOST.setter
    def SMTPD_HOST(self, value):
        self._host = value
        self.OnChanged()

    @property
    def SMTPD_PORT(self):
        return self._port

    @SMTPD_PORT.setter
    def SMTPD_PORT(self, value):
        self._port = int(value)
        self.OnChanged()

    @property
    def SMTPD_LOGIN_NAME(self):
        return self._login_name

    @SMTPD_LOGIN_NAME.setter
    def SMTPD_LOGIN_NAME(self, value):
        self._login_name = value
        self.OnChanged()

    @property
    def SMTPD_LOGIN_PASSWORD(self):
        return self._login_password

    @SMTPD_LOGIN_PASSWORD.setter
    def SMTPD_LOGIN_PASSWORD(self, value):
        self._login_password = value
        self.OnChanged()

    @property
    def SMTPD_ENFORCE_AUTH(self):
        return self._enforce_auth

    @SMTPD_ENFORCE_AUTH.setter
    def SMTPD_ENFORCE_AUTH(self, value):
        self._enforce_auth = self.convert_to_bool(value)
        self.OnChanged()

    @property
    def SMTPD_AUTH_REQUIRE_TLS(self):
        return self._auth_require_tls

    @SMTPD_AUTH_REQUIRE_TLS.setter
    def SMTPD_AUTH_REQUIRE_TLS(self, value):
        self._auth_require_tls = self.convert_to_bool(value)
        self.OnChanged()

    @property
    def SMTPD_SSL_CERTS_PATH(self):
        return self._ssl_certs_path

    @SMTPD_SSL_CERTS_PATH.setter
    def SMTPD_SSL_CERTS_PATH(self, value):
        self._ssl_certs_path = value
        self.OnChanged()

    @property
    def SMTPD_USE_STARTTLS(self):
        return self._use_starttls

    @SMTPD_USE_STARTTLS.setter
    def SMTPD_USE_STARTTLS(self, value):
        self._use_starttls = self.convert_to_bool(value)
        self.OnChanged()

    @property
    def SMTPD_USE_TLS(self):
        return self._use_tls

    @SMTPD_USE_TLS.setter
    def SMTPD_USE_TLS(self, value):
        self._use_tls = self.convert_to_bool(value)
        self.OnChanged()

    @property
    def SMTPD_USE_SSL(self):
        return self._use_ssl

    @SMTPD_USE_SSL.setter
    def SMTPD_USE_SSL(self, value):
        self._use_ssl = self.convert_to_bool(value)
        self.OnChanged()
