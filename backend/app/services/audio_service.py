from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings


ALLOWED_AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".webm",
    ".ogg",
}

MAX_AUDIO_SIZE = settings.max_audio_size_mb * 1024 * 1024


async def save_audio(
    consultation_id: int,
    file: UploadFile,
) -> str:
    original_name = file.filename or ""

    extension = Path(original_name).suffix.lower()

    if extension not in ALLOWED_AUDIO_EXTENSIONS:
        raise ValueError(
            f"Unsupported audio format: {extension}"
        )

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = (
        f"consultation_{consultation_id}_"
        f"{uuid4().hex}{extension}"
    )

    destination = upload_dir / filename

    size = 0

    try:
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)

                if size > MAX_AUDIO_SIZE:
                    destination.unlink(missing_ok=True)

                    raise ValueError(
                        "Audio file exceeds the maximum size."
                    )

                output.write(chunk)

    finally:
        await file.close()

    return str(destination)