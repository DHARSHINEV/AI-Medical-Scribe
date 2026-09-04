from pathlib import Path

from faster_whisper import WhisperModel


class SpeechToText:
    """Speech-to-text service using Faster-Whisper."""

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size

        # CPU configuration for maximum compatibility on the hackathon setup.
        self.model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
        )

    def transcribe(self, audio_path: str) -> dict:
        """
        Transcribe an audio file.

        Returns:
            {
                "text": "...",
                "language": "...",
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
            raise FileNotFoundError(
                f"Audio file not found: {audio_path}"
            )

        segments, info = self.model.transcribe(
            str(path),
            beam_size=5,
            vad_filter=True,
        )

        segment_list = []
        full_text = []

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
            "language": info.language,
            "segments": segment_list,
        }


def speech_to_text(audio_path: str, model_size: str = "base") -> dict:
    """
    Convenience function used by the AI pipeline.
    """
    transcriber = SpeechToText(model_size=model_size)
    return transcriber.transcribe(audio_path)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Transcribe an audio file using Faster-Whisper."
    )

    parser.add_argument(
        "audio_path",
        help="Path to the audio file",
    )

    parser.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        help="Whisper model size",
    )

    args = parser.parse_args()

    result = speech_to_text(
        audio_path=args.audio_path,
        model_size=args.model,
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )