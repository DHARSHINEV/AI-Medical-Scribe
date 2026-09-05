import io
from app.models.patient import Patient


def test_upload_lab_report_success_and_retrieval(client, db_session):
    patient = Patient(name="Carlos Santana", mrn="MRN-LAB-01")
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    pdf_bytes = b"%PDF-1.4 mock pdf lab report content"
    files = {"file": ("CBC_Report.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    data = {"title": "Complete Blood Count"}

    # 1. Upload
    res = client.post(f"/api/patients/{patient.id}/labs", files=files, data=data)
    assert res.status_code == 201
    payload = res.json()
    assert payload["patient_id"] == patient.id
    assert payload["title"] == "Complete Blood Count"
    assert payload["filename"] == "CBC_Report.pdf"
    assert payload["mime_type"] == "application/pdf"
    assert payload["file_size_bytes"] == len(pdf_bytes)
    lab_id = payload["id"]

    # 2. List patient labs
    list_res = client.get(f"/api/patients/{patient.id}/labs")
    assert list_res.status_code == 200
    labs = list_res.json()
    assert len(labs) == 1
    assert labs[0]["id"] == lab_id

    # 3. List all clinic labs
    all_res = client.get("/api/labs")
    assert all_res.status_code == 200
    assert any(x["id"] == lab_id for x in all_res.json())

    # 4. Download / view file
    file_res = client.get(f"/api/labs/{lab_id}/file")
    assert file_res.status_code == 200
    assert file_res.content == pdf_bytes

    # 5. Delete lab report
    del_res = client.delete(f"/api/labs/{lab_id}")
    assert del_res.status_code == 204

    # Confirm deleted
    assert client.get(f"/api/labs/{lab_id}").status_code == 404


def test_upload_lab_report_invalid_format_rejected(client, db_session):
    patient = Patient(name="Dana Scully", mrn="MRN-LAB-02")
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    txt_bytes = b"Some plain text"
    files = {"file": ("notes.txt", io.BytesIO(txt_bytes), "text/plain")}

    res = client.post(f"/api/patients/{patient.id}/labs", files=files)
    assert res.status_code == 400
    assert "unsupported" in res.json()["detail"].lower()


def test_upload_lab_report_patient_not_found(client):
    files = {"file": ("report.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")}
    res = client.post("/api/patients/99999/labs", files=files)
    assert res.status_code == 404
