from unittest.mock import patch


def test_soap_generation_and_safety_checks(client, sample_audio_bytes):
    # Setup Patient with known Penicillin allergy & Asthma
    p_res = client.post(
        "/api/patients",
        json={
            "name": "Sarah Connor",
            "mrn": "MRN-401",
            "conditions": ["Asthma"],
            "allergies": ["Penicillin"],
            "medications": ["Albuterol"],
        },
    )
    patient_id = p_res.json()["id"]

    c_res = client.post(f"/api/patients/{patient_id}/consultations", json={})
    consultation_id = c_res.json()["id"]

    files = {"file": ("consultation.wav", sample_audio_bytes, "audio/wav")}
    client.post(f"/api/consultations/{consultation_id}/audio", files=files)

    # Transcript mentions amoxicillin (allergy conflict with penicillin) and reports no allergies
    mock_transcript = {
        "text": (
            "Doctor: What is the issue? "
            "Patient: I have a sore throat for three days. "
            "Doctor: Do you have any allergies? "
            "Patient: No allergies. "
            "Doctor: I will prescribe amoxicillin."
        ),
        "language": "en",
        "segments": [
            {"start": 0.0, "end": 2.0, "text": "Doctor: What is the issue?"},
            {"start": 2.1, "end": 5.0, "text": "Patient: I have a sore throat for three days."},
            {"start": 5.1, "end": 7.0, "text": "Doctor: Do you have any allergies?"},
            {"start": 7.1, "end": 8.5, "text": "Patient: No allergies."},
            {"start": 8.6, "end": 11.0, "text": "Doctor: I will prescribe amoxicillin."},
        ],
    }

    with patch("app.ai.transcription.transcriber.SpeechToText.transcribe", return_value=mock_transcript):
        client.post(f"/api/consultations/{consultation_id}/transcribe")

    # 1. Generate SOAP Note
    soap_res = client.post(f"/api/consultations/{consultation_id}/generate-note")
    assert soap_res.status_code == 200
    soap_data = soap_res.json()
    assert "sore throat" in soap_data["subjective"].lower()
    assert "amoxicillin" in soap_data["plan"].lower()
    assert soap_data["approved"] is False

    # 2. Clinician Edit SOAP Note
    update_res = client.put(
        f"/api/consultations/{consultation_id}/note",
        json={"plan": "Patient advised rest, warm fluids, avoid amoxicillin due to allergy."},
    )
    assert update_res.status_code == 200
    assert "avoid amoxicillin" in update_res.json()["plan"]

    # 3. Clinical Second Look Safety Validation
    safety_res = client.post(f"/api/consultations/{consultation_id}/validate")
    assert safety_res.status_code == 200
    alerts = safety_res.json()
    assert len(alerts) > 0

    # Must flag allergy conflict (Penicillin vs No allergies OR Penicillin vs Amoxicillin)
    allergy_conflicts = [a for a in alerts if a["type"] == "allergy_conflict"]
    assert len(allergy_conflicts) >= 1
    assert any(a["severity"] in ("High", "high") for a in allergy_conflicts)

    # 4. Resolve Alert
    alert_to_resolve = allergy_conflicts[0]
    resolve_res = client.post(
        f"/api/alerts/{alert_to_resolve['id']}/resolve",
        json={"resolved": True},
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["resolved"] is True
