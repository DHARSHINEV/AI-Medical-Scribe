"""
MediScribe Python REST Backend Server
Pure Python 3 standard library (http.server + socketserver).
Provides REST endpoints for:
- Model status & telemetry
- Real-time dataset ingestion & listing
- Continuous training / fine-tuning with live epoch progress
- Clinician DPO feedback logging
- Clinical Second Look & SOAP inference
- Optional static file serving
"""

import http.server
import socketserver
import json
import urllib.parse
import threading
import time
import os
import sys

from model import ClinicalNLPModel
from dataset_manager import DatasetManager
from db import db

PORT = 8000
HOST = "127.0.0.1"

# Initialize singletons
nlp_model = ClinicalNLPModel()
dataset_mgr = DatasetManager()

# Global training state tracker
training_state = {
    "is_training": False,
    "current_epoch": 0,
    "total_epochs": 0,
    "current_loss": nlp_model.current_loss,
    "accuracy": nlp_model.accuracy,
    "perplexity": nlp_model.perplexity,
    "progress_pct": 0,
    "status_message": "Idle",
    "last_checkpoint": None
}

def run_background_training(epochs=5, learning_rate=0.015):
    """Executes multi-epoch training in a background thread."""
    global training_state
    training_state["is_training"] = True
    training_state["total_epochs"] = epochs
    training_state["status_message"] = f"Training started ({epochs} epochs)..."

    samples = dataset_mgr.get_samples(limit=500)

    for ep in range(1, epochs + 1):
        training_state["current_epoch"] = ep
        training_state["status_message"] = f"Running Epoch {ep}/{epochs} - Computing gradients..."
        
        # Simulate realistic step time per epoch
        time.sleep(0.6)

        metrics = nlp_model.train_epoch(samples, learning_rate=learning_rate, epoch_num=ep)
        
        training_state["current_loss"] = metrics["loss"]
        training_state["accuracy"] = metrics["accuracy"]
        training_state["perplexity"] = metrics["perplexity"]
        training_state["progress_pct"] = int((ep / epochs) * 100)

    # Save versioned checkpoint
    checkpoint_res = nlp_model.save_checkpoint()
    training_state["last_checkpoint"] = checkpoint_res
    training_state["is_training"] = False
    training_state["status_message"] = f"Completed! Promoted model to {nlp_model.version}"
    print(f"[Training] {training_state['status_message']}")


class MediScribeHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Serve parent folder as static file directory
        parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        super().__init__(*args, directory=parent_dir, **kwargs)

    def _set_cors_headers(self, content_type="application/json"):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Type", content_type)

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def _read_json_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            raw_body = self.rfile.read(content_length).decode("utf-8")
            try:
                return json.loads(raw_body)
            except Exception as e:
                return {}
        return {}

    def _send_json_response(self, data, status=200):
        response_bytes = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self._set_cors_headers("application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # API: Model & Server Status
        if path == "/api/status":
            stats = dataset_mgr.get_stats()
            self._send_json_response({
                "status": "online",
                "service": "MediScribe-Clinical-Backend",
                "model_version": nlp_model.version,
                "epochs_completed": nlp_model.epochs_completed,
                "current_loss": nlp_model.current_loss,
                "accuracy": nlp_model.accuracy,
                "perplexity": nlp_model.perplexity,
                "total_samples": stats["total_samples"],
                "total_tokens": stats["total_tokens"],
                "vocab_size": nlp_model.vocab_size,
                "is_training": training_state["is_training"],
                "last_trained": nlp_model.last_trained_timestamp
            })
            return

        # API: List Ingested Datasets
        elif path == "/api/datasets/list":
            cat = query.get("category", [None])[0]
            limit = int(query.get("limit", [100])[0])
            samples = dataset_mgr.get_samples(category=cat, limit=limit)
            stats = dataset_mgr.get_stats()
            self._send_json_response({
                "samples": samples,
                "stats": stats
            })
            return

        # API: Live Training Progress
        elif path == "/api/train/progress":
            self._send_json_response({
                "training_state": training_state,
                "history": nlp_model.training_history[-10:]
            })
            return

        # API: SQLite Database Statistics
        elif path == "/api/db/stats":
            self._send_json_response(db.get_db_stats())
            return

        # Fallback to static file server (for serving index.html, styles.css, etc.)
        super().do_GET()

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        body = self._read_json_body()

        # API: Ingest Clinical Dataset Sample
        if path == "/api/datasets/ingest":
            category = body.get("category", "Clinical Guideline")
            title = body.get("title", "Clinical Data Entry")
            text = body.get("text", "")
            source = body.get("source", "Real-Time Ingestion")

            if not text.strip():
                self._send_json_response({"error": "Dataset text cannot be empty"}, status=400)
                return

            new_sample = dataset_mgr.ingest_sample(category, title, text, source)
            self._send_json_response({
                "success": True,
                "sample": new_sample,
                "stats": dataset_mgr.get_stats()
            })
            return

        # API: Ingest Batch Benchmark Datasets
        elif path == "/api/datasets/ingest_benchmark":
            benchmark_name = body.get("benchmark", "mimic_cardio")
            benchmark_samples = [
                {
                    "category": "EHR Clinical Notes",
                    "title": "Cardiology Consultation: Atrial Fibrillation with RVR",
                    "text": "68M with established atrial fibrillation on Apixaban 5mg BID and Metoprolol Succinate 50mg daily. Complains of palpitations and lightheadedness for 3 days. ECG reveals irregular tachycardia at 128 bpm without ST elevation. Auscultation irregular rhythm, no murmurs. Lungs clear. Diltiazem titrated for rate control. Electrolytes normal (K 4.2 mEq/L, Mg 2.1 mg/dL).",
                    "source": "MIMIC-IV Cardio Cohort"
                },
                {
                    "category": "Clinical Guidelines",
                    "title": "GOLD 2026 COPD Staging & Inhaler Therapy Protocols",
                    "text": "Classification of airflow limitation in chronic obstructive pulmonary disease: Post-bronchodilator FEV1/FVC < 0.70 confirms diagnosis. Stage 1 Mild (FEV1 >= 80%), Stage 2 Moderate (50-79%), Stage 3 Severe (30-49%), Stage 4 Very Severe (< 30%). Initial maintenance therapy for Group E (high exacerbation risk) requires dual LABA/LAMA bronchodilation or triple therapy with inhaled corticosteroids if eosinophils >= 300 cells/uL.",
                    "source": "GOLD Global COPD Report"
                },
                {
                    "category": "FDA Safety & Interactions",
                    "title": "NSAID-Induced Acute Kidney Injury & ACE-Inhibitor Interaction",
                    "text": "Concomitant administration of nonsteroidal anti-inflammatory drugs (Ibuprofen, Naproxen) with ACE inhibitors (Lisinopril) or ARBs impairs glomerular filtration via efferent arteriolar vasodilation coupled with afferent vasoconstriction. Clinicians must caution hypertensive patients against OTC NSAID overuse.",
                    "source": "FDA Drug Safety Bulletin"
                }
            ]
            added = []
            for b in benchmark_samples:
                s = dataset_mgr.ingest_sample(b["category"], b["title"], b["text"], b["source"])
                added.append(s)

            self._send_json_response({
                "success": True,
                "added_count": len(added),
                "stats": dataset_mgr.get_stats()
            })
            return

        # API: Start Training on Ingested Real-Time Datasets
        elif path == "/api/train/start":
            if training_state["is_training"]:
                self._send_json_response({
                    "success": False,
                    "message": "Training is already in progress",
                    "training_state": training_state
                }, status=409)
                return

            epochs = int(body.get("epochs", 5))
            lr = float(body.get("learning_rate", 0.015))

            # Spawn training thread
            thread = threading.Thread(target=run_background_training, args=(epochs, lr), daemon=True)
            thread.start()

            self._send_json_response({
                "success": True,
                "message": f"Real-time training initiated for {epochs} epochs.",
                "training_state": training_state
            })
            return

        # API: Log Clinician Feedback (DPO active learning)
        elif path == "/api/feedback/log":
            encounter_id = body.get("encounterId", "CONS-UNKNOWN")
            original_soap = body.get("originalSoap", {})
            clinician_soap = body.get("clinicianSoap", {})
            clinician = body.get("clinician", "Dr. Demo Clinician")

            feedback_sample = dataset_mgr.log_clinician_feedback(
                encounter_id=encounter_id,
                original_soap=original_soap,
                clinician_soap=clinician_soap,
                clinician_name=clinician
            )

            self._send_json_response({
                "success": True,
                "message": "Clinician review diff logged as DPO active learning sample",
                "sample": feedback_sample,
                "stats": dataset_mgr.get_stats()
            })
            return

        # API: Sync Patients & Consultations from Frontend into SQLite
        elif path == "/api/db/sync":
            patients = body.get("patients", [])
            consultations = body.get("consultations", [])

            with db.get_connection() as conn:
                cursor = conn.cursor()
                for p in patients:
                    cursor.execute("""
                        INSERT OR REPLACE INTO patients (id, name, age, sex, mrn, chief_complaint, allergies_json, conditions_json, medications_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        p.get("id"),
                        p.get("name"),
                        p.get("age"),
                        p.get("sex"),
                        p.get("mrn", "N/A"),
                        p.get("chiefComplaint", ""),
                        json.dumps(p.get("historicalAllergies", [])),
                        json.dumps(p.get("historicalConditions", [])),
                        json.dumps(p.get("historicalMedications", []))
                    ))
                for c in consultations:
                    cursor.execute("""
                        INSERT OR REPLACE INTO consultations (id, patient_id, date, status, chief_complaint, duration, clinician, transcript_json, soap_json, alerts_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        c.get("id"),
                        c.get("patientId"),
                        c.get("date"),
                        c.get("status"),
                        c.get("chiefComplaint"),
                        c.get("duration"),
                        c.get("clinician"),
                        json.dumps(c.get("transcript", [])),
                        json.dumps(c.get("soapNote", {})),
                        json.dumps(c.get("secondLookAlerts", []))
                    ))
                conn.commit()

            self._send_json_response({
                "success": True,
                "synced_patients": len(patients),
                "synced_consultations": len(consultations),
                "db_stats": db.get_db_stats()
            })
            return

        # API: Clinical Second Look & Inference
        elif path == "/api/analyze":
            transcript = body.get("transcript", [])
            patient = body.get("patient", {})

            analysis_result = nlp_model.infer_clinical_analysis(transcript, patient)
            self._send_json_response(analysis_result)
            return

        else:
            self._send_json_response({"error": "Endpoint not found"}, status=404)


def start_server():
    print("=" * 65)
    print("  MediScribe Clinical AI REST Backend & Real-Time Training Engine")
    print(f"  Server URL: http://{HOST}:{PORT}")
    print(f"  API Health: http://{HOST}:{PORT}/api/status")
    print(f"  Active Model: {nlp_model.version}")
    print(f"  Ingested Samples: {len(dataset_mgr.samples)}")
    print("=" * 65)
    
    # Allow port reuse immediately
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((HOST, PORT), MediScribeHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down MediScribe backend...")
            httpd.shutdown()


if __name__ == "__main__":
    start_server()
