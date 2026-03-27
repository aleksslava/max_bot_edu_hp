import asyncio
from json import JSONDecodeError, loads
from maxapi import Bot
from maxapi.enums.upload_type import UploadType
from maxapi.types.attachments.upload import AttachmentUpload, AttachmentPayload
import logging
from pathlib import Path
from typing import Dict, Union

logger = logging.getLogger(__name__)

async def upload_video_and_get_token(bot: Bot, path: str) -> str:
    # 1) получить URL и token для видео
    upload = await bot.get_upload_url(UploadType.VIDEO)  # upload.url + upload.token
    if not upload.token:
        raise RuntimeError("MAX не вернул token для видео")
    else:
        logger.info(f'Получен токен для видео: {path.split("/")[-1]}')

    # 2) залить файл на upload.url (multipart/form-data, поле 'data')
    await bot.upload_file(url=upload.url, path=path, type=UploadType.VIDEO)

    return upload.token


async def upload_all_videos_and_get_tokens(
    bot,
    folder: Union[str, Path],
) -> Dict[str, str]:
    folder = Path(folder)
    video_tokens: Dict[str, str] = {}

    files = sorted(folder.glob("*.mp4"))

    for p in files:
        key = p.stem
        video_tokens[key] = await upload_video_and_get_token(
            bot=bot,
            path=str(p),   # <-- важно
        )

    for p in sorted(folder.glob("*.avi")):
        key = p.stem
        video_tokens[key] = await upload_video_and_get_token(
            bot=bot,
            path=str(p),   # <-- важно
        )

    return video_tokens


async def upload_image_and_get_token(bot: Bot, path: str) -> str:
    # 1) получить URL для загрузки фото
    upload = await bot.get_upload_url(UploadType.IMAGE)  # upload.url + upload.token

    # 2) залить файл на upload.url (multipart/form-data, поле 'data')
    upload_response = await bot.upload_file(
        url=upload.url,
        path=path,
        type=UploadType.IMAGE,
    )

    # Для IMAGE MAX может не прислать token в get_upload_url,
    # тогда он приходит в ответе upload_file внутри photos.*.token.
    token = upload.token
    if not token:
        try:
            upload_json = loads(upload_response)
        except JSONDecodeError as exc:
            raise RuntimeError(
                "MAX не вернул token для фото: не удалось распарсить ответ upload_file"
            ) from exc

        photos = upload_json.get("photos")
        if isinstance(photos, dict):
            for photo_data in photos.values():
                if isinstance(photo_data, dict) and photo_data.get("token"):
                    token = photo_data["token"]
                    break

        if not token and isinstance(upload_json.get("token"), str):
            token = upload_json["token"]

    if not token:
        raise RuntimeError("MAX не вернул token для фото")

    logger.info(f'Получен токен для фото: {path.split("/")[-1]}')
    return token

async def upload_all_photo_and_get_tokens(
    bot,
    folder: Union[str, Path],
) -> Dict[str, str]:
    folder = Path(folder)
    image_tokens: Dict[str, str] = {}

    files = sorted(folder.glob("*.png"))

    for p in files:
        key = p.stem
        image_tokens[key] = await upload_image_and_get_token(
            bot=bot,
            path=str(p),   # <-- важно
        )

    return image_tokens
