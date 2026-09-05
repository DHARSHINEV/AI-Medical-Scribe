"""
MediScribe Real-Time Dataset Manager & Ingestion Engine
Manages clinical knowledge bases, streaming real-time dataset ingestion,
and Clinician DPO (Direct Preference Optimization) feedback pairs.
"""

import json
import os
import time
from db import db

class DatasetManager:
    def __init__(self, data_dir=None):
        self.data_dir = data_dir or os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.datasets_file = os.path.join(self.data_dir, "datasets.json")
        self.samples = []
        self.load_datasets()

    def _get_seed_datasets(self):
        """Pre-populates baseline clinical benchmark datasets."""
        return [
            {
                "id": "DS-MIMIC-001",
                "category": "EHR Clinical Notes",
                "source": "MIMIC-IV Ambulatory Benchmark",
                "title": "Primary Care: 45M Persistent Cough & Exertional Dyspnea",
                "text": "Patient presents with 2-week history of non-productive cough following viral upper respiratory infection. Endorses mild shortness of breath climbing two flights of stairs. Denies fever, chest pain, hemoptysis. Background essential hypertension treated with oral Amlodipine. Documented allergy to Penicillin with urticaria reaction. Auscultation reveals clear lung fields bilaterally without crackles or wheezing. Plan: CXR, verify Amlodipine dosage, symptomatic throat lozenges, avoid beta-lactam antibiotics.",
                "tokens": 74,
                "ingested_at": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": "DS-GUIDE-002",
                "category": "Clinical Guidelines",
                "source": "AHA/ACC Hypertension Guidelines",
                "title": "Stage 1 & Stage 2 Hypertension Management Protocols",
                "text": "First-line pharmacotherapy for essential hypertension in non-black adult patients includes thiazide diuretics, CCBs (such as Amlodipine 5-10 mg daily), and ACE-inhibitors or ARBs. Initial evaluation requires resting blood pressure measurement across two separate visits, serum creatinine, electrolytes, and lipid panel. Clinicians must confirm exact dosage and verify adherence before adjusting antihypertensive regimens.",
                "tokens": 68,
                "ingested_at": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": "DS-DRUG-003",
                "category": "FDA Safety & Interactions",
                "source": "FDA Adverse Event Reporting & Drug Safety",
                "title": "Beta-Lactam Antibiotic Cross-Reactivity in Penicillin-Allergic Patients",
                "text": "Patients with documented severe IgE-mediated Penicillin hypersensitivity (anaphylaxis, angioedema, widespread urticarial rash) carry up to a 10% risk of cross-reactivity with first-generation cephalosporins and aminopenicillins (Amoxicillin, Ampicillin). Verbal patient statements claiming lack of allergies must be cross-referenced against historical electronic medical records prior to ordering antimicrobials.",
                "tokens": 62,
                "ingested_at": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": "DS-MIMIC-004",
                "category": "EHR Clinical Notes",
                "source": "Endocrinology Clinical Cohort",
                "title": "Routine Type 2 Diabetes & Primary Hypothyroidism Review",
                "text": "62F presented for 6-month routine metabolic review. Denies polyuria, polydipsia, or peripheral neuropathy. On Metformin 500mg BID and Levothyroxine 75mcg daily. In-clinic fasting fingerstick glucose 108 mg/dL. Recent HbA1c 6.4%. Thyroid function tests within target TSH 2.1 mIU/L. Exam shows diabetic foot exam intact sensation 10g monofilament. Continued current therapy with 6-month follow-up.",
                "tokens": 65,
                "ingested_at": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": "DS-GUIDE-005",
                "category": "Clinical Guidelines",
                "source": "IDSA Pharyngitis Management Guidelines",
                "title": "Acute Pharyngitis & Centor Diagnostic Scoring",
                "text": "Evaluation of acute sore throat requires assessing Centor criteria: absence of cough, tonsillar exudates, tender anterior cervical adenopathy, and history of fever. Patients with scores 0-1 have low probability of Group A Streptococcus and do not warrant antibiotic therapy. Symptomatic treatment with warm salt water gargles and oral analgesics is indicated.",
                "tokens": 61,
                "ingested_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        ]

    def load_datasets(self):
        if os.path.exists(self.datasets_file):
            try:
                with open(self.datasets_file, "r", encoding="utf-8") as f:
                    self.samples = json.load(f)
            except Exception as e:
                print(f"[DatasetManager] Error loading datasets: {e}")
                self.samples = self._get_seed_datasets()
                self.save_datasets()
        else:
            self.samples = self._get_seed_datasets()
            self.save_datasets()

    def save_datasets(self):
        with open(self.datasets_file, "w", encoding="utf-8") as f:
            json.dump(self.samples, f, indent=2)
        # Mirror to SQLite database
        try:
            for s in self.samples:
                db.insert_dataset_sample(
                    sample_id=s.get("id"),
                    category=s.get("category", "General"),
                    source=s.get("source", "N/A"),
                    title=s.get("title", ""),
                    content=s.get("text", ""),
                    tokens=s.get("tokens", 0)
                )
        except Exception as e:
            print(f"[DB] SQLite sync error: {e}")

    def ingest_sample(self, category, title, text, source="Custom Ingestion"):
        """Ingests a new real-time clinical sample into the dataset."""
        words = text.split()
        sample_id = f"DS-{category[:3].upper()}-{int(time.time() * 1000) % 100000:05d}"
        new_sample = {
            "id": sample_id,
            "category": category,
            "source": source,
            "title": title,
            "text": text.strip(),
            "tokens": len(words),
            "ingested_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.samples.insert(0, new_sample)
        self.save_datasets()
        return new_sample

    def log_clinician_feedback(self, encounter_id, original_soap, clinician_soap, clinician_name="Dr. Demo Clinician"):
        """
        Logs clinician correction pairs (Draft vs Signed) as Direct Preference
        Optimization (DPO) / active learning reinforcement pairs.
        """
        diff_text = f"Encounter: {encounter_id}. Clinician {clinician_name} verified and modified note sections."
        feedback_text = (
            f"Original AI Draft:\n{json.dumps(original_soap, indent=1)}\n\n"
            f"Clinician Final Signed Note:\n{json.dumps(clinician_soap, indent=1)}"
        )
        return self.ingest_sample(
            category="Clinician Feedback (DPO)",
            title=f"Active Learning Diff: Encounter {encounter_id}",
            text=feedback_text,
            source=f"Clinician Review: {clinician_name}"
        )

    def get_stats(self):
        total_tokens = sum(s.get("tokens", 0) for s in self.samples)
        categories = {}
        for s in self.samples:
            cat = s.get("category", "General")
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_samples": len(self.samples),
            "total_tokens": total_tokens,
            "categories": categories,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_samples(self, category=None, limit=100):
        if category and category != "ALL":
            filtered = [s for s in self.samples if s.get("category") == category]
            return filtered[:limit]
        return self.samples[:limit]
