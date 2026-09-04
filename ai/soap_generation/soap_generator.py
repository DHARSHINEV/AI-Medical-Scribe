import json
import re
from typing import Dict, List, Optional


class SOAPGenerator:
    """
    SOAP note generator for MediScribe.

    The generator is designed for the MVP and follows strict
    documentation rules:

    - Uses only information present in the transcript/entities.
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

    @staticmethod
    def _sentence_list(items: List[str]) -> str:
        """Convert extracted items into sentences."""
        if not items:
            return ""

        return ". ".join(
            str(item).strip().rstrip(".")
            for item in items
            if str(item).strip()
        ) + "."

    # ------------------------------------------------------------------
    # Subjective
    # ------------------------------------------------------------------

    def _generate_subjective(
        self,
        transcript: str,
        entities: Dict[str, List[str]],
    ) -> str:
        """
        Generate the Subjective section.

        Subjective information includes:
        - Symptoms
        - Duration
        - Severity
        - Medications mentioned
        - Allergies
        - Relevant patient/family history
        """

        parts = []

        symptoms = entities.get("symptoms", [])
        duration = entities.get("duration", [])
        severity = entities.get("severity", [])
        medications = entities.get("medications", [])
        allergies = entities.get("allergies", [])
        past_history = entities.get("past_medical_history", [])
        family_history = entities.get("family_history", [])

        # Symptoms
        if symptoms:
            parts.append(
                f"Patient reports {self._join(symptoms)}."
            )

        # Duration
        if duration:
            parts.append(
                f"Duration reported: {self._join(duration)}."
            )

        # Severity
        if severity:
            parts.append(
                f"Reported severity descriptors: "
                f"{self._join(severity)}."
            )

        # Current medications
        if medications:
            parts.append(
                f"Current medications mentioned: "
                f"{self._join(medications)}."
            )

        # Allergies
        if allergies:
            parts.append(
                f"Reported allergies: {self._join(allergies)}."
            )
        else:
            # Check transcript for explicit negative allergy statement.
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

        # Past medical history
        if past_history:
            parts.append(
                f"Past medical history mentioned: "
                f"{self._join(past_history)}."
            )

        # Family history
        if family_history:
            parts.append(
                f"Family history mentioned: "
                f"{self._join(family_history)}."
            )

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

        The current MVP does not infer objective findings.
        It only reports information explicitly documented.
        """

        # The current clinical NLP schema does not yet contain
        # structured vital signs, examination findings, labs,
        # or imaging results.

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
    ) -> str:
        """
        Generate the Assessment section.

        IMPORTANT:
        Symptoms are NOT converted into diagnoses.
        A diagnosis is reported only if it was explicitly extracted.
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

        Only explicit plan-related information is reported.

        The system does NOT create new treatment recommendations.
        """

        medications = entities.get("medications", [])
        dosage = entities.get("dosage", [])

        parts = []

        # Split transcript into conversational sentences.
        sentences = re.split(
            r"(?<=[.!?])\s+",
            transcript.strip(),
        )

        plan_keywords = [
            "take",
            "rest",
            "drink",
            "follow up",
            "follow-up",
            "prescribe",
            "prescription",
            "give you",
            "advice",
            "recommended",
            "recommend",
            "medicine",
            "days",
            "fluids",
        ]

        plan_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()

            if not sentence:
                continue

            lower = sentence.lower()

            if any(
                keyword in lower
                for keyword in plan_keywords
            ):
                if sentence.lower() not in [
                    item.lower()
                    for item in plan_sentences
                ]:
                    plan_sentences.append(sentence)

        # Explicit plan information from transcript
        if plan_sentences:
            parts.append(
                "Explicit plan information: "
                + " ".join(plan_sentences)
            )

        # Medication information
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
    ) -> Dict[str, str]:
        """
        Generate a deterministic SOAP note for the MVP demo.

        This mode does not require an external LLM/API.
        """

        return {
            "subjective": self._generate_subjective(
                transcript,
                entities,
            ),
            "objective": self._generate_objective(
                transcript,
                entities,
            ),
            "assessment": self._generate_assessment(
                transcript,
                entities,
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
    ) -> Dict[str, str]:
        """
        Generate a structured SOAP note.

        Args:
            transcript:
                Medical consultation transcript.

            entities:
                Clinical entities extracted by the clinical NLP module.

        Returns:
            Dictionary containing:
                subjective
                objective
                assessment
                plan
        """

        if not transcript or not transcript.strip():
            raise ValueError(
                "Transcript cannot be empty."
            )

        if entities is None:
            entities = {}

        if self.mode == "demo":
            return self.generate_demo(
                transcript,
                entities,
            )

        # Future LLM/API implementation can be added here.
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
    mode: str = "demo",
) -> Dict[str, str]:
    """
    Convenience function used by the AI pipeline.
    """

    generator = SOAPGenerator(mode=mode)

    return generator.generate(
        transcript=transcript,
        entities=entities,
    )


# ----------------------------------------------------------------------
# Command-line interface
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

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
        "--mode",
        default="demo",
        choices=["demo"],
        help="SOAP generation mode.",
    )

    args = parser.parse_args()

    # Load entities if supplied.
    entities = {}

    if args.entities:
        with open(
            args.entities,
            "r",
            encoding="utf-8",
        ) as file:
            entities = json.load(file)

    result = generate_soap(
        transcript=args.transcript,
        entities=entities,
        mode=args.mode,
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )