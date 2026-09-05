import re
from typing import Any, Dict, List, Optional


class ClinicalEntityExtractor:
    """
    Clinical Information Extractor for MediScribe.

    Extracts:
        - symptoms
        - diseases / conditions
        - allergies
        - medications
        - dosage
        - duration
        - severity
        - past medical history
        - family history
        - findings

    NOTE ON IMPLEMENTATION HONESTY:
    This is a rule-based MVP clinical NLP extractor using regular expressions,
    dictionary matching, and contextual negation detection.
    It does not diagnose patients or replace a trained medical NLP pipeline.
    """

    def __init__(self):
        self.symptoms = [
            "headache",
            "sore throat",
            "fever",
            "cough",
            "coughing",
            "wheezing",
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
            "chills",
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
            "copd",
            "cancer",
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
            "albuterol",
            "inhaler",
            "steroids",
            "lisinopril",
            "atorvastatin",
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

        self.findings = [
            "wheezing on auscultation",
            "elevated blood pressure",
            "normal heart rate",
            "clear breath sounds",
            "red throat",
            "pharyngeal erythema",
            "normal temperature",
        ]

        # Negation triggers
        self.negation_patterns = [
            r"\bno\b",
            r"\bnot\b",
            r"\bdenies\b",
            r"\bdenied\b",
            r"\bwithout\b",
            r"\bnegative for\b",
            r"\bnever had\b",
            r"\bno history of\b",
            r"\brule out\b",
            r"\bdoesn't have\b",
            r"\bdoes not have\b",
            r"\bdon't have\b",
            r"\bdo not have\b",
            r"\bfree of\b",
        ]

        # Uncertainty triggers
        self.uncertain_patterns = [
            r"\bpossible\b",
            r"\bpossibly\b",
            r"\bmaybe\b",
            r"\buncertain\b",
            r"\bsuspected\b",
            r"\bquestionable\b",
            r"\bunclear\b",
        ]

    @staticmethod
    def _contains_term(text: str, term: str) -> bool:
        """Check whether a term exists as a complete word/phrase."""
        pattern = rf"\b{re.escape(term)}\b"
        return bool(re.search(pattern, text, re.IGNORECASE))

    @staticmethod
    def _clean_list(values: List[str]) -> List[str]:
        """Remove duplicates while preserving order."""
        result: List[str] = []
        for value in values:
            value = value.strip()
            if value and value.lower() not in [item.lower() for item in result]:
                result.append(value)
        return result

    def _is_negated(self, sentence_or_clause: str, term: str) -> bool:
        """
        Check if a term in a sentence is preceded or modified by a negation trigger.
        Example: 'No fever', 'denies chest pain', 'does not have fever'.
        """
        pattern = rf"(?:{'|'.join(self.negation_patterns)})\s+(?:[\w\s]{{0,25}}?)\b{re.escape(term)}\b"
        if re.search(pattern, sentence_or_clause, re.IGNORECASE):
            return True

        # Check immediate reverse patterns like 'fever: none' or 'fever is absent'
        reverse_pattern = rf"\b{re.escape(term)}\b\s+(?:is\s+)?(?:absent|none|negative)"
        if re.search(reverse_pattern, sentence_or_clause, re.IGNORECASE):
            return True

        return False

    def _is_uncertain(self, sentence_or_clause: str, term: str) -> bool:
        pattern = rf"(?:{'|'.join(self.uncertain_patterns)})\s+(?:[\w\s]{{0,25}}?)\b{re.escape(term)}\b"
        return bool(re.search(pattern, sentence_or_clause, re.IGNORECASE))

    # ------------------------------------------------------------------
    # Dict-based extraction (retained for backward compatibility)
    # ------------------------------------------------------------------

    def _extract_symptoms(self, text: str) -> List[str]:
        symptoms = []
        for symptom in self.symptoms:
            if self._contains_term(text, symptom):
                symptoms.append(symptom)
        return self._clean_list(symptoms)

    def _extract_diseases(self, text: str) -> List[str]:
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
            patient_text = re.sub(pattern, "", patient_text, flags=re.IGNORECASE)

        diseases = []
        for disease in self.diseases:
            if self._contains_term(patient_text, disease):
                diseases.append(disease)
        return self._clean_list(diseases)

    def _extract_allergies(self, text: str) -> List[str]:
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
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                value = match.strip()
                value = re.sub(
                    r"\b(and|but|because|so|with|which)\b.*$",
                    "",
                    value,
                    flags=re.IGNORECASE,
                ).strip()
                if value:
                    allergies.append(value)
        return self._clean_list(allergies)

    def _extract_medications(self, text: str) -> List[str]:
        medications = []
        for medication in self.medications:
            if self._contains_term(text, medication):
                medications.append(medication)
        return self._clean_list(medications)

    def _extract_dosage(self, text: str) -> List[str]:
        dosage_patterns = [
            r"\b\d+(?:\.\d+)?\s*(?:mg|g|mcg|ml|mL|milligram|milligrams|gram|grams|microgram|micrograms)\b",
            r"\b\d+\s*(?:tablet|tablets|capsule|capsules|pill|pills)\b",
            r"\b(?:once|twice|three times|four times)\s+a\s+day\b",
            r"\b\d+\s+times\s+a\s+day\b",
            r"\bevery\s+\d+\s+hours?\b",
        ]
        dosages = []
        for pattern in dosage_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                val = match.group(0).strip()
                if val:
                    dosages.append(val)
        return self._clean_list(dosages)

    def _extract_duration(self, text: str) -> List[str]:
        number = r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
        unit = r"(?:day|days|week|weeks|month|months|year|years|hour|hours)"
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
            for match in re.finditer(pattern, text, re.IGNORECASE):
                val = match.group(0).strip()
                if val and val.lower() not in [d.lower() for d in durations]:
                    durations.append(val)
        return durations

    def _extract_severity(self, text: str) -> List[str]:
        severity = []
        for term in self.severity_terms:
            if self._contains_term(text, term):
                severity.append(term)
        return self._clean_list(severity)

    def _extract_past_medical_history(self, text: str) -> List[str]:
        history = []
        history_patterns = [
            r"\bhistory of ([^.?!]+)",
            r"\bpast medical history includes ([^.?!]+)",
            r"\bpreviously diagnosed with ([^.?!]+)",
            r"\bI have had ([^.?!]+) for years\b",
            r"\bI had ([^.?!]+) in the past",
            r"\bI have ([a-zA-Z\s]+)\b",
        ]
        for pattern in history_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                val = match.strip()
                for disease in self.diseases:
                    if self._contains_term(val, disease):
                        history.append(disease)
        return self._clean_list(history)

    def _extract_family_history(self, text: str) -> List[str]:
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
        for pattern in family_patterns:
            for match in re.findall(pattern, text, re.IGNORECASE):
                for disease in self.diseases:
                    if self._contains_term(match, disease):
                        family_history.append(disease)
        return self._clean_list(family_history)

    def extract(self, text: str) -> Dict[str, List[str]]:
        """Legacy dict-based extraction for backward compatibility with tests/pipeline."""
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

    # ------------------------------------------------------------------
    # Rich Structured Extraction with Negation & Evidence Linking
    # ------------------------------------------------------------------

    def extract_structured(
        self,
        text: str,
        segments: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract structured ClinicalEntity records with:
        - type: 'symptom' | 'condition' | 'medication' | 'allergy' | 'finding' | 'duration' | 'severity'
        - value: normalized string
        - status: 'present' | 'absent' | 'uncertain' | 'historical'
        - evidence_segment_id: ID of transcript segment if available
        - confidence: None (no invented confidence scores)
        """
        if not text or not text.strip():
            return []

        structured_entities: List[Dict[str, Any]] = []
        seen_keys = set()

        # Break text into segments or sentences for evidence and clause analysis
        clauses_with_ids: List[Dict[str, Any]] = []
        if segments:
            for seg in segments:
                seg_id = seg.get("id")
                seg_text = seg.get("text", "")
                for sentence in re.split(r"(?<=[.?!])\s+", seg_text):
                    sentence = sentence.strip()
                    if sentence:
                        clauses_with_ids.append({"text": sentence, "segment_id": seg_id})
        else:
            for sentence in re.split(r"(?<=[.?!])\s+", text):
                sentence = sentence.strip()
                if sentence:
                    clauses_with_ids.append({"text": sentence, "segment_id": None})

        # Track symptom results to resolve negation across clauses
        symptom_results: Dict[str, Dict[str, Any]] = {}

        for item in clauses_with_ids:
            sentence = item["text"]
            seg_id = item["segment_id"]
            is_question = sentence.endswith("?") or bool(
                re.match(r"^\s*(do|does|did|are|is|have|has|any)\b", sentence, re.IGNORECASE)
            )

            # 1. Symptoms
            for symptom in self.symptoms:
                if self._contains_term(sentence, symptom):
                    if self._is_negated(sentence, symptom):
                        # Negation explicitly found ("No fever") -> absent takes highest precedence
                        symptom_results[symptom.lower()] = {
                            "type": "symptom",
                            "value": symptom,
                            "label": symptom.title(),
                            "status": "absent",
                            "confidence": None,
                            "evidence_segment_id": seg_id,
                        }
                    elif not is_question and symptom.lower() not in symptom_results:
                        status = "uncertain" if self._is_uncertain(sentence, symptom) else "present"
                        symptom_results[symptom.lower()] = {
                            "type": "symptom",
                            "value": symptom,
                            "label": symptom.title(),
                            "status": status,
                            "confidence": None,
                            "evidence_segment_id": seg_id,
                        }

            # 2. Conditions / Diseases
            for disease in self.diseases:
                if self._contains_term(sentence, disease):
                    is_family = bool(
                        re.search(
                            r"\b(father|mother|brother|sister|grandfather|grandmother|family)\b",
                            sentence,
                            re.IGNORECASE,
                        )
                    )
                    status = "present"
                    if is_family:
                        status = "historical"
                    elif self._is_negated(sentence, disease):
                        status = "absent"
                    elif re.search(
                        r"\b(history of|past|previously diagnosed|known)\b",
                        sentence,
                        re.IGNORECASE,
                    ):
                        status = "historical"

                    key = ("condition", disease.lower(), status)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        structured_entities.append(
                            {
                                "type": "condition",
                                "value": disease,
                                "label": disease.title(),
                                "status": status,
                                "confidence": None,
                                "evidence_segment_id": seg_id,
                            }
                        )

            # 3. Medications
            for med in self.medications:
                if self._contains_term(sentence, med):
                    status = "present"
                    if self._is_negated(sentence, med):
                        status = "absent"
                    elif self._is_uncertain(sentence, med):
                        status = "uncertain"

                    key = ("medication", med.lower(), status)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        structured_entities.append(
                            {
                                "type": "medication",
                                "value": med,
                                "label": med.title(),
                                "status": status,
                                "confidence": None,
                                "evidence_segment_id": seg_id,
                            }
                        )

            # 4. Allergies
            allergy_match = re.search(
                r"\ballergic to ([a-zA-Z0-9\- ]+)", sentence, re.IGNORECASE
            )
            if allergy_match:
                allergy_val = re.sub(
                    r"\b(and|but|because|so|with|which)\b.*$",
                    "",
                    allergy_match.group(1),
                    flags=re.IGNORECASE,
                ).strip()
                if allergy_val:
                    key = ("allergy", allergy_val.lower(), "present")
                    if key not in seen_keys:
                        seen_keys.add(key)
                        structured_entities.append(
                            {
                                "type": "allergy",
                                "value": allergy_val,
                                "label": f"Allergic to {allergy_val.title()}",
                                "status": "present",
                                "confidence": None,
                                "evidence_segment_id": seg_id,
                            }
                        )

            # 5. Duration
            durations = self._extract_duration(sentence)
            for dur in durations:
                key = ("duration", dur.lower(), "present")
                if key not in seen_keys:
                    seen_keys.add(key)
                    structured_entities.append(
                        {
                            "type": "finding",
                            "value": dur,
                            "label": f"Duration: {dur}",
                            "status": "present",
                            "confidence": None,
                            "evidence_segment_id": seg_id,
                        }
                    )

            # 6. Severity
            for sev in self.severity_terms:
                if self._contains_term(sentence, sev):
                    key = ("severity", sev.lower(), "present")
                    if key not in seen_keys:
                        seen_keys.add(key)
                        structured_entities.append(
                            {
                                "type": "finding",
                                "value": sev,
                                "label": f"Severity: {sev}",
                                "status": "present",
                                "confidence": None,
                                "evidence_segment_id": seg_id,
                            }
                        )

        for sym_data in symptom_results.values():
            structured_entities.append(sym_data)

        return structured_entities


def extract_entities(text: str) -> Dict[str, List[str]]:
    """Convenience function used by the AI pipeline."""
    extractor = ClinicalEntityExtractor()
    return extractor.extract(text)
