/**
 * MediScribe - Core Application Framework
 * PEC Techathon 4.0 MVP
 */

window.MediScribe = window.MediScribe || {};

// Storage Keys
const STORAGE_KEYS = {
  PATIENTS: 'mediscribe_patients',
  CONSULTATIONS: 'mediscribe_consultations',
  ACTIVE_CONSULTATION: 'mediscribe_active_consultation',
  AUDIT_LOGS: 'mediscribe_audit_logs',
  SETTINGS: 'mediscribe_settings'
};

// Storage Manager
MediScribe.Storage = {
  init() {
    // Seed default patients if absent
    if (!localStorage.getItem(STORAGE_KEYS.PATIENTS) && MediScribe.DemoData) {
      localStorage.setItem(STORAGE_KEYS.PATIENTS, JSON.stringify(MediScribe.DemoData.patients));
    }
    // Seed default consultations if absent
    if (!localStorage.getItem(STORAGE_KEYS.CONSULTATIONS) && MediScribe.DemoData) {
      localStorage.setItem(STORAGE_KEYS.CONSULTATIONS, JSON.stringify(MediScribe.DemoData.initialConsultations));
    }
    // Ensure active consultation pointer exists
    if (!localStorage.getItem(STORAGE_KEYS.ACTIVE_CONSULTATION)) {
      localStorage.setItem(STORAGE_KEYS.ACTIVE_CONSULTATION, 'CONS-2026-08-29-001');
    }
    // Ensure settings
    if (!localStorage.getItem(STORAGE_KEYS.SETTINGS)) {
      localStorage.setItem(STORAGE_KEYS.SETTINGS, JSON.stringify({
        provider: 'DemoProvider',
        clinicianName: 'Dr. Demo Clinician',
        mockLatency: 350,
        enableAutoAudit: true
      }));
    }
  },

  getPatients() {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.PATIENTS);
      return data ? JSON.parse(data) : (MediScribe.DemoData ? MediScribe.DemoData.patients : []);
    } catch (e) {
      console.error('Failed to load patients', e);
      return [];
    }
  },

  getPatientById(id) {
    const patients = this.getPatients();
    return patients.find(p => p.id === id) || patients[0];
  },

  getConsultations() {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.CONSULTATIONS);
      return data ? JSON.parse(data) : [];
    } catch (e) {
      console.error('Failed to load consultations', e);
      return [];
    }
  },

  getConsultationById(id) {
    const consultations = this.getConsultations();
    return consultations.find(c => c.id === id) || null;
  },

  getActiveConsultation() {
    const activeId = localStorage.getItem(STORAGE_KEYS.ACTIVE_CONSULTATION);
    if (!activeId) return null;
    return this.getConsultationById(activeId);
  },

  setActiveConsultation(id) {
    localStorage.setItem(STORAGE_KEYS.ACTIVE_CONSULTATION, id);
  },

  saveConsultation(consultation) {
    const consultations = this.getConsultations();
    const index = consultations.findIndex(c => c.id === consultation.id);
    if (index >= 0) {
      consultations[index] = consultation;
    } else {
      consultations.unshift(consultation);
    }
    localStorage.setItem(STORAGE_KEYS.CONSULTATIONS, JSON.stringify(consultations));
    MediScribe.Audit.log('Consultation Saved', `Saved consultation ${consultation.id} (${consultation.patientName})`);
    if (typeof MediScribe.syncToDatabase === 'function') MediScribe.syncToDatabase();
    return consultation;
  },

  deleteConsultation(id) {
    let consultations = this.getConsultations();
    consultations = consultations.filter(c => c.id !== id);
    localStorage.setItem(STORAGE_KEYS.CONSULTATIONS, JSON.stringify(consultations));
    MediScribe.Audit.log('Consultation Deleted', `Deleted consultation ${id}`);
    if (typeof MediScribe.syncToDatabase === 'function') MediScribe.syncToDatabase();
  },

  savePatient(patient) {
    const patients = this.getPatients();
    if (!patient.id) {
      patient.id = 'PT-' + Math.floor(1000 + Math.random() * 9000);
    }
    const index = patients.findIndex(p => p.id === patient.id);
    if (index >= 0) {
      patients[index] = patient;
    } else {
      patients.push(patient);
    }
    localStorage.setItem(STORAGE_KEYS.PATIENTS, JSON.stringify(patients));
    MediScribe.Audit.log('Patient Saved', `Saved patient record: ${patient.name} (${patient.id})`);
    if (typeof MediScribe.syncToDatabase === 'function') MediScribe.syncToDatabase();
    return patient;
  },

  createConsultation(data = {}) {
    const id = 'CONS-' + new Date().toISOString().split('T')[0] + '-' + Math.floor(100 + Math.random() * 900);
    const patientId = data.patientId || 'DEMO-001';
    const patient = this.getPatientById(patientId);

    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const newConsultation = {
      id: id,
      patientId: patient.id,
      patientName: patient.name,
      date: data.date || now.toISOString().split('T')[0],
      time: timeStr,
      visitType: data.visitType || patient.visitType || 'General Consultation',
      chiefComplaint: data.chiefComplaint || patient.chiefComplaint || 'Routine Medical Evaluation',
      duration: '00:00',
      status: 'Draft',
      clinician: data.clinician || 'Dr. Demo Clinician',
      transcript: data.transcript || [],
      soapNote: data.soapNote || null,
      secondLookAlerts: data.secondLookAlerts || [],
      codingSuggestions: data.codingSuggestions || [],
      followUpSuggestions: data.followUpSuggestions || [],
      attachedLabs: []
    };

    this.saveConsultation(newConsultation);
    this.setActiveConsultation(id);
    MediScribe.Audit.log('Consultation Created', `Initiated new consultation ${id} for ${patient.name}`);
    return newConsultation;
  },

  getStats() {
    const consultations = this.getConsultations();
    return {
      total: consultations.length,
      draft: consultations.filter(c => c.status === 'Draft').length,
      reviewed: consultations.filter(c => c.status === 'Reviewed').length,
      approved: consultations.filter(c => c.status === 'Approved').length
    };
  },

  getSettings() {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.SETTINGS);
      return data ? JSON.parse(data) : { provider: 'DemoProvider', clinicianName: 'Dr. Demo Clinician' };
    } catch (e) {
      return { provider: 'DemoProvider', clinicianName: 'Dr. Demo Clinician' };
    }
  },

  saveSettings(settings) {
    localStorage.setItem(STORAGE_KEYS.SETTINGS, JSON.stringify(settings));
    MediScribe.Audit.log('Settings Updated', 'User adjusted application configuration');
  },

  resetAllData() {
    localStorage.removeItem(STORAGE_KEYS.PATIENTS);
    localStorage.removeItem(STORAGE_KEYS.CONSULTATIONS);
    localStorage.removeItem(STORAGE_KEYS.ACTIVE_CONSULTATION);
    localStorage.removeItem(STORAGE_KEYS.AUDIT_LOGS);
    localStorage.removeItem(STORAGE_KEYS.SETTINGS);
    this.init();
    MediScribe.Toast.show('All synthetic data has been reset to defaults.', 'success');
  }
};

