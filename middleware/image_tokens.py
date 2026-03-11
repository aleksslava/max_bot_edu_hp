# middlewares/video_tokens.py
from typing import Any, Awaitable, Callable, Dict, Mapping
from maxapi.filters.middleware import BaseMiddleware

class ImageTokensMiddleware(BaseMiddleware):
    def __init__(self, image_tokens: Mapping[str, str]):
        self.image_tokens = image_tokens

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event_object: Any,
        data: Dict[str, Any],
    ) -> Any:
        data["image_tokens"] = self.image_tokens
        return await handler(event_object, data)