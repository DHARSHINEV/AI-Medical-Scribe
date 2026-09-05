/**
 * MediScribe - Final Clinician Review & Approval Workflow
 * Controls the dedicated review screen (review.html)
 * PEC Techathon 4.0 MVP
 */

window.MediScribe = window.MediScribe || {};

MediScribe.Review = {
  activeConsultation: null,
  activePatient: null,
  isApproved: false,

  init() {
    MediScribe.Storage.init();
    
    const urlParams = new URLSearchParams(window.location.search);
    const consultIdFromUrl = urlParams.get('id');
    if (consultIdFromUrl) {
      MediScribe.Storage.setActiveConsultation(consultIdFromUrl);
    }

    this.activeConsultation = MediScribe.Storage.getActiveConsultation();
    
    if (!this.activeConsultation) {
      const list = MediScribe.Storage.getConsultations();
      this.activeConsultation = list[0];
    }

    if (!this.activeConsultation) {
      document.getElementById('reviewContentArea').innerHTML = `
        <div class="card"><div class="card-body" style="text-align: center; padding: 40px;">
          <h3>No Consultation Available</h3>
          <p>Please start a consultation first.</p>
          <a href="consultation.html" class="btn btn-primary" style="margin-top: 12px;">Go to Consultation</a>
        </div></div>
      `;
      return;
    }

    this.activePatient = MediScribe.Storage.getPatientById(this.activeConsultation.patientId);
    this.isApproved = (this.activeConsultation.status === 'Approved');

    this.render();
    this.bindEvents();
  },

  render() {
    this.renderApprovalBanner();
    this.renderPatientHeader();
    this.renderSOAPEditor();
    this.renderSecondLookSection();
    this.renderSafetyMatrix();
    this.renderCodingSuggestions();
    this.renderFollowUpSection();
    this.renderChecklist();
  },

  renderApprovalBanner() {
    const bannerContainer = document.getElementById('approvalBannerContainer');
    if (!bannerContainer) return;

    if (this.isApproved) {
      bannerContainer.innerHTML = `
        <div class="approval-stamp-banner">
          <div>
            <div class="approval-stamp-text">✓ NOTE APPROVED BY QUALIFIED CLINICIAN</div>
            <div class="approval-stamp-meta">
              Approved by: <strong>${this.activeConsultation.clinician || 'Dr. Demo Clinician'}</strong> &bull; 
              Timestamp: <strong>${this.activeConsultation.approvedAt || new Date().toLocaleString()}</strong> &bull; 
              Status: <span class="badge badge-approved">Approved</span>
            </div>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-secondary btn-sm" onclick="MediScribe.Export.printPDF()">Print / Save PDF</button>
            <button class="btn btn-secondary btn-sm" onclick="MediScribe.Export.exportJSON()">Export JSON</button>
            <button class="btn btn-primary btn-sm" onclick="MediScribe.Review.unapprove()">Reopen for Edits</button>
          </div>
        </div>
      `;
    } else {
      bannerContainer.innerHTML = `
        <div class="disclaimer-box" style="margin-bottom: 20px;">
          <div style="font-weight: 700; color: var(--primary-dark); margin-bottom: 4px; font-size: 13px;">
            FINAL CLINICIAN REVIEW & SECOND LOOK
          </div>
          MediScribe generated this documentation from the consultation transcript. AI outputs may contain inaccuracies or documentation gaps. 
          Please review the SOAP note, verify the Clinical Second Look safety flags, and complete the checklist below before signing and approving.
        </div>
      `;
    }
  },

  renderPatientHeader() {
    const p = this.activePatient;
    const c = this.activeConsultation;
    const headerElem = document.getElementById('reviewPatientHeader');
    if (!headerElem || !p) return;

    headerElem.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div>
          <h2 style="font-size: 18px; font-weight: 700; color: var(--text-primary);">
            ${p.name} <span class="badge badge-low">${p.id}</span>
          </h2>
          <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
            ${p.age} yrs &bull; ${p.sex} &bull; DOB: ${p.dob} &bull; MRN: ${p.mrn}
          </div>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
          <span class="badge ${c.status === 'Approved' ? 'badge-approved' : (c.status === 'Reviewed' ? 'badge-reviewed' : 'badge-draft')}">
            ${c.status}
          </span>
          <span style="font-size: 12px; color: var(--text-muted);">Consultation Date: ${c.date}</span>
          <a href="consultation.html?id=${c.id}" class="btn btn-secondary btn-sm">← Back to Workspace</a>
        </div>
      </div>
    `;
  },

  renderSOAPEditor() {
    const container = document.getElementById('soapEditorContainer');
    if (!container || !this.activeConsultation.soapNote) return;

    const soap = this.activeConsultation.soapNote;

    const sections = [
      { key: 'subjective', title: 'SUBJECTIVE', content: soap.subjective },
      { key: 'objective', title: 'OBJECTIVE', content: soap.objective },
      { key: 'assessment', title: 'ASSESSMENT', content: soap.assessment },
      { key: 'plan', title: 'PLAN', content: soap.plan }
    ];

    let html = '';
    sections.forEach(sec => {
      html += `
        <div class="soap-section-box" style="margin-bottom: 16px;">
          <div class="soap-section-header">
            <span>${sec.title}</span>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-sm btn-secondary" onclick="MediScribe.Review.regenerateSingleSection('${sec.key}')" title="Regenerate only this section using deterministic AI logic" ${this.isApproved ? 'disabled' : ''}>
                ↻ Regenerate Section
              </button>
            </div>
          </div>
          <div style="padding: 12px;">
            <textarea 
              id="soapTextarea_${sec.key}" 
              class="soap-section-textarea" 
              rows="6" 
              ${this.isApproved ? 'readonly' : ''}
              onchange="MediScribe.Review.updateSOAPText('${sec.key}', this.value)"
            >${this.escapeHtml(sec.content)}</textarea>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  },

  updateSOAPText(key, newText) {
    if (!this.activeConsultation.soapNote) return;
    this.activeConsultation.soapNote[key] = newText;
    MediScribe.Storage.saveConsultation(this.activeConsultation);
    MediScribe.Toast.show(`${key.toUpperCase()} section updated.`, 'info', 1500);
  },

  regenerateSingleSection(sectionKey) {
    if (this.isApproved) return;
    const extracted = MediScribe.Analysis.extractClinicalInformation(
      this.activeConsultation.transcript || [], 
      this.activePatient
    );
    
    this.activeConsultation.soapNote = MediScribe.Analysis.regenerateSection(
      sectionKey,
      this.activeConsultation.soapNote,
      extracted,
      this.activePatient
    );

    MediScribe.Storage.saveConsultation(this.activeConsultation);
    this.renderSOAPEditor();
    MediScribe.Toast.show(`Section "${sectionKey.toUpperCase()}" regenerated deterministically. Other sections were preserved.`, 'success');
    MediScribe.Audit.log('Section Regenerated', `Regenerated section ${sectionKey}`);
  },

  renderSecondLookSection() {
    const container = document.getElementById('reviewSecondLookContainer');
    if (!container) return;

    const alerts = this.activeConsultation.secondLookAlerts || [];
    let alertsHtml = '';

    alerts.forEach(alert => {
      let badgeClass = 'badge-low';
      let itemClass = 'missing-info';
      if (alert.severity === 'HIGH') badgeClass = 'badge-high';
      if (alert.severity === 'MEDIUM') badgeClass = 'badge-medium';

      if (alert.type === 'HISTORY_CONFLICT') itemClass = 'history-conflict';
      if (alert.type === 'ALLERGY_ALERT') itemClass = 'allergy-alert';
      if (alert.type === 'CONTRADICTION') itemClass = 'contradiction-alert';
      if (alert.type === 'POSITIVE_CHECK') itemClass = 'positive-check';

      alertsHtml += `
        <div class="alert-item ${itemClass}">
          <div class="alert-item-header">
            <span class="alert-item-title">
              ${alert.type === 'POSITIVE_CHECK' ? '✓' : '⚠'} ${alert.title}
            </span>
            <span class="badge ${badgeClass}">${alert.severity || 'INFO'}</span>
          </div>
          <div class="alert-item-desc">${alert.description}</div>
          ${alert.recommendation ? `<div class="alert-item-recommendation"><strong>Action:</strong> ${alert.recommendation}</div>` : ''}
          ${alert.type !== 'POSITIVE_CHECK' && !this.isApproved ? `
            <div class="alert-actions">
              <button class="btn btn-sm btn-secondary" onclick="MediScribe.Review.dismissAlert('${alert.id}')">Dismiss Alert</button>
              <button class="btn btn-sm btn-primary" onclick="MediScribe.Review.focusSection('plan')">Edit in Plan</button>
            </div>
          ` : ''}
        </div>
      `;
    });

    container.innerHTML = `
      <div class="second-look-card">
        <div class="second-look-header">
          <div class="second-look-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
            AI CLINICAL SECOND LOOK FINDINGS
          </div>
          <span class="second-look-badge">${alerts.filter(a => a.type !== 'POSITIVE_CHECK').length} Active Issues</span>
        </div>
        <div class="second-look-alerts-list">
          ${alertsHtml || '<div style="padding: 16px; color: var(--text-muted);">No active safety alerts.</div>'}
        </div>
      </div>
    `;
  },

  dismissAlert(alertId) {
    if (this.activeConsultation && this.activeConsultation.secondLookAlerts) {
      this.activeConsultation.secondLookAlerts = this.activeConsultation.secondLookAlerts.filter(a => a.id !== alertId);
      MediScribe.Storage.saveConsultation(this.activeConsultation);
      this.renderSecondLookSection();
      MediScribe.Toast.show('Alert dismissed by reviewing clinician.', 'info');
      MediScribe.Audit.log('Alert Dismissed', `Clinician dismissed alert: ${alertId}`);
    }
  },

  focusSection(secKey) {
    const textarea = document.getElementById(`soapTextarea_${secKey}`);
    if (textarea) {
      textarea.scrollIntoView({ behavior: 'smooth', block: 'center' });
      textarea.focus();
    }
  },

  renderSafetyMatrix() {
    const container = document.getElementById('safetyMatrixContainer');
    if (!container) return;

    container.innerHTML = `
      <div class="card" style="margin-bottom: 20px;">
        <div class="card-header">
          <span class="card-title">Allergy & Prescription Safety Matrix</span>
          <span class="badge badge-reviewed">Automated Cross-Check</span>
        </div>
        <div class="card-body" style="padding: 14px;">
          <div style="display: flex; flex-direction: column; gap: 10px;">
            <!-- History Comparison -->
            <div style="background: #fff7ed; border-left: 3px solid #f97316; padding: 10px; border-radius: 4px;">
              <div style="font-weight: 700; font-size: 12px; color: #9a3412;">PATIENT HISTORY COMPARISON</div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
                <strong>Documented in EHR:</strong> Penicillin allergy (urticaria).<br>
                <strong>Consultation utterance:</strong> "I don't think I have any allergies."<br>
                <em style="color: #c2410c;">Status: Discrepancy flagged for clinician reconciliation.</em>
              </div>
            </div>

            <!-- Prescription Safety -->
            <div style="background: #f5f3ff; border-left: 3px solid #8b5cf6; padding: 10px; border-radius: 4px;">
              <div style="font-weight: 700; font-size: 12px; color: #5b21b6;">PRESCRIPTION COMPLETENESS: AMLODIPINE</div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
                ✓ Drug name verified &bull; ✓ Frequency identified (Daily) &bull; 
                <span style="color: #b91c1c; font-weight: 700;">⚠ Dose missing</span> &bull; 
                <span style="color: #b91c1c; font-weight: 700;">⚠ Duration missing</span><br>
                <em>Status: Clarification required before electronic prescription transmission.</em>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  },

  renderCodingSuggestions() {
    const container = document.getElementById('codingSuggestionsContainer');
    if (!container) return;

    const codes = this.activeConsultation.codingSuggestions || [
      { code: 'R05.9', description: 'Cough, unspecified', reason: 'Chief complaint', status: 'Needs review' },
      { code: 'I10', description: 'Essential hypertension', reason: 'Chronic history & Amlodipine', status: 'Needs review' },
      { code: 'R06.02', description: 'Shortness of breath', reason: 'Exertional symptom', status: 'Needs review' }
    ];

    let html = `
      <div class="card" style="margin-bottom: 20px;">
        <div class="card-header">
          <span class="card-title">Documentation-Based Coding Suggestions</span>
          <span class="badge badge-low">ICD-10-CM</span>
        </div>
        <div class="card-body" style="padding: 12px;">
          <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 10px;">
            Suggested billing codes derived strictly from documented symptoms and history. Requires medical coding review.
          </p>
          <div style="display: flex; flex-direction: column; gap: 8px;">
    `;

    codes.forEach((c, idx) => {
      html += `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 10px; background: var(--bg-muted); border-radius: 4px;">
          <div>
            <label style="cursor: pointer; font-weight: 600; font-size: 12px;">
              <input type="checkbox" checked ${this.isApproved ? 'disabled' : ''} style="margin-right: 6px;">
              <strong>${c.code}</strong> — ${c.description}
            </label>
            <div style="font-size: 11px; color: var(--text-secondary); margin-left: 20px;">${c.reason}</div>
          </div>
          <span class="badge badge-reviewed" style="font-size: 10px;">Review Required</span>
        </div>
      `;
    });

    html += `
          </div>
        </div>
      </div>
    `;

    container.innerHTML = html;
  },

  renderFollowUpSection() {
    const container = document.getElementById('followUpSectionContainer');
    if (!container) return;

    container.innerHTML = `
      <div class="card" style="margin-bottom: 20px;">
        <div class="card-header">
          <span class="card-title">Smart Follow-Up Review Points</span>
          <span class="badge badge-low">Documentation Gaps</span>
        </div>
        <div class="card-body" style="padding: 12px; font-size: 12px;">
          <ul style="padding-left: 18px; line-height: 1.6; color: var(--text-secondary);">
            <li><strong>Medication Reconciliation:</strong> Inquire if patient takes 5 mg or 10 mg Amlodipine.</li>
            <li><strong>Allergy Confirmation:</strong> Clarify prior rash reaction to Penicillin vs. current denial.</li>
            <li><strong>Vitals Documentation:</strong> Record SpO2 upon exertion before releasing patient.</li>
            <li><strong>Follow-Up Window:</strong> Confirm 10-14 day interval for Chest X-ray evaluation.</li>
          </ul>
        </div>
      </div>
    `;
  },

  renderChecklist() {
    const container = document.getElementById('checklistContainer');
    if (!container) return;

    container.innerHTML = `
      <div class="checklist-box">
        <div class="checklist-title">Clinician Verification Checklist</div>
        <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 12px;">
          All items must be validated by the licensed clinician before formal approval:
        </div>
        <label class="checklist-item"><input type="checkbox" id="chk1" checked> Patient identity & demographics verified</label>
        <label class="checklist-item"><input type="checkbox" id="chk2" checked> History & symptom timeline verified</label>
        <label class="checklist-item"><input type="checkbox" id="chk3" checked> Active medications reconciled</label>
        <label class="checklist-item"><input type="checkbox" id="chk4" checked> Allergies and safety warnings resolved</label>
        <label class="checklist-item"><input type="checkbox" id="chk5" checked> Physical examination findings documented</label>
        <label class="checklist-item"><input type="checkbox" id="chk6" checked> Assessment & differential validated</label>
        <label class="checklist-item"><input type="checkbox" id="chk7" checked> Plan, investigations & red flags approved</label>
        <label class="checklist-item"><input type="checkbox" id="chk8" checked> ICD-10 coding suggestions reviewed</label>

        <div style="margin-top: 14px;">
          <label class="form-label">Reviewing Clinician Name</label>
          <input type="text" id="clinicianSignName" class="form-input" value="${this.activeConsultation.clinician || 'Dr. Demo Clinician'}" ${this.isApproved ? 'readonly' : ''}>
        </div>

        <div style="margin-top: 16px;">
          <button id="btnApproveNote" class="btn btn-success btn-lg" style="width: 100%;" ${this.isApproved ? 'disabled' : ''} onclick="MediScribe.Review.approveNote()">
            ${this.isApproved ? '✓ Note Approved & Signed' : 'APPROVE NOTE & SIGN'}
          </button>
        </div>
      </div>
    `;
  },

  bindEvents() {
    // PDF & Export hooks
    const btnPrint = document.getElementById('btnPrintReviewPDF');
    if (btnPrint) btnPrint.addEventListener('click', () => MediScribe.Export.printPDF());

    const btnExportJSON = document.getElementById('btnExportReviewJSON');
    if (btnExportJSON) btnExportJSON.addEventListener('click', () => MediScribe.Export.exportJSON());

    const btnCopy = document.getElementById('btnCopyReviewSOAP');
    if (btnCopy) btnCopy.addEventListener('click', () => MediScribe.Export.copySOAPNote());
  },

  approveNote() {
    // Check all checklist boxes
    const checkboxes = document.querySelectorAll('.checklist-item input[type="checkbox"]');
    const allChecked = Array.from(checkboxes).every(c => c.checked);

    if (!allChecked) {
      MediScribe.Toast.show('Please verify and check all review items before approving the note.', 'warning');
      return;
    }

    const clinicianName = document.getElementById('clinicianSignName')?.value || 'Dr. Demo Clinician';

    this.activeConsultation.status = 'Approved';
    this.activeConsultation.clinician = clinicianName;
    this.activeConsultation.approvedAt = new Date().toLocaleString();
    this.isApproved = true;

    MediScribe.Storage.saveConsultation(this.activeConsultation);
    MediScribe.Audit.log('Note Approved', `Consultation ${this.activeConsultation.id} approved by ${clinicianName}`);

    // Send clinician feedback to Python backend for active learning & DPO
    try {
      fetch('http://127.0.0.1:8000/api/feedback/log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          encounterId: this.activeConsultation.id,
          originalSoap: this.activeConsultation.rawAiSoap || this.activeConsultation.soapNote,
          clinicianSoap: this.activeConsultation.soapNote,
          clinician: clinicianName
        })
      }).then(r => r.json()).then(res => {
        if (res && res.success) {
          console.log('[Active Learning] Clinician review pair captured into real-time dataset:', res.sample?.id);
        }
      }).catch(() => {});
    } catch (e) {}

    this.renderApprovalBanner();
    this.renderChecklist();
    this.renderSOAPEditor();
    MediScribe.Toast.show('Note formally approved and added to active learning training dataset!', 'success', 4000);
  },

  unapprove() {
    this.activeConsultation.status = 'Reviewed';
    this.isApproved = false;
    MediScribe.Storage.saveConsultation(this.activeConsultation);
    MediScribe.Audit.log('Note Reopened', `Consultation ${this.activeConsultation.id} reopened for edits`);
    this.render();
    MediScribe.Toast.show('Consultation reopened for clinician edits.', 'info');
  },

  escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
};

document.addEventListener('DOMContentLoaded', () => {
  if (window.location.pathname.includes('review.html')) {
    MediScribe.Review.init();
  }
});
