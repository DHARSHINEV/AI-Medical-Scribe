from datetime import datetime, timezone, timedelta
import pytest
from app.models.patient import Patient
from app.models.consultation import Consultation
from app.models.clinical_note import ClinicalNote
from app.models.transcript import TranscriptSegment
from app.models.clinical_entity import ClinicalEntity
from app.models.clinical_alert import ClinicalAlert
from app.services import audit_service


def _get_auth_headers(client, email="doctor@mediscribe.com", password="doctor123"):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _setup_canonical_approved_consultation(db_session, test_doctor):
    """Helper to populate patient, approved consultation, note, segments, entities, alerts, and audit logs."""
    patient = Patient(
        name="Asha Patel",
        mrn="MRN-HIST-001",
        age=44,
        gender="female",
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    now = datetime.now(timezone.utc)
    consultation = Consultation(
        patient_id=patient.id,
        doctor_id=test_doctor.id,
        status="approved",
        stage="approved",
        approved_by=test_doctor.id,
        approved_at=now,
        created_at=now - timedelta(hours=2),
        updated_at=now,
    )
    db_session.add(consultation)
    db_session.commit()
    db_session.refresh(consultation)

    note = ClinicalNote(
        consultation_id=consultation.id,
        subjective="Patient reports 3-day history of dry cough and mild shortness of breath.",
        objective="Vitals: BP 120/80, HR 72, SpO2 98%. Lungs clear to auscultation.",
        assessment="Acute bronchitis, mild.",
        plan="Hydration, rest, inhaler PRN. Follow up in 7 days if symptoms persist.",
        approved=True,
        approved_by=test_doctor.id,
        approved_at=now,
        created_at=now - timedelta(hours=1),
        updated_at=now,
    )
    db_session.add(note)

    # Transcript segments
    seg1 = TranscriptSegment(
        consultation_id=consultation.id,
        speaker="Doctor",
        text="Good morning Asha, how are you feeling today?",
        start_time=0.0,
        end_time=3.5,
    )
    seg2 = TranscriptSegment(
        consultation_id=consultation.id,
        speaker="Patient",
        text="I have had a dry cough for three days.",
        start_time=3.8,
        end_time=7.2,
    )
    db_session.add_all([seg1, seg2])

    # Clinical entities
    e1 = ClinicalEntity(
        consultation_id=consultation.id,
        type="symptom",
        value="dry cough",
        label="Cough",
        status="present",
        confidence=0.96,
        evidence_segment_id=None,
    )
    e2 = ClinicalEntity(
        consultation_id=consultation.id,
        type="condition",
        value="bronchitis",
        label="Bronchitis",
        status="present",
        confidence=0.91,
        evidence_segment_id=None,
    )
    db_session.add_all([e1, e2])

    # Safety alert (historical, resolved)
    alert = ClinicalAlert(
        consultation_id=consultation.id,
        type="documentation_gap",
        title="Documentation Gap: Symptom Duration Missing",
        detail="Check duration of cough symptom.",
        severity="medium",
        requires_review=True,
        resolved=True,
    )
    db_session.add(alert)
    db_session.commit()

    # Audit log entries
    audit_service.log_event(
        db=db_session,
        action="TRANSCRIPTION_COMPLETED",
        user_id=test_doctor.id,
        consultation_id=consultation.id,
        details={"segment_count": 2},
    )
    audit_service.log_event(
        db=db_session,
        action="CLINICAL_EXTRACTION_COMPLETED",
        user_id=test_doctor.id,
        consultation_id=consultation.id,
        details={"entity_count": 2},
    )
    audit_service.log_event(
        db=db_session,
        action="SOAP_GENERATED",
        user_id=test_doctor.id,
        consultation_id=consultation.id,
        details={"note_id": note.id},
    )
    audit_service.log_event(
        db=db_session,
        action="SAFETY_ALERT_RESOLVED",
        user_id=test_doctor.id,
        consultation_id=consultation.id,
        details={"alert_id": alert.id, "resolved": True},
    )
    audit_service.log_event(
        db=db_session,
        action="CONSULTATION_APPROVED",
        user_id=test_doctor.id,
        consultation_id=consultation.id,
        details={"note_id": note.id, "approved_at": now.isoformat()},
    )

    return patient, consultation, note, alert


def test_patient_consultation_history(client, db_session, test_doctor):
    patient, consultation, _, _ = _setup_canonical_approved_consultation(db_session, test_doctor)

    res = client.get(f"/api/patients/{patient.id}/consultations")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 1

    item = data[0]
    assert item["id"] == consultation.id
    assert item["patient_id"] == patient.id
    assert item["doctor_id"] == test_doctor.id
    assert item["status"] == "approved"
    assert item["stage"] == "approved"
    assert item["approved_by"] == test_doctor.id
    assert item["approved_at"] is not None
    assert "created_at" in item
    assert "updated_at" in item


def test_consultation_detail(client, db_session, test_doctor):
    _, consultation, _, _ = _setup_canonical_approved_consultation(db_session, test_doctor)

    res = client.get(f"/api/consultations/{consultation.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == consultation.id
    assert data["status"] == "approved"
    assert data["stage"] == "approved"
    assert data["approved_by"] == test_doctor.id
    assert data["approved_at"] is not None


def test_approved_soap_retrieval(client, db_session, test_doctor):
    _, consultation, note, _ = _setup_canonical_approved_consultation(db_session, test_doctor)

    res = client.get(f"/api/consultations/{consultation.id}/note")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == note.id
    assert data["consultation_id"] == consultation.id
    assert data["subjective"] == note.subjective
    assert data["objective"] == note.objective
    assert data["assessment"] == note.assessment
    assert data["plan"] == note.plan
    assert data["approved"] is True
    assert data["approved_by"] == test_doctor.id
    assert data["approved_at"] is not None
    assert "created_at" in data
    assert "updated_at" in data


def test_transcript_retrieval(client, db_session, test_doctor):
    _, consultation, _, _ = _setup_canonical_approved_consultation(db_session, test_doctor)

    res = client.get(f"/api/consultations/{consultation.id}/transcript")
    assert res.status_code == 200
    segments = res.json()
    assert len(segments) == 2
    assert segments[0]["consultation_id"] == consultation.id
    assert segments[0]["speaker"] == "Doctor"
    assert segments[0]["start_time"] == 0.0
    assert segments[1]["speaker"] == "Patient"
    assert segments[1]["start_time"] == 3.8
    assert segments[0]["start_time"] < segments[1]["start_time"]


def test_clinical_entity_retrieval(client, db_session, test_doctor):
    _, consultation, _, _ = _setup_canonical_approved_consultation(db_session, test_doctor)

    # Test /clinical_entities
    res = client.get(f"/api/consultations/{consultation.id}/clinical_entities")
    assert res.status_code == 200
    entities = res.json()
    assert len(entities) == 2
    e_types = [e["type"] for e in entities]
    assert "symptom" in e_types
    assert "condition" in e_types
    for e in entities:
        assert "type" in e
        assert "value" in e
        assert "label" in e
        assert "status" in e
        assert "confidence" in e
        assert "evidence_segment_id" in e

    # Test /clinical-entities compatibility alias
    res_alias = client.get(f"/api/consultations/{consultation.id}/clinical-entities")
    assert res_alias.status_code == 200
    assert len(res_alias.json()) == 2


def test_safety_history_retrieval(client, db_session, test_doctor):
    _, consultation, _, alert = _setup_canonical_approved_consultation(db_session, test_doctor)

    res = client.get(f"/api/consultations/{consultation.id}/safety")
    assert res.status_code == 200
    data = res.json()
    assert data["consultation_id"] == consultation.id
    assert data["alert_count"] == 1
    # Alert was resolved, so review_required should be False
    assert data["review_required"] is False
    assert len(data["alerts"]) == 1
    assert data["alerts"][0]["id"] == alert.id
    assert data["alerts"][0]["resolved"] is True
    assert data["alerts"][0]["requires_review"] is True

    # Call it a second time to ensure no alerts are duplicated or regenerated
    res2 = client.get(f"/api/consultations/{consultation.id}/safety")
    assert res2.json()["alert_count"] == 1


def test_audit_history_retrieval(client, db_session, test_doctor):
    _, consultation, _, _ = _setup_canonical_approved_consultation(db_session, test_doctor)

    res = client.get(f"/api/consultations/{consultation.id}/audit")
    assert res.status_code == 200
    audit_logs = res.json()
    assert len(audit_logs) >= 5

    actions = [a["action"] for a in audit_logs]
    assert "TRANSCRIPTION_COMPLETED" in actions
    assert "CLINICAL_EXTRACTION_COMPLETED" in actions
    assert "SOAP_GENERATED" in actions
    assert "SAFETY_ALERT_RESOLVED" in actions
    assert "CONSULTATION_APPROVED" in actions

    for log in audit_logs:
        assert "action" in log
        assert "user_id" in log
        assert "consultation_id" in log
        assert "details" in log
        assert "created_at" in log
        assert log["consultation_id"] == consultation.id


def test_approved_note_modification_blocked(client, db_session, test_doctor):
    _, consultation, _, _ = _setup_canonical_approved_consultation(db_session, test_doctor)
    headers = _get_auth_headers(client)

    update_payload = {
        "assessment": "Modified assessment after approval"
    }
    res = client.put(f"/api/consultations/{consultation.id}/note", json=update_payload, headers=headers)
    assert res.status_code in (400, 409)
    assert "Approved notes cannot be modified without formal revision" in res.json()["detail"]


def test_patient_scoping(client, db_session, test_doctor):
    patient1, consult1, _, _ = _setup_canonical_approved_consultation(db_session, test_doctor)

    patient2 = Patient(
        name="Bob Martin",
        mrn="MRN-HIST-002",
        age=49,
        gender="male",
    )
    db_session.add(patient2)
    db_session.commit()
    db_session.refresh(patient2)

    consult2 = Consultation(
        patient_id=patient2.id,
        doctor_id=test_doctor.id,
        status="review",
        stage="review",
    )
    db_session.add(consult2)
    db_session.commit()

    # Patient 1 should only see consult1
    res1 = client.get(f"/api/patients/{patient1.id}/consultations")
    assert res1.status_code == 200
    data1 = res1.json()
    assert len(data1) == 1
    assert data1[0]["id"] == consult1.id
    assert data1[0]["patient_id"] == patient1.id

    # Patient 2 should only see consult2
    res2 = client.get(f"/api/patients/{patient2.id}/consultations")
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2) == 1
    assert data2[0]["id"] == consult2.id
    assert data2[0]["patient_id"] == patient2.id

    # Non-existent patient should return 404
    res_none = client.get("/api/patients/999999/consultations")
    assert res_none.status_code == 404


def test_ordering_of_historical_consultations(client, db_session, test_doctor):
    patient = Patient(
        name="Clara Oswald",
        mrn="MRN-HIST-003",
        age=35,
        gender="female",
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    now = datetime.now(timezone.utc)
    c1 = Consultation(
        patient_id=patient.id,
        status="approved",
        stage="approved",
        created_at=now - timedelta(days=5),
    )
    c2 = Consultation(
        patient_id=patient.id,
        status="approved",
        stage="approved",
        created_at=now - timedelta(days=1),
    )
    c3 = Consultation(
        patient_id=patient.id,
        status="review",
        stage="review",
        created_at=now,
    )
    db_session.add_all([c1, c2, c3])
    db_session.commit()

    res = client.get(f"/api/patients/{patient.id}/consultations")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    # Ordered by created_at desc: c3 (newest), then c2, then c1 (oldest)
    assert data[0]["id"] == c3.id
    assert data[1]["id"] == c2.id
    assert data[2]["id"] == c1.id
