import logging
import threading
from typing import Optional
from faster_whisper import WhisperModel
from app.core.config import settings

logger = logging.getLogger(__name__)


class WhisperModelManager:
    """
    Singleton / Cached model manager for Faster-Whisper.
    Ensures model weights are loaded once into memory instead of reloading per request.
    Supports CPU / GPU detection and configurable model sizes.
    """

    _instance: Optional["WhisperModelManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._models: dict[str, WhisperModel] = {}
        self._model_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "WhisperModelManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_model(
        self,
        model_size: Optional[str] = None,
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> WhisperModel:
        """
        Retrieve or lazily initialize the Faster-Whisper model.
        """
        size = model_size or getattr(settings, "whisper_model", "base")
        key = f"{size}_{device}_{compute_type}"

        if key not in self._models:
            with self._model_lock:
                if key not in self._models:
                    logger.info(
                        f"Loading Faster-Whisper model '{size}' on {device} ({compute_type})..."
                    )
                    model = WhisperModel(
                        size,
                        device=device,
                        compute_type=compute_type,
                    )
                    self._models[key] = model
                    logger.info(f"Model '{size}' loaded successfully.")

        return self._models[key]


whisper_manager = WhisperModelManager.get_instance()
