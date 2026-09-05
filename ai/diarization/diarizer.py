from typing import Dict, List


class SpeakerDiarizer:
    """
    Lightweight speaker diarization for the MediScribe MVP.

    The MVP uses configurable speaker mapping rather than a heavy
    real-time speaker-identification model.
    """

    def __init__(
        self,
        speaker_mapping: Dict[str, str] | None = None,
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
                raise TypeError(
                    f"Segment {index} must be a dictionary"
                )

            if "text" not in segment:
                raise ValueError(
                    f"Segment {index} is missing 'text'"
                )

            speaker_id = f"SPEAKER_{index % 2:02d}"

            speaker = self.speaker_mapping.get(
                speaker_id,
                speaker_id,
            )

            diarized_segments.append(
                {
                    "start": segment.get("start", 0.0),
                    "end": segment.get("end", 0.0),
                    "speaker": speaker,
                    "text": segment["text"].strip(),
                }
            )

        return diarized_segments

    def format_transcript(
        self,
        diarized_segments: List[dict],
    ) -> str:
        """
        Convert diarized segments into a readable clinical transcript.
        """

        lines = []

        for segment in diarized_segments:
            lines.append(
                f"{segment['speaker']}: {segment['text']}"
            )

        return "\n".join(lines)


def diarize(
    segments: List[dict],
    speaker_mapping: Dict[str, str] | None = None,
) -> List[dict]:
    """
    Convenience function used by the AI pipeline.
    """

    diarizer = SpeakerDiarizer(
        speaker_mapping=speaker_mapping
    )

    return diarizer.diarize(segments)


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) != 2:
        print(
            "Usage: python -m ai.diarization.diarizer "
            "<segments.json>"
        )
        sys.exit(1)

    with open(
        sys.argv[1],
        "r",
        encoding="utf-8",
    ) as file:
        segments = json.load(file)

    result = diarize(segments)

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )