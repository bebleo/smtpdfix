import logging

log = logging.getLogger(__name__)


class EventHandler():
    def __init__(self):
        self._handlers = set()

    def __iadd__(self, handler):
        self._handlers.add(handler)
        return self

    def __isub__(self, handler):
        self._handlers.remove(handler)
        return self

    def __call__(self, *args, **kwargs):
        for handler in self._handlers:
            handler(*args, **kwargs)
