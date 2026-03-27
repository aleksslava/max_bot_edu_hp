import os
from pathlib import Path
from typing import Dict, Union

from dotenv import load_dotenv, set_key, dotenv_values

# upload_video_and_get_token(bot, path: str) -> str
from services.video_upload import upload_video_and_get_token, upload_image_and_get_token


def _env_var_name_from_stem(stem: str) -> str:
    # lesson_1 -> MAX_VIDEO_TOKEN_LESSON_1
    return f"MAX_VIDEO_TOKEN_{stem.upper()}"

def _env_var_name_from_stem_image(stem: str) -> str:
    # lesson_1 -> MAX_VIDEO_TOKEN_LESSON_1
    return f"MAX_IMAGE_TOKEN_{stem.upper()}"


async def ensure_video_tokens_in_env(
    bot,
    folder: Union[str, Path],
    env_path: Union[str, Path],
) -> Dict[str, str]:
    folder = Path(folder)
    env_path = Path(env_path)

    # если .env отсутствует — создадим пустой
    env_path.parent.mkdir(parents=True, exist_ok=True)
    if not env_path.exists():
        env_path.write_text("", encoding="utf-8")

    # загрузим переменные из конкретного файла
    load_dotenv(dotenv_path=str(env_path), override=False)

    # значения из .env (чтобы не зависеть только от os.environ)
    env_values = dotenv_values(str(env_path))

    video_tokens: Dict[str, str] = {}

    for mp4 in sorted(folder.glob("*.mp4")):
        stem = mp4.stem
        env_var = _env_var_name_from_stem(stem)

        token = os.getenv(env_var) or env_values.get(env_var)

        if not token:
            token = await upload_video_and_get_token(bot=bot, path=str(mp4))
            # запишем/обновим ключ в .env
            set_key(str(env_path), env_var, token)

            # обновим окружение текущего процесса (на всякий случай)
            os.environ[env_var] = token

        video_tokens[stem] = token

    for avi in sorted(folder.glob("*.avi")):
        stem = avi.stem
        env_var = _env_var_name_from_stem(stem)

        token = os.getenv(env_var) or env_values.get(env_var)

        if not token:
            token = await upload_video_and_get_token(bot=bot, path=str(avi))
            # запишем/обновим ключ в .env
            set_key(str(env_path), env_var, token)

            # обновим окружение текущего процесса (на всякий случай)
            os.environ[env_var] = token

        video_tokens[stem] = token

    return video_tokens


async def ensure_image_tokens_in_env(
    bot,
    folder: Union[str, Path],
    env_path: Union[str, Path],
) -> Dict[str, str]:
    folder = Path(folder)
    env_path = Path(env_path)

    # если .env отсутствует — создадим пустой
    env_path.parent.mkdir(parents=True, exist_ok=True)
    if not env_path.exists():
        env_path.write_text("", encoding="utf-8")

    # загрузим переменные из конкретного файла
    load_dotenv(dotenv_path=str(env_path), override=False)

    # значения из .env (чтобы не зависеть только от os.environ)
    env_values = dotenv_values(str(env_path))

    image_tokens: Dict[str, str] = {}

    for png in sorted(folder.glob("*.png")):
        stem = png.stem
        env_var = _env_var_name_from_stem_image(stem)

        token = os.getenv(env_var) or env_values.get(env_var)

        if not token:
            token = await upload_image_and_get_token(bot=bot, path=str(png))
            # запишем/обновим ключ в .env
            set_key(str(env_path), env_var, token)

            # обновим окружение текущего процесса (на всякий случай)
            os.environ[env_var] = token

        image_tokens[stem] = token

    return image_tokens