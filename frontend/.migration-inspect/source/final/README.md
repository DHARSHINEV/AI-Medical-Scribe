# MediScribe — Live AI Medical Scribe & Clinical Safety Assistant

> **PEC Techathon 4.0 MVP**  
> *Track: Healthcare & Assistive Intelligence*  
> **Listen &rarr; Understand &rarr; Document &rarr; Cross-Check &rarr; Review &rarr; Approve**

---

## 1. Project Overview

**MediScribe** is a live clinical documentation and safety-support web application. It listens to a doctor-patient consultation, transcribes the conversation with speaker labeling, extracts structured clinical observations, and drafts a complete **SOAP Note** (Subjective, Objective, Assessment, Plan).

### Central Product Principle
> **"MediScribe doesn't just document the consultation. It gives the clinician a second look before the note is finalized."**

Commercial ambient scribes focus exclusively on transcription speed. MediScribe introduces an automated clinical safety second look that cross-checks conversations against stored EHR patient history, flags missing dosage parameters, warns of potential allergy conflicts, detects clinical contradictions, and suggests documentation review points.

---

## 2. Problem Statement

1. **Clinician Burnout & Cognitive Overload:** Physicians spend over 2 hours on EHR data entry for every hour of patient care, leading to mental fatigue and rushed documentation.
2. **Clinical Blind Spots in Real-Time Dialogues:** Patients often forget their exact medication dosages or verbally deny allergies they previously experienced (e.g. childhood penicillin hives). Busy doctors can easily miss these discrepancies during a fast-paced walk-in encounter.
3. **Black-Box AI Risks:** Autonomous AI doctors or unstructured LLMs frequently fabricate vitals or hallucinate diagnoses, posing severe patient safety risks.

---

## 3. The MediScribe Solution & Key Innovation

### The Key Innovation: "AI Clinical Second Look"

After generating the preliminary SOAP note, MediScribe performs a second-pass analysis across 4 clinical vectors:

1. **Patient History Checker (Discrepancy Detector):**
   - *Example:* Arun Kumar's stored EHR chart lists an active **Penicillin allergy** (urticaria/generalized rash). In the consultation, Arun casually states: *"I don't think I have any allergies."*
   - MediScribe immediately flags: `⚠ HISTORY DISCREPANCY: Previous record: Penicillin allergy documented. Current conversation: Allergy status is uncertain. Please verify before finalizing documentation.`
2. **Prescription Completeness Check:**
   - *Example:* The patient mentions taking **Amlodipine** for hypertension, but forgets the milligram strength.
   - MediScribe flags: `⚠ Dose missing, ⚠ Duration missing. Status: Needs Review.`
3. **Contradiction Detection:**
   - Detects discrepancies between spoken dialogue, previous history, and proposed treatment plans.
4. **Explainable Evidence Linking:**
   - Every extracted clinical entity and SOAP sentence features a `[View Source]` link that instantly scrolls to and highlights the exact timestamped segment in the transcript.
   - Explainability tags: `CONFIRMED FROM TRANSCRIPT`, `INFERRED / NEEDS REVIEW`, `NOT DOCUMENTED`, `CONFLICT DETECTED`.

---

## 4. Clinician Control & Non-Autonomous Guardrails

- **No Autonomous Diagnosis:** MediScribe never diagnoses disease autonomously.
- **No Autonomous Prescribing:** It never orders or modifies prescriptions without human review.
- **Section-Level Regeneration:** Clinicians can regenerate a single block (e.g. Assessment) without overwriting manual edits in other sections.
- **8-Point Verification Sign-Off:** Notes cannot be approved without explicit verification of identity, allergies, medications, and clinical plans.

---

## 5. Technology Stack & Zero-Build Architecture

MediScribe is built strictly as a **standard HTML5 website** requiring **zero npm packages, zero Node build steps, and zero frameworks**:

- **HTML5:** Semantic layouts, `<canvas>` Web Audio visualizers, native drag-and-drop file zones.
- **CSS3:** Clean healthcare SaaS theme, responsive 3-column grid, alert styles, and dedicated `@media print` medical letterhead stylesheets.
- **Vanilla JavaScript (ES6+):** Pure browser scripts with a modular `window.MediScribe` namespace.
- **Browser Web APIs:**
  - `navigator.mediaDevices.getUserMedia()`: Real microphone audio capture.
  - `MediaRecorder`: Audio stream management.
  - `AudioContext` & `AnalyserNode`: Real-time audio waveform visualizer.
  - `SpeechRecognition` / `webkitSpeechRecognition`: Browser speech-to-text with graceful fallbacks.
  - `localStorage`: Client-side persistence for patients, encounters, and audit logs.
  - `navigator.clipboard`: One-click SOAP note clipboard copying.
  - `window.print()`: Clean PDF medical report generation.

---

## 6. Project Directory Structure

```
mediscribe/
│
├── index.html                  # Main dashboard (KPIs, quick actions, recent encounters)
├── consultation.html           # 3-column live workspace (Patient, Transcript & Mic, AI Docs)
├── review.html                 # Final clinician review, Clinical Second Look, sign-off
├── history.html                # Consultation history with search and status filtering
├── labs.html                   # Lab Report Analyzer with reference range checking
├── settings.html               # AI architecture settings, audit trail, storage reset
│
├── css/
│   └── styles.css              # Clean clinical theme, responsive grid, badges, print styles
│
├── js/
│   ├── app.js                  # Namespace, storage manager, toasts, audit logging
│   ├── recorder.js             # getUserMedia, AudioContext visualizer, SpeechRecognition
│   ├── transcript.js           # Transcript rendering, speaker attribution, evidence scroll
│   ├── consultation.js         # 3-column workspace orchestrator & patient switcher
│   ├── analysis.js             # Deterministic clinical engine (SOAP, Second Look, ICD-10)
│   ├── history.js              # Consultation list & records manager
│   ├── labs.js                 # Lab file parser & reference range comparison
│   ├── review.js               # Review screen, section regenerator, approval workflow
│   ├── export.js               # PDF print generator, JSON schema export, clipboard copy
│   └── demo.js                 # 5-minute judge demo controller & pitch script
│
├── data/
│   └── demo-data.js            # Synthetic patient database (Arun Kumar, Sarah Jenkins, Priya Sharma)
│
├── exports/
│   ├── sample_cbc_lab_report.txt   # Sample CBC report for live judge upload testing
│   └── sample_metabolic_panel.txt  # Sample BMP report for live judge upload testing
│
└── README.md                   # Comprehensive documentation
```

---

## 7. How to Run the Website

### Option 1: Direct File Open (Zero Setup)
Simply double-click:
```
index.html
```
The entire application will open and run in any modern web browser (Google Chrome, Microsoft Edge, Mozilla Firefox, Safari).

### Option 2: Local HTTP Server (Optional)
If preferred, you can run a lightweight server:

```powershell
# Using Python
python -m http.server 8000

# Or using npx
npx serve .
```
Then navigate to `http://localhost:8000`.

---

## 8. Five-Minute Hackathon Judge Demo Script

Follow this step-by-step presentation flow during judging:

| Time | Action | What to Say / Point Out |
|---|---|---|
| **00:00 – 00:30** | Open `index.html` (Dashboard) | *"MediScribe is an AI medical documentation assistant with a built-in Clinical Second Look. We don't just transcribe — we protect clinicians and patients from documentation gaps."* |
| **00:30 – 01:30** | Click **Start Demo Consultation** | Point out the 3 columns: Arun Kumar's stored EHR history on the left, live transcript with speaker tags in the center, and live mic visualizer. |
| **01:30 – 02:00** | Click **⚡ Generate SOAP Note & Second Look** | Show structured Subjective, Objective, Assessment, and Plan note drafted in milliseconds. Point out explainable `[View Source]` links. |
| **02:00 – 03:00** | Focus on **AI CLINICAL SECOND LOOK** Card | Point out: (1) **History Discrepancy:** EHR lists Penicillin allergy, but Arun said *"I don't think I have any allergies"*. (2) **Missing Information:** Arun takes Amlodipine, but omitted the dose. |
| **03:00 – 03:45** | Navigate to **Lab Reports** (`labs.html`) | Click **Load Sample CBC Report** (or drag `exports/sample_cbc_lab_report.txt`). Show Hemoglobin at 11.2 g/dL flagged strictly as *"Outside supplied reference range"* without autonomous diagnosis. Click **Add to Consultation**. |
| **03:45 – 04:15** | Go to **Review & Approve** (`review.html`) | Show section-level regeneration (click `↻ Regenerate Section` on Assessment). Demonstrate that other sections remain untouched. |
| **04:15 – 04:45** | Complete Clinician Checklist & Click **APPROVE NOTE** | The note is locked and officially stamped: `✓ NOTE APPROVED BY QUALIFIED CLINICIAN (Dr. Demo Clinician)`. |
| **04:45 – 05:00** | Click **Print / Save PDF** or **Export JSON** | View clean medical clinic letterhead PDF ready for electronic health records. |

> **Pro Tip:** Look for the floating **TECHATHON 4.0 Judge Demo Guide** bar at the bottom of the screen! You can click through each step automatically with built-in pitch prompts.

---

## 9. AI Provider Architecture & Security

- **Default Provider:** `DemoProvider` running local deterministic rule-based algorithms. Requires **zero external API keys** and zero network requests.
- **Enterprise Architecture:** In production, LLM queries interface with a secure proxy (e.g. `POST /api/mediscribe-proxy`) rather than embedding secret API keys in client JavaScript.
- **Data Privacy & Synthetic Data:** All patient records, diagnoses, and lab results are 100% fictitious synthetic records for educational demonstration.
- **Audit Logging:** Every transcription capture, SOAP note generation, alert resolution, and note sign-off creates a permanent audit record accessible in `settings.html`.

---

## 10. Regulatory & Clinical Disclaimer

> **PROTOTYPE DEMONSTRATION ONLY — SYNTHETIC DATA**  
> MediScribe is an AI-assisted clinical documentation and safety-support prototype created for PEC Techathon 4.0. It is **not** a certified medical device, autonomous diagnostic agent, or prescribing system. All medical documentation and safety recommendations must be validated by a licensed physician before clinical application.
