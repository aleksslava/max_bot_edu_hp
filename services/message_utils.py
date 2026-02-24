import html
import re

from maxapi.types import Message


def clean_markup(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def split_text(text: str, limit: int = 3500) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + limit, len(text))
        if end < len(text):
            split_pos = text.rfind("\n", start, end)
            if split_pos <= start:
                split_pos = end
            end = split_pos
        chunks.append(text[start:end].strip())
        start = end
    return [chunk for chunk in chunks if chunk]


def normalize_phone(raw_text: str) -> str | None:
    digits = re.sub(r"\D", "", raw_text)
    if not digits:
        return None
    if len(digits) == 10:
        digits = "7" + digits
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    if len(digits) == 11 and digits.startswith("7"):
        return "+" + digits
    return None


def get_text(message: Message) -> str:
    body = getattr(message, "body", None)
    text = getattr(body, "text", None)
    return (text or "").strip()


def get_chat_id(message: Message) -> str:
    recipient = getattr(message, "recipient", None)
    chat_id = getattr(recipient, "chat_id", "")
    return str(chat_id)


def get_user_id(message: Message) -> int:
    sender = getattr(message, "sender", None)
    user_id = getattr(sender, "user_id", None)
    try:
        return int(user_id)
    except (TypeError, ValueError):
        return 0


def get_user_name(message: Message) -> str:
    sender = getattr(message, "sender", None)
    name = getattr(sender, "name", None)
    if name:
        return str(name)
    return ""


def parse_number_answers(raw_text: str) -> list[int]:
    return [int(value) for value in re.findall(r"-?\d+", raw_text)]
