/**
 * MediScribe - Consultation Workspace Orchestrator
 * Controls the 3-column live consultation interface (consultation.html)
 * PEC Techathon 4.0 MVP
 */

window.MediScribe = window.MediScribe || {};

MediScribe.Consultation = {
  activePatient: null,
  activeConsultation: null,
  analysisResults: null,

  init() {
    // 1. Initialize Storage & get active consultation
    MediScribe.Storage.init();
    
    // Check URL parameters for specific consultation ID or patient ID
    const urlParams = new URLSearchParams(window.location.search);
    const consultIdFromUrl = urlParams.get('id');
    const patientIdFromUrl = urlParams.get('patientId');
    const isNew = urlParams.get('new') === 'true';

    if (consultIdFromUrl) {
      MediScribe.Storage.setActiveConsultation(consultIdFromUrl);
    }

    if (isNew) {
      setTimeout(() => {
        if (MediScribe.NewConsultationModal) {
          MediScribe.NewConsultationModal.open();
        }
      }, 150);
    }

    this.activeConsultation = MediScribe.Storage.getActiveConsultation();

    if (!this.activeConsultation) {
      // Fallback create or pick default
      const all = MediScribe.Storage.getConsultations();
      this.activeConsultation = all[0] || null;
      if (this.activeConsultation) {
        MediScribe.Storage.setActiveConsultation(this.activeConsultation.id);
      }
    }

    // Determine active patient
    const patientId = patientIdFromUrl || (this.activeConsultation ? this.activeConsultation.patientId : 'DEMO-001');
    this.activePatient = MediScribe.Storage.getPatientById(patientId);

    // 2. Initialize Subcomponents
    MediScribe.Transcript.init('transcriptBody');
    this.setupRecorderCallbacks();
    this.bindEvents();

    // 3. Render Initial State
    this.renderWorkspaceSelectors();
    this.renderPatientDetails();

    const badge = document.getElementById('activeEncounterBadge');
    if (badge && this.activeConsultation) {
      badge.textContent = `${this.activeConsultation.status} Note`;
      badge.className = `badge ${this.activeConsultation.status === 'Approved' ? 'badge-approved' : (this.activeConsultation.status === 'Reviewed' ? 'badge-reviewed' : 'badge-draft')}`;
    }

    if (this.activeConsultation) {
      // Load saved transcript if any
      if (this.activeConsultation.transcript && this.activeConsultation.transcript.length > 0) {
        MediScribe.Transcript.setSegments(this.activeConsultation.transcript);
      } else if (MediScribe.DemoData && this.activePatient.id === 'DEMO-001' && (window.location.search.includes('demo=true') || this.activeConsultation.id === 'CONS-2026-08-29-001')) {
        // Pre-populate with demo dialogue for initial demo consultation
        MediScribe.Transcript.setSegments(MediScribe.DemoData.demoConsultationDialogue);
      } else {
        MediScribe.Transcript.setSegments([]);
      }

      // If already has analysis/SOAP, render it
      if (this.activeConsultation.soapNote) {
        this.renderDocumentationPreview(this.activeConsultation.soapNote, this.activeConsultation.secondLookAlerts || []);
      }
    }
  },

  renderWorkspaceSelectors() {
    // Consultation selector
    const consultSelect = document.getElementById('workspaceConsultationSelect');
    if (consultSelect) {
      const consultations = MediScribe.Storage.getConsultations();
      consultSelect.innerHTML = consultations.map(c => 
        `<option value="${c.id}" ${this.activeConsultation && this.activeConsultation.id === c.id ? 'selected' : ''}>
          ${c.id} &bull; ${c.patientName} (${c.status})
        </option>`
      ).join('');

      consultSelect.onchange = (e) => {
        MediScribe.Storage.setActiveConsultation(e.target.value);
        window.location.href = `consultation.html?id=${e.target.value}`;
      };
    }

    // Patient selector
    const patSelect = document.getElementById('workspacePatientSelect');
    if (patSelect) {
      const patients = MediScribe.Storage.getPatients();
      patSelect.innerHTML = patients.map(p => 
        `<option value="${p.id}" ${this.activePatient && this.activePatient.id === p.id ? 'selected' : ''}>
          ${p.name} (${p.id})
        </option>`
      ).join('') + '<option value="__NEW__">➕ + Register New Patient...</option>';

      patSelect.onchange = (e) => {
        if (e.target.value === '__NEW__') {
          MediScribe.NewConsultationModal.open('__NEW__');
        } else {
          this.selectPatient(e.target.value);
        }
      };
    }
  },

  setupRecorderCallbacks() {
    MediScribe.Recorder.init({
      onTranscriptChunk: (chunk) => {
        MediScribe.Transcript.addSegment(chunk);
        this.saveCurrentConsultationState();
      },
      onStatusChange: (status) => {
        this.updateRecordingUI(status);
      }
    });
  },

  bindEvents() {
    // Microphone buttons
    const btnStartRec = document.getElementById('btnStartRecording');
    const btnPauseRec = document.getElementById('btnPauseRecording');
    const btnResumeRec = document.getElementById('btnResumeRecording');
    const btnStopRec = document.getElementById('btnStopRecording');
    const btnCancelRec = document.getElementById('btnCancelRecording');

    if (btnStartRec) btnStartRec.addEventListener('click', () => this.handleStartRecording());
    if (btnPauseRec) btnPauseRec.addEventListener('click', () => MediScribe.Recorder.pause());
    if (btnResumeRec) btnResumeRec.addEventListener('click', () => MediScribe.Recorder.resume());
    if (btnStopRec) btnStopRec.addEventListener('click', () => this.handleStopRecording());
    if (btnCancelRec) btnCancelRec.addEventListener('click', () => MediScribe.Recorder.cancel());

    // Demo Consultation Buttons
    const btnDemoConsult = document.getElementById('btnStartDemoConsult');
    if (btnDemoConsult) {
      btnDemoConsult.addEventListener('click', () => this.loadDemoConsultation());
    }

    // Manual Transcript Button
    const btnManualEntry = document.getElementById('btnManualTranscript');
    if (btnManualEntry) {
      btnManualEntry.addEventListener('click', () => this.openManualTranscriptModal());
    }

    // Generate Documentation button
    const btnGenerateSOAP = document.getElementById('btnGenerateSOAP');
    if (btnGenerateSOAP) {
      btnGenerateSOAP.addEventListener('click', () => this.generateDocumentation());
    }

    // Search transcript
    const searchInput = document.getElementById('transcriptSearchInput');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        MediScribe.Transcript.search(e.target.value);
      });
    }

    // Clear transcript
    const btnClear = document.getElementById('btnClearTranscript');
    if (btnClear) {
      btnClear.addEventListener('click', () => {
        if (confirm('Are you sure you want to clear the transcript?')) {
          MediScribe.Transcript.clear();
          this.saveCurrentConsultationState();
        }
      });
    }
  },

  async handleStartRecording() {
    const started = await MediScribe.Recorder.start();
    if (started) {
      MediScribe.Toast.show('Live microphone recording active. Speak into your mic.', 'info');
    }
  },

  handleStopRecording() {
    const duration = MediScribe.Recorder.stop();
    if (this.activeConsultation) {
      this.activeConsultation.duration = duration;
      this.saveCurrentConsultationState();
    }
    MediScribe.Toast.show(`Recording finished (${duration}). You can now click Generate SOAP Note.`, 'success');
  },

  updateRecordingUI(status) {
    const dot = document.getElementById('recordingStatusDot');
    const label = document.getElementById('recordingStatusLabel');
    const timer = document.getElementById('recordingTimerDisplay');
    const btnStart = document.getElementById('btnStartRecording');
    const btnPause = document.getElementById('btnPauseRecording');
    const btnResume = document.getElementById('btnResumeRecording');
    const btnStop = document.getElementById('btnStopRecording');
    const btnCancel = document.getElementById('btnCancelRecording');

    if (!dot || !label) return;

    if (status.state === 'recording') {
      dot.className = 'recording-dot active';
      label.textContent = 'RECORDING (Mic Active)';
      label.style.color = 'var(--danger)';
      if (btnStart) btnStart.style.display = 'none';
      if (btnPause) btnPause.style.display = 'inline-flex';
      if (btnResume) btnResume.style.display = 'none';
      if (btnStop) btnStop.style.display = 'inline-flex';
      if (btnCancel) btnCancel.style.display = 'inline-flex';
    } else if (status.state === 'paused') {
      dot.className = 'recording-dot';
      label.textContent = 'RECORDING PAUSED';
      label.style.color = 'var(--warning)';
      if (btnPause) btnPause.style.display = 'none';
      if (btnResume) btnResume.style.display = 'inline-flex';
    } else {
      dot.className = 'recording-dot';
      label.textContent = 'Microphone Idle';
      label.style.color = 'var(--text-muted)';
      if (btnStart) btnStart.style.display = 'inline-flex';
      if (btnPause) btnPause.style.display = 'none';
      if (btnResume) btnResume.style.display = 'none';
      if (btnStop) btnStop.style.display = 'none';
      if (btnCancel) btnCancel.style.display = 'none';
    }

    if (timer && status.elapsed) {
      timer.textContent = status.elapsed;
    }
  },

  loadDemoConsultation() {
    if (!MediScribe.DemoData) return;
    // Set to Arun Kumar
    this.selectPatient('DEMO-001');
    MediScribe.Transcript.setSegments(MediScribe.DemoData.demoConsultationDialogue);
    
    // Automatically prepare consultation state
    if (this.activeConsultation) {
      this.activeConsultation.transcript = MediScribe.DemoData.demoConsultationDialogue;
      this.activeConsultation.duration = '02:14';
      this.saveCurrentConsultationState();
    }

    MediScribe.Toast.show('Realistic synthetic consultation loaded for Arun Kumar.', 'success');
  },

  selectPatient(patientId) {
    this.activePatient = MediScribe.Storage.getPatientById(patientId);
    if (this.activeConsultation) {
      this.activeConsultation.patientId = this.activePatient.id;
      this.activeConsultation.patientName = this.activePatient.name;
      this.activeConsultation.visitType = this.activePatient.visitType;
      this.activeConsultation.chiefComplaint = this.activePatient.chiefComplaint;
      this.saveCurrentConsultationState();
    }
    this.renderPatientDetails();
  },

  renderPatientDetails() {
    const p = this.activePatient;
    if (!p) return;

    const elem = document.getElementById('patientInfoContainer');
    if (!elem) return;

    elem.innerHTML = `
      <div class="patient-info-list">
        <div class="patient-info-row">
          <span class="patient-info-label">Full Name</span>
          <span class="patient-info-val">${p.name}</span>
        </div>
        <div class="patient-info-row">
          <span class="patient-info-label">Patient ID</span>
          <span class="patient-info-val"><span class="badge badge-low">${p.id}</span></span>
        </div>
        <div class="patient-info-row">
          <span class="patient-info-label">Age / Sex</span>
          <span class="patient-info-val">${p.age} yrs / ${p.sex}</span>
        </div>
        <div class="patient-info-row">
          <span class="patient-info-label">Visit Type</span>
          <span class="patient-info-val">${p.visitType}</span>
        </div>
        <div class="patient-info-row">
          <span class="patient-info-label">Chief Complaint</span>
          <span class="patient-info-val" style="color: var(--primary-dark);">${p.chiefComplaint}</span>
        </div>
        <div class="patient-info-row">
          <span class="patient-info-label">Date</span>
          <span class="patient-info-val">${new Date().toISOString().split('T')[0]}</span>
        </div>
      </div>

      <div style="margin-top: 16px;">
        <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.04em;">
          Stored EHR Background (Synthetic)
        </div>
        <div class="history-item">
          <div class="history-item-title">Chronic Conditions</div>
          <div class="history-item-detail">${(p.historicalConditions || []).map(c => typeof c === 'string' ? c : c.condition).join(', ') || 'None on file'}</div>
        </div>
        <div class="history-item">
          <div class="history-item-title">Historical Medications</div>
          <div class="history-item-detail">${(p.historicalMedications || []).map(m => typeof m === 'string' ? m : `${m.name} ${m.dose || ''} (${m.frequency || 'Daily'})`).join(', ') || 'None on file'}</div>
        </div>
        <div class="history-item" style="border-left: 3px solid #ef4444; background: #fff1f2;">
          <div class="history-item-title" style="color: #991b1b;">Documented Allergies</div>
          <div class="history-item-detail" style="font-weight: 600; color: #b91c1c;">${(p.historicalAllergies || []).map(a => typeof a === 'string' ? a : `${a.allergen} (${a.reaction || 'Allergy'})`).join(', ') || 'NKDA (No known drug allergies)'}</div>
        </div>
      </div>
    `;
  },

  generateDocumentation() {
    const segments = MediScribe.Transcript.getSegments();
    if (segments.length === 0) {
      MediScribe.Toast.show('Cannot generate documentation from an empty transcript. Please record audio or click Start Demo Consultation.', 'warning');
      return;
    }

    const provider = MediScribe.Providers.getActive();
    MediScribe.Toast.show(`Analyzing consultation with ${provider.name}...`, 'info');

    // Run deterministic analysis
    const result = MediScribe.Analysis.runFullPipeline(segments, this.activePatient);
    this.analysisResults = result;

    if (this.activeConsultation) {
      this.activeConsultation.transcript = segments;
      this.activeConsultation.soapNote = result.soap_note;
      this.activeConsultation.secondLookAlerts = result.all_second_look_alerts;
      this.activeConsultation.codingSuggestions = result.coding_suggestions;
      this.activeConsultation.followUpSuggestions = result.follow_up_suggestions;
      this.activeConsultation.status = 'Reviewed';
      this.saveCurrentConsultationState();
    }

    this.renderDocumentationPreview(result.soap_note, result.all_second_look_alerts);
    MediScribe.Toast.show('SOAP Note and AI Clinical Second Look generated successfully!', 'success');
  },

  renderDocumentationPreview(soapNote, alerts) {
    const container = document.getElementById('documentationResultsContainer');
    if (!container) return;

    // Render Second Look Alerts
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
          ${alert.type !== 'POSITIVE_CHECK' ? `
            <div class="alert-actions">
              ${alert.sourceSegmentId ? `<button class="btn btn-sm btn-secondary" onclick="MediScribe.Transcript.scrollToSegment('${alert.sourceSegmentId}')">View Source</button>` : ''}
              <button class="btn btn-sm btn-secondary" onclick="MediScribe.Consultation.dismissAlert('${alert.id}')">Dismiss</button>
              <button class="btn btn-sm btn-primary" onclick="window.location.href='review.html'">Edit Note</button>
            </div>
          ` : ''}
        </div>
      `;
    });

    container.innerHTML = `
      <!-- AI Clinical Second Look Highlight Box -->
      <div class="second-look-card" style="margin-bottom: 20px;">
        <div class="second-look-header">
          <div class="second-look-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
            AI CLINICAL SECOND LOOK
          </div>
          <span class="second-look-badge">${alerts.filter(a => a.type !== 'POSITIVE_CHECK').length} Safety Alerts</span>
        </div>
        <div class="second-look-alerts-list">
          ${alertsHtml}
        </div>
      </div>

      <!-- SOAP Note Sections Preview -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">Generated SOAP Note</span>
          <a href="review.html" class="btn btn-sm btn-primary">Open Full Review & Approval →</a>
        </div>
        <div class="card-body" style="padding: 12px;">
          <div class="soap-section-box">
            <div class="soap-section-header">
              <span>SUBJECTIVE</span>
              <span class="evidence-tag confirmed">Evidence Linked</span>
            </div>
            <div class="soap-section-content">${this.escapeHtml(soapNote.subjective)}</div>
          </div>
          <div class="soap-section-box">
            <div class="soap-section-header">
              <span>OBJECTIVE</span>
              <span class="evidence-tag inferred">Physical Exam & Labs</span>
            </div>
            <div class="soap-section-content">${this.escapeHtml(soapNote.objective)}</div>
          </div>
          <div class="soap-section-box">
            <div class="soap-section-header">
              <span>ASSESSMENT</span>
              <span class="evidence-tag inferred">Requires Clinician Validation</span>
            </div>
            <div class="soap-section-content">${this.escapeHtml(soapNote.assessment)}</div>
          </div>
          <div class="soap-section-box">
            <div class="soap-section-header">
              <span>PLAN</span>
              <span class="evidence-tag confirmed">Safety Verified</span>
            </div>
            <div class="soap-section-content">${this.escapeHtml(soapNote.plan)}</div>
          </div>
        </div>
        <div class="card-footer">
          <button class="btn btn-secondary" onclick="MediScribe.Export.copySOAPNote()">Copy Note</button>
          <a href="review.html" class="btn btn-primary">Proceed to Final Review & Approval →</a>
        </div>
      </div>
    `;
  },

  dismissAlert(alertId) {
    if (this.activeConsultation && this.activeConsultation.secondLookAlerts) {
      this.activeConsultation.secondLookAlerts = this.activeConsultation.secondLookAlerts.filter(a => a.id !== alertId);
      this.saveCurrentConsultationState();
      this.renderDocumentationPreview(this.activeConsultation.soapNote, this.activeConsultation.secondLookAlerts);
      MediScribe.Toast.show('Safety alert dismissed by clinician.', 'info');
      MediScribe.Audit.log('Alert Dismissed', `Clinician dismissed alert: ${alertId}`);
    }
  },

  openManualTranscriptModal() {
    const modalId = 'manualTranscriptModal';
    let modal = document.getElementById(modalId);
    if (!modal) {
      modal = document.createElement('div');
      modal.id = modalId;
      modal.className = 'modal-overlay';
      document.body.appendChild(modal);
    }

    modal.innerHTML = `
      <div class="modal-container">
        <div class="modal-header">
          <h3 class="modal-title">Enter Transcript Utterances</h3>
          <button class="modal-close-btn" onclick="MediScribe.Modal.close('${modalId}')">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">Speaker</label>
            <select id="manualSpeaker" class="form-select">
              <option value="DOCTOR">DOCTOR</option>
              <option value="PATIENT" selected>PATIENT</option>
              <option value="UNKNOWN">UNKNOWN</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Statement</label>
            <textarea id="manualText" class="form-textarea" rows="4" placeholder="Type doctor or patient statement..."></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="MediScribe.Modal.close('${modalId}')">Cancel</button>
          <button class="btn btn-primary" onclick="MediScribe.Consultation.saveManualUtterance()">Add Statement</button>
        </div>
      </div>
    `;

    MediScribe.Modal.open(modalId);
  },

  saveManualUtterance() {
    const speaker = document.getElementById('manualSpeaker').value;
    const text = document.getElementById('manualText').value;

    if (!text.trim()) {
      MediScribe.Toast.show('Please enter speech text.', 'warning');
      return;
    }

    MediScribe.Transcript.addSegment({
      speaker: speaker,
      timestamp: MediScribe.Recorder.formatTime(MediScribe.Transcript.getSegments().length * 6),
      text: text.trim()
    });

    this.saveCurrentConsultationState();
    MediScribe.Modal.close('manualTranscriptModal');
    MediScribe.Toast.show('Statement added to transcript.', 'success');
  },

  saveCurrentConsultationState() {
    if (!this.activeConsultation) return;
    this.activeConsultation.transcript = MediScribe.Transcript.getSegments();
    MediScribe.Storage.saveConsultation(this.activeConsultation);

    const ind = document.getElementById('saveStatusIndicator');
    if (ind) {
      const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      ind.textContent = `✓ Saved ${time}`;
      ind.style.color = 'var(--success)';
    }
  },

  escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
};

document.addEventListener('DOMContentLoaded', () => {
  if (window.location.pathname.includes('consultation.html')) {
    MediScribe.Consultation.init();
  }
});
