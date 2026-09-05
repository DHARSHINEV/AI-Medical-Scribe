import pytest
from sqlalchemy import select

from app.core.security import create_access_token, get_password_hash
from app.models.audit_log import AuditLog
from app.models.clinical_alert import ClinicalAlert
from app.models.clinical_note import ClinicalNote
from app.models.consultation import Consultation
from app.models.patient import Patient
from app.models.user import User


@pytest.fixture
def approval_setup(db_session):
    # Clinician: Dr. Sarah Jenkins
    doctor = User(
        name="Dr. Sarah Jenkins",
        email="doctor@mediscribe.com",
        password_hash=get_password_hash("doctor123"),
        role="doctor",
    )
    db_session.add(doctor)
    db_session.commit()
    db_session.refresh(doctor)

    patient = Patient(
        mrn="MRN-APP-510",
        name="David Miller",
        age=45,
        gender="male",
        allergies=[],
        conditions=[],
        medications=[],
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    # Valid review consultation
    c_review = Consultation(
        patient_id=patient.id,
        doctor_id=doctor.id,
        status="review",
        stage="review",
    )
    # Consultation in draft state
    c_draft = Consultation(
        patient_id=patient.id,
        doctor_id=doctor.id,
        status="draft",
        stage="idle",
    )
    db_session.add_all([c_review, c_draft])
    db_session.commit()
    db_session.refresh(c_review)
    db_session.refresh(c_draft)

    # Note for review consultation
    note_review = ClinicalNote(
        consultation_id=c_review.id,
        subjective="Patient reports mild cough.",
        objective="Chest clear.",
        assessment="Upper respiratory tract infection.",
        plan="Hydration and rest.",
        approved=False,
    )
    db_session.add(note_review)
    db_session.commit()
    db_session.refresh(note_review)

    token = create_access_token({"sub": str(doctor.id), "email": doctor.email})
    headers = {"Authorization": f"Bearer {token}"}

    return {
        "doctor": doctor,
        "token": token,
        "headers": headers,
        "patient": patient,
        "c_review": c_review,
        "c_draft": c_draft,
        "note_review": note_review,
    }


def test_successful_authenticated_approval_and_db_persistence(
    client, db_session, approval_setup
):
    c = approval_setup["c_review"]
    headers = approval_setup["headers"]
    doctor = approval_setup["doctor"]

    # Call approval endpoint
    res = client.post(f"/api/consultations/{c.id}/approve", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "approved"
    assert data["stage"] == "approved"
    assert data["approved"] is True
    assert data["approved_by"] == doctor.id
    assert data["approved_at"] is not None

    # Verify directly in SQLite/ORM for both tables
    db_session.expire_all()
    c_db = db_session.get(Consultation, c.id)
    assert c_db.status == "approved"
    assert c_db.stage == "approved"
    assert c_db.approved_by == doctor.id
    assert c_db.approved_at is not None

    note_db = db_session.scalar(
        select(ClinicalNote).where(ClinicalNote.consultation_id == c.id)
    )
    assert note_db.approved is True
    assert note_db.approved_by == doctor.id
    assert note_db.approved_at is not None
    assert note_db.approved_by == c_db.approved_by


def test_unauthenticated_approval_rejected(client, db_session, approval_setup):
    c = approval_setup["c_review"]

    # Call without Authorization header
    res = client.post(f"/api/consultations/{c.id}/approve")
    assert res.status_code == 401
    assert "authentication is required" in res.json()["detail"].lower()

    # DB state must remain unchanged
    db_session.expire_all()
    c_db = db_session.get(Consultation, c.id)
    assert c_db.status == "review"
    assert c_db.stage == "review"
    assert c_db.approved_by is None

    note_db = db_session.scalar(
        select(ClinicalNote).where(ClinicalNote.consultation_id == c.id)
    )
    assert note_db.approved is False
    assert note_db.approved_by is None


def test_missing_clinical_note_rejected(client, db_session, approval_setup):
    doctor = approval_setup["doctor"]
    patient = approval_setup["patient"]
    headers = approval_setup["headers"]

    # Consultation in review state but without note
    c_no_note = Consultation(
        patient_id=patient.id,
        doctor_id=doctor.id,
        status="review",
        stage="review",
    )
    db_session.add(c_no_note)
    db_session.commit()
    db_session.refresh(c_no_note)

    res = client.post(f"/api/consultations/{c_no_note.id}/approve", headers=headers)
    assert res.status_code == 400
    assert "without a generated clinical note" in res.json()["detail"].lower()


def test_unresolved_review_required_alert_blocks_approval(
    client, db_session, approval_setup
):
    c = approval_setup["c_review"]
    headers = approval_setup["headers"]

    # Add an unresolved alert where requires_review = True
    alert = ClinicalAlert(
        consultation_id=c.id,
        type="allergy_conflict",
        title="High Severity Conflict",
        detail="Penicillin allergy conflict detected.",
        severity="High",
        requires_review=True,
        resolved=False,
    )
    db_session.add(alert)
    db_session.commit()

    res = client.post(f"/api/consultations/{c.id}/approve", headers=headers)
    assert res.status_code == 400
    assert "safety alerts require review" in res.json()["detail"].lower()

    # Resolve the alert -> approval should now succeed
    alert.resolved = True
    db_session.commit()

    res2 = client.post(f"/api/consultations/{c.id}/approve", headers=headers)
    assert res2.status_code == 200
    assert res2.json()["approved"] is True


def test_informational_alert_does_not_block_approval(
    client, db_session, approval_setup
):
    c = approval_setup["c_review"]
    headers = approval_setup["headers"]

    # Add only informational alert where requires_review = False
    info_alert = ClinicalAlert(
        consultation_id=c.id,
        type="historical_condition",
        title="Previous Asthma History",
        detail="Patient has history of asthma.",
        severity="Low",
        requires_review=False,
        resolved=False,
    )
    db_session.add(info_alert)
    db_session.commit()

    res = client.post(f"/api/consultations/{c.id}/approve", headers=headers)
    assert res.status_code == 200
    assert res.json()["approved"] is True


def test_invalid_state_rejection(client, approval_setup):
    c_draft = approval_setup["c_draft"]
    headers = approval_setup["headers"]

    res = client.post(f"/api/consultations/{c_draft.id}/approve", headers=headers)
    assert res.status_code == 400
    assert "not in review state" in res.json()["detail"].lower()


def test_cross_consultation_not_found_rejected(client, approval_setup):
    headers = approval_setup["headers"]

    res = client.post("/api/consultations/99999/approve", headers=headers)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_audit_log_verification(client, db_session, approval_setup):
    c = approval_setup["c_review"]
    headers = approval_setup["headers"]
    doctor = approval_setup["doctor"]

    client.post(f"/api/consultations/{c.id}/approve", headers=headers)

    logs = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.consultation_id == c.id,
                AuditLog.action == "CONSULTATION_APPROVED",
            )
        ).all()
    )
    assert len(logs) == 1
    log = logs[0]
    assert log.action == "CONSULTATION_APPROVED"
    assert log.user_id == doctor.id
    assert log.consultation_id == c.id
    assert "note_id" in log.details
    assert "approved_at" in log.details


def test_approval_idempotency_returns_409(client, approval_setup):
    c = approval_setup["c_review"]
    headers = approval_setup["headers"]

    # First approval attempt succeeds
    res1 = client.post(f"/api/consultations/{c.id}/approve", headers=headers)
    assert res1.status_code == 200

    # Second approval attempt returns 409 Conflict
    res2 = client.post(f"/api/consultations/{c.id}/approve", headers=headers)
    assert res2.status_code == 409
    assert "already been approved" in res2.json()["detail"].lower()
