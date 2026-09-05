def test_consultation_lifecycle_and_audio_upload(client, sample_audio_bytes):
    # 1. Create Patient
    patient_res = client.post(
        "/api/patients",
        json={"name": "John Doe", "mrn": "MRN-101"},
    )
    patient_id = patient_res.json()["id"]

    # 2. Create Consultation
    consult_res = client.post(
        f"/api/patients/{patient_id}/consultations",
        json={},
    )
    assert consult_res.status_code == 201
    consultation_id = consult_res.json()["id"]
    assert consult_res.json()["stage"] == "idle"
    assert consult_res.json()["status"] == "draft"

    # 3. Upload Audio (valid audio file)
    files = {"file": ("test_audio.wav", sample_audio_bytes, "audio/wav")}
    upload_res = client.post(
        f"/api/consultations/{consultation_id}/audio",
        files=files,
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert upload_data["stage"] == "uploaded"
    assert upload_data["audio_path"] is not None

    # 4. Upload Audio with 'audio' field name (frontend contract compatibility)
    files_audio_field = {"audio": ("test_recording.webm", sample_audio_bytes, "audio/webm")}
    upload_res_2 = client.post(
        f"/api/consultations/{consultation_id}/audio",
        files=files_audio_field,
    )
    assert upload_res_2.status_code == 200

    # 5. Invalid Audio extension rejection
    invalid_file = {"file": ("malicious.exe", b"binary", "application/octet-stream")}
    bad_upload = client.post(
        f"/api/consultations/{consultation_id}/audio",
        files=invalid_file,
    )
    assert bad_upload.status_code == 400

    # 6. Get Consultation
    get_res = client.get(f"/api/consultations/{consultation_id}")
    assert get_res.status_code == 200
    assert get_res.json()["stage"] == "uploaded"

    # 7. List Patient Consultations
    list_res = client.get(f"/api/patients/{patient_id}/consultations")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
