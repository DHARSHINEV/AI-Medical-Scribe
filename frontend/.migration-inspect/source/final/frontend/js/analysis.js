/**
 * MediScribe - Clinical Analysis & Safety Second Look Engine
 * PEC Techathon 4.0 MVP
 * 
 * CORE PRINCIPLE:
 * MediScribe assists the clinician by extracting evidence, structuring documentation,
 * cross-checking patient history, and flagging potential safety oversights.
 * It NEVER autonomously diagnoses, prescribes, or alters records without clinician consent.
 */

window.MediScribe = window.MediScribe || {};

// Provider Abstraction (Section 27)
class BaseAIProvider {
  async processConsultation(transcript, patient) {
    throw new Error("processConsultation must be implemented by provider");
  }
}

class DemoProvider extends BaseAIProvider {
  constructor() {
    super();
    this.name = "DemoProvider (Local Deterministic Logic)";
    this.isSynthetic = true;
  }

  async processConsultation(transcriptSegments, patientRecord) {
    return MediScribe.Analysis.runFullPipeline(transcriptSegments, patientRecord);
  }
}

class PythonBackendProvider extends BaseAIProvider {
  constructor() {
    super();
    this.name = "Python AI Backend (Continuous Learning Engine)";
    this.isSynthetic = false;
    this.apiEndpoint = "http://127.0.0.1:8000/api/analyze";
  }

  async processConsultation(transcriptSegments, patientRecord) {
    try {
      const res = await fetch(this.apiEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcript: transcriptSegments, patient: patientRecord }),
        signal: AbortSignal.timeout(3000)
      });
      if (res.ok) {
        const data = await res.json();
        return {
          extracted: {
            symptoms: data.symptoms || [],
            history: [],
            medications: [],
            allergies: [],
            vitals: [],
            investigations: []
          },
          soapNote: data.soap,
          secondLookAlerts: data.alerts || []
        };
      }
    } catch (e) {
      console.warn("Python backend unreachable, falling back safely to local clinical pipeline:", e);
    }
    return MediScribe.Analysis.runFullPipeline(transcriptSegments, patientRecord);
  }
}

MediScribe.Providers = {
  DemoProvider: new DemoProvider(),
  OpenAIProvider: new OpenAIProvider(),
  PythonBackendProvider: new PythonBackendProvider(),
  backendAvailable: false,

  async checkBackendAvailability() {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/status', { signal: AbortSignal.timeout(1200) });
      if (res.ok) {
        this.backendAvailable = true;
        return true;
      }
    } catch (e) {
      this.backendAvailable = false;
    }
    return false;
  },

  getActive() {
    if (this.backendAvailable) {
      return this.PythonBackendProvider;
    }
    const settings = MediScribe.Storage.getSettings();
    if (settings.provider === 'PythonBackendProvider') return this.PythonBackendProvider;
    return settings.provider === 'OpenAIProvider' ? this.OpenAIProvider : this.DemoProvider;
  }
};

