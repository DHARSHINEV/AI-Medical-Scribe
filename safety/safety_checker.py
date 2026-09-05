from typing import Any, Dict, List


class SafetyChecker:
    """
    Safety and consistency checker for MediScribe.

    The safety layer compares:
    - Current consultation information
    - Previously documented patient history
    - Current medications and allergies

    It does not diagnose the patient and does not create
    treatment recommendations.
    """

    def __init__(self):
        pass

    @staticmethod
    def _normalize(value: str) -> str:
        """Normalize text for comparison."""

        return " ".join(
            str(value).strip().lower().split()
        )

    @classmethod
    def _contains_match(
        cls,
        item: str,
        values: List[str],
    ) -> bool:
        """Check whether an item approximately matches any value."""

        normalized_item = cls._normalize(item)

        for value in values:
            normalized_value = cls._normalize(value)

            if (
                normalized_item == normalized_value
                or normalized_item in normalized_value
                or normalized_value in normalized_item
            ):
                return True

        return False

    # ------------------------------------------------------------------
    # Allergy checks
    # ------------------------------------------------------------------

    def check_allergies(
        self,
        entities: Dict[str, Any],
        patient_history_context: Dict[str, Any],
        transcript: str,
    ) -> List[Dict[str, Any]]:
        """
        Detect conflicts between stored allergies and
        current consultation allergy statements.
        """

        alerts = []

        previous_history = patient_history_context.get(
            "previous_patient_history",
            {},
        )

        stored_allergies = previous_history.get(
            "allergies",
            [],
        )

        current_allergies = entities.get(
            "allergies",
            [],
        )

        transcript_lower = transcript.lower()

        # Explicit current positive allergies
        if stored_allergies and current_allergies:
            for stored_allergy in stored_allergies:
                if self._contains_match(
                    stored_allergy,
                    current_allergies,
                ):
                    alerts.append(
                        {
                            "type": "allergy_consistent",
                            "severity": "info",
                            "message": (
                                f"Current consultation confirms "
                                f"the previously documented allergy: "
                                f"{stored_allergy}."
                            ),
                            "requires_review": False,
                        }
                    )

        # Detect explicit negative allergy statements
        negative_allergy_patterns = [
    "no allergies",
    "no known allergies",
    "no allergy",
    "not allergic",
    "don't have any allergies",
    "do not have any allergies",
    "no, i don't",
    "no i don't",
]

        has_negative_allergy = any(
            phrase in transcript_lower
            for phrase in negative_allergy_patterns
        )

        if has_negative_allergy and stored_allergies:
            alerts.append(
                {
                    "type": "allergy_conflict",
                    "severity": "high",
                    "message": (
                        "Stored patient history lists "
                        f"{self._join(stored_allergies)} "
                        "as an allergy, while the current "
                        "consultation reports no known allergies."
                    ),
                    "requires_review": True,
                }
            )

        return alerts

    # ------------------------------------------------------------------
    # Medication checks
    # ------------------------------------------------------------------

    def check_medications(
        self,
        entities: Dict[str, Any],
        patient_history_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Compare current medications with previously documented
        medications.
        """

        alerts = []

        previous_history = patient_history_context.get(
            "previous_patient_history",
            {},
        )

        previous_medications = previous_history.get(
            "medications",
            [],
        )

        current_medications = entities.get(
            "medications",
            [],
        )

        if not previous_medications or not current_medications:
            return alerts

        for current_medication in current_medications:
            if self._contains_match(
                current_medication,
                previous_medications,
            ):
                alerts.append(
                    {
                        "type": "medication_consistent",
                        "severity": "info",
                        "message": (
                            f"Medication '{current_medication}' "
                            "is already present in the patient's "
                            "previous medication history."
                        ),
                        "requires_review": False,
                    }
                )

        return alerts

    # ------------------------------------------------------------------
    # Missing information checks
    # ------------------------------------------------------------------

    def check_missing_information(
        self,
        entities: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Identify important information that is absent from
        the current consultation.

        These are review flags, not diagnoses.
        """

        alerts = []

        symptoms = entities.get(
            "symptoms",
            [],
        )

        duration = entities.get(
            "duration",
            [],
        )

        medications = entities.get(
            "medications",
            [],
        )

        if symptoms and not duration:
            alerts.append(
                {
                    "type": "missing_duration",
                    "severity": "medium",
                    "message": (
                        "Symptoms were documented, but "
                        "their duration was not captured."
                    ),
                    "requires_review": True,
                }
            )

        if symptoms and not medications:
            alerts.append(
                {
                    "type": "medication_information_missing",
                    "severity": "low",
                    "message": (
                        "No current medication information "
                        "was captured in the consultation."
                    ),
                    "requires_review": True,
                }
            )

        return alerts

    # ------------------------------------------------------------------
    # History consistency checks
    # ------------------------------------------------------------------

    def check_history_consistency(
        self,
        entities: Dict[str, Any],
        patient_history_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Check whether current and historical information
        may need clinician review.
        """

        alerts = []

        previous_history = patient_history_context.get(
            "previous_patient_history",
            {},
        )

        previous_diseases = previous_history.get(
            "diseases",
            [],
        )

        current_diseases = entities.get(
            "diseases",
            [],
        )

        # Report previously documented conditions that are
        # relevant historical context, without treating them
        # as new diagnoses.
        for disease in previous_diseases:
            if not self._contains_match(
                disease,
                current_diseases,
            ):
                alerts.append(
                    {
                        "type": "historical_condition",
                        "severity": "info",
                        "message": (
                            f"Previously documented condition: "
                            f"{disease}. Review for relevance "
                            "to the current consultation."
                        ),
                        "requires_review": False,
                    }
                )

        return alerts

    # ------------------------------------------------------------------
    # Main safety check
    # ------------------------------------------------------------------

    def check(
        self,
        transcript: str,
        entities: Dict[str, Any],
        patient_history_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run all MediScribe safety checks.
        """

        if not isinstance(
            transcript,
            str,
        ):
            raise TypeError(
                "transcript must be a string."
            )

        if not isinstance(
            entities,
            dict,
        ):
            raise TypeError(
                "entities must be a dictionary."
            )

        if not isinstance(
            patient_history_context,
            dict,
        ):
            raise TypeError(
                "patient_history_context must be a dictionary."
            )

        alerts: List[Dict[str, Any]] = []

        alerts.extend(
            self.check_allergies(
                entities=entities,
                patient_history_context=patient_history_context,
                transcript=transcript,
            )
        )

        alerts.extend(
            self.check_medications(
                entities=entities,
                patient_history_context=patient_history_context,
            )
        )

        alerts.extend(
            self.check_missing_information(
                entities=entities,
            )
        )

        alerts.extend(
            self.check_history_consistency(
                entities=entities,
                patient_history_context=patient_history_context,
            )
        )

        high_alerts = [
            alert
            for alert in alerts
            if alert.get("severity") == "high"
        ]

        review_required = any(
            alert.get("requires_review", False)
            for alert in alerts
        )

        return {
            "alerts": alerts,
            "alert_count": len(alerts),
            "high_priority_alert_count": len(high_alerts),
            "review_required": review_required,
        }

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _join(values: List[str]) -> str:
        """Convert a list into readable text."""

        cleaned = [
            str(value).strip()
            for value in values
            if str(value).strip()
        ]

        if not cleaned:
            return ""

        if len(cleaned) == 1:
            return cleaned[0]

        if len(cleaned) == 2:
            return f"{cleaned[0]} and {cleaned[1]}"

        return ", ".join(
            cleaned[:-1]
        ) + f", and {cleaned[-1]}"


def run_safety_checks(
    transcript: str,
    entities: Dict[str, Any],
    patient_history_context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convenience function for the MediScribe pipeline.
    """

    checker = SafetyChecker()

    return checker.check(
        transcript=transcript,
        entities=entities,
        patient_history_context=patient_history_context,
    )


# ----------------------------------------------------------------------
# Standalone test
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import json

    example_transcript = (
        "Do you have any allergies? "
        "No, I don't."
    )

    example_entities = {
        "symptoms": ["headache"],
        "diseases": [],
        "allergies": [],
        "medications": ["painkillers"],
        "dosage": [],
        "duration": ["three days"],
        "severity": ["mild"],
        "past_medical_history": [],
        "family_history": [],
    }

    example_history_context = {
        "previous_patient_history": {
            "diseases": [
                "diabetes",
                "hypertension",
            ],
            "allergies": [
                "penicillin",
            ],
            "medications": [
                "metformin",
            ],
            "past_medical_history": [
                "diabetes",
            ],
        },
        "family_history": [
            "heart disease",
        ],
    }

    result = run_safety_checks(
        transcript=example_transcript,
        entities=example_entities,
        patient_history_context=example_history_context,
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )