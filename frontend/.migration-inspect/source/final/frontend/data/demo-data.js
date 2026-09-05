/**
 * MediScribe - Demo Data Module
 * Synthetic clinical records for PEC Techathon 4.0 MVP
 * STRICT COMPLIANCE: All data is 100% synthetic and fictitious.
 */

window.MediScribe = window.MediScribe || {};

window.MediScribe.DemoData = {
  patients: [
    {
      id: "DEMO-001",
      name: "Arun Kumar",
      age: 45,
      sex: "Male",
      dob: "1981-04-12",
      mrn: "MRN-782910",
      visitType: "Primary Care / Walk-in",
      chiefComplaint: "Persistent cough for 2 weeks",
      historicalConditions: [
        { condition: "Hypertension", diagnosedDate: "2021-06-15", status: "Active" },
        { condition: "Seasonal Allergic Rhinitis", diagnosedDate: "2019-03-20", status: "Intermittent" }
      ],
      historicalMedications: [
        { name: "Amlodipine", dose: "5 mg", frequency: "Daily", route: "Oral", purpose: "Hypertension" }
      ],
      historicalAllergies: [
        { allergen: "Penicillin", reaction: "Urticaria / Generalized rash", severity: "Moderate", notedDate: "2018-09-10" }
      ],
      historicalVitals: {
        lastRecorded: "2026-06-10",
        bp: "128/82 mmHg",
        hr: "74 bpm",
        temp: "98.4 °F",
        spo2: "98%",
        weight: "76 kg"
      }
    },
    {
      id: "DEMO-002",
      name: "Sarah Jenkins",
      age: 38,
      sex: "Female",
      dob: "1988-11-03",
      mrn: "MRN-441209",
      visitType: "Endocrinology Follow-Up",
      chiefComplaint: "Routine diabetes and thyroid review",
      historicalConditions: [
        { condition: "Type 2 Diabetes Mellitus", diagnosedDate: "2020-01-14", status: "Active" },
        { condition: "Hypothyroidism", diagnosedDate: "2017-08-22", status: "Active" }
      ],
      historicalMedications: [
        { name: "Metformin", dose: "500 mg", frequency: "Twice daily", route: "Oral", purpose: "Glycemic control" },
        { name: "Levothyroxine", dose: "75 mcg", frequency: "Daily", route: "Oral", purpose: "Thyroid hormone replacement" }
      ],
      historicalAllergies: [
        { allergen: "Sulfa antibiotics", reaction: "Facial edema", severity: "Severe", notedDate: "2015-04-05" }
      ],
      historicalVitals: {
        lastRecorded: "2026-07-02",
        bp: "122/78 mmHg",
        hr: "68 bpm",
        temp: "98.6 °F",
        spo2: "99%",
        weight: "64 kg"
      }
    },
    {
      id: "DEMO-003",
      name: "Priya Sharma",
      age: 29,
      sex: "Female",
      dob: "1997-02-18",
      mrn: "MRN-601934",
      visitType: "Urgent Care",
      chiefComplaint: "Sore throat and mild difficulty swallowing",
      historicalConditions: [
        { condition: "Mild intermittent asthma", diagnosedDate: "2016-10-11", status: "Well-controlled" }
      ],
      historicalMedications: [
        { name: "Albuterol Inhaler", dose: "90 mcg", frequency: "PRN (as needed)", route: "Inhalation", purpose: "Bronchospasm" }
      ],
      historicalAllergies: [
        { allergen: "No known drug allergies (NKDA)", reaction: "N/A", severity: "None", notedDate: "2024-01-15" }
      ],
      historicalVitals: {
        lastRecorded: "2026-05-18",
        bp: "116/74 mmHg",
        hr: "80 bpm",
        temp: "99.1 °F",
        spo2: "99%",
        weight: "58 kg"
      }
    }
  ],

  demoConsultationDialogue: [
    {
      id: "seg-1",
      timestamp: "00:08",
      speaker: "DOCTOR",
      text: "Good morning, Arun. What brings you into the clinic today?"
    },
    {
      id: "seg-2",
      timestamp: "00:14",
      speaker: "PATIENT",
      text: "Good morning, doctor. I've had a cough for around two weeks now, mostly dry, and it just hasn't improved."
    },
    {
      id: "seg-3",
      timestamp: "00:22",
      speaker: "DOCTOR",
      text: "I see. Any fever, chills, or night sweats over these past two weeks?"
    },
    {
      id: "seg-4",
      timestamp: "00:28",
      speaker: "PATIENT",
      text: "No fever at all. My temperature feels normal."
    },
    {
      id: "seg-5",
      timestamp: "00:35",
      speaker: "DOCTOR",
      text: "Any shortness of breath or chest tightness when you exert yourself?"
    },
    {
      id: "seg-6",
      timestamp: "00:42",
      speaker: "PATIENT",
      text: "Sometimes I feel slightly short of breath when climbing the stairs at home, but nothing severe."
    },
    {
      id: "seg-7",
      timestamp: "00:54",
      speaker: "DOCTOR",
      text: "What medications are you currently taking on a regular basis?"
    },
    {
      id: "seg-8",
      timestamp: "01:02",
      speaker: "PATIENT",
      text: "Just my blood pressure medication that I take every morning."
    },
    {
      id: "seg-9",
      timestamp: "01:08",
      speaker: "DOCTOR",
      text: "Do you know the name and dose of that medication?"
    },
    {
      id: "seg-10",
      timestamp: "01:15",
      speaker: "PATIENT",
      text: "I think it is amlodipine. I don't remember the exact milligram strength."
    },
    {
      id: "seg-11",
      timestamp: "01:25",
      speaker: "DOCTOR",
      text: "Understood. And do you have any known allergies to medications, foods, or environmental triggers?"
    },
    {
      id: "seg-12",
      timestamp: "01:34",
      speaker: "PATIENT",
      text: "I don't think I have any allergies."
    },
    {
      id: "seg-13",
      timestamp: "01:46",
      speaker: "DOCTOR",
      text: "Alright. I'm listening to your lungs now. Breath sounds are clear bilaterally with no wheezing or crackles. Heart sounds are regular S1/S2. Throat has mild posterior pharyngeal erythema, no exudates."
    },
    {
      id: "seg-14",
      timestamp: "02:05",
      speaker: "DOCTOR",
      text: "Your cough is likely a post-viral tracheobronchial irritation or possibly related to your antihypertensive therapy. We will order a routine chest X-ray to be certain, and suggest conservative hydration and throat lozenges. Let's verify your exact amlodipine dose."
    }
  ],

  sampleLabs: [
    {
      id: "LAB-CBC-001",
      title: "Complete Blood Count (CBC) with Differential",
      patientId: "DEMO-001",
      patientName: "Arun Kumar",
      orderDate: "2026-08-28",
      specimen: "Whole Blood (EDTA)",
      results: [
        { test: "Hemoglobin", value: 11.2, unit: "g/dL", refLow: 13.0, refHigh: 17.5, status: "Outside supplied reference range", flag: "LOW" },
        { test: "Hematocrit", value: 34.8, unit: "%", refLow: 39.0, refHigh: 50.0, status: "Outside supplied reference range", flag: "LOW" },
        { test: "White Blood Cell Count (WBC)", value: 7.4, unit: "x10^3/uL", refLow: 4.5, refHigh: 11.0, status: "Within normal limits", flag: "NORMAL" },
        { test: "Platelet Count", value: 245, unit: "x10^3/uL", refLow: 150, refHigh: 450, status: "Within normal limits", flag: "NORMAL" },
        { test: "Red Blood Cell Count (RBC)", value: 4.1, unit: "x10^6/uL", refLow: 4.3, refHigh: 5.9, status: "Outside supplied reference range", flag: "LOW" },
        { test: "Neutrophils (%)", value: 62.0, unit: "%", refLow: 40.0, refHigh: 70.0, status: "Within normal limits", flag: "NORMAL" },
        { test: "Lymphocytes (%)", value: 28.5, unit: "%", refLow: 20.0, refHigh: 45.0, status: "Within normal limits", flag: "NORMAL" }
      ],
      clinicianNote: "Mild microcytic anemia pattern noted on CBC. Recommend serum ferritin and iron panel correlation."
    },
    {
      id: "LAB-BMP-002",
      title: "Basic Metabolic Panel (BMP)",
      patientId: "DEMO-002",
      patientName: "Sarah Jenkins",
      orderDate: "2026-08-25",
      specimen: "Serum",
      results: [
        { test: "Fasting Blood Glucose", value: 142, unit: "mg/dL", refLow: 70, refHigh: 99, status: "Outside supplied reference range", flag: "HIGH" },
        { test: "Serum Creatinine", value: 0.9, unit: "mg/dL", refLow: 0.6, refHigh: 1.2, status: "Within normal limits", flag: "NORMAL" },
        { test: "Blood Urea Nitrogen (BUN)", value: 16, unit: "mg/dL", refLow: 7, refHigh: 20, status: "Within normal limits", flag: "NORMAL" },
        { test: "Serum Potassium", value: 4.3, unit: "mmol/L", refLow: 3.5, refHigh: 5.0, status: "Within normal limits", flag: "NORMAL" },
        { test: "Serum Sodium", value: 139, unit: "mmol/L", refLow: 135, refHigh: 145, status: "Within normal limits", flag: "NORMAL" },
        { test: "eGFR", value: 88, unit: "mL/min/1.73m2", refLow: 60, refHigh: 120, status: "Within normal limits", flag: "NORMAL" }
      ],
      clinicianNote: "Elevated fasting blood sugar in established T2D. Correlate with current Metformin dosing and HbA1c."
    }
  ],

  initialConsultations: [
    {
      id: "CONS-2026-08-29-001",
      patientId: "DEMO-001",
      patientName: "Arun Kumar",
      date: "2026-08-29",
      time: "09:15 AM",
      visitType: "Primary Care / Walk-in",
      chiefComplaint: "Persistent cough for 2 weeks",
      duration: "02:14",
      status: "Draft",
      clinician: "Dr. Demo Clinician",
      soapNote: {
        subjective: "Chief Complaint: Persistent cough for around 2 weeks, predominantly dry.\nHistory of Present Illness: 45-year-old male with history of hypertension presents with 2-week history of cough. Denies fever, chills, or night sweats. Endorses occasional mild shortness of breath on exertion (stairs).\nMedications: Amlodipine (dose not documented during consultation; historical dose 5 mg daily).\nAllergies: Current consultation reports 'no allergies'; historical record documents Penicillin allergy.\nReview of Systems: Respiratory positive for cough and mild DOE. Constitutional negative for fever.",
        objective: "Vitals: Not documented during current consultation.\nPhysical Examination: Lungs clear to auscultation bilaterally; no wheezes, rales, or rhonchi. Heart regular rate and rhythm, S1/S2 present. Oropharynx displays mild posterior pharyngeal erythema without exudate or tonsillar hypertrophy.",
        assessment: "1. Persistent cough, unspecified (ICD-10: R05.9) - duration 2 weeks; differential includes post-viral irritation vs. ACEi/CCB-related etiology.\n2. Mild dyspnea on exertion, mentioned but requires clinical monitoring.\n3. Essential hypertension (ICD-10: I10) - baseline control on Amlodipine.",
        plan: "1. Diagnostic: Order routine 2-view Chest X-Ray to evaluate lung parenchyma.\n2. Medications: Continue Amlodipine; verify exact dosage with pharmacy.\n3. Symptomatic care: Adequate hydration, warm fluids, over-the-counter throat lozenges.\n4. Safety: Allergy reconciliation required regarding Penicillin before prescribing any antimicrobial therapy.\n5. Follow-up: Re-evaluate in 10-14 days or immediately if dyspnea worsens or fever develops."
      },
      secondLookAlerts: [
        {
          id: "alert-1",
          type: "HISTORY_CONFLICT",
          severity: "HIGH",
          title: "Allergy History Discrepancy",
          description: "Previous medical record documents Penicillin allergy (urticaria/rash). In current consultation, patient stated: 'I don't think I have any allergies.'",
          recommendation: "Reconcile allergy record with patient before prescribing beta-lactam antibiotics.",
          status: "Pending"
        },
        {
          id: "alert-2",
          type: "MISSING_INFO",
          severity: "MEDIUM",
          title: "Medication Dose Not Documented",
          description: "Amlodipine was identified as patient's active antihypertensive, but dosage strength was not specified in the dialogue.",
          recommendation: "Confirm whether patient is taking 5 mg or 10 mg daily.",
          status: "Pending"
        },
        {
          id: "alert-3",
          type: "DOCUMENTATION_GAP",
          severity: "MEDIUM",
          title: "Exertional Dyspnea Follow-up",
          description: "Patient mentioned mild shortness of breath when climbing stairs, but formal SpO2 measurement is missing from vitals.",
          recommendation: "Record resting and exertional pulse oximetry if clinically indicated.",
          status: "Pending"
        }
      ],
      codingSuggestions: [
        { code: "R05.9", description: "Cough, unspecified", confidence: "High", reason: "Chief complaint documented in transcript" },
        { code: "I10", description: "Essential (primary) hypertension", confidence: "Medium", reason: "Documented chronic condition and active Amlodipine usage" },
        { code: "R06.02", description: "Shortness of breath", confidence: "Low", reason: "Patient endorsed exertional dyspnea" }
      ]
    },
    {
      id: "CONS-2026-08-27-002",
      patientId: "DEMO-002",
      patientName: "Sarah Jenkins",
      date: "2026-08-27",
      time: "11:30 AM",
      visitType: "Endocrinology Follow-Up",
      chiefComplaint: "Routine diabetes and thyroid review",
      duration: "06:40",
      status: "Approved",
      clinician: "Dr. Demo Clinician",
      approvedAt: "2026-08-27 11:45 AM",
      soapNote: {
        subjective: "Patient attends for regular endocrine review. Reports adherence to Metformin 500mg BID and Levothyroxine 75mcg daily. No hypoglycemia episodes reported.",
        objective: "Vitals: BP 122/78 mmHg, HR 68 bpm. Labs: Fasting Blood Glucose 142 mg/dL. Thyroid gland non-tender, no nodules.",
        assessment: "1. Type 2 Diabetes Mellitus - suboptimally controlled fasting glucose.\n2. Primary Hypothyroidism - clinically euthyroid on current replacement.",
        plan: "1. Order HbA1c and comprehensive metabolic panel.\n2. Dietary counseling on carbohydrate distribution.\n3. Continue Metformin 500mg BID; review in 3 months with lab results."
      },
      secondLookAlerts: [],
      codingSuggestions: [
        { code: "E11.9", description: "Type 2 diabetes mellitus without complications", confidence: "High", reason: "Active disease review" },
        { code: "E03.9", description: "Hypothyroidism, unspecified", confidence: "High", reason: "Chronic thyroid management" }
      ]
    },
    {
      id: "CONS-2026-08-24-003",
      patientId: "DEMO-003",
      patientName: "Priya Sharma",
      date: "2026-08-24",
      time: "02:10 PM",
      visitType: "Urgent Care",
      chiefComplaint: "Sore throat and mild difficulty swallowing",
      duration: "04:15",
      status: "Reviewed",
      clinician: "Dr. Demo Clinician",
      soapNote: {
        subjective: "29-year-old female presents with 3-day history of odynophagia. Denies cough or rhinorrhea. Mild subjective fevers at home.",
        objective: "Vitals: Temp 99.1 F, BP 116/74, HR 80. Examination: Bilateral tonsillar erythema 2+ without exudate. Anterior cervical lymphadenopathy palpable.",
        assessment: "Acute pharyngitis (ICD-10: J02.9) - Centor criteria score 2 (low probability for streptococcal etiology).",
        plan: "1. Rapid Strep antigen test performed.\n2. Symptomatic analgesia with acetaminophen/ibuprofen.\n3. Follow up if symptoms persist past 7 days."
      },
      secondLookAlerts: [],
      codingSuggestions: [
        { code: "J02.9", description: "Acute pharyngitis, unspecified", confidence: "High", reason: "Documented sore throat and pharyngeal exam" }
      ]
    }
  ]
};
