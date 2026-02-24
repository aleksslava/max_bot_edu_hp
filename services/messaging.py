import asyncio
import logging
from typing import Any

from maxapi.types import Message, NewMessageLink

from services.context import bot
from services.message_utils import split_text

logger = logging.getLogger(__name__)


async def _send_text_parts(
    chat_id: str | int,
    parts: list[str],
    link: NewMessageLink | None = None,
    attachments: list[Any] | None = None,
) -> None:
    for index, part in enumerate(parts):
        await bot.send_message(
            chat_id=chat_id,
            text=part,
            link=link if index == 0 else None,
            attachments=attachments if index == 0 else None,
        )


def _handle_send_task_result(task: asyncio.Task[None]) -> None:
    try:
        task.result()
    except Exception:
        logger.exception("Failed to send message via maxapi")


def send_text(
    chat_id: str | int,
    text: str,
    link: NewMessageLink | None = None,
    attachments: list[Any] | None = None,
) -> None:
    parts = split_text(text)
    if not parts:
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(
            _send_text_parts(
                chat_id=chat_id,
                parts=parts,
                link=link,
                attachments=attachments,
            )
        )
        return

    task = loop.create_task(
        _send_text_parts(
            chat_id=chat_id,
            parts=parts,
            link=link,
            attachments=attachments,
        )
    )
    task.add_done_callback(_handle_send_task_result)


async def answer_or_edit(
    message: Message,
    text: str,
    attachments: list | None = None,
    edit: bool = False,
) -> None:
    if edit:
        await message.edit(text=text, attachments=attachments)
    else:
        await message.answer(text=text, attachments=attachments)
