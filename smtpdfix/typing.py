import asyncio
import os
from typing import Any, Callable, Coroutine, Dict, Optional, Union

from pytest import __version__ as pytest_version

# Type aliases
AsyncServer = asyncio.base_events.Server
CallableHandler = Callable[..., Optional[Dict[Any, Any]]]
PathType = Union[str, os.PathLike]
ServerCoroutine = Coroutine[Any, Any, asyncio.base_events.Server]

# Because the location of the TempPathFactory type definition is moved in
# version 6.2.0 we need to do some acrobats to make it pretty.
if pytest_version < "6.2.0":  # pragma: no cover
    from _pytest.tmpdir import TempPathFactory as TPF
else:
    from pytest import TempPathFactory as TPF
TempPathFactory = TPF