// Audit Log Manager (Clinical Traceability)
MediScribe.Audit = {
  getLogs() {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.AUDIT_LOGS);
      return data ? JSON.parse(data) : [];
    } catch (e) {
      return [];
    }
  },

  log(action, detail) {
    const logs = this.getLogs();
    const newEntry = {
      id: 'AUDIT-' + Date.now() + '-' + Math.floor(Math.random() * 1000),
      timestamp: new Date().toISOString(),
      action: action,
      detail: detail,
      actor: 'Demo Clinician (Browser Session)'
    };
    logs.unshift(newEntry);
    // Keep max 100 logs
    if (logs.length > 100) logs.pop();
    localStorage.setItem(STORAGE_KEYS.AUDIT_LOGS, JSON.stringify(logs));
  },

  clear() {
    localStorage.removeItem(STORAGE_KEYS.AUDIT_LOGS);
  }
};

// Toast Notification Engine
MediScribe.Toast = {
  container: null,

  ensureContainer() {
    if (!this.container) {
      this.container = document.getElementById('toast-container');
      if (!this.container) {
        this.container = document.createElement('div');
        this.container.id = 'toast-container';
        document.body.appendChild(this.container);
      }
    }
  },

  show(message, type = 'info', duration = 3500) {
    this.ensureContainer();
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✓';
    if (type === 'warning') icon = '⚠';
    if (type === 'danger') icon = '✖';

    toast.innerHTML = `
      <span style="font-size: 15px; line-height: 1;">${icon}</span>
      <span style="flex: 1;">${message}</span>
    `;

    this.container.appendChild(toast);

    setTimeout(() => {
      toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 300);
    }, duration);
  }
};

// Modal Helper
MediScribe.Modal = {
  open(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add('open');
      modal.style.display = 'flex';
    }
  },
  close(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('open');
      modal.style.display = 'none';
    }
  }
};

// Global New Consultation Modal & Creator
MediScribe.NewConsultationModal = {
  modalId: 'globalNewConsultationModal',

  open(preselectedPatientId = null) {
    let modal = document.getElementById(this.modalId);
    if (!modal) {
      modal = document.createElement('div');
      modal.id = this.modalId;
      modal.className = 'modal-overlay';
      document.body.appendChild(modal);
    }

    const patients = MediScribe.Storage.getPatients();
    const settings = MediScribe.Storage.getSettings();

    modal.innerHTML = `
      <div class="modal-container" style="max-width: 620px;">
        <div class="modal-header">
          <h3 class="modal-title">Create New Clinical Consultation</h3>
          <button class="modal-close-btn" onclick="MediScribe.Modal.close('${this.modalId}')">&times;</button>
        </div>
        <div class="modal-body">
          <form id="newConsultationForm" onsubmit="event.preventDefault(); MediScribe.NewConsultationModal.submit();">
            
            <div class="form-group">
              <label class="form-label">Select Patient</label>
              <select id="ncPatientSelect" class="form-select" onchange="MediScribe.NewConsultationModal.handlePatientChange(this.value)">
                ${patients.map(p => `<option value="${p.id}" ${preselectedPatientId === p.id ? 'selected' : ''}>${p.name} (${p.id} &bull; ${p.age}y/${p.sex} &bull; ${p.visitType || 'Walk-in'})</option>`).join('')}
                <option value="__NEW__" ${preselectedPatientId === '__NEW__' ? 'selected' : ''}>➕ + Register New Custom Patient...</option>
              </select>
            </div>

            <!-- New Custom Patient Section (Hidden by default unless __NEW__ chosen) -->
            <div id="ncNewPatientFields" style="display: none; background: var(--bg-muted); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 14px; margin-bottom: 16px;">
              <div style="font-weight: 700; font-size: 13px; color: var(--primary-dark); margin-bottom: 10px;">
                New Patient Registration
              </div>
              <div style="display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 10px; margin-bottom: 10px;">
                <div>
                  <label class="form-label">Full Name *</label>
                  <input type="text" id="ncNewName" class="form-input" placeholder="e.g. Rajesh Patel">
                </div>
                <div>
                  <label class="form-label">Age *</label>
                  <input type="number" id="ncNewAge" class="form-input" placeholder="e.g. 52" min="1" max="120">
                </div>
                <div>
                  <label class="form-label">Sex *</label>
                  <select id="ncNewSex" class="form-select">
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
              </div>

              <div class="form-group">
                <label class="form-label">Known Allergies (Crucial for Second Look Safety Check)</label>
                <input type="text" id="ncNewAllergies" class="form-input" placeholder="e.g. Penicillin (Generalized rash) or Sulfa drugs, or None">
              </div>

              <div class="form-group">
                <label class="form-label">Active Medications on File</label>
                <input type="text" id="ncNewMeds" class="form-input" placeholder="e.g. Amlodipine 5mg daily, Atorvastatin 20mg">
              </div>

              <div class="form-group" style="margin-bottom: 0;">
                <label class="form-label">Chronic Medical History / Diagnoses</label>
                <input type="text" id="ncNewConditions" class="form-input" placeholder="e.g. Hypertension, Type 2 Diabetes, Asthma">
              </div>
            </div>

            <!-- Encounter Information -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px;">
              <div>
                <label class="form-label">Visit Type / Specialty *</label>
                <input type="text" id="ncVisitType" class="form-input" value="Primary Care / Urgent Walk-in" placeholder="e.g. Primary Care, Cardiology Review">
              </div>
              <div>
                <label class="form-label">Attending Clinician</label>
                <input type="text" id="ncClinician" class="form-input" value="${settings.clinicianName || 'Dr. Demo Clinician'}">
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">Chief Complaint *</label>
              <input type="text" id="ncChiefComplaint" class="form-input" placeholder="e.g. Persistent cough for 2 weeks or Severe throat pain">
            </div>

            <div class="form-group">
              <label class="form-label">Initial Transcript / Encounter Mode</label>
              <select id="ncInitialMode" class="form-select">
                <option value="empty">Start with Fresh Blank Workspace (Use Live Microphone or Type)</option>
                <option value="demo">Pre-load Synthetic Consultation Dialogue (Ready for Scribing)</option>
              </select>
            </div>

            <div style="font-size: 11px; color: var(--text-muted); line-height: 1.4;">
              Creates a new <strong>Draft</strong> consultation in browser <code>localStorage</code>. All safety second-look cross-checks will be linked to this patient profile.
            </div>

          </form>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="MediScribe.Modal.close('${this.modalId}')">Cancel</button>
          <button class="btn btn-primary" onclick="MediScribe.NewConsultationModal.submit()">Create &amp; Start Consultation &rarr;</button>
        </div>
      </div>
    `;

    MediScribe.Modal.open(this.modalId);

    // Initial prefill if existing patient selected
    if (preselectedPatientId && preselectedPatientId !== '__NEW__') {
      this.handlePatientChange(preselectedPatientId);
    } else if (patients.length > 0) {
      this.handlePatientChange(patients[0].id);
    }
  },

  handlePatientChange(val) {
    const newFields = document.getElementById('ncNewPatientFields');
    const complaintInput = document.getElementById('ncChiefComplaint');
    const visitTypeInput = document.getElementById('ncVisitType');

    if (val === '__NEW__') {
      if (newFields) newFields.style.display = 'block';
      if (complaintInput) complaintInput.value = '';
    } else {
      if (newFields) newFields.style.display = 'none';
      const patient = MediScribe.Storage.getPatientById(val);
      if (patient) {
        if (complaintInput) complaintInput.value = patient.chiefComplaint || '';
        if (visitTypeInput) visitTypeInput.value = patient.visitType || 'Primary Care Walk-in';
      }
    }
  },

  submit() {
    const patientSelectVal = document.getElementById('ncPatientSelect')?.value;
    const visitType = document.getElementById('ncVisitType')?.value.trim() || 'Primary Care';
    const chiefComplaint = document.getElementById('ncChiefComplaint')?.value.trim() || 'Medical Evaluation';
    const clinician = document.getElementById('ncClinician')?.value.trim() || 'Dr. Demo Clinician';
    const initialMode = document.getElementById('ncInitialMode')?.value;

    let targetPatientId = patientSelectVal;

    // If new patient was selected, create and store the patient first
    if (patientSelectVal === '__NEW__') {
      const name = document.getElementById('ncNewName')?.value.trim();
      const age = parseInt(document.getElementById('ncNewAge')?.value) || 40;
      const sex = document.getElementById('ncNewSex')?.value || 'Male';
      const allergyStr = document.getElementById('ncNewAllergies')?.value.trim();
      const medsStr = document.getElementById('ncNewMeds')?.value.trim();
      const condStr = document.getElementById('ncNewConditions')?.value.trim();

      if (!name) {
        MediScribe.Toast.show('Please enter the patient full name.', 'warning');
        return;
      }

      // Structure allergies
      const allergies = allergyStr ? [{
        allergen: allergyStr.split('(')[0].trim(),
        reaction: allergyStr.includes('(') ? allergyStr.replace(/.*\((.*)\).*/, '$1') : 'Known hypersensitivity',
        severity: 'Moderate',
        notedDate: new Date().toISOString().split('T')[0]
      }] : [];

      // Structure medications
      const medications = medsStr ? medsStr.split(',').map(m => ({
        name: m.trim(),
        dose: 'As prescribed',
        frequency: 'Daily',
        route: 'Oral',
        purpose: 'Chronic therapy'
      })) : [];

      // Structure conditions
      const conditions = condStr ? condStr.split(',').map(c => ({
        condition: c.trim(),
        diagnosedDate: 'Prior history',
        status: 'Active'
      })) : [];

      const newPatient = {
        id: 'PT-' + Math.floor(1000 + Math.random() * 9000),
        name: name,
        age: age,
        sex: sex,
        dob: `${new Date().getFullYear() - age}-01-01`,
        mrn: 'MRN-' + Math.floor(100000 + Math.random() * 900000),
        visitType: visitType,
        chiefComplaint: chiefComplaint,
        historicalConditions: conditions,
        historicalMedications: medications,
        historicalAllergies: allergies,
        historicalVitals: {
          lastRecorded: new Date().toISOString().split('T')[0],
          bp: '120/80 mmHg',
          hr: '72 bpm',
          temp: '98.6 °F',
          spo2: '99%',
          weight: '70 kg'
        }
      };

      MediScribe.Storage.savePatient(newPatient);
      targetPatientId = newPatient.id;
      MediScribe.Toast.show(`Registered new patient: ${name} (${newPatient.id})`, 'success');
    }

    // Determine transcript
    let initialTranscript = [];
    if (initialMode === 'demo' && MediScribe.DemoData) {
      initialTranscript = MediScribe.DemoData.demoConsultationDialogue;
    }

    // Create Consultation
    const newConsultation = MediScribe.Storage.createConsultation({
      patientId: targetPatientId,
      visitType: visitType,
      chiefComplaint: chiefComplaint,
      clinician: clinician,
      transcript: initialTranscript
    });

    MediScribe.Modal.close(this.modalId);
    MediScribe.Toast.show(`New consultation created (${newConsultation.id}). Opening workspace...`, 'success');

    // Navigate to consultation workspace
    setTimeout(() => {
      window.location.href = `consultation.html?id=${newConsultation.id}`;
    }, 400);
  }
};

