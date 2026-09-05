import json
from pathlib import Path

from ai.clinical_nlp.entity_extractor import ClinicalEntityExtractor
from ai.patient_history.history_context import (
    build_patient_history_context,
)
from ai.soap_generation.soap_generator import SOAPGenerator
from safety.safety_checker import SafetyChecker


def test_clinical_entity_extraction():
    transcript = (
        "I have a headache and a sore throat. "
        "I have had these symptoms for three days. "
        "I have a fever."
    )

    extractor = ClinicalEntityExtractor()
    entities = extractor.extract(transcript)

    assert "headache" in entities["symptoms"]
    assert "sore throat" in entities["symptoms"]
    assert "fever" in entities["symptoms"]
    assert len(entities["duration"]) > 0


def test_patient_history_context():
    patient_history = {
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
        "family_history": [
            "heart disease",
        ],
    }

    current_entities = {
        "symptoms": [
            "headache",
            "fever",
        ],
        "diseases": [],
        "allergies": [],
        "medications": [
            "painkillers",
        ],
        "dosage": [],
        "duration": [
            "three days",
        ],
        "severity": [
            "mild",
        ],
        "past_medical_history": [],
        "family_history": [],
    }

    context = build_patient_history_context(
        patient_history=patient_history,
        current_entities=current_entities,
    )

    assert "diabetes" in context["relevant_context"]["diseases"]
    assert "hypertension" in context["relevant_context"]["diseases"]
    assert "penicillin" in context["relevant_context"]["allergies"]
    assert "metformin" in context["relevant_context"]["medications"]
    assert "painkillers" in context["relevant_context"]["medications"]
    assert "heart disease" in context["family_history"]


def test_soap_generation_uses_history_context():
    transcript = (
        "I have a headache and a fever. "
        "I have had this for three days."
    )

    entities = {
        "symptoms": [
            "headache",
            "fever",
        ],
        "diseases": [],
        "allergies": [],
        "medications": [
            "painkillers",
        ],
        "dosage": [],
        "duration": [
            "three days",
        ],
        "severity": [],
        "past_medical_history": [],
        "family_history": [],
    }

    history_context = {
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

    generator = SOAPGenerator(mode="demo")

    soap = generator.generate(
        transcript=transcript,
        entities=entities,
        patient_history_context=history_context,
    )

    assert "headache" in soap["subjective"]
    assert "fever" in soap["subjective"]
    assert "diabetes" in soap["subjective"]
    assert "hypertension" in soap["subjective"]
    assert "penicillin" in soap["subjective"]
    assert "metformin" in soap["subjective"]
    assert "heart disease" in soap["subjective"]


def test_allergy_conflict_detection():
    transcript = (
        "Do you have any allergies? "
        "No, I don't."
    )

    entities = {
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

    history_context = {
        "previous_patient_history": {
            "diseases": [],
            "allergies": [
                "penicillin",
            ],
            "medications": [],
            "past_medical_history": [],
        },
        "family_history": [],
    }

    checker = SafetyChecker()

    safety = checker.check(
        transcript=transcript,
        entities=entities,
        patient_history_context=history_context,
    )

    assert safety["review_required"] is True
    assert safety["high_priority_alert_count"] == 1

    allergy_alerts = [
        alert
        for alert in safety["alerts"]
        if alert["type"] == "allergy_conflict"
    ]

    assert len(allergy_alerts) == 1
    assert allergy_alerts[0]["severity"] == "high"
    assert allergy_alerts[0]["requires_review"] is True


def test_negative_allergy_without_history():
    transcript = (
        "Do you have any allergies? "
        "No, I don't."
    )

    entities = {
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

    history_context = {
        "previous_patient_history": {
            "diseases": [],
            "allergies": [],
            "medications": [],
            "past_medical_history": [],
        },
        "family_history": [],
    }

    checker = SafetyChecker()

    safety = checker.check(
        transcript=transcript,
        entities=entities,
        patient_history_context=history_context,
    )

    assert not any(
        alert["type"] == "allergy_conflict"
        for alert in safety["alerts"]
    )


def test_historical_conditions_are_not_new_diagnoses():
    transcript = (
        "I have a headache and sore throat."
    )

    entities = {
        "symptoms": [
            "headache",
            "sore throat",
        ],
        "diseases": [],
        "allergies": [],
        "medications": [],
        "dosage": [],
        "duration": [],
        "severity": [],
        "past_medical_history": [],
        "family_history": [],
    }

    history_context = {
        "previous_patient_history": {
            "diseases": [
                "diabetes",
            ],
            "allergies": [],
            "medications": [],
            "past_medical_history": [
                "diabetes",
            ],
        },
        "family_history": [],
    }

    generator = SOAPGenerator(mode="demo")

    soap = generator.generate(
        transcript=transcript,
        entities=entities,
        patient_history_context=history_context,
    )

    assert "No confirmed diagnosis was documented." in soap["assessment"]
    assert "Previously documented conditions: diabetes." in soap["assessment"]


def test_demo_pipeline_result_file_exists():
    result_path = Path(
        "demo-data"
    ) / "pipeline_result.json"

    assert result_path.exists()

    with open(
        result_path,
        "r",
        encoding="utf-8",
    ) as file:
        result = json.load(file)

    assert "transcript" in result
    assert "entities" in result
    assert "patient_history_context" in result
    assert "soap" in result
    assert "safety" in result
    assert "review" in result

    assert result["review"]["status"] == "pending"
    assert result["review"]["approved"] is False