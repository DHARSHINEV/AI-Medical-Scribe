/**
 * MediScribe - Export Engine
 * Generates PDF (via print-ready window.print()), JSON schema download, and clipboard copy
 * PEC Techathon 4.0 MVP
 */

window.MediScribe = window.MediScribe || {};

MediScribe.Export = {

  /**
   * PDF Export via formatted window.print()
   */
  printPDF() {
    const consult = MediScribe.Storage.getActiveConsultation();
    if (!consult) {
      MediScribe.Toast.show('No active consultation found to export.', 'warning');
      return;
    }

    const patient = MediScribe.Storage.getPatientById(consult.patientId);

    // Populate or update the print container
    let printElem = document.getElementById('printMedicalDocumentArea');
    if (!printElem) {
      printElem = document.createElement('div');
      printElem.id = 'printMedicalDocumentArea';
      printElem.className = 'print-only-area';
      document.body.appendChild(printElem);
    }

    const soap = consult.soapNote || {
      subjective: 'Not documented',
      objective: 'Not documented',
      assessment: 'Not documented',
      plan: 'Not documented'
    };

    printElem.innerHTML = `
      <div style="font-family: Arial, sans-serif; color: black; padding: 20px; line-height: 1.5;">
        <!-- Header -->
        <div style="border-bottom: 2px solid #0f172a; padding-bottom: 12px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: flex-end;">
          <div>
            <h1 style="font-size: 22px; margin: 0; color: #0f172a;">METROHEALTH OUTPATIENT CLINIC</h1>
            <div style="font-size: 11px; color: #475569;">Department of Internal Medicine &bull; Clinical Documentation Summary</div>
          </div>
          <div style="text-align: right; font-size: 11px;">
            <div><strong>Consultation ID:</strong> ${consult.id}</div>
            <div><strong>Date:</strong> ${consult.date} ${consult.time || ''}</div>
          </div>
        </div>

        <!-- Demographics Box -->
        <div style="border: 1px solid #94a3b8; border-radius: 4px; padding: 10px 14px; margin-bottom: 16px; background-color: #f8fafc; font-size: 12px;">
          <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;">
            <div><strong>Patient Name:</strong> ${patient ? patient.name : consult.patientName}</div>
            <div><strong>Patient ID:</strong> ${consult.patientId}</div>
            <div><strong>Age / Sex:</strong> ${patient ? patient.age + ' yrs / ' + patient.sex : 'N/A'}</div>
            <div><strong>Visit Type:</strong> ${consult.visitType}</div>
          </div>
        </div>

        <!-- SOAP Note Content -->
        <div style="margin-bottom: 16px;">
          <div style="font-size: 13px; font-weight: bold; background: #e2e8f0; padding: 4px 8px; margin-bottom: 6px;">SUBJECTIVE</div>
          <div style="font-size: 12px; white-space: pre-line; margin-bottom: 14px; padding-left: 8px;">${this.escapeHtml(soap.subjective)}</div>

          <div style="font-size: 13px; font-weight: bold; background: #e2e8f0; padding: 4px 8px; margin-bottom: 6px;">OBJECTIVE</div>
          <div style="font-size: 12px; white-space: pre-line; margin-bottom: 14px; padding-left: 8px;">${this.escapeHtml(soap.objective)}</div>

          <div style="font-size: 13px; font-weight: bold; background: #e2e8f0; padding: 4px 8px; margin-bottom: 6px;">ASSESSMENT</div>
          <div style="font-size: 12px; white-space: pre-line; margin-bottom: 14px; padding-left: 8px;">${this.escapeHtml(soap.assessment)}</div>

          <div style="font-size: 13px; font-weight: bold; background: #e2e8f0; padding: 4px 8px; margin-bottom: 6px;">PLAN</div>
          <div style="font-size: 12px; white-space: pre-line; margin-bottom: 14px; padding-left: 8px;">${this.escapeHtml(soap.plan)}</div>
        </div>

        <!-- Clinician Signature Block -->
        <div style="border-top: 1px solid #0f172a; padding-top: 14px; margin-top: 24px; display: flex; justify-content: space-between; font-size: 12px;">
          <div>
            <div><strong>Electronically Signed By:</strong> ${consult.clinician || 'Dr. Demo Clinician'}</div>
            <div><strong>Status:</strong> ${consult.status} &bull; <strong>Signed At:</strong> ${consult.approvedAt || new Date().toLocaleString()}</div>
          </div>
          <div style="text-align: right;">
            <div>_________________________________________</div>
            <div style="font-size: 10px; color: #64748b;">Clinician Signature Verification</div>
          </div>
        </div>

        <!-- Permanent Legal / Regulatory Disclaimer -->
        <div style="margin-top: 24px; border-top: 1px dashed #cbd5e1; padding-top: 8px; font-size: 9px; color: #64748b; line-height: 1.3;">
          <strong>PROTOTYPE DEMONSTRATION RECORD:</strong> MediScribe is an AI-assisted clinical documentation and safety-support prototype developed for PEC Techathon 4.0. It is not an autonomous medical system. All medical information and synthetic records contained herein must be independently reviewed and verified by a licensed clinician.
        </div>
      </div>
    `;

    MediScribe.Audit.log('PDF Printed', `Triggered print dialog for ${consult.id}`);
    window.print();
  },

  /**
   * JSON Export matching Section 29 structured schema
   */
  exportJSON() {
    const consult = MediScribe.Storage.getActiveConsultation();
    if (!consult) {
      MediScribe.Toast.show('No consultation active to export.', 'warning');
      return;
    }

    const patient = MediScribe.Storage.getPatientById(consult.patientId);

    // Build standard Section 29 JSON structure
    const payload = {
      meta: {
        system: "MediScribe - Live AI Medical Scribe & Clinical Safety Assistant",
        version: "1.0.0-mvp",
        hackathon: "PEC Techathon 4.0",
        exportTimestamp: new Date().toISOString(),
        disclaimer: "SYNTHETIC DEMO DATA ONLY. NOT AN AUTONOMOUS MEDICAL SYSTEM."
      },
      patient_information: {
        id: patient.id,
        name: patient.name,
        age: patient.age,
        sex: patient.sex,
        dob: patient.dob,
        mrn: patient.mrn,
        visitType: consult.visitType,
        chiefComplaint: consult.chiefComplaint
      },
      consultation_metadata: {
        id: consult.id,
        date: consult.date,
        duration: consult.duration,
        status: consult.status,
        clinician: consult.clinician,
        approvedAt: consult.approvedAt || null
      },
      transcript: consult.transcript || [],
      soap_note: consult.soapNote || {},
      clinical_second_look_alerts: consult.secondLookAlerts || [],
      coding_suggestions: consult.codingSuggestions || [],
      follow_up_suggestions: consult.followUpSuggestions || []
    };

    const jsonString = JSON.stringify(payload, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `MediScribe_${consult.id}_${consult.patientName.replace(/\s+/g, '_')}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    MediScribe.Toast.show('Structured JSON exported successfully.', 'success');
    MediScribe.Audit.log('JSON Exported', `Downloaded structured JSON for ${consult.id}`);
  },

  /**
   * Clipboard Copy
   */
  async copySOAPNote() {
    const consult = MediScribe.Storage.getActiveConsultation();
    if (!consult || !consult.soapNote) {
      MediScribe.Toast.show('No SOAP note available to copy.', 'warning');
      return;
    }

    const soap = consult.soapNote;
    const formattedText = `MEDISCRIBE CLINICAL NOTE
Patient: ${consult.patientName} (${consult.patientId})
Date: ${consult.date} | Clinician: ${consult.clinician || 'Dr. Demo Clinician'}
Status: ${consult.status}

=== SUBJECTIVE ===
${soap.subjective}

=== OBJECTIVE ===
${soap.objective}

=== ASSESSMENT ===
${soap.assessment}

=== PLAN ===
${soap.plan}

[Documented via MediScribe AI Assistant - Verified by Clinician]`;

    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(formattedText);
        MediScribe.Toast.show('SOAP Note copied to clipboard for EHR pasting!', 'success');
      } else {
        // Fallback textarea copy
        const ta = document.createElement('textarea');
        ta.value = formattedText;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        MediScribe.Toast.show('SOAP Note copied to clipboard!', 'success');
      }
      MediScribe.Audit.log('Note Copied', `Copied SOAP note for ${consult.id} to clipboard`);
    } catch (e) {
      console.error('Clipboard copy failed', e);
      MediScribe.Toast.show('Could not copy to clipboard. Please copy manually.', 'warning');
    }
  },

  escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
};
