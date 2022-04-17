import asyncio
import os
from typing import Any, Callable, Coroutine, Dict, Optional, Union

# Type aliases
AsyncServer = asyncio.base_events.Server
CallableHandler = Callable[..., Optional[Dict[Any, Any]]]
PathType = Union[str, os.PathLike]
ServerCoroutine = Coroutine[Any, Any, asyncio.base_events.Server]
