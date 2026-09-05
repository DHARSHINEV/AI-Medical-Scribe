from unittest.mock import patch
from sqlalchemy import select
from app.core.security import create_access_token
from app.models.audit_log import AuditLog
from app.models.clinical_alert import ClinicalAlert
from app.models.clinical_entity import ClinicalEntity
from app.models.clinical_note import ClinicalNote
from app.models.consultation import Consultation
from app.models.transcript import TranscriptSegment


def test_canonical_asha_demo_pipeline(client, db_session, test_doctor, sample_audio_bytes):
    """
    Canonical end-to-end synthetic scenario:
    Patient: Asha (DEMO-001), 42F, Asthma, Penicillin allergy.
    Consultation: Cough & wheezing for 3 days, no fever, asthma, allergic to penicillin.
    """
    # 1. Create Patient Asha
    patient_res = client.post(
        "/api/patients",
        json={
            "name": "Asha",
            "mrn": "DEMO-001",
            "age": 42,
            "gender": "Female",
            "conditions": ["Asthma"],
            "allergies": ["Penicillin"],
            "medications": ["Albuterol Inhaler"],
        },
    )
    assert patient_res.status_code == 201
    patient = patient_res.json()
    patient_id = patient["id"]
    assert patient["name"] == "Asha"
    assert patient["mrn"] == "DEMO-001"

    # 2. Create Consultation
    consult_res = client.post(
        f"/api/patients/{patient_id}/consultations",
        json={"doctor_id": test_doctor.id},
    )
    assert consult_res.status_code == 201
    consultation = consult_res.json()
    consultation_id = consultation["id"]
    assert consultation["stage"] == "idle"
    assert consultation["status"] == "draft"

    # 3. Upload Audio
    files = {"audio": ("asha_consultation.wav", sample_audio_bytes, "audio/wav")}
    upload_res = client.post(
        f"/api/consultations/{consultation_id}/audio",
        files=files,
    )
    assert upload_res.status_code == 200
    assert upload_res.json()["stage"] == "uploaded"

    # Canonical Dialogue
    canonical_transcript_data = {
        "text": (
            "What brings you in today? "
            "I've been coughing and wheezing for three days. "
            "Do you have fever? "
            "No fever. "
            "Do you have any known medical conditions? "
            "I have asthma. "
            "Do you have any allergies? "
            "I'm allergic to penicillin. "
            "I'll give you advice and rest."
        ),
        "language": "en",
        "segments": [
            {"start": 0.0, "end": 2.5, "text": "What brings you in today?"},
            {"start": 2.6, "end": 6.8, "text": "I've been coughing and wheezing for three days."},
            {"start": 6.9, "end": 8.5, "text": "Do you have fever?"},
            {"start": 8.6, "end": 9.9, "text": "No fever."},
            {"start": 10.0, "end": 12.8, "text": "Do you have any known medical conditions?"},
            {"start": 12.9, "end": 14.5, "text": "I have asthma."},
            {"start": 14.6, "end": 16.5, "text": "Do you have any allergies?"},
            {"start": 16.6, "end": 18.8, "text": "I'm allergic to penicillin."},
            {"start": 18.9, "end": 21.5, "text": "I'll give you advice and rest."},
        ],
    }

    # 4. Transcribe Audio
    with patch("app.ai.transcription.transcriber.SpeechToText.transcribe", return_value=canonical_transcript_data):
        tx_res = client.post(f"/api/consultations/{consultation_id}/transcribe")
        assert tx_res.status_code == 200
        segments = tx_res.json()
        assert len(segments) == 9
        assert segments[0]["speaker"] == "Doctor"
        assert segments[1]["speaker"] == "Patient"

    # 5. Verify Transcript Saved in DB
    db_segments = list(
        db_session.scalars(
            select(TranscriptSegment).where(TranscriptSegment.consultation_id == consultation_id)
        ).all()
    )
    assert len(db_segments) == 9

    # 6. Extract Clinical Entities
    extract_res = client.post(f"/api/consultations/{consultation_id}/extract")
    assert extract_res.status_code == 200
    entities = extract_res.json()

    # Verify expected extraction:
    # - cough -> present
    # - wheezing -> present
    # - duration -> 3 days
    # - fever -> absent (negation preserved!)
    # - asthma -> historical/present condition
    # - penicillin -> allergy
    cough = next((e for e in entities if "cough" in e["value"].lower()), None)
    assert cough is not None
    assert cough["status"] == "present"

    wheeze = next((e for e in entities if "wheez" in e["value"].lower()), None)
    assert wheeze is not None
    assert wheeze["status"] == "present"

    fever = next((e for e in entities if e["value"].lower() == "fever"), None)
    assert fever is not None
    assert fever["status"] == "absent", f"Expected fever status 'absent', got: {fever['status']}"

    asthma = next((e for e in entities if e["value"].lower() == "asthma"), None)
    assert asthma is not None
    assert asthma["type"] == "condition"

    penicillin = next((e for e in entities if "penicillin" in e["value"].lower()), None)
    assert penicillin is not None
    assert penicillin["type"] == "allergy"

    # 7. Generate SOAP Note
    soap_res = client.post(f"/api/consultations/{consultation_id}/generate-note")
    assert soap_res.status_code == 200
    soap = soap_res.json()
    assert "coughing" in soap["subjective"].lower() or "cough" in soap["subjective"].lower()
    assert "three days" in soap["subjective"].lower()
    assert "asthma" in soap["subjective"].lower() or "asthma" in soap["assessment"].lower()
    assert "penicillin" in soap["subjective"].lower()
    assert soap["approved"] is False

    # 8. Run Clinical Second Look Safety Validation
    safety_res = client.post(f"/api/consultations/{consultation_id}/validate")
    assert safety_res.status_code == 200
    alerts = safety_res.json()
    assert len(alerts) > 0

    # 9. Verify Stage is now 'review'
    consult_after_safety = client.get(f"/api/consultations/{consultation_id}").json()
    assert consult_after_safety["stage"] == "review"
    assert consult_after_safety["status"] == "review"

    # 10. Clinician Review & Edit Draft Note
    edit_res = client.put(
        f"/api/consultations/{consultation_id}/note",
        json={"plan": "Prescribed albuterol nebulization and rest for 3 days. Penicillin avoided."},
    )
    assert edit_res.status_code == 200
    assert "Penicillin avoided" in edit_res.json()["plan"]

    # 11. Approve Note
    token = create_access_token({"sub": str(test_doctor.id), "email": test_doctor.email})
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Resolve review-required alerts before approval
    for alert in alerts:
        if alert.get("requires_review"):
            client.post(
                f"/api/consultations/{consultation_id}/safety/{alert['id']}/resolve",
                headers=auth_headers,
            )

    approve_res = client.post(
        f"/api/consultations/{consultation_id}/approve",
        headers=auth_headers,
    )
    assert approve_res.status_code == 200
    approval_data = approve_res.json()
    assert approval_data["approved"] is True
    assert approval_data["status"] == "approved"
    assert approval_data["stage"] == "approved"
    assert approval_data["approved_by"] == test_doctor.id

    # 12. Verify Audit Log
    logs = list(
        db_session.scalars(
            select(AuditLog).where(AuditLog.consultation_id == consultation_id)
        ).all()
    )
    actions = {l.action for l in logs}
    assert "CONSULTATION_CREATED" in actions
    assert "AUDIO_UPLOADED" in actions
    assert "TRANSCRIPTION_COMPLETED" in actions
    assert "CLINICAL_EXTRACTION_COMPLETED" in actions
    assert "SOAP_GENERATED" in actions
    assert ("CONSULTATION_APPROVED" in actions or "NOTE_APPROVED" in actions)

    # 13. Retrieve Consultation History for Patient
    history_res = client.get(f"/api/patients/{patient_id}/history")
    assert history_res.status_code == 200
    patient_history = history_res.json()
    assert len(patient_history) == 1
    assert patient_history[0]["status"] == "approved"
    assert patient_history[0]["stage"] == "approved"
