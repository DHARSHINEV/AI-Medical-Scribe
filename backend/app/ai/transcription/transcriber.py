import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.ai.transcription.model_manager import whisper_manager
from app.core.config import settings

logger = logging.getLogger(__name__)


class SpeechToText:
    """
    Speech-to-text service using Faster-Whisper.
    Uses cached WhisperModel instances to avoid reloading weights per request.
    """

    def __init__(
        self,
        model_size: Optional[str] = None,
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        self.model_size = model_size or getattr(settings, "whisper_model", "base")
        self.device = device
        self.compute_type = compute_type

    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe an audio file.

        Returns:
            {
                "text": "...",
                "language": "en",
                "segments": [
                    {
                        "start": 0.0,
                        "end": 2.5,
                        "text": "..."
                    }
                ]
            }
        """
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        model = whisper_manager.get_model(
            model_size=self.model_size,
            device=self.device,
            compute_type=self.compute_type,
        )

        language = getattr(settings, "whisper_language", None)
        transcribe_kwargs: Dict[str, Any] = {
            "beam_size": 5,
            "vad_filter": True,
        }
        if language:
            transcribe_kwargs["language"] = language

        try:
            segments, info = model.transcribe(str(path), **transcribe_kwargs)
        except Exception as exc:
            logger.error(f"Error during audio transcription: {exc}")
            raise

        segment_list: List[Dict[str, Any]] = []
        full_text: List[str] = []

        for segment in segments:
            text = segment.text.strip()
            if text:
                full_text.append(text)
                segment_list.append(
                    {
                        "start": round(segment.start, 2),
                        "end": round(segment.end, 2),
                        "text": text,
                    }
                )

        return {
            "text": " ".join(full_text),
            "language": info.language if info else "en",
            "segments": segment_list,
        }


def speech_to_text(audio_path: str, model_size: Optional[str] = None) -> Dict[str, Any]:
    """Convenience helper function for transcription."""
    transcriber = SpeechToText(model_size=model_size)
    return transcriber.transcribe(audio_path)
