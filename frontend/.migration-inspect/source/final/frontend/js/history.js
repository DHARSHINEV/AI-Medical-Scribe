/**
 * MediScribe - Consultation History Module
 * Lists, filters, and manages stored consultations from localStorage
 * PEC Techathon 4.0 MVP
 */

window.MediScribe = window.MediScribe || {};

MediScribe.History = {
  currentFilter: 'ALL',
  searchQuery: '',

  init() {
    MediScribe.Storage.init();
    this.render();
    this.bindEvents();
  },

  bindEvents() {
    const searchInput = document.getElementById('historySearchInput');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.toLowerCase().trim();
        this.render();
      });
    }

    const filterSelect = document.getElementById('historyStatusFilter');
    if (filterSelect) {
      filterSelect.addEventListener('change', (e) => {
        this.currentFilter = e.target.value;
        this.render();
      });
    }

    const btnNewConsult = document.getElementById('btnNewConsultationFromHistory');
    if (btnNewConsult) {
      btnNewConsult.addEventListener('click', () => this.createNewConsultation());
    }
  },

  render() {
    const tableBody = document.getElementById('historyTableBody');
    if (!tableBody) return;

    let consultations = MediScribe.Storage.getConsultations();

    // Filter by status
    if (this.currentFilter !== 'ALL') {
      consultations = consultations.filter(c => c.status.toLowerCase() === this.currentFilter.toLowerCase());
    }

    // Filter by search query
    if (this.searchQuery) {
      consultations = consultations.filter(c => 
        c.patientName.toLowerCase().includes(this.searchQuery) ||
        c.chiefComplaint.toLowerCase().includes(this.searchQuery) ||
        c.id.toLowerCase().includes(this.searchQuery)
      );
    }

    if (consultations.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; padding: 32px; color: var(--text-muted);">
            No consultations match your criteria.
          </td>
        </tr>
      `;
      return;
    }

    let html = '';
    consultations.forEach(c => {
      let badgeClass = 'badge-draft';
      if (c.status === 'Approved') badgeClass = 'badge-approved';
      if (c.status === 'Reviewed') badgeClass = 'badge-reviewed';

      html += `
        <tr>
          <td>
            <div style="font-weight: 600; color: var(--text-primary);">${this.escapeHtml(c.patientName)}</div>
            <div style="font-size: 11px; color: var(--text-muted);">${c.patientId} &bull; ${c.id}</div>
          </td>
          <td>${c.date} <span style="font-size: 11px; color: var(--text-muted);">${c.time || ''}</span></td>
          <td style="font-weight: 500;">${this.escapeHtml(c.chiefComplaint)}</td>
          <td>${c.duration || '02:14'}</td>
          <td>
            <span class="badge ${badgeClass}">${c.status}</span>
          </td>
          <td style="font-size: 12px; color: var(--text-secondary);">${c.clinician || 'Dr. Demo Clinician'}</td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button class="btn btn-sm btn-primary" onclick="MediScribe.History.openConsultation('${c.id}')">Open</button>
              <button class="btn btn-sm btn-secondary" onclick="MediScribe.History.reviewConsultation('${c.id}')">Review</button>
              <button class="btn btn-sm btn-secondary" style="color: var(--danger);" onclick="MediScribe.History.deleteItem('${c.id}')" title="Delete Consultation">&times;</button>
            </div>
          </td>
        </tr>
      `;
    });

    tableBody.innerHTML = html;
  },

  openConsultation(id) {
    MediScribe.Storage.setActiveConsultation(id);
    window.location.href = `consultation.html?id=${id}`;
  },

  reviewConsultation(id) {
    MediScribe.Storage.setActiveConsultation(id);
    window.location.href = `review.html?id=${id}`;
  },

  deleteItem(id) {
    if (confirm(`Delete consultation record ${id}?`)) {
      MediScribe.Storage.deleteConsultation(id);
      this.render();
      MediScribe.Toast.show(`Consultation ${id} removed.`, 'info');
    }
  },

  createNewConsultation() {
    MediScribe.NewConsultationModal.open();
  },

  escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
};

document.addEventListener('DOMContentLoaded', () => {
  if (window.location.pathname.includes('history.html')) {
    MediScribe.History.init();
  }
});
