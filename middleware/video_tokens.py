# middlewares/video_tokens.py
from typing import Any, Awaitable, Callable, Dict, Mapping
from maxapi.filters.middleware import BaseMiddleware

class VideoTokensMiddleware(BaseMiddleware):
    def __init__(self, video_tokens: Mapping[str, str]):
        self.video_tokens = video_tokens

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event_object: Any,
        data: Dict[str, Any],
    ) -> Any:
        data["video_tokens"] = self.video_tokens
        return await handler(event_object, data)