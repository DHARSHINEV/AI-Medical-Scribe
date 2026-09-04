import re
from typing import Dict, List


class ClinicalEntityExtractor:
    """
    Lightweight clinical information extractor for the MediScribe MVP.

    Extracts:
        - symptoms
        - diseases
        - allergies
        - medications
        - dosage
        - duration
        - severity
        - past medical history
        - family history

    This is a rule-based MVP component.
    It does not diagnose the patient.
    """

    def __init__(self):
        self.symptoms = [
            "headache",
            "sore throat",
            "fever",
            "cough",
            "cold",
            "fatigue",
            "tiredness",
            "dizziness",
            "nausea",
            "vomiting",
            "diarrhea",
            "stomach pain",
            "abdominal pain",
            "chest pain",
            "back pain",
            "body pain",
            "shortness of breath",
            "breathing difficulty",
            "runny nose",
            "blocked nose",
            "weakness",
            "pain",
            "itching",
            "rash",
            "swelling",
        ]

        self.diseases = [
            "diabetes",
            "hypertension",
            "asthma",
            "migraine",
            "arthritis",
            "pneumonia",
            "bronchitis",
            "gastritis",
            "ulcer",
            "covid",
            "covid-19",
            "flu",
            "influenza",
            "heart disease",
            "kidney disease",
            "liver disease",
            "thyroid disease",
        ]

        self.medications = [
            "paracetamol",
            "acetaminophen",
            "ibuprofen",
            "aspirin",
            "amoxicillin",
            "azithromycin",
            "metformin",
            "insulin",
            "omeprazole",
            "pantoprazole",
            "cetirizine",
            "antibiotics",
            "painkillers",
            "pain killer",
            "medicine",
            "medication",
        ]

        self.severity_terms = [
            "mild",
            "moderate",
            "severe",
            "little",
            "slight",
            "slightly",
            "high",
            "low",
            "very high",
            "very severe",
            "bad",
            "worst",
        ]

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _contains_term(text: str, term: str) -> bool:
        """
        Check whether a term exists as a complete word/phrase.
        """
        pattern = rf"\b{re.escape(term)}\b"
        return bool(re.search(pattern, text, re.IGNORECASE))

    @staticmethod
    def _clean_list(values: List[str]) -> List[str]:
        """
        Remove duplicates while preserving order.
        """
        result = []

        for value in values:
            value = value.strip()

            if value and value.lower() not in [
                item.lower() for item in result
            ]:
                result.append(value)

        return result

    # ------------------------------------------------------------------
    # Symptoms
    # ------------------------------------------------------------------

    def _extract_symptoms(self, text: str) -> List[str]:
        symptoms = []

        for symptom in self.symptoms:
            if self._contains_term(text, symptom):
                symptoms.append(symptom)

        return self._clean_list(symptoms)

    # ------------------------------------------------------------------
    # Diseases
    # ------------------------------------------------------------------

    def _extract_diseases(self, text: str) -> List[str]:
        """
        Extract diseases while avoiding diseases mentioned only
        as family history.

        Example:
            "My father has diabetes."

        should produce:
            family_history = ["diabetes"]

        and NOT:
            diseases = ["diabetes"]
        """

        diseases = []

        # Remove family-history sentences before extracting
        # patient diseases.
        family_patterns = [
            r"\bmy father\b[^.?!]*",
            r"\bmy mother\b[^.?!]*",
            r"\bmy brother\b[^.?!]*",
            r"\bmy sister\b[^.?!]*",
            r"\bmy grandfather\b[^.?!]*",
            r"\bmy grandmother\b[^.?!]*",
            r"\bfather\b[^.?!]*",
            r"\bmother\b[^.?!]*",
            r"\bbrother\b[^.?!]*",
            r"\bsister\b[^.?!]*",
            r"\bfamily\b[^.?!]*",
        ]

        patient_text = text

        for pattern in family_patterns:
            patient_text = re.sub(
                pattern,
                "",
                patient_text,
                flags=re.IGNORECASE,
            )

        for disease in self.diseases:
            if self._contains_term(patient_text, disease):
                diseases.append(disease)

        return self._clean_list(diseases)

    # ------------------------------------------------------------------
    # Allergies
    # ------------------------------------------------------------------

    def _extract_allergies(self, text: str) -> List[str]:
        """
        Extract allergy information.

        The MVP explicitly handles negative statements such as:

            "I do not have any allergies."
            "No allergies."
            "I have no allergies."

        These produce an empty allergy list.
        """

        negative_patterns = [
            r"\bno allergies\b",
            r"\bno known allergies\b",
            r"\bdo not have any allergies\b",
            r"\bdon't have any allergies\b",
            r"\bdo not have allergies\b",
            r"\bdon't have allergies\b",
            r"\bno allergy\b",
            r"\bnot allergic to anything\b",
        ]

        for pattern in negative_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return []

        allergies = []

        allergy_patterns = [
            r"\ballergic to ([a-zA-Z0-9\- ]+)",
            r"\ballergy to ([a-zA-Z0-9\- ]+)",
            r"\ballergies to ([a-zA-Z0-9\- ]+)",
        ]

        for pattern in allergy_patterns:
            matches = re.findall(
                pattern,
                text,
                re.IGNORECASE,
            )

            for match in matches:
                value = match.strip()

                # Remove common trailing words.
                value = re.sub(
                    r"\b(and|but|because|so|with|which)\b.*$",
                    "",
                    value,
                    flags=re.IGNORECASE,
                ).strip()

                if value:
                    allergies.append(value)

        return self._clean_list(allergies)

    # ------------------------------------------------------------------
    # Medications
    # ------------------------------------------------------------------

    def _extract_medications(self, text: str) -> List[str]:
        medications = []

        for medication in self.medications:
            if self._contains_term(text, medication):
                medications.append(medication)

        return self._clean_list(medications)

    # ------------------------------------------------------------------
    # Dosage
    # ------------------------------------------------------------------

    def _extract_dosage(self, text: str) -> List[str]:
        """
        Extract common dosage expressions.

        Examples:
            500 mg
            10 mg
            5 ml
            1 tablet
            2 tablets
            twice a day
            three times a day
        """

        dosage_patterns = [
            r"\b\d+(?:\.\d+)?\s*(?:mg|g|mcg|ml|mL|milligram|milligrams|"
            r"gram|grams|microgram|micrograms)\b",

            r"\b\d+\s*(?:tablet|tablets|capsule|capsules|pill|pills)\b",

            r"\b(?:once|twice|three times|four times)\s+a\s+day\b",

            r"\b\d+\s+times\s+a\s+day\b",

            r"\bevery\s+\d+\s+hours?\b",
        ]

        dosages = []

        for pattern in dosage_patterns:
            matches = re.finditer(
                pattern,
                text,
                re.IGNORECASE,
            )

            for match in matches:
                value = match.group(0).strip()

                if value:
                    dosages.append(value)

        return self._clean_list(dosages)

    # ------------------------------------------------------------------
    # Duration
    # ------------------------------------------------------------------

    def _extract_duration(self, text: str) -> List[str]:
        """
        Extract duration expressions such as:

        - for three days
        - for about three days
        - for 3 days
        - for about 3 days
        - for a week
        - for an hour
        - since yesterday
        - since today
        - three days ago
        """

        number = (
            r"(?:"
            r"\d+|"
            r"one|two|three|four|five|six|seven|"
            r"eight|nine|ten|eleven|twelve"
            r")"
        )

        unit = (
            r"(?:"
            r"day|days|week|weeks|month|months|year|years|"
            r"hour|hours"
            r")"
        )

        patterns = [
            rf"\bfor about {number} {unit}\b",
            rf"\bfor {number} {unit}\b",
            rf"\bfor about (?:a|an|one) {unit}\b",
            rf"\bfor (?:a|an|one) {unit}\b",
            r"\bsince (?:yesterday|today|last night|last week|last month)\b",
            rf"\b{number} {unit} ago\b",
        ]

        durations = []

        for pattern in patterns:
            matches = re.finditer(
                pattern,
                text,
                re.IGNORECASE,
            )

            for match in matches:
                value = match.group(0).strip()

                if value and value.lower() not in [
                    item.lower() for item in durations
                ]:
                    durations.append(value)

        return durations

    # ------------------------------------------------------------------
    # Severity
    # ------------------------------------------------------------------

    def _extract_severity(self, text: str) -> List[str]:
        severity = []

        for term in self.severity_terms:
            if self._contains_term(text, term):
                severity.append(term)

        return self._clean_list(severity)

    # ------------------------------------------------------------------
    # Past Medical History
    # ------------------------------------------------------------------

    def _extract_past_medical_history(self, text: str) -> List[str]:
        """
        Extract diseases/conditions explicitly mentioned as
        past medical history.

        Example:
            "I have a history of asthma."

        -> ["asthma"]
        """

        history = []

        history_patterns = [
            r"\bhistory of ([^.?!]+)",
            r"\bpast medical history includes ([^.?!]+)",
            r"\bpreviously diagnosed with ([^.?!]+)",
            r"\bI had ([^.?!]+) in the past",
        ]

        for pattern in history_patterns:
            matches = re.findall(
                pattern,
                text,
                re.IGNORECASE,
            )

            for match in matches:
                value = match.strip()

                for disease in self.diseases:
                    if self._contains_term(value, disease):
                        history.append(disease)

        return self._clean_list(history)

    # ------------------------------------------------------------------
    # Family History
    # ------------------------------------------------------------------

    def _extract_family_history(self, text: str) -> List[str]:
        """
        Extract diseases/conditions mentioned in family history.

        Examples:

            "My father has diabetes."

            -> ["diabetes"]

            "My mother has hypertension."

            -> ["hypertension"]
        """

        family_history = []

        family_patterns = [
            r"\bmy father\b[^.?!]*",
            r"\bmy mother\b[^.?!]*",
            r"\bmy brother\b[^.?!]*",
            r"\bmy sister\b[^.?!]*",
            r"\bmy grandfather\b[^.?!]*",
            r"\bmy grandmother\b[^.?!]*",
            r"\bmy family\b[^.?!]*",
            r"\bfamily history\b[^.?!]*",
        ]

        family_sentences = []

        for pattern in family_patterns:
            matches = re.findall(
                pattern,
                text,
                re.IGNORECASE,
            )

            family_sentences.extend(matches)

        for sentence in family_sentences:
            for disease in self.diseases:
                if self._contains_term(sentence, disease):
                    family_history.append(disease)

        return self._clean_list(family_history)

    # ------------------------------------------------------------------
    # Main extraction
    # ------------------------------------------------------------------

    def extract(self, text: str) -> Dict[str, List[str]]:
        """
        Extract all supported clinical entities.
        """

        if not isinstance(text, str):
            raise TypeError("text must be a string")

        if not text.strip():
            return {
                "symptoms": [],
                "diseases": [],
                "allergies": [],
                "medications": [],
                "dosage": [],
                "duration": [],
                "severity": [],
                "past_medical_history": [],
                "family_history": [],
            }

        return {
            "symptoms": self._extract_symptoms(text),
            "diseases": self._extract_diseases(text),
            "allergies": self._extract_allergies(text),
            "medications": self._extract_medications(text),
            "dosage": self._extract_dosage(text),
            "duration": self._extract_duration(text),
            "severity": self._extract_severity(text),
            "past_medical_history": self._extract_past_medical_history(text),
            "family_history": self._extract_family_history(text),
        }


# ----------------------------------------------------------------------
# Convenience function
# ----------------------------------------------------------------------

def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Convenience function used by the MediScribe AI pipeline.
    """

    extractor = ClinicalEntityExtractor()

    return extractor.extract(text)


# ----------------------------------------------------------------------
# Command-line testing
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Extract clinical entities from text."
    )

    parser.add_argument(
        "text",
        help="Clinical conversation text to analyze.",
    )

    args = parser.parse_args()

    result = extract_entities(args.text)

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )