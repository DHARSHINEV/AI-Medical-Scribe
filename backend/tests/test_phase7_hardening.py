import pytest
from app.core.security import create_access_token, get_password_hash
from app.models.clinical_alert import ClinicalAlert
from app.models.clinical_note import ClinicalNote
from app.models.consultation import Consultation
from app.models.patient import Patient
from app.models.user import User


@pytest.fixture
def auth_headers(db_session):
    doctor = User(
        name="Dr. Test Specialist",
        email="specialist@mediscribe.com",
        password_hash=get_password_hash("doctor123"),
        role="doctor",
    )
    db_session.add(doctor)
    db_session.commit()
    db_session.refresh(doctor)

    token = create_access_token(
        data={"sub": str(doctor.id), "email": doctor.email, "role": doctor.role}
    )
    return {"Authorization": f"Bearer {token}"}, doctor


@pytest.fixture
def second_doctor(db_session):
    doctor = User(
        name="Dr. Other Clinician",
        email="other@mediscribe.com",
        password_hash=get_password_hash("doctor123"),
        role="doctor",
    )
    db_session.add(doctor)
    db_session.commit()
    db_session.refresh(doctor)

    token = create_access_token(
        data={"sub": str(doctor.id), "email": doctor.email, "role": doctor.role}
    )
    return {"Authorization": f"Bearer {token}"}, doctor


def test_consultation_doctor_ownership_enforcement(client, auth_headers, db_session):
    headers, doctor = auth_headers

    # Create a patient
    patient = Patient(name="Test Patient Ownership", mrn="MRN-OWN-001")
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    # 1. Post consultation with a spoofed/arbitrary doctor_id (e.g. 9999)
    response = client.post(
        f"/api/patients/{patient.id}/consultations",
        json={"doctor_id": 9999},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()

    # The returned consultation must have doctor_id == doctor.id, NOT 9999
    assert data["doctor_id"] == doctor.id

    # Verify directly in database
    db_consultation = db_session.get(Consultation, data["id"])
    assert db_consultation.doctor_id == doctor.id


def test_unauthenticated_approval_returns_401(client, db_session):
    patient = Patient(name="Test Patient 401", mrn="MRN-401-001")
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    consultation = Consultation(
        patient_id=patient.id,
        status="review",
        stage="review",
    )
    db_session.add(consultation)
    db_session.commit()
    db_session.refresh(consultation)

    # Attempt approval with no auth header
    response = client.post(f"/api/consultations/{consultation.id}/approve")
    assert response.status_code == 401


def test_unresolved_review_required_alerts_block_approval(client, auth_headers, db_session):
    headers, doctor = auth_headers

    patient = Patient(name="Test Patient Alert Block", mrn="MRN-ALERT-001")
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    consultation = Consultation(
        patient_id=patient.id,
        doctor_id=doctor.id,
        status="review",
        stage="review",
    )
    db_session.add(consultation)
    db_session.commit()
    db_session.refresh(consultation)

    note = ClinicalNote(
        consultation_id=consultation.id,
        subjective="Subj",
        objective="Obj",
        assessment="Assess",
        plan="Plan",
    )
    db_session.add(note)

    # Add an unresolved review-required alert
    alert = ClinicalAlert(
        consultation_id=consultation.id,
        type="allergy_conflict",
        title="Severe Drug Interaction",
        detail="Patient record lists Penicillin allergy",
        severity="High",
        requires_review=True,
        resolved=False,
    )
    db_session.add(alert)
    db_session.commit()

    # Attempt to approve -> must fail with 400
    response = client.post(
        f"/api/consultations/{consultation.id}/approve",
        headers=headers,
    )
    assert response.status_code == 400
    assert "safety alerts require review" in response.json()["detail"].lower()

    # Now resolve the alert
    resolve_res = client.post(
        f"/api/consultations/{consultation.id}/safety/{alert.id}/resolve",
        json={"resolved": True},
        headers=headers,
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["resolved"] is True

    # Now approval succeeds
    approve_res = client.post(
        f"/api/consultations/{consultation.id}/approve",
        headers=headers,
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["approved"] is True
    assert approve_res.json()["approved_by"] == doctor.id


def test_cross_consultation_alert_resolution_rejected(client, auth_headers, db_session):
    headers, doctor = auth_headers

    patient = Patient(name="Test Patient Cross", mrn="MRN-CROSS-001")
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    consultation_1 = Consultation(patient_id=patient.id, doctor_id=doctor.id, status="review", stage="review")
    consultation_2 = Consultation(patient_id=patient.id, doctor_id=doctor.id, status="review", stage="review")
    db_session.add_all([consultation_1, consultation_2])
    db_session.commit()

    # Alert belongs to consultation 1
    alert_1 = ClinicalAlert(
        consultation_id=consultation_1.id,
        type="gap",
        title="Gap",
        detail="Detail",
        severity="Medium",
    )
    db_session.add(alert_1)
    db_session.commit()

    # Attempt resolving alert_1 via consultation_2 endpoint
    response = client.post(
        f"/api/consultations/{consultation_2.id}/safety/{alert_1.id}/resolve",
        json={"resolved": True},
        headers=headers,
    )
    assert response.status_code == 400
    assert "does not belong to consultation" in response.json()["detail"].lower()


def test_approved_note_cannot_be_modified(client, auth_headers, db_session):
    headers, doctor = auth_headers

    patient = Patient(name="Test Patient Immutable", mrn="MRN-IMMUT-001")
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    consultation = Consultation(
        patient_id=patient.id,
        doctor_id=doctor.id,
        status="approved",
        stage="approved",
        approved_by=doctor.id,
    )
    db_session.add(consultation)
    db_session.commit()

    note = ClinicalNote(
        consultation_id=consultation.id,
        subjective="Subj",
        objective="Obj",
        assessment="Assess",
        plan="Plan",
        approved=True,
        approved_by=doctor.id,
    )
    db_session.add(note)
    db_session.commit()

    # Attempt PUT on approved note
    response = client.put(
        f"/api/consultations/{consultation.id}/note",
        json={"plan": "Modified Plan"},
        headers=headers,
    )
    assert response.status_code == 400
    assert "approved notes cannot be modified" in response.json()["detail"].lower()


def test_cross_doctor_note_editing_forbidden(client, auth_headers, second_doctor, db_session):
    headers_1, doctor_1 = auth_headers
    headers_2, doctor_2 = second_doctor

    patient = Patient(name="Test Patient Cross Doctor", mrn="MRN-DR-001")
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    # Consultation assigned to doctor 1
    consultation = Consultation(
        patient_id=patient.id,
        doctor_id=doctor_1.id,
        status="review",
        stage="review",
    )
    db_session.add(consultation)
    db_session.commit()

    note = ClinicalNote(
        consultation_id=consultation.id,
        subjective="Original",
        objective="Original",
        assessment="Original",
        plan="Original",
        approved=False,
    )
    db_session.add(note)
    db_session.commit()

    # Doctor 2 attempts to edit Doctor 1's note -> 403 Forbidden
    response = client.put(
        f"/api/consultations/{consultation.id}/note",
        json={"plan": "Doctor 2 Tampering"},
        headers=headers_2,
    )
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_openapi_no_duplicate_operation_ids(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()

    operation_ids = []
    duplicates = []
    for path, path_item in schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if isinstance(operation, dict) and "operationId" in operation:
                op_id = operation["operationId"]
                if op_id in operation_ids:
                    duplicates.append((op_id, method.upper(), path))
                operation_ids.append(op_id)

    assert duplicates == [], f"Found duplicate Operation IDs: {duplicates}"
