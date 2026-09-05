from unittest.mock import patch
from app.ai.diarization.diarizer import SpeakerDiarizer
from app.core.security import create_access_token
from app.models.consultation import Consultation
from app.models.patient import Patient
from app.models.user import User
from tests.test_ambient_ws import generate_pcm16_sine_wave


def test_speaker_diarizer_deterministic_turn_assignment():
    """Verify SpeakerDiarizer assigns same role for continuous speech and alternates on pauses."""
    diarizer = SpeakerDiarizer(pause_threshold=1.2)

    # Sequence of segments:
    # 1. Doctor says two sentences in quick succession (gap = 0.2s)
    # 2. Patient responds after 2.0s pause
    # 3. Doctor follows up after 1.5s pause
    # 4. Doctor continues speaking immediately (gap = 0.1s)
    input_segments = [
        {"start": 0.0, "end": 2.0, "text": "Good morning Eleanor."},
        {"start": 2.2, "end": 4.5, "text": "How have you been feeling since last week?"},
        {"start": 6.5, "end": 9.0, "text": "I have been having persistent shortness of breath."},
        {"start": 10.5, "end": 12.0, "text": "Let me listen to your lungs."},
        {"start": 12.1, "end": 13.5, "text": "Take a deep breath for me."},
    ]

    result = diarizer.diarize(input_segments)
    assert len(result) == 5

    # Turn 1: Doctor (first 2 segments)
    assert result[0]["speaker"] == "Doctor"
    assert result[1]["speaker"] == "Doctor"

    # Turn 2: Patient (3rd segment)
    assert result[2]["speaker"] == "Patient"

    # Turn 3: Doctor (4th and 5th segments)
    assert result[3]["speaker"] == "Doctor"
    assert result[4]["speaker"] == "Doctor"


def test_ambient_session_speaker_consistency_across_chunks(client, db_session):
    """Verify AmbientSession maintains consistent Doctor/Patient roles across multiple streamed chunks."""
    doc = User(name="Dr. Sarah", email="sarah@hospital.org", password_hash="hash", role="doctor")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    patient = Patient(name="Eleanor Vance", mrn="MRN-SPEAKER-01")
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    consultation = Consultation(patient_id=patient.id, doctor_id=doc.id, status="draft", stage="idle")
    db_session.add(consultation)
    db_session.commit()
    db_session.refresh(consultation)

    token = create_access_token(data={"sub": str(doc.id), "email": doc.email, "role": doc.role})

    # Chunk 1: Doctor speaking turn (2 sentences)
    whisper_chunk_1 = {
        "text": "Hello Eleanor. How have you been feeling?",
        "language": "en",
        "segments": [
            {"start": 0.0, "end": 1.0, "text": "Hello Eleanor."},
            {"start": 1.2, "end": 2.5, "text": "How have you been feeling?"},
        ],
    }

    pcm_chunk_1 = generate_pcm16_sine_wave(duration_s=2.5)

    with patch("app.ai.transcription.transcriber.SpeechToText.transcribe", return_value=whisper_chunk_1):
        with client.websocket_connect(f"/ws/consultations/{consultation.id}/ambient?token={token}") as ws:
            init_msg = ws.receive_json()
            assert init_msg["type"] == "connected"

            ws.send_bytes(pcm_chunk_1)
            evt1 = ws.receive_json()
            assert evt1["type"] in ("transcript_partial", "transcript_final")
            assert evt1["speaker"] == "Doctor"

            evt2 = ws.receive_json()
            assert evt2["type"] in ("transcript_partial", "transcript_final")
            assert evt2["speaker"] == "Doctor"  # Continuous turn: stays Doctor!

            # Finalize
            ws.send_json({"type": "stop"})
            finalizing = ws.receive_json()
            assert finalizing["type"] == "finalizing"
            comp = ws.receive_json()
            assert comp["type"] == "completed"


    # Verify final database segments
    db_session.expire_all()
    updated_c = db_session.get(Consultation, consultation.id)
    assert len(updated_c.segments) >= 1
    for seg in updated_c.segments:
        assert seg.speaker in ("Doctor", "Patient")
