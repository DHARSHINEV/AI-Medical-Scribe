/**
 * MediScribe - 5-Minute Judge Demo Guide & Controller
 * Optimized for PEC Techathon 4.0 Presentation Flow
 */

window.MediScribe = window.MediScribe || {};

MediScribe.Demo = {
  currentStepIndex: 0,
  demoSteps: [
    {
      step: 1,
      time: "00:00 – 00:30",
      title: "Dashboard & Problem Intro",
      narration: "«MediScribe is an AI medical documentation assistant with a built-in Clinical Second Look. We don't just transcribe — we safeguard clinical records against oversights.»",
      actionLabel: "Start Demo Consultation →",
      targetPage: "consultation.html",
      execute: () => {
        MediScribe.Storage.setActiveConsultation('CONS-2026-08-29-001');
        window.location.href = 'consultation.html?demo=true';
      }
    },
    {
      step: 2,
      time: "00:30 – 01:30",
      title: "Live Transcript & Patient Context",
      narration: "«Notice our 3-column clinical workspace. On the left is Arun Kumar's stored EHR history with a documented Penicillin allergy. In the center is the real-time transcript with diarized speaker labels.»",
      actionLabel: "Generate SOAP Note →",
      targetPage: "consultation.html",
      execute: () => {
        if (window.MediScribe.Consultation) {
          MediScribe.Consultation.generateDocumentation();
        }
      }
    },
    {
      step: 3,
      time: "01:30 – 02:00",
      title: "Structured SOAP Documentation",
      narration: "«MediScribe instantly structures the conversation into Subjective, Objective, Assessment, and Plan. Notice every clinical claim links directly to its timestamped source utterance.»",
      actionLabel: "Explore Clinical Second Look →",
      targetPage: "consultation.html",
      execute: () => {
        const card = document.querySelector('.second-look-card');
        if (card) card.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    },
    {
      step: 4,
      time: "02:00 – 03:00",
      title: "AI Clinical Second Look (Core Innovation)",
      narration: "«This is our core innovation: The Clinical Second Look! It caught a critical history conflict: Arun's chart shows a Penicillin allergy, but he verbally stated 'I don't think I have any allergies.' It also caught that his Amlodipine dose was missing.»",
      actionLabel: "Analyze Lab Report →",
      targetPage: "labs.html",
      execute: () => {
        window.location.href = 'labs.html';
      }
    },
    {
      step: 5,
      time: "03:00 – 03:45",
      title: "Lab Report Analyzer & Range Checking",
      narration: "«Our Lab Analyzer ingests pathology documents, detects parameters, and compares them to reference ranges. Notice Hemoglobin is 11.2, correctly flagged as Outside supplied reference range without jumping to autonomous diagnoses.»",
      actionLabel: "Attach Lab to Note →",
      targetPage: "labs.html",
      execute: () => {
        if (window.MediScribe.Labs) {
          MediScribe.Labs.addToActiveConsultation();
          setTimeout(() => { window.location.href = 'review.html'; }, 1000);
        }
      }
    },
    {
      step: 6,
      time: "03:45 – 04:45",
      title: "Clinician Review & Safety Resolution",
      narration: "«In the final review screen, the physician retains 100% authority. We can regenerate a single section like Assessment without modifying others, resolve safety flags, and complete the sign-off checklist.»",
      actionLabel: "Approve & Sign Note →",
      targetPage: "review.html",
      execute: () => {
        if (window.MediScribe.Review) {
          MediScribe.Review.approveNote();
        }
      }
    },
    {
      step: 7,
      time: "04:45 – 05:00",
      title: "PDF / EHR Export & Wrap Up",
      narration: "«With one click, we generate an official clinic-formatted PDF ready for medical records, export structured JSON, or copy directly into any EHR. Complete, safe, and fully audited!»",
      actionLabel: "Print / Save PDF →",
      targetPage: "review.html",
      execute: () => {
        MediScribe.Export.printPDF();
      }
    }
  ],

  init() {
    // Floating demo helper disabled per user request for clean clinical interface
  },

  renderFloatingHelper() {
    // Check if helper bar already exists
    if (document.getElementById('floatingDemoHelper')) return;

    const bar = document.createElement('div');
    bar.id = 'floatingDemoHelper';
    bar.style.position = 'fixed';
    bar.style.bottom = '16px';
    bar.style.left = '50%';
    bar.style.transform = 'translateX(-50%)';
    bar.style.backgroundColor = '#0f172a';
    bar.style.color = '#ffffff';
    bar.style.padding = '10px 18px';
    bar.style.borderRadius = '30px';
    bar.style.boxShadow = '0 8px 24px rgba(0, 0, 0, 0.25)';
    bar.style.display = 'flex';
    bar.style.alignItems = 'center';
    bar.style.gap = '14px';
    bar.style.zIndex = '9999';
    bar.style.fontSize = '12px';
    bar.style.fontFamily = 'inherit';

    bar.innerHTML = `
      <div style="display: flex; align-items: center; gap: 6px;">
        <span style="background: #38bdf8; color: #0f172a; font-weight: 700; padding: 2px 6px; border-radius: 4px; font-size: 10px;">TECHATHON 4.0</span>
        <strong style="font-size: 13px;">Judge Demo Guide:</strong>
      </div>
      <div id="demoStepInfo" style="color: #cbd5e1; max-width: 460px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
        Step 1/7: Dashboard & Problem Intro
      </div>
      <div style="display: flex; gap: 6px;">
        <button id="btnDemoQuickAction" class="btn btn-sm btn-primary" style="font-weight: 600; padding: 4px 12px; font-size: 11px;">
          Next Demo Step &rarr;
        </button>
        <button id="btnDemoNarrationModal" class="btn btn-sm btn-secondary" style="font-size: 11px; padding: 4px 8px; background: #1e293b; color: #f8fafc; border-color: #334155;">
          Speech Script
        </button>
        <button onclick="document.getElementById('floatingDemoHelper').style.display='none'" style="background: none; border: none; color: #94a3b8; font-size: 16px; cursor: pointer; padding: 0 4px;" title="Hide helper">&times;</button>
      </div>
    `;

    document.body.appendChild(bar);

    // Track active page to synchronize step
    const path = window.location.pathname;
    if (path.includes('consultation.html')) {
      this.currentStepIndex = 1;
    } else if (path.includes('labs.html')) {
      this.currentStepIndex = 4;
    } else if (path.includes('review.html')) {
      this.currentStepIndex = 5;
    } else {
      this.currentStepIndex = 0;
    }

    this.updateHelperDisplay();

    document.getElementById('btnDemoQuickAction').addEventListener('click', () => {
      this.triggerCurrentStep();
    });

    document.getElementById('btnDemoNarrationModal').addEventListener('click', () => {
      this.openNarrationModal();
    });
  },

  updateHelperDisplay() {
    const step = this.demoSteps[this.currentStepIndex];
    if (!step) return;

    const infoElem = document.getElementById('demoStepInfo');
    const btnElem = document.getElementById('btnDemoQuickAction');

    if (infoElem) {
      infoElem.innerHTML = `<strong>Step ${step.step}/7:</strong> ${step.title} (${step.time})`;
    }
    if (btnElem) {
      btnElem.textContent = step.actionLabel;
    }
  },

  triggerCurrentStep() {
    const step = this.demoSteps[this.currentStepIndex];
    if (!step) return;

    step.execute();

    // Advance step index
    this.currentStepIndex = (this.currentStepIndex + 1) % this.demoSteps.length;
    this.updateHelperDisplay();
  },

  openNarrationModal() {
    const step = this.demoSteps[this.currentStepIndex];
    const modalId = 'demoNarrationModal';
    let modal = document.getElementById(modalId);
    if (!modal) {
      modal = document.createElement('div');
      modal.id = modalId;
      modal.className = 'modal-overlay';
      document.body.appendChild(modal);
    }

    modal.innerHTML = `
      <div class="modal-container" style="max-width: 540px;">
        <div class="modal-header">
          <h3 class="modal-title">Techathon 5-Minute Pitch Script</h3>
          <button class="modal-close-btn" onclick="MediScribe.Modal.close('${modalId}')">&times;</button>
        </div>
        <div class="modal-body" style="font-size: 13px; line-height: 1.6;">
          <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; margin-bottom: 6px;">
            Step ${step.step} (${step.time}) &bull; ${step.title}
          </div>
          <div style="background: #f8fafc; border-left: 4px solid var(--primary); padding: 12px; border-radius: 4px; font-style: italic; color: #0f172a; margin-bottom: 16px;">
            ${step.narration}
          </div>
          <div style="font-weight: 600; margin-bottom: 8px;">Key Innovations to Highlight:</div>
          <ul style="padding-left: 20px; font-size: 12px; color: var(--text-secondary);">
            <li><strong>AI Clinical Second Look:</strong> Automated cross-referencing of conversation against EHR history.</li>
            <li><strong>Explainable Evidence Linking:</strong> Jump directly to transcript source tags.</li>
            <li><strong>Clinician Autonomy:</strong> Never diagnoses or prescribes; supports clinician oversight.</li>
          </ul>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="MediScribe.Modal.close('${modalId}')">Close</button>
          <button class="btn btn-primary" onclick="MediScribe.Modal.close('${modalId}'); MediScribe.Demo.triggerCurrentStep();">
            Execute This Step
          </button>
        </div>
      </div>
    `;

    MediScribe.Modal.open(modalId);
  },

  /**
   * Stream dialogue with typewriter effect into the transcript panel
   */
  streamDemoDialogue(onComplete) {
    if (!MediScribe.DemoData) return;
    const dialogue = MediScribe.DemoData.demoConsultationDialogue;
    MediScribe.Transcript.clear();

    let i = 0;
    const interval = setInterval(() => {
      if (i < dialogue.length) {
        MediScribe.Transcript.addSegment(dialogue[i]);
        i++;
      } else {
        clearInterval(interval);
        if (onComplete) onComplete();
      }
    }, 450);
  }
};

document.addEventListener('DOMContentLoaded', () => {
  MediScribe.Demo.init();
});
