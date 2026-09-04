import argparse
import json
import re
from typing import Any, Dict, List, Optional


class SOAPGenerator:
    """
    SOAP note generator for MediScribe.

    The generator is designed for the MVP and follows strict
    documentation rules:

    - Uses only information present in the transcript/entities/history.
    - Does not invent diagnoses, medications, dosages, or findings.
    - Preserves allergy negations.
    - Preserves duration and severity information.
    - Keeps patient history and family history separate.
    - Requires clinician review before the note is approved.
    """

    def __init__(self, mode: str = "demo"):
        self.mode = mode

    # ------------------------------------------------------------------
    # Utility functions
    # ------------------------------------------------------------------

    @staticmethod
    def _join(items: List[str]) -> str:
        """Convert a list of strings into readable text."""

        cleaned = [
            str(item).strip()
            for item in items
            if str(item).strip()
        ]

        if not cleaned:
            return ""

        if len(cleaned) == 1:
            return cleaned[0]

        if len(cleaned) == 2:
            return f"{cleaned[0]} and {cleaned[1]}"

        return ", ".join(cleaned[:-1]) + f", and {cleaned[-1]}"

    # ------------------------------------------------------------------
    # Subjective
    # ------------------------------------------------------------------

    def _generate_subjective(
        self,
        transcript: str,
        entities: Dict[str, List[str]],
        patient_history_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate the Subjective section.

        Includes:
        - Current symptoms
        - Duration
        - Severity
        - Current medications
        - Current allergy information
        - Previous patient history
        - Family history
        """

        parts = []

        symptoms = entities.get("symptoms", [])
        duration = entities.get("duration", [])
        severity = entities.get("severity", [])
        medications = entities.get("medications", [])
        allergies = entities.get("allergies", [])
        past_history = entities.get("past_medical_history", [])
        family_history = entities.get("family_history", [])

        # --------------------------------------------------------------
        # Current symptoms
        # --------------------------------------------------------------

        if symptoms:
            parts.append(
                f"Patient reports {self._join(symptoms)}."
            )

        # --------------------------------------------------------------
        # Duration
        # --------------------------------------------------------------

        if duration:
            parts.append(
                f"Duration reported: {self._join(duration)}."
            )

        # --------------------------------------------------------------
        # Severity
        # --------------------------------------------------------------

        if severity:
            parts.append(
                f"Reported severity descriptors: "
                f"{self._join(severity)}."
            )

        # --------------------------------------------------------------
        # Current medications
        # --------------------------------------------------------------

        if medications:
            parts.append(
                f"Current medications mentioned: "
                f"{self._join(medications)}."
            )

        # --------------------------------------------------------------
        # Current allergy information
        # --------------------------------------------------------------

        if allergies:
            parts.append(
                f"Reported allergies: {self._join(allergies)}."
            )
        else:
            negative_allergy_patterns = [
                r"\bno allergies\b",
                r"\bno known allergies\b",
                r"\bno allergy\b",
                r"\bnot allergic\b",
                r"\bdo not have any allergies\b",
                r"\bdon't have any allergies\b",
            ]

            has_negative_allergy = any(
                re.search(
                    pattern,
                    transcript,
                    flags=re.IGNORECASE,
                )
                for pattern in negative_allergy_patterns
            )

            if has_negative_allergy:
                parts.append(
                    "Patient reports no known allergies."
                )

        # --------------------------------------------------------------
        # History extracted directly from current consultation
        # --------------------------------------------------------------

        if past_history:
            parts.append(
                f"Past medical history mentioned: "
                f"{self._join(past_history)}."
            )

        if family_history:
            parts.append(
                f"Family history mentioned: "
                f"{self._join(family_history)}."
            )

        # --------------------------------------------------------------
        # Previous patient history from history context
        # --------------------------------------------------------------

        if patient_history_context:
            previous_history = patient_history_context.get(
                "previous_patient_history",
                {},
            )

            previous_diseases = previous_history.get(
                "diseases",
                [],
            )

            previous_allergies = previous_history.get(
                "allergies",
                [],
            )

            previous_medications = previous_history.get(
                "medications",
                [],
            )

            previous_medical_history = previous_history.get(
                "past_medical_history",
                [],
            )

            context_parts = []

            if previous_diseases:
                context_parts.append(
                    f"Known previous conditions: "
                    f"{self._join(previous_diseases)}."
                )

            if previous_medical_history:
                context_parts.append(
                    f"Previous medical history: "
                    f"{self._join(previous_medical_history)}."
                )

            if previous_allergies:
                context_parts.append(
                    f"Known previous allergies: "
                    f"{self._join(previous_allergies)}."
                )

            if previous_medications:
                context_parts.append(
                    f"Previously documented medications: "
                    f"{self._join(previous_medications)}."
                )

            if context_parts:
                parts.append(
                    "Relevant previous patient history: "
                    + " ".join(context_parts)
                )

            # ----------------------------------------------------------
            # Family history from stored patient context
            # ----------------------------------------------------------

            context_family_history = patient_history_context.get(
                "family_history",
                [],
            )

            if context_family_history:
                parts.append(
                    f"Known family history: "
                    f"{self._join(context_family_history)}."
                )

        # --------------------------------------------------------------
        # Empty subjective section
        # --------------------------------------------------------------

        if not parts:
            return (
                "No subjective clinical information was "
                "documented in the transcript."
            )

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Objective
    # ------------------------------------------------------------------

    def _generate_objective(
        self,
        transcript: str,
        entities: Dict[str, List[str]],
    ) -> str:
        """
        Generate the Objective section.

        The MVP does not infer objective findings.
        """

        return (
            "No objective measurements, vital signs, examination "
            "findings, laboratory results, or imaging results were "
            "documented in the transcript."
        )

    # ------------------------------------------------------------------
    # Assessment
    # ------------------------------------------------------------------

    def _generate_assessment(
        self,
        transcript: str,
        entities: Dict[str, List[str]],
        patient_history_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate the Assessment section.

        Symptoms are not converted into diagnoses.

        A condition is reported only when it is explicitly
        documented or previously known in the patient history.
        """

        diseases = entities.get("diseases", [])
        symptoms = entities.get("symptoms", [])

        parts = []

        if diseases:
            parts.append(
                f"Documented condition(s): {self._join(diseases)}."
            )
        else:
            if symptoms:
                parts.append(
                    f"Symptoms documented in the conversation: "
                    f"{self._join(symptoms)}."
                )

            # ----------------------------------------------------------
            # Add historical conditions as context, not new diagnoses
            # ----------------------------------------------------------

            if patient_history_context:
                previous_history = patient_history_context.get(
                    "previous_patient_history",
                    {},
                )

                historical_diseases = previous_history.get(
                    "diseases",
                    [],
                )

                if historical_diseases:
                    parts.append(
                        f"Previously documented conditions: "
                        f"{self._join(historical_diseases)}."
                    )

            parts.append(
                "No confirmed diagnosis was documented."
            )

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Plan
    # ------------------------------------------------------------------

    def _generate_plan(
        self,
        transcript: str,
        entities: Dict[str, List[str]],
    ) -> str:
        """
        Generate the Plan section.

        Only explicit treatment, medication, advice, or follow-up
        information is reported.

        The system does NOT create new treatment recommendations.
        """

        medications = entities.get("medications", [])
        dosage = entities.get("dosage", [])

        parts = []

        sentences = re.split(
            r"(?<=[.!?])\s+",
            transcript.strip(),
        )

        plan_patterns = [
            r"\bI'll give you\b",
            r"\bI will give you\b",
            r"\bwe'll give you\b",
            r"\bwe will give you\b",
            r"\btake the\b",
            r"\btake your\b",
            r"\btake .* medicine\b",
            r"\bdrink .* fluids\b",
            r"\bdrink warm fluids\b",
            r"\brest\b",
            r"\bfollow up\b",
            r"\bfollow-up\b",
            r"\bprescribe\b",
            r"\bprescription\b",
            r"\brecommended\b",
            r"\brecommend\b",
        ]

        question_patterns = [
            r"^\s*(do|does|did|are|is|have|has|how|what|when|where|why|can|could|would|will)\b",
            r"\?\s*$",
        ]

        plan_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()

            if not sentence:
                continue

            if any(
                re.search(
                    pattern,
                    sentence,
                    flags=re.IGNORECASE,
                )
                for pattern in question_patterns
            ):
                continue

            if re.match(
                r"^\s*(for|since)\b",
                sentence,
                flags=re.IGNORECASE,
            ):
                continue

            if any(
                re.search(
                    pattern,
                    sentence,
                    flags=re.IGNORECASE,
                )
                for pattern in plan_patterns
            ):
                if sentence.lower() not in [
                    item.lower()
                    for item in plan_sentences
                ]:
                    plan_sentences.append(sentence)

        if plan_sentences:
            parts.append(
                "Explicit plan information: "
                + " ".join(plan_sentences)
            )

        if medications:
            medication_text = self._join(medications)

            if dosage:
                parts.append(
                    f"Medication mentioned: {medication_text}. "
                    f"Dosage information mentioned: "
                    f"{self._join(dosage)}."
                )
            else:
                parts.append(
                    f"Medication mentioned: "
                    f"{medication_text}."
                )

        if not parts:
            return (
                "No explicit treatment or follow-up plan was "
                "documented in the transcript."
            )

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Demo generation
    # ------------------------------------------------------------------

    def generate_demo(
        self,
        transcript: str,
        entities: Dict[str, List[str]],
        patient_history_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Generate a deterministic SOAP note for the MVP demo.
        """

        return {
            "subjective": self._generate_subjective(
                transcript,
                entities,
                patient_history_context,
            ),
            "objective": self._generate_objective(
                transcript,
                entities,
            ),
            "assessment": self._generate_assessment(
                transcript,
                entities,
                patient_history_context,
            ),
            "plan": self._generate_plan(
                transcript,
                entities,
            ),
        }

    # ------------------------------------------------------------------
    # Main generation method
    # ------------------------------------------------------------------

    def generate(
        self,
        transcript: str,
        entities: Optional[Dict[str, List[str]]] = None,
        patient_history_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Generate a structured SOAP note.

        Args:
            transcript:
                Medical consultation transcript.

            entities:
                Clinical entities extracted from the consultation.

            patient_history_context:
                Previously known patient history combined with
                current consultation context.
        """

        if not transcript or not transcript.strip():
            raise ValueError(
                "Transcript cannot be empty."
            )

        if entities is None:
            entities = {}

        if self.mode == "demo":
            return self.generate_demo(
                transcript=transcript,
                entities=entities,
                patient_history_context=patient_history_context,
            )

        raise NotImplementedError(
            f"SOAP generation mode '{self.mode}' "
            "is not implemented."
        )


# ----------------------------------------------------------------------
# Convenience function
# ----------------------------------------------------------------------

def generate_soap(
    transcript: str,
    entities: Optional[Dict[str, List[str]]] = None,
    patient_history_context: Optional[Dict[str, Any]] = None,
    mode: str = "demo",
) -> Dict[str, str]:

    generator = SOAPGenerator(mode=mode)

    return generator.generate(
        transcript=transcript,
        entities=entities,
        patient_history_context=patient_history_context,
    )


# ----------------------------------------------------------------------
# Command-line interface
# ----------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a SOAP note from a transcript."
    )

    parser.add_argument(
        "transcript",
        help="Medical consultation transcript.",
    )

    parser.add_argument(
        "--entities",
        default=None,
        help=(
            "Optional path to a JSON file containing "
            "clinical entities."
        ),
    )

    parser.add_argument(
        "--history-context",
        default=None,
        help=(
            "Optional path to a JSON file containing "
            "patient history context."
        ),
    )

    parser.add_argument(
        "--mode",
        default="demo",
        choices=["demo"],
        help="SOAP generation mode.",
    )

    args = parser.parse_args()

    entities = {}

    if args.entities:
        with open(
            args.entities,
            "r",
            encoding="utf-8",
        ) as file:
            entities = json.load(file)

    patient_history_context = None

    if args.history_context:
        with open(
            args.history_context,
            "r",
            encoding="utf-8",
        ) as file:
            patient_history_context = json.load(file)

    result = generate_soap(
        transcript=args.transcript,
        entities=entities,
        patient_history_context=patient_history_context,
        mode=args.mode,
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )