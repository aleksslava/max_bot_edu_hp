from maxapi.types import Link, Message

from services.context import bot
from services.message_utils import split_text


def send_text(
    chat_id: str,
    text: str,
    link: Link | None = None,
    attachments: list | None = None,
) -> None:
    parts = split_text(text)
    for index, part in enumerate(parts):
        bot.send_text(
            chat_id=chat_id,
            text=part,
            link=link if index == 0 else None,
            attachments=attachments if index == 0 else None,
        )


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
