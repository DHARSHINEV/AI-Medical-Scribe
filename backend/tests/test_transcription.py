from unittest.mock import patch


def test_transcription_service_and_retry_safety(client, sample_audio_bytes):
    # Setup Patient & Consultation
    p_res = client.post("/api/patients", json={"name": "Alice", "mrn": "MRN-201"})
    patient_id = p_res.json()["id"]

    c_res = client.post(f"/api/patients/{patient_id}/consultations", json={})
    consultation_id = c_res.json()["id"]

    # Upload Audio
    files = {"file": ("consultation.wav", sample_audio_bytes, "audio/wav")}
    client.post(f"/api/consultations/{consultation_id}/audio", files=files)

    mock_whisper_result = {
        "text": "Hello doctor. I have been coughing for three days.",
        "language": "en",
        "segments": [
            {"start": 0.0, "end": 2.1, "text": "Hello doctor."},
            {"start": 2.2, "end": 5.0, "text": "I have been coughing for three days."},
        ],
    }

    # Transcribe 1st time
    with patch("app.ai.transcription.transcriber.SpeechToText.transcribe", return_value=mock_whisper_result):
        tx_res_1 = client.post(f"/api/consultations/{consultation_id}/transcribe")
        assert tx_res_1.status_code == 200
        segments_1 = tx_res_1.json()
        assert len(segments_1) == 2
        assert segments_1[0]["speaker"] == "Doctor"
        assert segments_1[1]["speaker"] == "Patient"
        assert segments_1[0]["text"] == "Hello doctor."

    # Verify retrieval
    get_tx = client.get(f"/api/consultations/{consultation_id}/transcript")
    assert get_tx.status_code == 200
    assert len(get_tx.json()) == 2

    # Retry Transcribe (2nd time) -> Must NOT duplicate segments
    mock_whisper_result_2 = {
        "text": "Updated audio transcription with three segments.",
        "language": "en",
        "segments": [
            {"start": 0.0, "end": 1.5, "text": "Hello."},
            {"start": 1.6, "end": 3.0, "text": "I feel sick."},
            {"start": 3.1, "end": 4.5, "text": "Let me check."},
        ],
    }
    with patch("app.ai.transcription.transcriber.SpeechToText.transcribe", return_value=mock_whisper_result_2):
        tx_res_2 = client.post(f"/api/consultations/{consultation_id}/transcribe")
        assert tx_res_2.status_code == 200
        segments_2 = tx_res_2.json()
        assert len(segments_2) == 3

    # Confirm total segments in database is exactly 3 (no stale duplicates)
    final_tx = client.get(f"/api/consultations/{consultation_id}/transcript")
    assert len(final_tx.json()) == 3