// Document Init & Dynamic Dashboard Synchronization
document.addEventListener('DOMContentLoaded', () => {
  MediScribe.Storage.init();

  // If on Dashboard (index.html), dynamically populate live stats and recent consultations
  if (window.location.pathname.endsWith('index.html') || window.location.pathname === '/' || window.location.pathname.endsWith('/')) {
    MediScribe.syncDashboard();
  }

  // Check Python backend connectivity and update header pill
  MediScribe.checkBackendStatus();

  // Bind global "New Consultation" buttons
  const globalNewBtns = document.querySelectorAll('.btn-trigger-new-consultation');
  globalNewBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      MediScribe.NewConsultationModal.open();
    });
  });
});

MediScribe.checkBackendStatus = async function() {
  const pill = document.getElementById('backendStatusPill');
  const text = document.getElementById('backendStatusText');
  if (!pill) return;

  try {
    const res = await fetch('http://127.0.0.1:8000/api/status', { signal: AbortSignal.timeout(1500) });
    if (res.ok) {
      const data = await res.json();
      if (MediScribe.Providers) MediScribe.Providers.backendAvailable = true;
      pill.style.background = '#dcfce7';
      pill.style.color = '#15803d';
      pill.style.borderColor = '#86efac';
      if (text) text.textContent = `AI Backend: Online (${data.model_version})`;
      // Background mirror to SQLite database
      MediScribe.syncToDatabase();
      return;
    }
  } catch (e) {}

  if (MediScribe.Providers) MediScribe.Providers.backendAvailable = false;
  pill.style.background = '#fee2e2';
  pill.style.color = '#b91c1c';
  pill.style.borderColor = '#fca5a5';
  if (text) text.textContent = 'AI Backend: Offline (Local Mode)';
};

