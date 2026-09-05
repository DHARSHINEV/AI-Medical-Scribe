from typing import Dict, List, Optional


class SpeakerDiarizer:
    """
    Speaker diarization / labeling module for MediScribe.

    NOTE ON IMPLEMENTATION HONESTY:
    This MVP component uses a deterministic alternating speaker heuristic
    (SPEAKER_00 -> Doctor, SPEAKER_01 -> Patient) as a development/demo fallback.
    It is NOT an acoustic speaker-clustering ML model (e.g. pyannote.audio).
    The backend architecture allows swapping in a full ML diarization model here
    without altering any downstream consumers.
    """

    def __init__(
        self,
        speaker_mapping: Optional[Dict[str, str]] = None,
    ):
        self.speaker_mapping = speaker_mapping or {
            "SPEAKER_00": "Doctor",
            "SPEAKER_01": "Patient",
        }

    def diarize(self, segments: List[dict]) -> List[dict]:
        """
        Add speaker labels to timestamped transcript segments.

        Expected input:
            [
                {
                    "start": 0.18,
                    "end": 2.98,
                    "text": "Good morning."
                }
            ]

        Returns:
            [
                {
                    "start": 0.18,
                    "end": 2.98,
                    "speaker": "Doctor",
                    "text": "Good morning."
                }
            ]
        """
        if not isinstance(segments, list):
            raise TypeError("segments must be a list")

        diarized_segments = []

        for index, segment in enumerate(segments):
            if not isinstance(segment, dict):
                raise TypeError(f"Segment {index} must be a dictionary")

            if "text" not in segment:
                raise ValueError(f"Segment {index} is missing 'text'")

            # Deterministic alternation fallback
            speaker_id = f"SPEAKER_{index % 2:02d}"
            speaker = self.speaker_mapping.get(speaker_id, "Unassigned")

            diarized_segments.append(
                {
                    "start": segment.get("start", 0.0),
                    "end": segment.get("end", 0.0),
                    "speaker": speaker,
                    "text": segment["text"].strip(),
                    "confidence": segment.get("confidence"),
                }
            )

        return diarized_segments

    def format_transcript(self, diarized_segments: List[dict]) -> str:
        """Convert diarized segments into a formatted clinical conversation transcript."""
        lines = []
        for segment in diarized_segments:
            speaker = segment.get("speaker", "Unassigned")
            lines.append(f"{speaker}: {segment['text']}")
        return "\n".join(lines)


def diarize(
    segments: List[dict],
    speaker_mapping: Optional[Dict[str, str]] = None,
) -> List[dict]:
    """Convenience function for diarization."""
    diarizer = SpeakerDiarizer(speaker_mapping=speaker_mapping)
    return diarizer.diarize(segments)
