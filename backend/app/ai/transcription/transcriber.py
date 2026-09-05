import io
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np

from app.ai.transcription.model_manager import whisper_manager
from app.core.config import settings

logger = logging.getLogger(__name__)


class SpeechToText:
    """
    Speech-to-text service using Faster-Whisper.
    Uses cached WhisperModel instances to avoid reloading weights per request.
    Optimized for fast CPU inference and streaming/incremental audio arrays.
    """

    def __init__(
        self,
        model_size: Optional[str] = None,
        device: str = "cpu",
        compute_type: str = "int8",
        beam_size: int = 1,
    ):
        self.model_size = model_size or getattr(settings, "whisper_model", "tiny")
        self.device = device
        self.compute_type = compute_type
        self.beam_size = beam_size

    def transcribe(
        self,
        audio_source: Union[str, Path, np.ndarray, io.BytesIO, bytes],
        beam_size: Optional[int] = None,
        vad_filter: bool = True,
        initial_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Transcribe an audio file or raw audio buffer (16kHz float32 NumPy array / bytes).

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
        audio_input: Any = audio_source
        if isinstance(audio_source, (str, Path)):
            path = Path(audio_source)
            if not path.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_source}")
            audio_input = str(path)
        elif isinstance(audio_source, bytes):
            audio_input = io.BytesIO(audio_source)

        model = whisper_manager.get_model(
            model_size=self.model_size,
            device=self.device,
            compute_type=self.compute_type,
        )

        language = getattr(settings, "whisper_language", "en")
        effective_beam = beam_size if beam_size is not None else self.beam_size

        transcribe_kwargs: Dict[str, Any] = {
            "beam_size": effective_beam,
            "best_of": 1,
            "temperature": 0.0,
            "condition_on_previous_text": False,
            "vad_filter": vad_filter,
        }
        if language:
            transcribe_kwargs["language"] = language
        if initial_prompt:
            transcribe_kwargs["initial_prompt"] = initial_prompt

        try:
            segments, info = model.transcribe(audio_input, **transcribe_kwargs)
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
            "language": info.language if info else (language or "en"),
            "segments": segment_list,
        }


def speech_to_text(audio_path: str, model_size: Optional[str] = None) -> Dict[str, Any]:
    """Convenience helper function for transcription."""
    transcriber = SpeechToText(model_size=model_size)
    return transcriber.transcribe(audio_path)

