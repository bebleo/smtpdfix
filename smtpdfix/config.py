import os
from distutils.util import strtobool

from dotenv import load_dotenv

_current_dir = os.path.dirname(__file__)
load_dotenv()


class Config():
    def __init__(self, filename=None, override=False):
        if filename:
            load_dotenv(filename, override=override)

    @property
    def SMTPD_HOST(self):
        return os.getenv("SMTPD_HOST")

    @property
    def SMTPD_PORT(self):
        return os.getenv("SMTPD_PORT")

    @property
    def SMTPD_LOGIN_NAME(self):
        return os.getenv("SMTPD_LOGIN_NAME", "user")

    @property
    def SMTPD_LOGIN_PASSWORD(self):
        return os.getenv("SMTPD_LOGIN_PASSWORD", "password")

    @property
    def SMTPD_ENFORCE_AUTH(self):
        return strtobool(os.getenv("SMTPD_ENFORCE_AUTH", "False"))

    @property
    def SMTPD_AUTH_REQUIRE_TLS(self):
        return strtobool(os.getenv("SMTPD_AUTH_REQUIRE_TLS", "True"))

    @property
    def SMTPD_SSL_CERTS_PATH(self):
        return os.getenv("SMTPD_SSL_CERTS_PATH",
                         os.path.join(_current_dir, "certs"))

    @property
    def SMTPD_USE_STARTTLS(self):
        return strtobool(os.getenv("SMTPD_USE_STARTTLS", "False"))

    @property
    def SMTPD_USE_TLS(self):
        return strtobool(os.getenv("SMTPD_USE_TLS", "False"))

    @property
    def SMTPD_USE_SSL(self):
        return strtobool(os.getenv("SMTPD_USE_SSL", "False"))
