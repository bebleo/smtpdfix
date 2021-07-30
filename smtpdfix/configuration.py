import os
from distutils.util import strtobool
from pathlib import Path

from dotenv import load_dotenv

from .event_handler import EventHandler

_current_dir = Path(__file__).parent
load_dotenv()


class Config():
    def __init__(self, filename=None, override=False):
        if filename:
            load_dotenv(filename, override=override)

        self.OnChanged = EventHandler()

        self._host = os.getenv("SMTPD_HOST")
        self._port = int(os.getenv("SMTPD_PORT", 8025))
        self._ready_timeout = float(os.getenv("SMTPD_READY_TIMEOUT", 5.0))
        self._login_username = os.getenv("SMTPD_LOGIN_NAME", "user")
        self._login_password = os.getenv("SMTPD_LOGIN_PASSWORD", "password")
        self._enforce_auth = strtobool(os.getenv("SMTPD_ENFORCE_AUTH",
                                                 "False"))
        self._auth_require_tls = strtobool(os.getenv("SMTPD_AUTH_REQUIRE_TLS",
                                                     "True"))
        self._ssl_cert_path = os.getenv("SMTPD_SSL_CERTS_PATH",
                                        _current_dir.joinpath("certs"))
        self._ssl_cert_files = (
            os.getenv("SMTPD_SSL_CERTIFICATE_FILE", "./cert.pem"),
            os.getenv("SMTPD_SSL_KEY_FILE"))
        self._use_starttls = strtobool(os.getenv("SMTPD_USE_STARTTLS",
                                                 "False"))
        self._use_ssl = (strtobool(os.getenv("SMTPD_USE_SSL", "False")) or
                         strtobool(os.getenv("SMTPD_USE_TLS", "False")))

    def convert_to_bool(self, value):
        """Consistently convert to bool."""
        if isinstance(value, str):
            return bool(strtobool(value))
        return bool(value)

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, value):
        self._host = value
        self.OnChanged()

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        self._port = int(value)
        self.OnChanged()

    @property
    def ready_timeout(self):
        return self._ready_timeout

    @ready_timeout.setter
    def ready_timeout(self, value):
        self._ready_timeout = float(value)
        self.OnChanged()

    @property
    def login_username(self):
        return self._login_username

    @login_username.setter
    def login_username(self, value):
        self._login_username = value
        self.OnChanged()

    @property
    def login_password(self):
        return self._login_password

    @login_password.setter
    def login_password(self, value):
        self._login_password = value
        self.OnChanged()

    @property
    def enforce_auth(self):
        return self._enforce_auth

    @enforce_auth.setter
    def enforce_auth(self, value):
        self._enforce_auth = self.convert_to_bool(value)
        self.OnChanged()

    @property
    def auth_require_tls(self):
        return self._auth_require_tls

    @auth_require_tls.setter
    def auth_require_tls(self, value):
        self._auth_require_tls = self.convert_to_bool(value)
        self.OnChanged()

    @property
    def ssl_certs_path(self):
        return self._ssl_cert_path

    @ssl_certs_path.setter
    def ssl_certs_path(self, value):
        self._ssl_cert_path = value
        self.OnChanged()

    @property
    def ssl_cert_files(self):
        return self._ssl_cert_files

    @ssl_cert_files.setter
    def ssl_cert_files(self, value):
        if isinstance(value, tuple):
            self._ssl_cert_files = value
        else:
            self._ssl_cert_files = (value, None)
        self.OnChanged()

    @property
    def use_starttls(self):
        return self._use_starttls

    @use_starttls.setter
    def use_starttls(self, value):
        self._use_starttls = self.convert_to_bool(value)
        self.OnChanged()

    @property
    def use_ssl(self):
        return self._use_ssl

    @use_ssl.setter
    def use_ssl(self, value):
        self._use_ssl = self.convert_to_bool(value)
        self.OnChanged()