MediScribe.syncToDatabase = async function() {
  try {
    const patients = MediScribe.Storage.getPatients();
    const consultations = MediScribe.Storage.getConsultations();
    await fetch('http://127.0.0.1:8000/api/db/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ patients, consultations })
    });
  } catch (e) {}
};

MediScribe.syncDashboard = function() {
  const stats = MediScribe.Storage.getStats();
  const consultations = MediScribe.Storage.getConsultations();

  // Update KPI counters if elements exist
  const statCards = document.querySelectorAll('.stats-grid .stat-card .stat-value');
  if (statCards.length >= 4) {
    statCards[0].textContent = stats.total;
    statCards[1].textContent = stats.draft;
    statCards[2].textContent = stats.reviewed;
    statCards[3].textContent = stats.approved;
  }

  // Populate recent consultations table
  const tbody = document.querySelector('.data-table tbody');
  if (tbody) {
    if (consultations.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 24px; color: var(--text-muted);">No consultations found. Click + New Consultation to create one.</td></tr>';
      return;
    }

    const recent = consultations.slice(0, 5);
    tbody.innerHTML = recent.map(c => {
      let badgeClass = 'badge-draft';
      if (c.status === 'Approved') badgeClass = 'badge-approved';
      if (c.status === 'Reviewed') badgeClass = 'badge-reviewed';

      const alertCount = (c.secondLookAlerts || []).length;
      let alertBadge = '<span class="badge badge-normal">Resolved / Clean</span>';
      if (alertCount > 0) {
        alertBadge = `<span class="badge badge-high">${alertCount} Safety Alerts</span>`;
      }

      return `
        <tr>
          <td>
            <div style="font-weight: 600;">${c.patientName}</div>
            <div style="font-size: 11px; color: var(--text-muted);">${c.patientId} &bull; ${c.id}</div>
          </td>
          <td>${c.date} <span style="font-size: 11px; color: var(--text-muted);">${c.time || ''}</span></td>
          <td style="font-weight: 500;">${c.chiefComplaint}</td>
          <td>${c.duration || '00:00'}</td>
          <td>${alertBadge}</td>
          <td><span class="badge ${badgeClass}">${c.status}</span></td>
          <td>
            <div style="display: flex; gap: 6px;">
              <a href="consultation.html?id=${c.id}" class="btn btn-sm btn-primary">Open</a>
              <a href="review.html?id=${c.id}" class="btn btn-sm btn-secondary">Review</a>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  }
};
