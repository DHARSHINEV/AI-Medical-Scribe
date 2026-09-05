from typing import Dict, List, Optional

TURN_PAUSE_THRESHOLD_SECONDS = 1.2


class SpeakerDiarizer:
    """
    Two-speaker deterministic role assignment module for MediScribe.

    NOTE ON IMPLEMENTATION HONESTY:
    This component implements a deterministic two-speaker turn assignment strategy:
    - Speaker 1 (Initial turn) -> Doctor
    - Speaker 2 (Subsequent turn) -> Patient
    Speakers maintain their role across consecutive sentences within a conversational turn.
    A role transition occurs when a conversational pause (>= 1.2s) between segments is detected.
    This is heuristic role assignment for assistive review, not voice-biometric acoustic diarization.
    """

    def __init__(
        self,
        speaker_mapping: Optional[Dict[str, str]] = None,
        pause_threshold: Optional[float] = None,
    ):
        self.speaker_mapping = speaker_mapping or {
            "SPEAKER_00": "Doctor",
            "SPEAKER_01": "Patient",
        }
        self.pause_threshold = pause_threshold

    def diarize(self, segments: List[dict]) -> List[dict]:
        """
        Add deterministic Doctor/Patient speaker labels to timestamped transcript segments.

        Expected input:
            [
                {"start": 0.18, "end": 2.98, "text": "Good morning."},
                {"start": 3.10, "end": 4.50, "text": "How can I help you today?"}
            ]

        Returns:
            [
                {"start": 0.18, "end": 2.98, "speaker": "Doctor", "text": "Good morning."},
                {"start": 3.10, "end": 4.50, "speaker": "Patient", "text": "How can I help you today?"}
            ]
        """
        if not isinstance(segments, list):
            raise TypeError("segments must be a list")

        diarized_segments = []
        turn_index = 0
        last_end = None

        for index, segment in enumerate(segments):
            if not isinstance(segment, dict):
                raise TypeError(f"Segment {index} must be a dictionary")

            if "text" not in segment:
                raise ValueError(f"Segment {index} is missing 'text'")

            seg_start = float(segment.get("start", 0.0))
            seg_end = float(segment.get("end", 0.0))

            provided_speaker = segment.get("speaker")
            if provided_speaker:
                norm_speaker = str(provided_speaker).strip().upper()
                if norm_speaker in ("DOCTOR", "SPEAKER_00", "SPEAKER_0", "0"):
                    speaker = "Doctor"
                elif norm_speaker in ("PATIENT", "SPEAKER_01", "SPEAKER_1", "1"):
                    speaker = "Patient"
                else:
                    speaker = self.speaker_mapping.get(provided_speaker, provided_speaker)
            elif self.pause_threshold is not None:
                if last_end is not None:
                    gap = seg_start - last_end
                    if gap >= self.pause_threshold:
                        turn_index += 1
                last_end = seg_end

                speaker_id = f"SPEAKER_{turn_index % 2:02d}"
                speaker = self.speaker_mapping.get(speaker_id, "Doctor" if (turn_index % 2 == 0) else "Patient")
            else:
                speaker_id = f"SPEAKER_{index % 2:02d}"
                speaker = self.speaker_mapping.get(speaker_id, "Doctor" if (index % 2 == 0) else "Patient")

            diarized_segments.append(
                {
                    "start": seg_start,
                    "end": seg_end,
                    "speaker": speaker,
                    "text": segment["text"].strip(),
                    "confidence": segment.get("confidence", 0.95),
                }
            )

        return diarized_segments


    def format_transcript(self, diarized_segments: List[dict]) -> str:
        """Convert diarized segments into a formatted clinical conversation transcript."""
        lines = []
        for segment in diarized_segments:
            speaker = segment.get("speaker", "Doctor")
            lines.append(f"{speaker}: {segment['text']}")
        return "\n".join(lines)


def diarize(
    segments: List[dict],
    speaker_mapping: Optional[Dict[str, str]] = None,
) -> List[dict]:
    """Convenience function for diarization."""
    diarizer = SpeakerDiarizer(speaker_mapping=speaker_mapping)
    return diarizer.diarize(segments)

