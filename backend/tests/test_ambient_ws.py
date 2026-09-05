import numpy as np
import pytest
from unittest.mock import patch
from starlette.testclient import TestClient

from app.core.security import create_access_token
from app.main import app
from app.models.consultation import Consultation
from app.models.patient import Patient
from app.models.user import User


def generate_pcm16_sine_wave(duration_s=2.5, sample_rate=16000, freq=440.0) -> bytes:
    """Generate mock 16kHz 16-bit mono PCM audio bytes."""
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    samples = (np.sin(2 * np.pi * freq * t) * 16384.0).astype(np.int16)
    return samples.tobytes()


def test_ambient_ws_unauthenticated_rejected(client):
    """WebSocket connection without valid JWT token should be rejected."""
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/consultations/1/ambient") as ws:
            ws.receive_json()


def test_ambient_ws_streaming_and_finalization(client, db_session):
    # 1. Setup Doctor, Patient, Consultation
    doc = User(name="Dr. House", email="house@hospital.org", password_hash="hash", role="doctor")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)


    patient = Patient(name="John Doe", mrn="MRN-AMBIENT-01")
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    consultation = Consultation(patient_id=patient.id, doctor_id=doc.id, status="draft", stage="idle")
    db_session.add(consultation)
    db_session.commit()
    db_session.refresh(consultation)

    token = create_access_token(data={"sub": str(doc.id), "email": doc.email, "role": doc.role})

    # Mock Whisper output with single segment
    mock_transcribe_result = {
        "text": "Doctor how have you been feeling today?",
        "language": "en",
        "segments": [
            {"start": 0.0, "end": 1.2, "text": "Doctor how have you been feeling today?"},
        ],
    }

    pcm_bytes = generate_pcm16_sine_wave(duration_s=2.5)

    with patch("app.ai.transcription.transcriber.SpeechToText.transcribe", return_value=mock_transcribe_result):
        with client.websocket_connect(f"/ws/consultations/{consultation.id}/ambient?token={token}") as ws:
            # Step 1: Verify connected message
            init_msg = ws.receive_json()
            assert init_msg["type"] == "connected"
            assert init_msg["consultation_id"] == consultation.id

            # Step 2: Send PCM16 audio bytes
            ws.send_bytes(pcm_bytes)

            # Receive partial or final transcript event
            evt1 = ws.receive_json()
            assert evt1["type"] in ("transcript_partial", "transcript_final")
            assert "text" in evt1
            assert evt1["speaker"] in ("Doctor", "Patient")

            # Step 3: Pause & Resume
            ws.send_json({"type": "pause"})
            pause_msg = ws.receive_json()
            assert pause_msg["type"] == "processing"
            assert pause_msg["stage"] == "paused"

            ws.send_json({"type": "resume"})
            resume_msg = ws.receive_json()
            assert resume_msg["type"] == "processing"
            assert resume_msg["stage"] == "recording"

            # Step 4: Finalize
            ws.send_json({"type": "stop"})
            finalizing_msg = ws.receive_json()
            assert finalizing_msg["type"] == "finalizing"

            completed_msg = ws.receive_json()
            assert completed_msg["type"] == "completed"
            assert completed_msg["consultation_id"] == consultation.id
            assert completed_msg["segment_count"] >= 1
            assert "timing_metrics" in completed_msg

        # 5. Verify database state
        db_session.expire_all()
        updated_c = db_session.get(Consultation, consultation.id)
        assert updated_c.stage == "transcribed"
        assert len(updated_c.segments) >= 1
        assert updated_c.audio_path is not None

        # 6. Verify downstream clinical AI pipeline works on finalized ambient consultation
        extract_res = client.post(f"/api/consultations/{consultation.id}/extract")
        assert extract_res.status_code == 200

        soap_res = client.post(f"/api/consultations/{consultation.id}/generate-note")
        assert soap_res.status_code == 200

        safety_res = client.post(f"/api/consultations/{consultation.id}/validate")
        assert safety_res.status_code == 200
