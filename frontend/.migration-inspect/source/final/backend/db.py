"""
MediScribe SQLite Database Manager (backend/db.py)
Provides relational SQL persistence for:
- Patients table
- Consultations table
- Ingested Training Datasets table
- Clinical Audit Logs table
"""

import sqlite3
import os
import json
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "mediscribe.db")

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_schema()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self):
        """Creates the relational SQL tables if they do not exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Patients Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patients (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    age INTEGER,
                    sex TEXT,
                    mrn TEXT,
                    chief_complaint TEXT,
                    allergies_json TEXT,
                    conditions_json TEXT,
                    medications_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Consultations Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consultations (
                    id TEXT PRIMARY KEY,
                    patient_id TEXT,
                    date TEXT,
                    status TEXT,
                    chief_complaint TEXT,
                    duration TEXT,
                    clinician TEXT,
                    transcript_json TEXT,
                    soap_json TEXT,
                    alerts_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (patient_id) REFERENCES patients (id)
                );
            """)

            # 3. Real-Time Ingested Datasets Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS datasets (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    source TEXT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tokens INTEGER,
                    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 4. Clinical Audit Logs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    action TEXT NOT NULL,
                    detail TEXT,
                    actor TEXT
                );
            """)
            conn.commit()

    # --- Dataset Operations ---
    def insert_dataset_sample(self, sample_id, category, source, title, content, tokens):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO datasets (id, category, source, title, content, tokens, ingested_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (sample_id, category, source, title, content, tokens, time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()

    def get_all_datasets(self, category=None, limit=100):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if category and category != "ALL":
                cursor.execute("SELECT * FROM datasets WHERE category = ? ORDER BY ingested_at DESC LIMIT ?", (category, limit))
            else:
                cursor.execute("SELECT * FROM datasets ORDER BY ingested_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    # --- Database Statistics ---
    def get_db_stats(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM datasets")
            ds_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM patients")
            pt_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM consultations")
            cons_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM audit_logs")
            audit_count = cursor.fetchone()[0]

            db_size_bytes = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

            return {
                "db_engine": "SQLite 3",
                "db_path": self.db_path,
                "db_size_kb": round(db_size_bytes / 1024, 2),
                "tables": {
                    "datasets": ds_count,
                    "patients": pt_count,
                    "consultations": cons_count,
                    "audit_logs": audit_count
                }
            }

# Global singleton
db = Database()
