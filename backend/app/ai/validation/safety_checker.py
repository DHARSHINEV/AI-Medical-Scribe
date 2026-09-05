import re
from typing import Any, Dict, List, Optional


class SafetyChecker:
    """
    Clinical Second Look / Safety Validation Layer for MediScribe.

    NOTE ON IMPLEMENTATION HONESTY:
    This MVP component uses deterministic clinical verification rules, cross-referencing
    consultation statements, extracted entities, and stored patient medical history.
    It does NOT implement autonomous diagnosis, medication prescribing, or dosing decisions.
    All alerts are phrased strictly as verification/review prompts for the clinician.
    """

    def __init__(self):
        # Known cross-allergy mappings (e.g. penicillin allergy vs penicillin/amoxicillin/ampicillin)
        self.allergy_cross_reactions = {
            "penicillin": [
                "penicillin",
                "amoxicillin",
                "ampicillin",
                "augmentin",
                "piperacillin",
            ],
            "sulfa": [
                "sulfa",
                "sulfamethoxazole",
                "bactrim",
                "septra",
            ],
            "aspirin": [
                "aspirin",
                "ibuprofen",
                "naproxen",
                "nsaids",
            ],
        }

    @staticmethod
    def _normalize(value: Any) -> str:
        return " ".join(str(value).strip().lower().split())

    @classmethod
    def _contains_match(cls, item: str, values: List[str]) -> bool:
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

    @staticmethod
    def _join(values: List[str]) -> str:
        cleaned = [str(v).strip() for v in values if str(v).strip()]
        if not cleaned:
            return ""
        if len(cleaned) == 1:
            return cleaned[0]
        if len(cleaned) == 2:
            return f"{cleaned[0]} and {cleaned[1]}"
        return ", ".join(cleaned[:-1]) + f", and {cleaned[-1]}"

    # ------------------------------------------------------------------
    # Allergy and Medication-Allergy Conflict Checks
    # ------------------------------------------------------------------

    def check_allergies(
        self,
        entities: Dict[str, Any],
        patient_history_context: Dict[str, Any],
        transcript: str,
    ) -> List[Dict[str, Any]]:
        alerts = []
        prev_hist = patient_history_context.get("previous_patient_history", {})
        stored_allergies = prev_hist.get("allergies", [])
        current_allergies = entities.get("allergies", [])
        current_medications = entities.get("medications", [])
        transcript_lower = transcript.lower()

        # 1. Stored allergy confirmed in consultation
        if stored_allergies and current_allergies:
            for stored_allergy in stored_allergies:
                if self._contains_match(stored_allergy, current_allergies):
                    alerts.append(
                        {
                            "type": "allergy_consistent",
                            "title": f"Allergy Confirmed: {stored_allergy.title()}",
                            "detail": f"Current consultation confirms previously documented allergy: {stored_allergy}.",
                            "message": f"Current consultation confirms previously documented allergy: {stored_allergy}.",
                            "severity": "Low",
                            "requires_review": False,
                        }
                    )

        # 2. Conflict: Stored allergy vs patient denying allergies in consultation
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
            phrase in transcript_lower for phrase in negative_allergy_patterns
        )

        if has_negative_allergy and stored_allergies:
            alerts.append(
                {
                    "type": "allergy_conflict",
                    "title": "Allergy Conflict Detected",
                    "detail": (
                        f"Stored patient history lists {self._join(stored_allergies)} as an allergy, "
                        "while current consultation reports no known allergies. Verify before approval."
                    ),
                    "message": (
                        f"Stored patient history lists {self._join(stored_allergies)} as an allergy, "
                        "while current consultation reports no known allergies."
                    ),
                    "severity": "High",
                    "requires_review": True,
                }
            )

        # 3. Medication-Allergy Cross-Reaction Conflict
        all_allergies = list(set(stored_allergies + current_allergies))
        for allergy in all_allergies:
            norm_allergy = self._normalize(allergy)
            # Find conflicting drug families
            conflicting_drugs = []
            for allergen_family, drugs in self.allergy_cross_reactions.items():
                if allergen_family in norm_allergy or norm_allergy in allergen_family:
                    conflicting_drugs.extend(drugs)

            if not conflicting_drugs:
                conflicting_drugs.append(norm_allergy)

            for med in current_medications:
                norm_med = self._normalize(med)
                if any(
                    drug in norm_med or norm_med in drug for drug in conflicting_drugs
                ):
                    alerts.append(
                        {
                            "type": "allergy_conflict",
                            "title": "Potential Medication-Allergy Conflict",
                            "detail": (
                                f"Patient has documented allergy to '{allergy}', but '{med}' was mentioned "
                                "in consultation. Verify safety before approval."
                            ),
                            "message": (
                                f"Potential conflict between documented allergy '{allergy}' and medication '{med}'. "
                                "Verify before approval."
                            ),
                            "severity": "High",
                            "requires_review": True,
                        }
                    )

        return alerts

    # ------------------------------------------------------------------
    # Medication Consistency & Uncertainty Checks
    # ------------------------------------------------------------------

    def check_medications(
        self,
        entities: Dict[str, Any],
        patient_history_context: Dict[str, Any],
        transcript: str,
    ) -> List[Dict[str, Any]]:
        alerts = []
        prev_hist = patient_history_context.get("previous_patient_history", {})
        previous_medications = prev_hist.get("medications", [])
        current_medications = entities.get("medications", [])

        for current_medication in current_medications:
            if self._contains_match(current_medication, previous_medications):
                alerts.append(
                    {
                        "type": "medication_consistent",
                        "title": f"Medication Ongoing: {current_medication.title()}",
                        "detail": f"Medication '{current_medication}' is already present in previous medication history.",
                        "message": f"Medication '{current_medication}' is already present in previous medication history.",
                        "severity": "Low",
                        "requires_review": False,
                    }
                )

        # Detect uncertain medication usage ("maybe taking", "might have taken")
        uncertain_patterns = [
            r"\b(maybe|not sure if|might be|forgot name of)\s+([\w\s]{1,30})?(medicine|medication|pill|tablet)\b",
            r"\btaking something for\b",
        ]
        for pat in uncertain_patterns:
            if re.search(pat, transcript, re.IGNORECASE):
                alerts.append(
                    {
                        "type": "uncertain_medication",
                        "title": "Uncertain Medication Statement",
                        "detail": "Patient mentioned taking an unconfirmed or uncertain medication. Clarification recommended.",
                        "message": "Patient mentioned taking an unconfirmed medication. Verify details before note approval.",
                        "severity": "Medium",
                        "requires_review": True,
                    }
                )
                break

        return alerts

    # ------------------------------------------------------------------
    # Missing Information / Documentation Gaps
    # ------------------------------------------------------------------

    def check_missing_information(
        self,
        entities: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        alerts = []
        symptoms = entities.get("symptoms", [])
        duration = entities.get("duration", [])
        medications = entities.get("medications", [])

        if symptoms and not duration:
            alerts.append(
                {
                    "type": "missing_duration",
                    "title": "Documentation Gap: Symptom Duration Missing",
                    "detail": "Symptoms were documented, but their duration was not captured in the conversation.",
                    "message": "Symptoms were documented, but their duration was not captured.",
                    "severity": "Medium",
                    "requires_review": True,
                }
            )

        if symptoms and not medications:
            alerts.append(
                {
                    "type": "medication_information_missing",
                    "title": "Documentation Gap: Medication Status Not Captured",
                    "detail": "No current medication status was captured in the consultation.",
                    "message": "No current medication information was captured in the consultation.",
                    "severity": "Low",
                    "requires_review": True,
                }
            )

        return alerts

    # ------------------------------------------------------------------
    # History Consistency Checks
    # ------------------------------------------------------------------

    def check_history_consistency(
        self,
        entities: Dict[str, Any],
        patient_history_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        alerts = []
        prev_hist = patient_history_context.get("previous_patient_history", {})
        previous_diseases = prev_hist.get("diseases", [])
        current_diseases = entities.get("diseases", [])

        for disease in previous_diseases:
            if not self._contains_match(disease, current_diseases):
                alerts.append(
                    {
                        "type": "historical_condition",
                        "title": f"Historical Condition: {disease.title()}",
                        "detail": f"Previously documented condition: {disease}. Review for relevance to current visit.",
                        "message": f"Previously documented condition: {disease}. Review for relevance to the current consultation.",
                        "severity": "Low",
                        "requires_review": False,
                    }
                )

        return alerts

    # ------------------------------------------------------------------
    # Main Safety Validation
    # ------------------------------------------------------------------

    def check(
        self,
        transcript: str,
        entities: Dict[str, Any],
        patient_history_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not isinstance(transcript, str):
            raise TypeError("transcript must be a string.")
        if not isinstance(entities, dict):
            raise TypeError("entities must be a dictionary.")
        if not isinstance(patient_history_context, dict):
            raise TypeError("patient_history_context must be a dictionary.")

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
                transcript=transcript,
            )
        )
        alerts.extend(self.check_missing_information(entities=entities))
        alerts.extend(
            self.check_history_consistency(
                entities=entities,
                patient_history_context=patient_history_context,
            )
        )

        high_alerts = [
            a
            for a in alerts
            if a.get("severity") in ("high", "High")
        ]
        review_required = any(a.get("requires_review", False) for a in alerts)

        return {
            "alerts": alerts,
            "alert_count": len(alerts),
            "high_priority_alert_count": len(high_alerts),
            "review_required": review_required,
        }


def run_safety_checks(
    transcript: str,
    entities: Dict[str, Any],
    patient_history_context: Dict[str, Any],
) -> Dict[str, Any]:
    checker = SafetyChecker()
    return checker.check(
        transcript=transcript,
        entities=entities,
        patient_history_context=patient_history_context,
    )
