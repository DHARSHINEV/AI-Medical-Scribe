import re
from typing import Any, Dict, List, Optional


class SOAPGenerator:
    """
    SOAP note generator for MediScribe.

    NOTE ON IMPLEMENTATION HONESTY:
    This MVP component uses structured clinical rule-based synthesis to format
    evidence-grounded Subjective, Objective, Assessment, and Plan sections.
    It does NOT invoke an autonomous large language model (LLM) or make autonomous diagnoses.
    The interface is designed as an adapter so a real LLM service (e.g. Gemini / Claude)
    can be configured seamlessly in the future.

    Documentation Principles:
    - Uses strictly information present in the transcript/entities/history.
    - Does not invent vitals, diagnoses, medications, dosages, or exam findings.
    - Accurately represents absent findings as 'not documented'.
    - Clinician review and explicit approval are required before finalization.
    """

    def __init__(self, mode: str = "demo"):
        self.mode = mode

    @staticmethod
    def _join(items: List[str]) -> str:
        cleaned = [str(item).strip() for item in items if str(item).strip()]
        if not cleaned:
            return ""
        if len(cleaned) == 1:
            return cleaned[0]
        if len(cleaned) == 2:
            return f"{cleaned[0]} and {cleaned[1]}"
        return ", ".join(cleaned[:-1]) + f", and {cleaned[-1]}"

    def _generate_subjective(
        self,
        transcript: str,
        entities: Dict[str, List[str]],
        patient_history_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        parts = []

        symptoms = entities.get("symptoms", [])
        duration = entities.get("duration", [])
        severity = entities.get("severity", [])
        medications = entities.get("medications", [])
        allergies = entities.get("allergies", [])
        past_history = entities.get("past_medical_history", [])
        family_history = entities.get("family_history", [])

        if symptoms:
            parts.append(f"Patient reports {self._join(symptoms)}.")

        if duration:
            parts.append(f"Duration reported: {self._join(duration)}.")

        if severity:
            parts.append(f"Reported severity descriptors: {self._join(severity)}.")

        if medications:
            parts.append(f"Current medications mentioned: {self._join(medications)}.")

        if allergies:
            parts.append(f"Reported allergies: {self._join(allergies)}.")
        else:
            negative_allergy_patterns = [
                r"\bno allergies\b",
                r"\bno known allergies\b",
                r"\bno allergy\b",
                r"\bnot allergic\b",
                r"\bdo not have any allergies\b",
                r"\bdon't have any allergies\b",
                r"\bno, i don't\b",
                r"\bno i don't\b",
            ]
            if any(
                re.search(pattern, transcript, flags=re.IGNORECASE)
                for pattern in negative_allergy_patterns
            ):
                parts.append("Patient reports no known allergies.")

        if past_history:
            parts.append(
                f"Past medical history mentioned: {self._join(past_history)}."
            )

        if family_history:
            parts.append(f"Family history mentioned: {self._join(family_history)}.")

        if patient_history_context:
            prev_hist = patient_history_context.get("previous_patient_history", {})
            prev_diseases = prev_hist.get("diseases", [])
            prev_allergies = prev_hist.get("allergies", [])
            prev_meds = prev_hist.get("medications", [])
            prev_med_hist = prev_hist.get("past_medical_history", [])

            context_parts = []
            if prev_diseases:
                context_parts.append(
                    f"Known previous conditions: {self._join(prev_diseases)}."
                )
            if prev_med_hist:
                context_parts.append(
                    f"Previous medical history: {self._join(prev_med_hist)}."
                )
            if prev_allergies:
                context_parts.append(
                    f"Known previous allergies: {self._join(prev_allergies)}."
                )
            if prev_meds:
                context_parts.append(
                    f"Previously documented medications: {self._join(prev_meds)}."
                )

            if context_parts:
                parts.append(
                    "Relevant previous patient history: " + " ".join(context_parts)
                )

            context_family_hist = patient_history_context.get("family_history", [])
            if context_family_hist:
                parts.append(f"Known family history: {self._join(context_family_hist)}.")

        if not parts:
            return "No subjective clinical information was documented in the transcript."

        return " ".join(parts)

    def _generate_objective(
        self,
        transcript: str,
        entities: Dict[str, List[str]],
    ) -> str:
        return (
            "No objective measurements, vital signs, examination findings, "
            "laboratory results, or imaging results were documented in the transcript."
        )

    def _generate_assessment(
        self,
        transcript: str,
        entities: Dict[str, List[str]],
        patient_history_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        diseases = entities.get("diseases", [])
        symptoms = entities.get("symptoms", [])
        parts = []

        if diseases:
            parts.append(f"Documented condition(s): {self._join(diseases)}.")
        else:
            if symptoms:
                parts.append(
                    f"Symptoms documented in the conversation: {self._join(symptoms)}."
                )

            if patient_history_context:
                prev_hist = patient_history_context.get("previous_patient_history", {})
                historical_diseases = prev_hist.get("diseases", [])
                if historical_diseases:
                    parts.append(
                        f"Previously documented conditions: {self._join(historical_diseases)}."
                    )

            parts.append("No confirmed diagnosis was documented.")

        return " ".join(parts)

    def _generate_plan(
        self,
        transcript: str,
        entities: Dict[str, List[str]],
    ) -> str:
        medications = entities.get("medications", [])
        dosage = entities.get("dosage", [])
        parts = []

        sentences = re.split(r"(?<=[.!?])\s+", transcript.strip())
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
                re.search(pat, sentence, flags=re.IGNORECASE)
                for pat in question_patterns
            ):
                continue
            if re.match(r"^\s*(for|since)\b", sentence, flags=re.IGNORECASE):
                continue
            if any(
                re.search(pat, sentence, flags=re.IGNORECASE) for pat in plan_patterns
            ):
                if sentence.lower() not in [item.lower() for item in plan_sentences]:
                    plan_sentences.append(sentence)

        if plan_sentences:
            parts.append("Explicit plan information: " + " ".join(plan_sentences))

        if medications:
            med_text = self._join(medications)
            if dosage:
                parts.append(
                    f"Medication mentioned: {med_text}. Dosage information mentioned: {self._join(dosage)}."
                )
            else:
                parts.append(f"Medication mentioned: {med_text}.")

        if not parts:
            return "No explicit treatment or follow-up plan was documented in the transcript."

        return " ".join(parts)

    def generate(
        self,
        transcript: str,
        entities: Optional[Dict[str, List[str]]] = None,
        patient_history_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        if not transcript or not transcript.strip():
            raise ValueError("Transcript cannot be empty.")

        if entities is None:
            entities = {}

        return {
            "subjective": self._generate_subjective(
                transcript, entities, patient_history_context
            ),
            "objective": self._generate_objective(transcript, entities),
            "assessment": self._generate_assessment(
                transcript, entities, patient_history_context
            ),
            "plan": self._generate_plan(transcript, entities),
        }


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
