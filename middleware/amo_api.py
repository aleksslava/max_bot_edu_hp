from __future__ import annotations
from typing import Any, Awaitable, Callable, Dict, Mapping
from maxapi.filters.middleware import BaseMiddleware

from amo_api.amo_api import AmoCRMWrapper

class AmoApiMiddleware(BaseMiddleware):
    def __init__(self, amo_api: AmoCRMWrapper, amo_fields: dict, admin_id: str,
                 webhook_url: str, utm_token: str) -> None:
        self._amo_api = amo_api
        self._amo_fields = amo_fields
        self.admin_id = admin_id
        self.webhook_url = webhook_url
        self.utm_token = utm_token

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event_object: Any,
        data: dict[str, Any],
    ) -> Any:
        data["amo_api"] = self._amo_api
        data["amo_fields"] = self._amo_fields
        data["admin_id"] = self.admin_id
        data["webhook_url"] = self.webhook_url
        data["utm_token"] = self.utm_token

        return await handler(event_object, data)