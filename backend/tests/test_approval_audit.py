from unittest.mock import patch
from sqlalchemy import select
from app.models.audit_log import AuditLog


def test_approval_workflow_and_audit_logging(client, db_session, test_doctor, sample_audio_bytes):
    # 1. Login
    login_res = client.post(
        "/api/auth/login",
        json={"email": "doctor@mediscribe.com", "password": "doctor123"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify /me
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "doctor@mediscribe.com"

    # 2. Create Patient & Consultation
    p_res = client.post("/api/patients", json={"name": "George", "mrn": "MRN-501"}, headers=headers)
    patient_id = p_res.json()["id"]

    c_res = client.post(f"/api/patients/{patient_id}/consultations", json={}, headers=headers)
    consultation_id = c_res.json()["id"]

    # 3. Attempt Approval Without Note -> Should Fail
    early_approve = client.post(f"/api/consultations/{consultation_id}/approve", headers=headers)
    assert early_approve.status_code == 400

    # 4. Upload Audio & Transcribe
    files = {"file": ("consult.wav", sample_audio_bytes, "audio/wav")}
    client.post(f"/api/consultations/{consultation_id}/audio", files=files, headers=headers)

    mock_transcript = {
        "text": "Doctor: Take paracetamol and rest. Patient: Thank you.",
        "language": "en",
        "segments": [{"start": 0.0, "end": 2.0, "text": "Doctor: Take paracetamol and rest."}],
    }
    with patch("app.ai.transcription.transcriber.SpeechToText.transcribe", return_value=mock_transcript):
        client.post(f"/api/consultations/{consultation_id}/transcribe", headers=headers)

    # 5. Generate Note
    client.post(f"/api/consultations/{consultation_id}/generate-note", headers=headers)

    # Validate Safety & Enter Review
    client.post(f"/api/consultations/{consultation_id}/validate", headers=headers)

    # 6. Approve Consultation
    approve_res = client.post(f"/api/consultations/{consultation_id}/approve", headers=headers)
    assert approve_res.status_code == 200
    assert approve_res.json()["approved"] is True
    assert approve_res.json()["status"] == "approved"
    assert approve_res.json()["stage"] == "approved"
    assert approve_res.json()["approved_at"] is not None

    # 7. Note cannot be modified after approval
    locked_edit = client.put(
        f"/api/consultations/{consultation_id}/note",
        json={"plan": "Modified after approval attempt"},
        headers=headers,
    )
    assert locked_edit.status_code == 400

    # 8. Verify Audit Logs Recorded
    logs = list(
        db_session.scalars(
            select(AuditLog).where(AuditLog.consultation_id == consultation_id)
        ).all()
    )
    actions = [l.action for l in logs]
    assert "CONSULTATION_CREATED" in actions
    assert "AUDIO_UPLOADED" in actions
    assert "TRANSCRIPTION_COMPLETED" in actions
    assert "SOAP_GENERATED" in actions
    assert ("CONSULTATION_APPROVED" in actions or "NOTE_APPROVED" in actions)
