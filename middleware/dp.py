from typing import Any, Awaitable, Callable, Dict, Mapping
from maxapi.filters.middleware import BaseMiddleware

from db import async_session_factory


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event_object: Any,
        data: dict[str, Any],
    ) -> Any:

        async with async_session_factory() as session:
            data["session"] = session
            return await handler(event_object, data)

