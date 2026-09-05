from pathlib import Path
from uuid import uuid4


ALLOWED_AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".webm",
    ".ogg",
}


def generate_audio_filename(
    consultation_id: int,
    original_filename: str | None,
) -> str:
    extension = Path(original_filename or "").suffix.lower()

    if extension not in ALLOWED_AUDIO_EXTENSIONS:
        extension = ".webm"

    return (
        f"consultation_{consultation_id}_"
        f"{uuid4().hex}{extension}"
    )

MAX_AUDIO_SIZE = 50 * 1024 * 1024  # 50 MB


def validate_audio_extension(
    filename: str | None,
) -> bool:
    if not filename:
        return False

    extension = Path(filename).suffix.lower()

    return extension in ALLOWED_AUDIO_EXTENSIONS