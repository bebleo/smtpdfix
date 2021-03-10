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

        self._smtpd_host = os.getenv("SMTPD_HOST")
        self._smtpd_port = os.getenv("SMTPD_PORT")
        self._smtpd_login_name = os.getenv("SMTPD_LOGIN_NAME", "user")
        self._smtpd_login_password = os.getenv("SMTPD_LOGIN_PASSWORD",
                                               "password")
        self._smtpd_enforce_auth = strtobool(os.getenv("SMTPD_ENFORCE_AUTH",
                                                       "False"))
        self._smtpd_auth_require_tls = strtobool(
                                           os.getenv("SMTPD_AUTH_REQUIRE_TLS",
                                                     "True"))
        self._smtpd_ssl_certs_path = os.getenv("SMTPD_SSL_CERTS_PATH",
                                               os.path.join(_current_dir,
                                                            "certs"))
        self._smtpd_use_starttls = strtobool(os.getenv("SMTPD_USE_STARTTLS",
                                                       "False"))
        self._smtpd_use_tls = strtobool(os.getenv("SMTPD_USE_TLS", "False"))
        self._smtpd_use_ssl = strtobool(os.getenv("SMTPD_USE_SSL", "False"))

    @property
    def SMTPD_HOST(self):
        return self._smtpd_host

    @SMTPD_HOST.setter
    def set_SMTPD_HOST(self, value):
        self._smtpd_host = value
        self.OnChanged()

    @property
    def SMTPD_PORT(self):
        return self._smtpd_port

    @SMTPD_PORT.setter
    def set_SMTPD_PORT(self, value):
        self._smtpd_port = value
        self.OnChanged()

    @property
    def SMTPD_LOGIN_NAME(self):
        return self._smtpd_login_name

    @SMTPD_LOGIN_NAME.setter
    def set_SMTPD_LOGIN_NAME(self, value):
        self._smtpd_login_name = value
        self.OnChanged()

    @property
    def SMTPD_LOGIN_PASSWORD(self):
        return self._smtpd_login_password

    @SMTPD_LOGIN_PASSWORD.setter
    def set_SMTPD_LOGIN_PASSWORD(self, value):
        self._smtpd_login_password = value
        self.OnChanged()()

    @property
    def SMTPD_ENFORCE_AUTH(self):
        return self._smtpd_enforce_auth

    @SMTPD_ENFORCE_AUTH.setter
    def set_SMTPD_ENFORCE_AUTH(self, value):
        self._smtpd_enforce_auth = value
        self.OnChanged()()

    @property
    def SMTPD_AUTH_REQUIRE_TLS(self):
        return self._smtpd_auth_require_tls

    @SMTPD_AUTH_REQUIRE_TLS.setter
    def set_SMTPD_AUTH_REQUIRE_TLS(self, value):
        self._smtpd_auth_require_tls = value
        self.OnChanged()

    @property
    def SMTPD_SSL_CERTS_PATH(self):
        return self._smtpd_ssl_certs_path

    @SMTPD_SSL_CERTS_PATH.setter
    def set_SMTPD_SSL_CERTS_PATH(self, value):
        self._smtpd_ssl_certs_path = value
        self.OnChanged()

    @property
    def SMTPD_USE_STARTTLS(self):
        return self._smtpd_use_starttls

    @SMTPD_USE_STARTTLS.setter
    def set_SMTPD_USE_STARTTLS(self, value):
        self._smtpd_use_starttls = value
        self.OnChanged()

    @property
    def SMTPD_USE_TLS(self):
        return self._smtpd_use_tls

    @SMTPD_USE_TLS.setter
    def set_SMTPD_USE_TLS(self, value):
        self._smtpd_use_tls = value
        self.OnChanged()

    @property
    def SMTPD_USE_SSL(self):
        return self._smtpd_use_ssl

    @SMTPD_USE_SSL.setter
    def set_SMTPD_USE_SSL(self, value):
        self._smtpd_use_ssl = value
        self.OnChanged()
