from datetime import datetime, timezone
import pytest
from sqlalchemy import select

from app.models.clinical_alert import ClinicalAlert
from app.models.clinical_entity import ClinicalEntity
from app.models.clinical_note import ClinicalNote
from app.models.consultation import Consultation
from app.models.patient import Patient
from app.models.transcript import TranscriptSegment
from app.models.user import User
from app.services import (
    clinical_service,
    consultation_service,
    note_service,
    safety_service,
    transcription_service,
)


@pytest.fixture
def sample_patient(db_session):
    patient = Patient(
        mrn="MRN-TEST-57",
        name="Asha Sharma",
        age=32,
        gender="female",
        allergies=["Penicillin"],
        conditions=["Asthma"],
        medications=[],
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


@pytest.fixture
def sample_consultation(db_session, sample_patient, test_doctor):
    consultation = Consultation(
        patient_id=sample_patient.id,
        doctor_id=test_doctor.id,
        status="draft",
        stage="idle",
    )
    db_session.add(consultation)
    db_session.commit()
    db_session.refresh(consultation)
    return consultation


def test_transcript_persistence(db_session, sample_consultation):
    """Test persisting transcript segments with proper speaker, timestamps and consultation_id."""
    segments = [
        TranscriptSegment(
            consultation_id=sample_consultation.id,
            speaker="Doctor",
            text="Good morning, Asha. How are you feeling today?",
            start_time=0.0,
            end_time=3.5,
            confidence=0.95,
        ),
        TranscriptSegment(
            consultation_id=sample_consultation.id,
            speaker="Patient",
            text="I have had a severe headache for three days and no fever.",
            start_time=3.6,
            end_time=7.2,
            confidence=0.92,
        ),
    ]
    for seg in segments:
        db_session.add(seg)
    db_session.commit()

    saved = list(
        db_session.scalars(
            select(TranscriptSegment).where(
                TranscriptSegment.consultation_id == sample_consultation.id
            )
        ).all()
    )
    assert len(saved) == 2
    assert saved[0].speaker == "Doctor"
    assert saved[1].speaker == "Patient"
    assert "headache" in saved[1].text


def test_clinical_entity_persistence_with_negation(
    db_session, sample_consultation
):
    """Test clinical entity extraction and persistence respecting schema column 'type' and negation."""
    # Seed transcript
    seg1 = TranscriptSegment(
        consultation_id=sample_consultation.id,
        speaker="Doctor",
        text="Do you have any allergies or fever?",
        start_time=0.0,
        end_time=2.0,
    )
    seg2 = TranscriptSegment(
        consultation_id=sample_consultation.id,
        speaker="Patient",
        text="I have a headache for three days, but no fever and no allergies.",
        start_time=2.1,
        end_time=6.0,
    )
    db_session.add_all([seg1, seg2])
    db_session.commit()
    db_session.refresh(seg1)
    db_session.refresh(seg2)

    entities = clinical_service.extract_clinical_entities(
        db=db_session, consultation=sample_consultation
    )

    assert len(entities) > 0

    # Verify column 'type' exists on all entities and check negation
    types = [e.type for e in entities]
    assert "symptom" in types

    fever_entity = next((e for e in entities if e.value == "fever"), None)
    assert fever_entity is not None
    assert fever_entity.status == "absent"  # Negated: "no fever"
    assert fever_entity.evidence_segment_id == seg2.id
    assert fever_entity.consultation_id == sample_consultation.id


def test_soap_note_persistence_unapproved_initially(
    db_session, sample_consultation
):
    """Test SOAP note generation produces exactly 1 active note initially marked unapproved."""
    seg = TranscriptSegment(
        consultation_id=sample_consultation.id,
        speaker="Patient",
        text="I have a terrible headache for three days. My father had heart disease.",
        start_time=0.0,
        end_time=5.0,
    )
    db_session.add(seg)
    db_session.commit()

    note = note_service.generate_soap_note(
        db=db_session, consultation=sample_consultation
    )

    assert note is not None
    assert note.consultation_id == sample_consultation.id
    assert len(note.subjective) > 0
    assert len(note.plan) > 0
    assert note.approved is False
    assert note.approved_by is None
    assert note.approved_at is None

    # Check total count is 1
    count = db_session.query(ClinicalNote).filter_by(
        consultation_id=sample_consultation.id
    ).count()
    assert count == 1


def test_safety_alert_persistence_including_allergy_conflict(
    db_session, sample_consultation
):
    """Test that safety checker produces and persists high-severity allergy conflict alert."""
    # Asha has Penicillin allergy stored in DB.
    # Consultation transcript contains explicit allergy denial: "No, I don't."
    seg1 = TranscriptSegment(
        consultation_id=sample_consultation.id,
        speaker="Doctor",
        text="Do you have any allergies?",
        start_time=0.0,
        end_time=2.0,
    )
    seg2 = TranscriptSegment(
        consultation_id=sample_consultation.id,
        speaker="Patient",
        text="No, I don't.",
        start_time=2.1,
        end_time=3.5,
    )
    db_session.add_all([seg1, seg2])
    db_session.commit()

    output = safety_service.validate_consultation_safety(
        db=db_session, consultation=sample_consultation
    )

    alerts = output["alerts"]
    assert len(alerts) > 0

    allergy_alerts = [a for a in alerts if a.type == "allergy_conflict"]
    assert len(allergy_alerts) == 1
    assert allergy_alerts[0].severity == "High"
    assert allergy_alerts[0].requires_review is True
    assert allergy_alerts[0].resolved is False
    assert "penicillin" in allergy_alerts[0].detail.lower()


def test_lifecycle_stage_and_status_transitions(
    db_session, sample_consultation, test_doctor
):
    """
    Test the complete stage lifecycle:
    uploaded -> transcribing -> transcribed -> extracting -> extracted
    -> generating -> generated -> safety_check -> review -> approved.
    Status moves from processing -> review -> approved.
    """
    # 1. Uploaded
    consultation_service.update_audio(
        db_session, sample_consultation, "uploads/test.mp3"
    )
    assert sample_consultation.stage == "uploaded"
    assert sample_consultation.status == "draft"

    # Seed transcript
    seg = TranscriptSegment(
        consultation_id=sample_consultation.id,
        speaker="Patient",
        text="I have a headache.",
        start_time=0.0,
        end_time=2.0,
    )
    db_session.add(seg)
    db_session.commit()

    # 2. Extracting & Extracted
    clinical_service.extract_clinical_entities(
        db_session, sample_consultation
    )
    assert sample_consultation.stage == "extracted"
    assert sample_consultation.status == "processing"

    # 3. Generating & Generated
    note_service.generate_soap_note(db_session, sample_consultation)
    assert sample_consultation.stage == "generated"
    assert sample_consultation.status == "processing"

    # 4. Safety Check & Review
    safety_service.validate_consultation_safety(
        db_session, sample_consultation
    )
    assert sample_consultation.stage == "review"
    assert sample_consultation.status == "review"

    # Resolve any review-required alerts before approval
    for a in sample_consultation.alerts:
        if a.requires_review:
            a.resolved = True
    db_session.commit()

    # 5. Doctor approval
    consultation_service.approve_consultation(
        db_session, sample_consultation, approved_by=test_doctor.id
    )
    assert sample_consultation.stage == "approved"
    assert sample_consultation.status == "approved"
    assert sample_consultation.approved_by == test_doctor.id
    assert sample_consultation.approved_at is not None


def test_idempotent_rerun(db_session, sample_consultation):
    """Test re-running stages multiple times does not produce duplicate records."""
    seg = TranscriptSegment(
        consultation_id=sample_consultation.id,
        speaker="Patient",
        text="I have a headache for two days.",
        start_time=0.0,
        end_time=3.0,
    )
    db_session.add(seg)
    db_session.commit()

    # Run 1
    clinical_service.extract_clinical_entities(
        db_session, sample_consultation
    )
    note_service.generate_soap_note(db_session, sample_consultation)
    safety_service.validate_consultation_safety(
        db_session, sample_consultation
    )

    ent_count_1 = db_session.query(ClinicalEntity).filter_by(
        consultation_id=sample_consultation.id
    ).count()
    note_count_1 = db_session.query(ClinicalNote).filter_by(
        consultation_id=sample_consultation.id
    ).count()
    alert_count_1 = db_session.query(ClinicalAlert).filter_by(
        consultation_id=sample_consultation.id
    ).count()

    assert ent_count_1 > 0
    assert note_count_1 == 1
    assert alert_count_1 > 0

    # Run 2 (Rerun)
    clinical_service.extract_clinical_entities(
        db_session, sample_consultation
    )
    note_service.generate_soap_note(db_session, sample_consultation)
    safety_service.validate_consultation_safety(
        db_session, sample_consultation
    )

    ent_count_2 = db_session.query(ClinicalEntity).filter_by(
        consultation_id=sample_consultation.id
    ).count()
    note_count_2 = db_session.query(ClinicalNote).filter_by(
        consultation_id=sample_consultation.id
    ).count()
    alert_count_2 = db_session.query(ClinicalAlert).filter_by(
        consultation_id=sample_consultation.id
    ).count()

    assert ent_count_1 == ent_count_2
    assert note_count_2 == 1
    assert alert_count_1 == alert_count_2
