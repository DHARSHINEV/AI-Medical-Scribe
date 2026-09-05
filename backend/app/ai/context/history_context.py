from typing import Any, Dict, List, Optional


class PatientHistoryContext:
    """
    Patient History Context component for MediScribe.
    Combines previously documented patient history (from database or dict)
    with information extracted from the current consultation.

    This component organizes context for SOAP synthesis and safety validation;
    it does not diagnose or modify patient medical records.
    """

    @staticmethod
    def _clean_list(values: List[str]) -> List[str]:
        result: List[str] = []
        for value in values:
            if not isinstance(value, str):
                continue
            val = value.strip()
            if val and val.lower() not in [item.lower() for item in result]:
                result.append(val)
        return result

    @classmethod
    def from_patient_model(cls, patient: Any) -> Dict[str, Any]:
        """Convert a SQLAlchemy Patient model instance into a normalized history dict."""
        if patient is None:
            return {}

        return {
            "mrn": getattr(patient, "mrn", None),
            "name": getattr(patient, "name", None),
            "age": getattr(patient, "age", None),
            "gender": getattr(patient, "gender", None),
            "diseases": list(getattr(patient, "conditions", []) or []),
            "allergies": list(getattr(patient, "allergies", []) or []),
            "medications": list(getattr(patient, "medications", []) or []),
            "past_medical_history": list(getattr(patient, "conditions", []) or []),
            "family_history": [],
        }

    def build_context(
        self,
        patient_history: Optional[Dict[str, Any]],
        current_entities: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        """Build structured patient history context."""
        if patient_history is None:
            patient_history = {}

        if not isinstance(patient_history, dict):
            raise TypeError("patient_history must be a dictionary or None.")

        if not isinstance(current_entities, dict):
            raise TypeError("current_entities must be a dictionary.")

        previous_diseases = patient_history.get("diseases", [])
        previous_allergies = patient_history.get("allergies", [])
        previous_medications = patient_history.get("medications", [])
        previous_medical_history = patient_history.get("past_medical_history", [])
        previous_family_history = patient_history.get("family_history", [])

        current_diseases = current_entities.get("diseases", [])
        current_allergies = current_entities.get("allergies", [])
        current_medications = current_entities.get("medications", [])
        current_past_history = current_entities.get("past_medical_history", [])
        current_family_history = current_entities.get("family_history", [])

        # Combine previous and current patient history
        relevant_diseases = self._clean_list(
            previous_diseases + current_diseases + current_past_history
        )
        known_allergies = self._clean_list(previous_allergies + current_allergies)
        known_medications = self._clean_list(
            previous_medications + current_medications
        )
        family_history = self._clean_list(
            previous_family_history + current_family_history
        )

        current_symptoms = self._clean_list(current_entities.get("symptoms", []))
        current_duration = self._clean_list(current_entities.get("duration", []))
        current_severity = self._clean_list(current_entities.get("severity", []))
        current_dosage = self._clean_list(current_entities.get("dosage", []))

        return {
            "previous_patient_history": {
                "diseases": self._clean_list(previous_diseases),
                "allergies": self._clean_list(previous_allergies),
                "medications": self._clean_list(previous_medications),
                "past_medical_history": self._clean_list(previous_medical_history),
            },
            "family_history": family_history,
            "current_consultation": {
                "symptoms": current_symptoms,
                "diseases": self._clean_list(current_diseases),
                "allergies": self._clean_list(current_allergies),
                "medications": self._clean_list(current_medications),
                "dosage": current_dosage,
                "duration": current_duration,
                "severity": current_severity,
            },
            "relevant_context": {
                "diseases": relevant_diseases,
                "allergies": known_allergies,
                "medications": known_medications,
                "family_history": family_history,
            },
        }


def build_patient_history_context(
    patient_history: Optional[Dict[str, Any]],
    current_entities: Dict[str, List[str]],
) -> Dict[str, Any]:
    """Convenience helper function for the MediScribe pipeline."""
    context_builder = PatientHistoryContext()
    return context_builder.build_context(
        patient_history=patient_history,
        current_entities=current_entities,
    )
