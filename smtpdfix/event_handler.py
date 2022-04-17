from __future__ import annotations

import logging
from typing import Any

from .typing import CallableHandler

log = logging.getLogger(__name__)


class EventHandler():
    def __init__(self) -> None:
        self._handlers: set[CallableHandler] = set()

    def __iadd__(self, handler: CallableHandler) -> EventHandler:
        self._handlers.add(handler)
        return self

    def __isub__(self, handler: CallableHandler) -> EventHandler:
        self._handlers.remove(handler)
        return self

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        for handler in self._handlers:
            handler(*args, **kwargs)