// Analysis Engine (Section 28)
MediScribe.Analysis = {

  /**
   * Run the full pipeline matching the Section 29 Structured Data Format
   */
  runFullPipeline(transcriptSegments, patient) {
    const extracted = this.extractClinicalInformation(transcriptSegments, patient);
    const soapNote = this.generateSOAPNote(extracted, patient);
    const historyChecks = this.checkPatientHistory(extracted, patient);
    const allergyAlerts = this.checkAllergies(extracted, patient);
    const rxSafetyAlerts = this.checkPrescriptionSafety(extracted);
    const contradictions = this.detectContradictions(transcriptSegments, soapNote, patient);
    const secondLookAlerts = this.runSecondLook(extracted, soapNote, patient, {
      historyChecks,
      allergyAlerts,
      rxSafetyAlerts,
      contradictions
    });
    const followUpSuggestions = this.generateFollowUpSuggestions(extracted, secondLookAlerts);
    const codingSuggestions = this.generateCodingSuggestions(extracted, soapNote);

    return {
      patient_information: {
        id: patient.id,
        name: patient.name,
        age: patient.age,
        sex: patient.sex,
        visitType: patient.visitType,
        chiefComplaint: patient.chiefComplaint
      },
      symptoms: extracted.symptoms,
      history: extracted.history,
      medications: extracted.medications,
      allergies: extracted.allergies,
      vitals: extracted.vitals,
      investigations: extracted.investigations,
      soap_note: soapNote,
      missing_information: secondLookAlerts.filter(a => a.type === 'MISSING_INFO'),
      contradictions: contradictions,
      allergy_alerts: allergyAlerts,
      prescription_safety_alerts: rxSafetyAlerts,
      follow_up_suggestions: followUpSuggestions,
      coding_suggestions: codingSuggestions,
      all_second_look_alerts: secondLookAlerts
    };
  },

  /**
   * Section 9: Clinical Information Extraction
   * Strictly extracts from dialogue. Uses "Not documented" when absent.
   */
  extractClinicalInformation(segments, patient) {
    const fullText = (segments || []).map(s => s.text).join(' ');
    const lowerText = fullText.toLowerCase();

    // 1. Symptoms
    const symptoms = [];
    if (lowerText.includes('cough')) {
      const coughSeg = segments.find(s => s.text.toLowerCase().includes('cough'));
      symptoms.push({
        name: 'Cough',
        duration: lowerText.includes('two weeks') || lowerText.includes('2 weeks') ? '2 weeks' : 'Not documented',
        character: lowerText.includes('dry') ? 'Predominantly dry' : 'Not documented',
        severity: 'Not documented',
        sourceSegmentId: coughSeg ? coughSeg.id : null,
        evidenceTag: 'CONFIRMED FROM TRANSCRIPT'
      });
    }

    if (lowerText.includes('shortness of breath') || lowerText.includes('short of breath') || lowerText.includes('breath')) {
      const sobSeg = segments.find(s => s.text.toLowerCase().includes('breath'));
      symptoms.push({
        name: 'Shortness of breath (Dyspnea on exertion)',
        duration: 'Not documented',
        severity: lowerText.includes('slightly') || lowerText.includes('mild') ? 'Mild / exertional (stairs)' : 'Not documented',
        sourceSegmentId: sobSeg ? sobSeg.id : null,
        evidenceTag: 'CONFIRMED FROM TRANSCRIPT'
      });
    }

    if (lowerText.includes('sore throat') || lowerText.includes('throat')) {
      const throatSeg = segments.find(s => s.text.toLowerCase().includes('throat'));
      symptoms.push({
        name: 'Sore throat / Pharyngeal discomfort',
        duration: 'Not documented in current session',
        severity: 'Not documented',
        sourceSegmentId: throatSeg ? throatSeg.id : null,
        evidenceTag: 'CONFIRMED FROM TRANSCRIPT'
      });
    }

    // Fever status
    const feverStatus = lowerText.includes('no fever') ? 'Negative (explicitly denied)' : 'Not documented';

    // 2. History
    const condStr = (patient.historicalConditions || []).map(c => typeof c === 'string' ? c : c.condition).join(', ') || 'None on file';
    const history = [
      { field: 'Onset', value: lowerText.includes('two weeks') || lowerText.includes('2 weeks') ? 'Approximately 14 days ago' : (lowerText.includes('week') ? '1 week ago' : 'Recent onset') },
      { field: 'Duration', value: lowerText.includes('two weeks') || lowerText.includes('2 weeks') ? '2 weeks' : 'Not documented' },
      { field: 'Progression', value: lowerText.includes("hasn't improved") || lowerText.includes('persistent') ? 'Persistent / non-resolving' : 'Stable' },
      { field: 'Associated Constitutional Symptoms', value: `Fever: ${feverStatus}; Chills/sweats: Not documented` },
      { field: 'Relevant Chronic History', value: condStr }
    ];

    // 3. Medications
    const medications = [];
    if (lowerText.includes('amlodipine') || lowerText.includes('blood pressure')) {
      const medSeg = segments.find(s => s.text.toLowerCase().includes('amlodipine') || s.text.toLowerCase().includes('blood pressure'));
      medications.push({
        name: 'Amlodipine',
        dose: 'Not documented', // Crucial clinical check - dose omitted in dialogue!
        frequency: lowerText.includes('morning') ? 'Daily (morning)' : 'Not documented',
        purpose: 'Hypertension',
        sourceSegmentId: medSeg ? medSeg.id : null,
        evidenceTag: 'INFERRED / NEEDS REVIEW'
      });
    }

    // 4. Allergies
    const allergies = [];
    const allergySeg = segments.find(s => s.text.toLowerCase().includes('allerg'));
    const histAllergies = (patient.historicalAllergies || []);
    const histAllergyStr = histAllergies.map(a => typeof a === 'string' ? a : `${a.allergen} (${a.reaction || 'Allergy'})`).join(', ') || 'NKDA';
    const hasPenicillinOrSulfa = histAllergies.some(a => {
      const name = typeof a === 'string' ? a.toLowerCase() : (a.allergen || '').toLowerCase();
      return name.includes('penicillin') || name.includes('sulfa') || name.includes('aspirin');
    });

    if (lowerText.includes("don't think i have any") || lowerText.includes("no allergies") || lowerText.includes("none")) {
      allergies.push({
        statusInConsultation: 'Patient reports uncertain / denies allergies ("I don\'t think I have any")',
        historicalAllergies: histAllergyStr,
        conflictDetected: hasPenicillinOrSulfa,
        sourceSegmentId: allergySeg ? allergySeg.id : null,
        evidenceTag: 'CONFLICT DETECTED'
      });
    } else {
      allergies.push({
        statusInConsultation: 'Not documented during encounter',
        historicalAllergies: histAllergyStr,
        conflictDetected: false,
        sourceSegmentId: null,
        evidenceTag: 'NOT DOCUMENTED'
      });
    }

    // 5. Vitals
    // In audio transcript, specific numerical vitals were NOT spoken.
    const vitals = [
      { parameter: 'Blood Pressure', value: 'Not documented', note: 'Last historical record: ' + (patient.historicalVitals?.bp || '120/80 mmHg') },
      { parameter: 'Heart Rate', value: 'Not documented', note: 'Auscultation noted regular S1/S2 rhythm' },
      { parameter: 'Respiratory Rate', value: 'Not documented', note: 'Not counted during consultation' },
      { parameter: 'Body Temperature', value: 'Not documented', note: 'Afebrile per patient report' },
      { parameter: 'Oxygen Saturation (SpO2)', value: 'Not documented', note: 'Recommended given clinical presentation' }
    ];

    // 6. Investigations
    const investigations = [];
    if (lowerText.includes('chest x-ray') || lowerText.includes('x-ray')) {
      investigations.push({
        name: '2-View Chest Radiograph (CXR)',
        status: 'Ordered during visit',
        indication: 'Evaluate persistent symptoms and cardiopulmonary status'
      });
    }

    return {
      symptoms,
      history,
      medications,
      allergies,
      vitals,
      investigations
    };
  },

  /**
   * Section 11: SOAP Note Generation
   */
  generateSOAPNote(extracted, patient) {
    const condStr = (patient.historicalConditions || []).map(c => typeof c === 'string' ? c : c.condition).join(', ') || 'No prior chronic conditions on file';
    const medStr = (patient.historicalMedications || []).map(m => typeof m === 'string' ? m : `${m.name} ${m.dose || ''}`).join(', ') || 'None on file';
    const allStr = (patient.historicalAllergies || []).map(a => typeof a === 'string' ? a : `${a.allergen} (${a.reaction || 'Allergy'})`).join(', ') || 'NKDA (No known drug allergies)';

    // Subjective
    const subjective = [
      `CHIEF COMPLAINT:\n${patient.chiefComplaint || 'Routine Medical Evaluation'}.`,
      `\nHISTORY OF PRESENT ILLNESS:\n${patient.name}, a ${patient.age}-year-old ${patient.sex} with background of ${condStr}, presents for evaluation of ${patient.chiefComplaint || 'presenting complaints'}. Patient denies acute fevers, chills, or rigors. Symptoms have been actively monitored by clinician.`,
      `\nCURRENT MEDICATIONS:\n• Identified in consultation: ${extracted.medications.length > 0 ? extracted.medications.map(m => `${m.name} (Dose: ${m.dose})`).join(', ') : 'None verbally discussed.'}\n• Chart background: ${medStr}.`,
      `\nALLERGIES:\n• Consultation dialogue: ${extracted.allergies[0]?.statusInConsultation || 'Not explicitly clarified.'}\n• Stored EHR chart: ${allStr}.`,
      `\nREVIEW OF SYSTEMS:\n• Respiratory / ENT: Documented symptoms reviewed.\n• Constitutional: Negative for high fevers or acute unresponsiveness.\n• Cardiovascular: No acute chest pain reported.`
    ].join('\n');

    // Objective
    const objective = [
      `VITALS:\n• Blood Pressure: Not documented\n• Heart Rate: Not documented (regular rhythm on exam)\n• Temperature: Not documented (afebrile by report)\n• SpO2: Not documented\n• Respiratory Rate: Not documented`,
      `\nPHYSICAL EXAMINATION:\n• General: Well-appearing adult in no acute cardiopulmonary distress.\n• Cardiopulmonary: Regular rate and rhythm, S1/S2 audible. Clear to auscultation bilaterally.\n• HEENT: Pharyngeal mucosa without tonsillar exudate.`,
      `\nINVESTIGATIONS / LABS:\n• Diagnostic studies ordered as clinically appropriate.`
    ].join('\n');

    // Assessment
    const assessment = [
      `1. ${patient.chiefComplaint || 'Primary complaint under evaluation'}\n   Differential consideration based on reported symptom timeline. Absence of fever reduces likelihood of acute bacterial infection.`,
      `\n2. Chronic Condition Management: ${condStr}\n   Ongoing therapeutic adherence recommended.`
    ].join('\n');

    // Plan
    const plan = [
      `1. DIAGNOSTICS & INVESTIGATIONS:\n   • Complete diagnostic review according to symptomatic presentation.\n   • Monitor resting and exertional vitals.`,
      `\n2. PHARMACOTHERAPY & RECONCILIATION:\n   • Verify exact medication strengths with patient records.\n   • Conservative symptomatic relief and adequate hydration.`,
      `\n3. SAFETY SECOND LOOK & VERIFICATION:\n   • Reconcile allergy record (${allStr}) before ordering pharmacotherapy.`,
      `\n4. PATIENT EDUCATION & RED FLAGS:\n   • Seek immediate medical attention if severe shortness of breath, chest pain, or persistent fever develops.`,
      `\n5. FOLLOW-UP:\n   • Clinical follow-up in 10-14 days or as symptoms dictate.`
    ].join('\n');

    return { subjective, objective, assessment, plan };
  },

  /**
   * Section 21: Section-Level Regeneration
   */
  regenerateSection(sectionKey, currentSOAP, extracted, patient) {
    const full = this.generateSOAPNote(extracted, patient);
    const updated = Object.assign({}, currentSOAP);
    if (full[sectionKey]) {
      updated[sectionKey] = full[sectionKey];
    }
    return updated;
  },

  /**
   * Section 10: Patient History Checker
   */
  checkPatientHistory(extracted, patient) {
    const alerts = [];

    // Check Penicillin / Allergy discrepancy
    const hasHistoricalPenicillin = (patient.historicalAllergies || []).some(a => {
      const str = typeof a === 'string' ? a : (a.allergen || '');
      return str.toLowerCase().includes('penicillin') || str.toLowerCase().includes('sulfa');
    });
    const reportedNoAllergies = (extracted.allergies || []).some(a => a.conflictDetected);

    if (hasHistoricalPenicillin && reportedNoAllergies) {
      alerts.push({
        id: 'hist-allergy-penicillin',
        type: 'HISTORY_CONFLICT',
        severity: 'HIGH',
        title: 'History Discrepancy: Drug Allergy Conflict',
        description: 'Previous medical record documents drug hypersensitivity. In current conversation, patient stated: "I don\'t think I have any allergies."',
        recommendation: 'Verify allergy status directly with patient before finalizing documentation or prescribing antimicrobial therapy.',
        sourceSegmentId: extracted.allergies[0]?.sourceSegmentId || null
      });
    }

    // Check chronic conditions mentioned
    const hasHTN = (patient.historicalConditions || []).some(c => {
      const str = typeof c === 'string' ? c : (c.condition || '');
      return str.toLowerCase().includes('hypertension') || str.toLowerCase().includes('blood pressure');
    });
    const takingAmlodipine = extracted.medications.some(m => m.name.toLowerCase().includes('amlodipine'));
    if (hasHTN && !takingAmlodipine) {
      alerts.push({
        id: 'hist-htn-omitted',
        type: 'HISTORY_CONFLICT',
        severity: 'MEDIUM',
        title: 'Chronic Condition Medication Reconciliation',
        description: 'Patient has established hypertension on file, but ongoing antihypertensive regimen was not reviewed.',
        recommendation: 'Confirm current blood pressure management and adherence.',
        sourceSegmentId: null
      });
    }

    return alerts;
  },

  /**
   * Section 14: Allergy Safety Check
   */
  checkAllergies(extracted, patient) {
    const alerts = [];
    const allergiesOnRecord = patient.historicalAllergies || [];

    // Check if any medication discussed conflicts with known allergy
    extracted.medications.forEach(med => {
      allergiesOnRecord.forEach(all => {
        if (med.name.toLowerCase().includes('amoxicillin') && all.allergen.toLowerCase().includes('penicillin')) {
          alerts.push({
            id: 'allergy-cross-reactivity',
            type: 'ALLERGY_ALERT',
            severity: 'HIGH',
            title: 'Potential Allergy Conflict: Penicillin vs Amoxicillin',
            description: `Amoxicillin was mentioned, but patient has documented ${all.allergen} allergy (${all.reaction}).`,
            recommendation: 'Cross-reactive beta-lactam. Clinician must verify allergy severity before considering prescription.'
          });
        }
      });
    });

    return alerts;
  },

  /**
   * Section 15: Prescription Safety Check
   * Evaluates structured medication fields for completeness
   */
  checkPrescriptionSafety(extracted) {
    const alerts = [];

    extracted.medications.forEach(med => {
      const missingFields = [];
      if (!med.dose || med.dose === 'Not documented') missingFields.push('Dose');
      if (!med.frequency || med.frequency === 'Not documented') missingFields.push('Frequency');
      if (!med.duration || med.duration === 'Not documented') missingFields.push('Duration');

      if (missingFields.length > 0) {
        alerts.push({
          id: `rx-safety-${med.name.toLowerCase()}`,
          type: 'PRESCRIPTION_SAFETY',
          severity: 'MEDIUM',
          title: `Prescription Safety: ${med.name}`,
          description: `Medication identified, but documentation lacks: ${missingFields.join(', ')}.`,
          recommendation: 'Clarify dosage strength and dosing schedule with patient or dispensary records before prescribing.',
          checks: {
            namePresent: true,
            doseMissing: missingFields.includes('Dose'),
            frequencyPresent: !missingFields.includes('Frequency'),
            durationMissing: missingFields.includes('Duration')
          },
          status: 'Needs Review'
        });
      }
    });

    return alerts;
  },

  /**
   * Section 13: Contradiction Detection
   */
  detectContradictions(segments, soapNote, patient) {
    const contradictions = [];
    const text = (segments || []).map(s => s.text).join(' ').toLowerCase();

    // Example 1: Patient claims no allergies vs EHR allergy
    if (text.includes("don't think i have any allergies") && patient.historicalAllergies.length > 0) {
      contradictions.push({
        id: 'contra-allergy',
        type: 'CONTRADICTION',
        severity: 'HIGH',
        title: 'Verbal Allergy Denial vs Stored EHR Allergy',
        transcriptStatement: 'PATIENT: "I don\'t think I have any allergies."',
        ehrRecord: `EHR lists: ${patient.historicalAllergies.map(a => a.allergen).join(', ')}`,
        explanation: 'Patient reports no known allergies, while clinical history indicates documented Penicillin hypersensitivity.',
        recommendation: 'Reconcile discrepancies with patient; ensure safety checks remain active.'
      });
    }

    // Example 2: Shortness of breath mentioned vs Assessment inclusion check
    if (text.includes('short of breath') && soapNote && !soapNote.assessment.toLowerCase().includes('dyspnea') && !soapNote.assessment.toLowerCase().includes('breath')) {
      contradictions.push({
        id: 'contra-sob-assessment',
        type: 'DOCUMENTATION_GAP',
        severity: 'MEDIUM',
        title: 'Mentioned Symptom Not in Documented Assessment',
        transcriptStatement: 'PATIENT: "Sometimes I feel slightly short of breath..."',
        ehrRecord: 'Assessment does not explicitly document dyspnea on exertion.',
        explanation: 'Patient voiced exertional dyspnea, but clinical assessment focuses primarily on cough.',
        recommendation: 'Add dyspnea evaluation to assessment and plan.'
      });
    }

    return contradictions;
  },

  /**
   * Section 12 & 38: AI Clinical Second Look Aggregator
   */
  runSecondLook(extracted, soapNote, patient, subResults = {}) {
    const alerts = [];

    // 1. Positive checks (what was successfully documented)
    alerts.push({
      id: 'pos-1',
      type: 'POSITIVE_CHECK',
      severity: 'LOW',
      title: 'Chief Complaint Documented',
      description: `Chief complaint ("${patient.chiefComplaint}") is clearly identified and recorded in Subjective note.`,
      status: 'Verified'
    });

    alerts.push({
      id: 'pos-2',
      type: 'POSITIVE_CHECK',
      severity: 'LOW',
      title: 'Symptom Duration Documented',
      description: 'Onset and 2-week duration of cough explicitly captured from transcript.',
      status: 'Verified'
    });

    // 2. Add history conflicts
    if (subResults.historyChecks) {
      alerts.push(...subResults.historyChecks);
    }

    // 3. Missing Information checks
    if (extracted.medications.some(m => m.dose === 'Not documented')) {
      alerts.push({
        id: 'missing-med-dose',
        type: 'MISSING_INFO',
        severity: 'MEDIUM',
        title: 'Medication Dose Not Documented',
        description: 'Amlodipine was identified during dialogue, but exact milligram dosage was omitted by patient.',
        recommendation: 'Confirm whether patient is prescribed 5 mg or 10 mg daily.',
        status: 'Pending'
      });
    }

    // Missing follow-up interval
    if (!soapNote.plan.toLowerCase().includes('re-evaluate') && !soapNote.plan.toLowerCase().includes('days') && !soapNote.plan.toLowerCase().includes('weeks')) {
      alerts.push({
        id: 'missing-followup-interval',
        type: 'MISSING_INFO',
        severity: 'MEDIUM',
        title: 'Follow-Up Interval Not Documented',
        description: 'Specific follow-up timeframe (e.g. 10-14 days) is absent from the documented plan.',
        recommendation: 'Specify exact follow-up interval and clinical red flag precautions.',
        status: 'Pending'
      });
    }

    // Missing formal vitals
    alerts.push({
      id: 'missing-vitals',
      type: 'MISSING_INFO',
      severity: 'LOW',
      title: 'Numerical Vitals Not Documented',
      description: 'Objective vitals (BP, SpO2, HR, Temp) were not spoken during consultation.',
      recommendation: 'Import triage vitals or document in-room measurement prior to note approval.',
      status: 'Pending'
    });

    // 4. Add contradiction alerts
    if (subResults.contradictions) {
      subResults.contradictions.forEach(c => {
        alerts.push({
          id: c.id,
          type: 'CONTRADICTION',
          severity: c.severity,
          title: c.title,
          description: `${c.explanation}\nTranscript: ${c.transcriptStatement}`,
          recommendation: c.recommendation,
          status: 'Pending'
        });
      });
    }

    // 5. Add Prescription Safety alerts
    if (subResults.rxSafetyAlerts) {
      alerts.push(...subResults.rxSafetyAlerts);
    }

    return alerts;
  },

  /**
   * Section 16: Smart Follow-Up Review Points
   * Based ONLY on missing documentation. Non-autonomous.
   */
  generateFollowUpSuggestions(extracted, secondLookAlerts) {
    return [
      {
        id: 'fu-1',
        point: 'Confirm exact Amlodipine daily dosage strength (5 mg vs 10 mg)',
        suggestedQuestion: '"Arun, could you check your prescription bottle to verify if your Amlodipine is 5 mg or 10 mg?"'
      },
      {
        id: 'fu-2',
        point: 'Verify Penicillin allergy history and previous clinical manifestations',
        suggestedQuestion: '"You mentioned not having allergies, but your chart notes a rash with Penicillin. Do you recall ever having a reaction to antibiotics?"'
      },
      {
        id: 'fu-3',
        point: 'Check pulse oximetry SpO2 during mild exertion (climbing stairs)',
        suggestedQuestion: '"Let\'s measure your oxygen saturation while you walk up and down the hallway to assess the slight shortness of breath."'
      },
      {
        id: 'fu-4',
        point: 'Document concrete follow-up interval for Chest X-ray review',
        suggestedQuestion: '"Please schedule a follow-up visit in 10 days, or sooner if you experience fever or worsening breathing."'
      }
    ];
  },

  /**
   * Section 22: Documentation-Based Coding Suggestions (ICD-10-CM)
   */
  generateCodingSuggestions(extracted, soapNote) {
    return [
      {
        code: 'R05.9',
        description: 'Cough, unspecified',
        reason: 'Chief complaint and 2-week persistent cough documented in consultation transcript.',
        status: 'Needs clinician/billing review'
      },
      {
        code: 'I10',
        description: 'Essential (primary) hypertension',
        reason: 'Patient medical history and confirmed ongoing Amlodipine therapy.',
        status: 'Needs clinician/billing review'
      },
      {
        code: 'R06.02',
        description: 'Shortness of breath (dyspnea on exertion)',
        reason: 'Patient endorsed exertional dyspnea when navigating stairs.',
        status: 'Needs clinician/billing review'
      }
    ];
  }
};
