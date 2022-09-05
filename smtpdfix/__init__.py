__all__ = (
    "AuthController",
    "Authenticator",
    "AuthMessage",
    "Config",
    "smtpd",
    "SMTPDFix",
)
__version__ = "0.4.0"

from .authenticator import Authenticator
from .configuration import Config
from .controller import AuthController
from .fixture import SMTPDFix, smtpd
from .handlers import AuthMessage

config = Config()
