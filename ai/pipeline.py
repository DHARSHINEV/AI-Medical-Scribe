import argparse
import json
from pathlib import Path
from typing import Any, Dict

from ai.speech_to_text.transcriber import SpeechToText
from ai.diarization.diarizer import SpeakerDiarizer
from ai.clinical_nlp.entity_extractor import ClinicalEntityExtractor
from ai.patient_history.history_context import (
    build_patient_history_context,
)
from ai.soap_generation.soap_generator import SOAPGenerator
from safety.safety_checker import SafetyChecker


class MediScribePipeline:
    """
    End-to-end AI pipeline for MediScribe.

    Workflow:

        Audio
          ↓
        Speech-to-Text
          ↓
        Speaker Separation
          ↓
        Clinical Information Extraction
          ↓
        Patient History Context
          ↓
        SOAP Note Generation
          ↓
        Safety & Consistency Checks
          ↓
        Clinician Review
          ↓
        Structured AI Output
    """

    def __init__(
        self,
        whisper_model: str = "tiny",
    ):
        self.whisper_model = whisper_model

        print(
            f"[AI] Loading Whisper model: {whisper_model}"
        )

        self.transcriber = SpeechToText(
            model_size=whisper_model
        )

        self.diarizer = SpeakerDiarizer()

        self.entity_extractor = ClinicalEntityExtractor()

        self.soap_generator = SOAPGenerator(
            mode="demo"
        )

        self.safety_checker = SafetyChecker()

    def run(
        self,
        audio_path: str,
        patient_history: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Run the complete MediScribe AI pipeline.
        """

        path = Path(audio_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Audio file not found: {audio_path}"
            )

        # --------------------------------------------------------------
        # STEP 1 — Speech-to-Text
        # --------------------------------------------------------------

        print("\n[1/6] Running Speech-to-Text...")

        transcription = self.transcriber.transcribe(
            str(path)
        )

        transcript = transcription.get(
            "text",
            ""
        )

        segments = transcription.get(
            "segments",
            []
        )

        if not transcript.strip():
            raise ValueError(
                "Speech-to-text returned an empty transcript."
            )

        print(
            f"[STT] Language: "
            f"{transcription.get('language', 'unknown')}"
        )

        print(
            f"[STT] Segments: {len(segments)}"
        )

        # --------------------------------------------------------------
        # STEP 2 — Speaker Separation
        # --------------------------------------------------------------

        print("\n[2/6] Running speaker separation...")

        diarized_segments = self.diarizer.diarize(
            segments
        )

        diarized_transcript = (
            self.diarizer.format_transcript(
                diarized_segments
            )
        )

        print(
            f"[Diarization] Processed "
            f"{len(diarized_segments)} segments."
        )

        # --------------------------------------------------------------
        # STEP 3 — Clinical Information Extraction
        # --------------------------------------------------------------

        print(
            "\n[3/6] Extracting clinical information..."
        )

        entities = self.entity_extractor.extract(
            transcript
        )

        print(
            "[Clinical NLP] Entities extracted."
        )

        # --------------------------------------------------------------
        # STEP 4 — Patient History Context
        # --------------------------------------------------------------

        print(
            "\n[4/6] Building patient history context..."
        )

        patient_history_context = (
            build_patient_history_context(
                patient_history=patient_history,
                current_entities=entities,
            )
        )

        print(
            "[Patient History] Context built successfully."
        )

        # --------------------------------------------------------------
        # STEP 5 — SOAP Generation
        # --------------------------------------------------------------

        print("\n[5/6] Generating SOAP note...")

        soap = self.soap_generator.generate(
            transcript=transcript,
            entities=entities,
            patient_history_context=patient_history_context,
        )

        print(
            "[SOAP] SOAP note generated."
        )

        # --------------------------------------------------------------
        # STEP 6 — Safety & Consistency Checks
        # --------------------------------------------------------------

        print(
            "\n[6/6] Running safety and consistency checks..."
        )

        safety = self.safety_checker.check(
            transcript=transcript,
            entities=entities,
            patient_history_context=patient_history_context,
        )

        print(
            "[Safety] Safety checks completed."
        )

        if safety["review_required"]:
            print(
                "[Safety] WARNING: Clinician review required."
            )

        if safety["high_priority_alert_count"] > 0:
            print(
                "[Safety] High-priority alerts: "
                f"{safety['high_priority_alert_count']}"
            )

        # --------------------------------------------------------------
        # CLINICIAN REVIEW STATE
        # --------------------------------------------------------------

        review = {
            "required": safety["review_required"],
            "status": "pending",
            "approved": False,
        }

        if safety["review_required"]:
            review["reason"] = (
                "One or more safety alerts require clinician review."
            )
        else:
            review["reason"] = (
                "No safety alert currently requires clinician review."
            )

        print(
            "[Review] Status: pending"
        )

        if review["required"]:
            print(
                "[Review] Clinician approval is required before finalization."
            )

        # --------------------------------------------------------------
        # FINAL STRUCTURED OUTPUT
        # --------------------------------------------------------------

        result = {
            "audio_file": str(path),
            "language": transcription.get("language"),
            "transcript": transcript,
            "segments": segments,
            "diarized_transcript": diarized_transcript,
            "diarized_segments": diarized_segments,
            "entities": entities,
            "patient_history_context": patient_history_context,
            "soap": soap,
            "safety": safety,
            "review": review,
        }

        return result


def load_patient_history(
    history_path: str | None,
) -> Dict[str, Any]:
    """
    Load patient history from a JSON file.

    If no history file is provided, an empty history
    dictionary is returned.
    """

    if not history_path:
        print(
            "[Patient History] No history file provided."
        )
        return {}

    path = Path(history_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Patient history file not found: {history_path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        patient_history = json.load(file)

    if not isinstance(
        patient_history,
        dict,
    ):
        raise ValueError(
            "Patient history JSON must contain an object."
        )

    print(
        f"[Patient History] Loaded from: {path}"
    )

    return patient_history


def main() -> None:
    """Command-line entry point."""

    parser = argparse.ArgumentParser(
        description="MediScribe end-to-end AI pipeline"
    )

    parser.add_argument(
        "audio_path",
        help="Path to the consultation audio file",
    )

    parser.add_argument(
        "--model",
        default="tiny",
        choices=[
            "tiny",
            "base",
            "small",
            "medium",
            "large-v3",
        ],
        help=(
            "Faster-Whisper model size "
            "(default: tiny)"
        ),
    )

    parser.add_argument(
        "--history",
        default=None,
        help=(
            "Optional path to patient history JSON file"
        ),
    )

    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Optional path to save the final "
            "JSON output"
        ),
    )

    args = parser.parse_args()

    try:
        patient_history = load_patient_history(
            args.history
        )

        pipeline = MediScribePipeline(
            whisper_model=args.model
        )

        result = pipeline.run(
            audio_path=args.audio_path,
            patient_history=patient_history,
        )

        print(
            "\n"
            + "=" * 70
        )

        print(
            "MEDISCRIBE AI PIPELINE RESULT"
        )

        print(
            "=" * 70
        )

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
        )

        # --------------------------------------------------------------
        # OPTIONAL JSON FILE OUTPUT
        # --------------------------------------------------------------

        if args.output:
            output_path = Path(
                args.output
            )

            output_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with open(
                output_path,
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    result,
                    file,
                    indent=2,
                    ensure_ascii=False,
                )

            print(
                f"\n[OUTPUT] Saved result to: "
                f"{output_path}"
            )

    except FileNotFoundError as error:
        print(
            f"\n[ERROR] {error}"
        )
        raise SystemExit(1)

    except Exception as error:
        print(
            "\n[ERROR] AI pipeline failed:"
        )

        print(
            f"{type(error).__name__}: {error}"
        )

        raise SystemExit(1)


if __name__ == "__main__":
    main()