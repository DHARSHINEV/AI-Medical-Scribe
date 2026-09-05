def test_patient_crud(client):
    # 1. Create Patient
    payload = {
        "name": "Asha Patel",
        "mrn": "DEMO-001",
        "age": 42,
        "gender": "Female",
        "conditions": ["Asthma"],
        "allergies": ["Penicillin"],
        "medications": ["Albuterol"],
    }
    response = client.post("/api/patients", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Asha Patel"
    assert data["mrn"] == "DEMO-001"
    patient_id = data["id"]

    # 2. Duplicate MRN Conflict
    duplicate_res = client.post("/api/patients", json=payload)
    assert duplicate_res.status_code == 409

    # 3. Get Patient
    get_res = client.get(f"/api/patients/{patient_id}")
    assert get_res.status_code == 200
    assert get_res.json()["mrn"] == "DEMO-001"

    # 4. List Patients
    list_res = client.get("/api/patients")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 5. Update Patient
    update_res = client.put(
        f"/api/patients/{patient_id}",
        json={"age": 43, "conditions": ["Asthma", "Mild Hypertension"]},
    )
    assert update_res.status_code == 200
    assert update_res.json()["age"] == 43
    assert "Mild Hypertension" in update_res.json()["conditions"]

    # 6. Patient History
    history_res = client.get(f"/api/patients/{patient_id}/history")
    assert history_res.status_code == 200
    assert isinstance(history_res.json(), list)
