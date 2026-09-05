from unittest.mock import patch


def test_clinical_extraction_negation_and_evidence(client, sample_audio_bytes):
    # Setup
    p_res = client.post("/api/patients", json={"name": "Bob", "mrn": "MRN-301"})
    patient_id = p_res.json()["id"]

    c_res = client.post(f"/api/patients/{patient_id}/consultations", json={})
    consultation_id = c_res.json()["id"]

    files = {"file": ("consultation.wav", sample_audio_bytes, "audio/wav")}
    client.post(f"/api/consultations/{consultation_id}/audio", files=files)

    # Transcription with explicit negation "No fever"
    mock_transcript = {
        "text": (
            "What brings you in? I have been coughing and wheezing for 3 days. "
            "Do you have a fever? No fever. I take paracetamol."
        ),
        "language": "en",
        "segments": [
            {"start": 0.0, "end": 2.0, "text": "What brings you in?"},
            {"start": 2.1, "end": 6.0, "text": "I have been coughing and wheezing for 3 days."},
            {"start": 6.1, "end": 8.0, "text": "Do you have a fever?"},
            {"start": 8.1, "end": 9.5, "text": "No fever."},
            {"start": 9.6, "end": 12.0, "text": "I take paracetamol."},
        ],
    }

    with patch("app.ai.transcription.transcriber.SpeechToText.transcribe", return_value=mock_transcript):
        client.post(f"/api/consultations/{consultation_id}/transcribe")

    # Extract Clinical Entities
    ext_res = client.post(f"/api/consultations/{consultation_id}/extract")
    assert ext_res.status_code == 200
    entities = ext_res.json()
    assert len(entities) > 0

    # 1. Verify Negation: Fever must be absent!
    fever_entity = next((e for e in entities if e["value"].lower() == "fever"), None)
    assert fever_entity is not None
    assert fever_entity["status"] == "absent", f"Expected fever status=absent, got {fever_entity['status']}"

    # 2. Verify Positive Symptoms
    cough_entity = next((e for e in entities if "cough" in e["value"].lower()), None)
    assert cough_entity is not None
    assert cough_entity["status"] == "present"

    # 3. Verify Medication
    med_entity = next((e for e in entities if e["value"].lower() == "paracetamol"), None)
    assert med_entity is not None
    assert med_entity["type"] == "medication"
    assert med_entity["status"] == "present"

    # 4. Verify Evidence Segment Linkage
    assert fever_entity["evidence_segment_id"] is not None
    assert fever_entity["evidenceSegmentId"] is not None

    # 5. Retry Safety: Extracting again does not accumulate duplicates
    ext_res_2 = client.post(f"/api/consultations/{consultation_id}/extract")
    assert ext_res_2.status_code == 200
    assert len(ext_res_2.json()) == len(entities)

    # 6. Retrieve via GET /entities
    get_res = client.get(f"/api/consultations/{consultation_id}/entities")
    assert get_res.status_code == 200
    assert len(get_res.json()) == len(entities)
