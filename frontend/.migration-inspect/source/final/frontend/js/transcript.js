/**
 * MediScribe - Live Transcript Manager
 * Handles segment rendering, editing, deletion, search, speaker attribution, and evidence scrolling
 * PEC Techathon 4.0 MVP
 */

window.MediScribe = window.MediScribe || {};

MediScribe.Transcript = {
  segments: [],
  containerElem: null,
  activeFilter: '',

  init(containerId = 'transcriptBody') {
    this.containerElem = document.getElementById(containerId);
  },

  setSegments(newSegments) {
    this.segments = JSON.parse(JSON.stringify(newSegments));
    this.render();
  },

  getSegments() {
    return this.segments;
  },

  addSegment(segment) {
    const newSeg = {
      id: segment.id || 'seg-' + Date.now() + '-' + Math.floor(Math.random() * 1000),
      timestamp: segment.timestamp || '00:00',
      speaker: segment.speaker || 'UNKNOWN',
      text: segment.text || ''
    };
    this.segments.push(newSeg);
    this.render();
    this.scrollToBottom();
    return newSeg;
  },

  updateSegment(id, updatedFields) {
    const seg = this.segments.find(s => s.id === id);
    if (seg) {
      Object.assign(seg, updatedFields);
      this.render();
      MediScribe.Audit.log('Transcript Edited', `Edited segment ${id} (${seg.speaker})`);
    }
  },

  deleteSegment(id) {
    this.segments = this.segments.filter(s => s.id !== id);
    this.render();
    MediScribe.Audit.log('Transcript Segment Deleted', `Deleted segment ${id}`);
    MediScribe.Toast.show('Transcript segment removed.', 'info');
  },

  changeSpeaker(id, newSpeaker) {
    const seg = this.segments.find(s => s.id === id);
    if (seg) {
      seg.speaker = newSpeaker;
      this.render();
    }
  },

  clear() {
    this.segments = [];
    this.render();
    MediScribe.Audit.log('Transcript Cleared', 'Transcript cleared by user');
  },

  search(query) {
    this.activeFilter = (query || '').toLowerCase().trim();
    this.render();
  },

  scrollToSegment(id) {
    if (!this.containerElem) return;
    // Remove previous highlights
    const prevHighlighted = this.containerElem.querySelectorAll('.transcript-segment.highlighted');
    prevHighlighted.forEach(el => el.classList.remove('highlighted'));

    const targetElem = document.getElementById(`segment-${id}`);
    if (targetElem) {
      targetElem.classList.add('highlighted');
      targetElem.scrollIntoView({ behavior: 'smooth', block: 'center' });
      MediScribe.Toast.show(`Evidence linked to transcript: ${targetElem.querySelector('.segment-time')?.textContent || ''}`, 'info', 2500);
    }
  },

  scrollToBottom() {
    if (this.containerElem) {
      this.containerElem.scrollTop = this.containerElem.scrollHeight;
    }
  },

  render() {
    if (!this.containerElem) return;

    if (this.segments.length === 0) {
      this.containerElem.innerHTML = `
        <div class="transcript-empty">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" y1="19" x2="12" y2="23"/>
            <line x1="8" y1="23" x2="16" y2="23"/>
          </svg>
          <div style="font-weight: 600; color: var(--text-primary);">No transcript segments yet</div>
          <p style="font-size: 12px; max-width: 280px;">Click <strong>Start Recording</strong> to speak, or <strong>Start Demo Consultation</strong> to load synthetic clinical dialogue.</p>
        </div>
      `;
      return;
    }

    const filtered = this.activeFilter 
      ? this.segments.filter(s => s.text.toLowerCase().includes(this.activeFilter) || s.speaker.toLowerCase().includes(this.activeFilter))
      : this.segments;

    let html = '';
    filtered.forEach(seg => {
      const speakerClass = (seg.speaker || 'unknown').toLowerCase();
      html += `
        <div class="transcript-segment ${speakerClass}" id="segment-${seg.id}">
          <div class="segment-meta">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="segment-speaker ${speakerClass}">${this.escapeHtml(seg.speaker)}</span>
              <span class="segment-time">${this.escapeHtml(seg.timestamp)}</span>
            </div>
            <div class="segment-actions">
              <button class="segment-action-btn" onclick="MediScribe.Transcript.toggleSpeakerDialog('${seg.id}')" title="Change Speaker">Toggle Speaker</button>
              <button class="segment-action-btn" onclick="MediScribe.Transcript.openEditModal('${seg.id}')" title="Edit Segment">Edit</button>
              <button class="segment-action-btn" onclick="MediScribe.Transcript.deleteSegment('${seg.id}')" title="Delete Segment">Delete</button>
            </div>
          </div>
          <div class="segment-text">${this.highlightMatch(this.escapeHtml(seg.text), this.activeFilter)}</div>
        </div>
      `;
    });

    this.containerElem.innerHTML = html;
  },

  toggleSpeakerDialog(id) {
    const seg = this.segments.find(s => s.id === id);
    if (!seg) return;
    const nextSpeaker = seg.speaker === 'DOCTOR' ? 'PATIENT' : (seg.speaker === 'PATIENT' ? 'UNKNOWN' : 'DOCTOR');
    this.changeSpeaker(id, nextSpeaker);
    MediScribe.Toast.show(`Speaker changed to ${nextSpeaker}`, 'info', 1800);
  },

  openEditModal(id) {
    const seg = this.segments.find(s => s.id === id);
    if (!seg) return;

    const modalId = 'editSegmentModal';
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
          <h3 class="modal-title">Edit Transcript Segment</h3>
          <button class="modal-close-btn" onclick="MediScribe.Modal.close('${modalId}')">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">Speaker</label>
            <select id="editSegSpeaker" class="form-select">
              <option value="DOCTOR" ${seg.speaker === 'DOCTOR' ? 'selected' : ''}>DOCTOR</option>
              <option value="PATIENT" ${seg.speaker === 'PATIENT' ? 'selected' : ''}>PATIENT</option>
              <option value="UNKNOWN" ${seg.speaker === 'UNKNOWN' ? 'selected' : ''}>UNKNOWN</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Timestamp</label>
            <input type="text" id="editSegTime" class="form-input" value="${this.escapeHtml(seg.timestamp)}">
          </div>
          <div class="form-group">
            <label class="form-label">Utterance Text</label>
            <textarea id="editSegText" class="form-textarea" rows="4">${this.escapeHtml(seg.text)}</textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="MediScribe.Modal.close('${modalId}')">Cancel</button>
          <button class="btn btn-primary" onclick="MediScribe.Transcript.saveEditModal('${seg.id}')">Save Changes</button>
        </div>
      </div>
    `;

    MediScribe.Modal.open(modalId);
  },

  saveEditModal(id) {
    const speaker = document.getElementById('editSegSpeaker').value;
    const timestamp = document.getElementById('editSegTime').value;
    const text = document.getElementById('editSegText').value;

    this.updateSegment(id, { speaker, timestamp, text });
    MediScribe.Modal.close('editSegmentModal');
    MediScribe.Toast.show('Segment updated successfully.', 'success');
  },

  highlightMatch(text, query) {
    if (!query) return text;
    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return text.replace(regex, '<mark style="background-color: #fef08a; padding: 1px 3px; border-radius: 2px;">$1</mark>');
  },

  escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
};
