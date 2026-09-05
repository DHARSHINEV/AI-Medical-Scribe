import pytest
from sqlalchemy import select

from app.core.security import create_access_token, get_password_hash
from app.models.audit_log import AuditLog
from app.models.clinical_note import ClinicalNote
from app.models.consultation import Consultation
from app.models.patient import Patient
from app.models.user import User


@pytest.fixture
def soap_setup(db_session, test_doctor):
    # Second doctor for authorization testing
    other_doctor = User(
        name="Dr. Gregory House",
        email="house@mediscribe.com",
        password_hash=get_password_hash("house123"),
        role="doctor",
    )
    db_session.add(other_doctor)
    db_session.commit()
    db_session.refresh(other_doctor)

    patient = Patient(
        mrn="MRN-SOAP-59",
        name="Maya Patel",
        age=28,
        gender="female",
        allergies=[],
        conditions=[],
        medications=[],
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    # Consultation 1 assigned to test_doctor
    c1 = Consultation(
        patient_id=patient.id,
        doctor_id=test_doctor.id,
        status="review",
        stage="review",
    )
    # Consultation 2 assigned to other_doctor
    c2 = Consultation(
        patient_id=patient.id,
        doctor_id=other_doctor.id,
        status="review",
        stage="review",
    )
    db_session.add_all([c1, c2])
    db_session.commit()
    db_session.refresh(c1)
    db_session.refresh(c2)

    # Note 1 for consultation 1
    note1 = ClinicalNote(
        consultation_id=c1.id,
        subjective="Original subjective note.",
        objective="Vitals BP 120/80.",
        assessment="Mild tension headache.",
        plan="Hydration and paracetamol as needed.",
        approved=False,
    )
    db_session.add(note1)
    db_session.commit()
    db_session.refresh(note1)

    token_doctor1 = create_access_token({"sub": str(test_doctor.id), "email": test_doctor.email})
    token_doctor2 = create_access_token({"sub": str(other_doctor.id), "email": other_doctor.email})

    return {
        "doctor1": test_doctor,
        "doctor2": other_doctor,
        "token1": token_doctor1,
        "token2": token_doctor2,
        "c1": c1,
        "c2": c2,
        "note1": note1,
    }


def test_get_soap_note_success_and_404(client, soap_setup):
    c1 = soap_setup["c1"]
    c2 = soap_setup["c2"]

    # 1. Existing note on c1
    res = client.get(f"/api/consultations/{c1.id}/note")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == soap_setup["note1"].id
    assert data["consultation_id"] == c1.id
    assert data["subjective"] == "Original subjective note."
    assert data["objective"] == "Vitals BP 120/80."
    assert data["assessment"] == "Mild tension headache."
    assert data["plan"] == "Hydration and paracetamol as needed."
    assert data["approved"] is False
    assert data["approved_by"] is None
    assert data["approved_at"] is None
    assert data["created_at"] is not None

    # 2. Non-existent note on c2 -> 404
    res2 = client.get(f"/api/consultations/{c2.id}/note")
    assert res2.status_code == 404

    # 3. Non-existent consultation -> 404
    res3 = client.get("/api/consultations/99999/note")
    assert res3.status_code == 404


def test_update_soap_note_contents_and_id_preservation(client, db_session, soap_setup):
    c1 = soap_setup["c1"]
    note1 = soap_setup["note1"]
    headers = {"Authorization": f"Bearer {soap_setup['token1']}"}

    update_payload = {
        "subjective": "Updated subjective: Patient reports headache resolved.",
        "plan": "Continue hydration and rest.",
    }

    res = client.put(
        f"/api/consultations/{c1.id}/note",
        json=update_payload,
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()

    # Same note ID remains
    assert data["id"] == note1.id
    assert data["consultation_id"] == c1.id

    # Contents actually changed
    assert data["subjective"] == "Updated subjective: Patient reports headache resolved."
    assert data["plan"] == "Continue hydration and rest."
    assert data["objective"] == "Vitals BP 120/80."  # Unmodified field preserved

    # Verify directly in DB
    db_session.refresh(note1)
    assert note1.subjective == "Updated subjective: Patient reports headache resolved."
    assert note1.updated_at is not None

    # Verify only 1 note exists in database
    count = db_session.query(ClinicalNote).filter_by(consultation_id=c1.id).count()
    assert count == 1


def test_update_soap_note_remains_unapproved_and_in_review(client, db_session, soap_setup):
    c1 = soap_setup["c1"]
    note1 = soap_setup["note1"]
    headers = {"Authorization": f"Bearer {soap_setup['token1']}"}

    res = client.put(
        f"/api/consultations/{c1.id}/note",
        json={"assessment": "Refined clinical assessment: episodic tension headache."},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()

    # Note remains unapproved
    assert data["approved"] is False
    assert data["approved_by"] is None
    assert data["approved_at"] is None

    # Consultation remains in review stage and status
    db_session.refresh(c1)
    assert c1.status == "review"
    assert c1.stage == "review"


def test_cross_doctor_authorization_rejected(client, soap_setup):
    c1 = soap_setup["c1"]  # belongs to doctor 1
    headers_doctor2 = {"Authorization": f"Bearer {soap_setup['token2']}"}  # doctor 2

    res = client.put(
        f"/api/consultations/{c1.id}/note",
        json={"plan": "Unauthorized edit attempt"},
        headers=headers_doctor2,
    )
    assert res.status_code == 403
    assert "permission" in res.json()["detail"].lower()


def test_audit_log_created_on_note_edit(client, db_session, soap_setup):
    c1 = soap_setup["c1"]
    headers = {"Authorization": f"Bearer {soap_setup['token1']}"}

    client.put(
        f"/api/consultations/{c1.id}/note",
        json={"plan": "New plan: follow up in 2 weeks."},
        headers=headers,
    )

    logs = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.consultation_id == c1.id,
                AuditLog.action == "CLINICAL_NOTE_UPDATED",
            )
        ).all()
    )
    assert len(logs) >= 1
    log = logs[-1]
    assert log.action == "CLINICAL_NOTE_UPDATED"
    assert log.user_id == soap_setup["doctor1"].id
    assert log.details["note_id"] == soap_setup["note1"].id
    assert "plan" in log.details["fields_updated"]
    # Check that medical text is NOT stored in audit log details
    assert "follow up in 2 weeks" not in str(log.details)


def test_repeated_updates_do_not_duplicate_notes(client, db_session, soap_setup):
    c1 = soap_setup["c1"]
    headers = {"Authorization": f"Bearer {soap_setup['token1']}"}

    # Perform 5 consecutive edits
    for i in range(5):
        res = client.put(
            f"/api/consultations/{c1.id}/note",
            json={"subjective": f"Edit iteration {i+1}"},
            headers=headers,
        )
        assert res.status_code == 200

    # Verify count remains exactly 1
    count = db_session.query(ClinicalNote).filter_by(consultation_id=c1.id).count()
    assert count == 1
