import { useState } from 'react'
import { Check, Download, ExternalLink, RefreshCw, ShieldAlert, ShieldCheck, Undo2 } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { Button, Notice, PageTitle, Panel } from '../components/layout/AppShell'
import { useConsultation } from '../hooks/useConsultation'
import { useAuth } from '../context/AuthContext'
import type { NormalizedSOAP } from '../context/ConsultationContext'

function EditableSOAP({
  letter,
  title,
  value,
  onSave,
  locked,
}: {
  letter: string
  title: string
  value: string
  onSave: (value: string) => Promise<void>
  locked: boolean
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  const handleSave = async () => {
    setSaving(true)
    setSaveError(null)
    try {
      await onSave(draft)
      setEditing(false)
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="soap-section">
      <span>{letter}</span>
      <div className="soap-content">
        <div className="soap-heading">
          <h3>{title}</h3>
          {!locked && !editing && (
            <button
              className="text-button"
              onClick={() => {
                setDraft(value)
                setEditing(true)
              }}
            >
              Edit
            </button>
          )}
        </div>

        {editing ? (
          <>
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              aria-label={`Edit ${title}`}
              rows={4}
            />
            {saveError && <p className="form-error">{saveError}</p>}
            <div className="inline-actions">
              <Button
                onClick={() => {
                  setDraft(value)
                  setEditing(false)
                }}
              >
                Cancel
              </Button>
              <Button primary onClick={handleSave} disabled={saving}>
                {saving ? 'Saving…' : 'Save'}
              </Button>
            </div>
          </>
        ) : (
          <p>{value || <em className="muted">Not documented</em>}</p>
        )}
      </div>
    </div>
  )
}

export default function ReviewPage() {
  const { id = '' } = useParams()
  const c = useConsultation(id)
  const { user } = useAuth()
  const [evidenceId, setEvidenceId] = useState<string | number | null>(null)
  const [approving, setApproving] = useState(false)
  const [approvalError, setApprovalError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const updateSection = async (key: keyof NormalizedSOAP, val: string) => {
    setActionError(null)
    try {
      await c.updateNote({ [key]: val })
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to update note on backend')
      throw err
    }
  }

  const handleApprove = async () => {
    if (hasUnresolvedAlerts) {
      setApprovalError('Cannot approve consultation while unresolved clinical safety alerts require review. Please resolve all required alerts in Second Look first.')
      return
    }
    setApproving(true)
    setApprovalError(null)
    try {
      await c.approve()
    } catch (err) {
      setApprovalError(err instanceof Error ? err.message : 'Approval failed')
    } finally {
      setApproving(false)
    }
  }

  const handleResolve = async (alertId: string | number, currentResolved: boolean) => {
    setActionError(null)
    try {
      await c.resolveAlert(alertId, !currentResolved)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to update alert resolution')
    }
  }

  const alerts = c.safetySummary?.alerts || []
  const hasUnresolvedAlerts = alerts.some((a) => !a.resolved && a.requires_review)
  const isLocked = c.approved

  return (
    <>
      <Notice />
      <PageTitle
        eyebrow={`REVIEW & APPROVE · #${c.consultation.id}`}
        title={c.approved ? 'Consultation Approved' : 'Review Generated Note & Safety Checks'}
      >
        <span className={`status-pill ${c.approved ? 'connected' : ''}`}>
          <i /> {c.approved ? 'Clinician Approved' : `Status: ${c.status.toUpperCase()}`}
        </span>
      </PageTitle>

      {approvalError && (
        <div className="form-error" style={{ marginBottom: '16px' }}>
          <b>Approval Error:</b> {approvalError}
        </div>
      )}

      {actionError && (
        <div className="form-error" style={{ marginBottom: '16px' }}>
          <b>Action Error:</b> {actionError}
        </div>
      )}

      <div className="review-layout">
        {/* Left Column: Authoritative SOAP Note */}
        <Panel
          title="Clinical SOAP Note"
          label={
            c.note.updatedAt
              ? `Last updated: ${new Date(c.note.updatedAt).toLocaleTimeString()}`
              : 'Assistive draft'
          }
        >
          <EditableSOAP
            letter="S"
            title="Subjective"
            value={c.note.Subjective || c.note.subjective}
            onSave={(v) => updateSection('subjective', v)}
            locked={isLocked}
          />
          <EditableSOAP
            letter="O"
            title="Objective"
            value={c.note.Objective || c.note.objective}
            onSave={(v) => updateSection('objective', v)}
            locked={isLocked}
          />
          <EditableSOAP
            letter="A"
            title="Assessment"
            value={c.note.Assessment || c.note.assessment}
            onSave={(v) => updateSection('assessment', v)}
            locked={isLocked}
          />
          <EditableSOAP
            letter="P"
            title="Plan"
            value={c.note.Plan || c.note.plan}
            onSave={(v) => updateSection('plan', v)}
            locked={isLocked}
          />

          <div className="review-actions">
            <Button
              onClick={() => {
                const blob = new Blob(
                  [
                    JSON.stringify(
                      {
                        consultationId: c.consultation.id,
                        patient: c.currentPatient,
                        soapNote: c.note,
                        approved: c.approved,
                        approvedAt: c.consultation.approved_at,
                        approvedBy: c.consultation.approved_by || user?.name,
                      },
                      null,
                      2
                    ),
                  ],
                  { type: 'application/json' }
                )
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `consultation-${c.consultation.id}-soap.json`
                a.click()
                URL.revokeObjectURL(url)
              }}
            >
              <Download size={15} /> Export Note JSON
            </Button>

            {!c.approved && (
              <Button
                primary
                onClick={handleApprove}
                disabled={approving || c.approved}
              >
                <Check size={15} /> {approving ? 'Approving…' : 'Approve note'}
              </Button>
            )}

            {c.approved && (
              <>
                <span
                  style={{
                    color: 'var(--teal)',
                    fontWeight: 700,
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <ShieldCheck size={16} /> Approved by {user?.name || 'Doctor'}
                  {c.consultation.approved_at &&
                    ` on ${new Date(c.consultation.approved_at).toLocaleDateString()}`}
                </span>
                <Link className="btn primary" to={`/prescription/${c.consultation.id}`}>
                  Prepare prescription
                </Link>
              </>
            )}
          </div>
        </Panel>

        {/* Right Column: Clinical Second Look & Audit Trail */}
        <div>
          <Panel
            title="Clinical Second Look"
            label={
              c.safetySummary
                ? `${c.safetySummary.alert_count} alert(s)`
                : 'Safety verification'
            }
          >
            <div style={{ padding: '0 16px 14px' }}>
              <div
                style={{
                  background: '#fff9eb',
                  border: '1px solid #f0d59d',
                  borderRadius: '7px',
                  padding: '10px 12px',
                  fontSize: '11px',
                  color: '#7b5212',
                  marginBottom: '14px',
                }}
              >
                <strong>Assistive Verification Layer:</strong> Second Look cross-checks EHR
                allergies, medications, and findings with transcript evidence. Review and resolve
                safety alerts before finalizing.
              </div>

              {alerts.length === 0 && (
                <div style={{ padding: '16px 0', color: 'var(--teal)', fontSize: '12px' }}>
                  <ShieldCheck size={16} style={{ verticalAlign: 'middle', marginRight: '6px' }} />
                  No safety discrepancies detected by Second Look.
                </div>
              )}

              {alerts.map((a) => {
                const segId = a.evidence_segment_id || a.evidenceSegmentId
                const isSelected = evidenceId != null && String(evidenceId) === String(segId)

                return (
                  <div
                    className={`alert ${isSelected ? 'selected' : ''}`}
                    key={a.id}
                    style={{
                      opacity: a.resolved ? 0.65 : 1,
                      borderLeft: a.resolved ? '3px solid var(--teal)' : '3px solid var(--amber)',
                      paddingLeft: '12px',
                      marginBottom: '12px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span className={`severity ${a.severity.toLowerCase()}`}>
                        {a.severity}
                      </span>
                      <button
                        className="text-button"
                        style={{ fontSize: '11px', color: a.resolved ? 'var(--muted)' : 'var(--blue)' }}
                        onClick={() => handleResolve(a.id, a.resolved)}
                      >
                        {a.resolved ? (
                          <>
                            <Undo2 size={12} /> Mark Unresolved
                          </>
                        ) : (
                          <>
                            <Check size={12} /> Resolve Alert
                          </>
                        )}
                      </button>
                    </div>

                    <b>{a.title}</b>
                    <p>{a.detail}</p>

                    {segId && (
                      <button
                        onClick={() => {
                          setEvidenceId(segId)
                          const el = document.getElementById(`evidence-${segId}`)
                          el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
                        }}
                      >
                        Open transcript evidence <ExternalLink size={13} />
                      </button>
                    )}
                  </div>
                )
              })}

              {evidenceId && (
                <div className="evidence-callout">
                  <b>Evidence segment #{evidenceId} selected</b>
                  <span>
                    {c.transcript.find((t) => String(t.id) === String(evidenceId))?.text ||
                      'Highlighted in consultation transcript.'}
                  </span>
                  <Link
                    to={`/consultations/${c.consultation.id}`}
                    style={{ fontSize: '11px', color: 'var(--blue)', fontWeight: 700 }}
                  >
                    View in Consultation Workspace →
                  </Link>
                </div>
              )}

              <div className="context-block" style={{ marginTop: '14px', borderBottom: 0 }}>
                <b>Review boundary</b>
                <span>
                  MediScribe does not prescribe or independently diagnose. Clinician approval is
                  authoritative.
                </span>
              </div>
            </div>
          </Panel>

          {/* Audit Logs Trail */}
          <Panel title="Consultation Audit Trail" label={`${c.auditLogs.length} events`}>
            <div style={{ padding: '0 16px', maxHeight: '240px', overflowY: 'auto' }}>
              {c.auditLogs.length === 0 ? (
                <p className="muted" style={{ padding: '12px 0' }}>
                  No audit logs recorded for this consultation.
                </p>
              ) : (
                c.auditLogs.map((log) => (
                  <div
                    key={log.id}
                    style={{
                      padding: '10px 0',
                      borderBottom: '1px solid var(--line)',
                      fontSize: '11px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <b style={{ color: 'var(--blue)' }}>{log.action}</b>
                      <span className="muted">
                        {new Date(log.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                    {log.details && (
                      <small className="muted" style={{ display: 'block', marginTop: '3px' }}>
                        {JSON.stringify(log.details)}
                      </small>
                    )}
                  </div>
                ))
              )}
            </div>
          </Panel>
        </div>
      </div>
    </>
  )
}
