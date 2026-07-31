# Logging for the smtpdfix package
# uses NullHandler to avoid "No handler found" warnings when no
# logging configuration is provided by the user.
# This is a common practice for libraries to avoid interfering with the
# application's logging configuration.
import logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
