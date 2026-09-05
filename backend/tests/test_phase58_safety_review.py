import pytest
from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.clinical_alert import ClinicalAlert
from app.models.consultation import Consultation
from app.models.patient import Patient
from app.models.transcript import TranscriptSegment
from app.models.user import User


@pytest.fixture
def test_setup(db_session, test_doctor):
    # Create patient with allergy
    patient = Patient(
        mrn="MRN-SAFE-58",
        name="Robert Frost",
        age=55,
        gender="male",
        allergies=["Penicillin"],
        conditions=["Asthma"],
        medications=[],
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    # Create consultation 1
    consultation1 = Consultation(
        patient_id=patient.id,
        doctor_id=test_doctor.id,
        status="review",
        stage="review",
    )
    # Create consultation 2 (for foreign alert resolution testing)
    consultation2 = Consultation(
        patient_id=patient.id,
        doctor_id=test_doctor.id,
        status="review",
        stage="review",
    )
    db_session.add_all([consultation1, consultation2])
    db_session.commit()
    db_session.refresh(consultation1)
    db_session.refresh(consultation2)

    # Transcript segment for evidence
    seg = TranscriptSegment(
        consultation_id=consultation1.id,
        speaker="Patient",
        text="No, I do not have any allergies doctor.",
        start_time=12.0,
        end_time=15.0,
    )
    db_session.add(seg)
    db_session.commit()
    db_session.refresh(seg)

    # Alert 1: High priority, requires review, with evidence
    alert1 = ClinicalAlert(
        consultation_id=consultation1.id,
        type="allergy_conflict",
        title="Allergy Conflict Detected",
        detail="Stored patient history lists Penicillin, but patient denied allergies.",
        severity="High",
        evidence_segment_id=seg.id,
        requires_review=True,
        resolved=False,
    )
    # Alert 2: Low priority, does not require review
    alert2 = ClinicalAlert(
        consultation_id=consultation1.id,
        type="historical_condition",
        title="Historical Condition: Asthma",
        detail="Previously documented Asthma. Review for relevance.",
        severity="Low",
        evidence_segment_id=None,
        requires_review=False,
        resolved=False,
    )
    # Alert 3 belonging to consultation 2
    alert3 = ClinicalAlert(
        consultation_id=consultation2.id,
        type="missing_duration",
        title="Documentation Gap",
        detail="Duration not captured.",
        severity="Medium",
        evidence_segment_id=None,
        requires_review=True,
        resolved=False,
    )
    db_session.add_all([alert1, alert2, alert3])
    db_session.commit()
    db_session.refresh(alert1)
    db_session.refresh(alert2)
    db_session.refresh(alert3)

    return {
        "doctor": test_doctor,
        "patient": patient,
        "c1": consultation1,
        "c2": consultation2,
        "alert1": alert1,
        "alert2": alert2,
        "alert3": alert3,
        "seg": seg,
    }


def test_get_safety_summary(client, test_setup):
    c1 = test_setup["c1"]
    res = client.get(f"/api/consultations/{c1.id}/safety")
    assert res.status_code == 200
    data = res.json()

    assert data["consultation_id"] == c1.id
    assert data["alert_count"] == 2
    assert data["high_priority_alert_count"] == 1
    assert data["review_required"] is True
    assert len(data["alerts"]) == 2

    # Verify evidence segment linkage
    alert_with_evidence = next(a for a in data["alerts"] if a["type"] == "allergy_conflict")
    assert alert_with_evidence["evidence_segment_id"] == test_setup["seg"].id
    assert alert_with_evidence["evidence_segment"] is not None
    assert "allergies" in alert_with_evidence["evidence_segment"]["text"].lower()


def test_alert_filtering_by_consultation(client, test_setup):
    c1 = test_setup["c1"]
    c2 = test_setup["c2"]

    res1 = client.get(f"/api/consultations/{c1.id}/safety")
    assert res1.status_code == 200
    assert res1.json()["alert_count"] == 2

    res2 = client.get(f"/api/consultations/{c2.id}/safety")
    assert res2.status_code == 200
    assert res2.json()["alert_count"] == 1
    assert res2.json()["alerts"][0]["id"] == test_setup["alert3"].id


def test_resolve_alert_success_and_review_required_update(client, db_session, test_setup):
    c1 = test_setup["c1"]
    alert1 = test_setup["alert1"]

    # Before resolution: review_required is True
    initial_summary = client.get(f"/api/consultations/{c1.id}/safety").json()
    assert initial_summary["review_required"] is True
    assert initial_summary["high_priority_alert_count"] == 1

    # Resolve alert 1
    res = client.post(
        f"/api/consultations/{c1.id}/safety/{alert1.id}/resolve",
        json={"resolved": True},
    )
    assert res.status_code == 200
    resolved_data = res.json()
    assert resolved_data["id"] == alert1.id
    assert resolved_data["resolved"] is True

    # Check consultation remains in review state (not approved)
    db_session.refresh(c1)
    assert c1.status == "review"
    assert c1.stage == "review"

    # After resolution: Alert 1 is resolved; Alert 2 has requires_review=False.
    # Therefore, review_required must become False!
    updated_summary = client.get(f"/api/consultations/{c1.id}/safety").json()
    assert updated_summary["review_required"] is False
    assert updated_summary["high_priority_alert_count"] == 0
    assert updated_summary["alert_count"] == 2


def test_resolve_already_resolved_alert_idempotent(client, test_setup):
    c1 = test_setup["c1"]
    alert1 = test_setup["alert1"]

    # First resolution
    res1 = client.post(f"/api/consultations/{c1.id}/safety/{alert1.id}/resolve")
    assert res1.status_code == 200
    assert res1.json()["resolved"] is True

    # Second resolution (idempotent retry)
    res2 = client.post(f"/api/consultations/{c1.id}/safety/{alert1.id}/resolve")
    assert res2.status_code == 200
    assert res2.json()["resolved"] is True


def test_cannot_resolve_another_consultations_alert(client, test_setup):
    c1 = test_setup["c1"]
    alert3 = test_setup["alert3"]  # belongs to consultation 2

    res = client.post(f"/api/consultations/{c1.id}/safety/{alert3.id}/resolve")
    assert res.status_code == 400
    assert "does not belong" in res.json()["detail"].lower()


def test_resolve_alert_audit_log(client, db_session, test_setup):
    c1 = test_setup["c1"]
    alert1 = test_setup["alert1"]

    client.post(f"/api/consultations/{c1.id}/safety/{alert1.id}/resolve")

    logs = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.consultation_id == c1.id,
                AuditLog.action == "SAFETY_ALERT_RESOLVED",
            )
        ).all()
    )
    assert len(logs) >= 1
    log = logs[-1]
    assert log.action == "SAFETY_ALERT_RESOLVED"
    assert log.details["alert_id"] == alert1.id
    assert log.details["resolved"] is True
    assert log.created_at is not None


def test_unresolve_alert_operation(client, db_session, test_setup):
    c1 = test_setup["c1"]
    alert1 = test_setup["alert1"]

    # Resolve
    client.post(f"/api/consultations/{c1.id}/safety/{alert1.id}/resolve")

    # Unresolve
    res = client.post(f"/api/consultations/{c1.id}/safety/{alert1.id}/unresolve")
    assert res.status_code == 200
    assert res.json()["resolved"] is False

    # Review required should be back to True
    summary = client.get(f"/api/consultations/{c1.id}/safety").json()
    assert summary["review_required"] is True
