import { useEffect, useState, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Upload,
  FileText,
  FileImage,
  ExternalLink,
  Trash2,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  Search,
  User,
  Clock,
  ShieldCheck,
} from 'lucide-react'
import { PageTitle, Panel, Notice } from '../components/layout/AppShell'
import { useAuth } from '../context/AuthContext'
import { labService, patientService } from '../services/domainServices'
import type { LabReport } from '../types/lab'
import type { Patient } from '../types/patient'

const ALLOWED_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg']
const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024 // 50MB

export default function LabsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialPatientId = searchParams.get('patientId') || ''
  const consultationId = searchParams.get('consultationId') || ''
  const { mode } = useAuth()

  // State
  const [patients, setPatients] = useState<Patient[]>([])
  const [selectedPatientId, setSelectedPatientId] = useState<string>(initialPatientId)
  const [reports, setReports] = useState<LabReport[]>([])
  const [loadingReports, setLoadingReports] = useState<boolean>(true)
  const [loadingPatients, setLoadingPatients] = useState<boolean>(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [customTitle, setCustomTitle] = useState<string>('')
  const [uploading, setUploading] = useState<boolean>(false)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState<boolean>(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  // Load patients list
  useEffect(() => {
    let active = true
    setLoadingPatients(true)
    patientService
      .getPatients()
      .then((data) => {
        if (active) {
          setPatients(data)
          if (!selectedPatientId && data.length > 0) {
            setSelectedPatientId(String(data[0].id))
          }
        }
      })
      .catch((err) => {
        if (active) {
          console.error('Failed to load patients', err)
        }
      })
      .finally(() => {
        if (active) setLoadingPatients(false)
      })

    return () => {
      active = false
    }
  }, [])

  // Load reports for selected patient (or all reports)
  const loadReports = async (patientId?: string) => {
    setLoadingReports(true)
    setErrorMessage(null)
    try {
      const data = await labService.getLabs(patientId || undefined)
      setReports(data)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load laboratory reports.'
      setErrorMessage(msg)
    } finally {
      setLoadingReports(false)
    }
  }

  useEffect(() => {
    loadReports(selectedPatientId)
  }, [selectedPatientId])

  // Handle patient switch
  const handlePatientChange = (patientId: string) => {
    setSelectedPatientId(patientId)
    if (patientId) {
      setSearchParams({ patientId })
    } else {
      setSearchParams({})
    }
    setSelectedFile(null)
    setValidationError(null)
    setSuccessMessage(null)
  }

  // File validation
  const validateAndSetFile = (file: File) => {
    setValidationError(null)
    setSuccessMessage(null)

    const ext = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setValidationError(
        `Invalid file format "${ext}". Supported formats: PDF, PNG, JPG, JPEG.`
      )
      setSelectedFile(null)
      return false
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(1)
      setValidationError(
        `File is too large (${sizeMB} MB). Maximum allowed size is 50 MB.`
      )
      setSelectedFile(null)
      return false
    }

    setSelectedFile(file)
    if (!customTitle) {
      // Default title without extension
      const baseName = file.name.replace(/\.[^/.]+$/, '')
      setCustomTitle(baseName)
    }
    return true
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      validateAndSetFile(files[0])
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0])
    }
  }

  // Execute upload
  const handleUpload = async () => {
    if (!selectedFile) {
      setValidationError('Please select a laboratory report file.')
      return
    }
    if (!selectedPatientId) {
      setValidationError('Please select a patient for this laboratory report.')
      return
    }

    setUploading(true)
    setValidationError(null)
    setErrorMessage(null)
    setSuccessMessage(null)

    try {
      const created = await labService.uploadLabReport(
        selectedPatientId,
        selectedFile,
        customTitle.trim() || undefined,
        consultationId ? Number(consultationId) : undefined
      )

      setSuccessMessage(`Laboratory report "${created.title}" uploaded successfully.`)
      setSelectedFile(null)
      setCustomTitle('')
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      // Refresh reports list
      await loadReports(selectedPatientId)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Upload failed. Please try again.'
      setErrorMessage(msg)
    } finally {
      setUploading(false)
    }
  }

  // Delete report
  const handleDelete = async (reportId: number, title: string) => {
    if (!window.confirm(`Are you sure you want to delete "${title}"?`)) {
      return
    }
    try {
      await labService.deleteLabReport(reportId)
      setReports((prev) => prev.filter((r) => r.id !== reportId))
      setSuccessMessage(`Report "${title}" removed.`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to delete report.'
      setErrorMessage(msg)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr)
      return d.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return dateStr
    }
  }

  const selectedPatient = patients.find((p) => String(p.id) === String(selectedPatientId))

  return (
    <>
      <PageTitle
        eyebrow="CLINICAL INVESTIGATIONS & DIAGNOSTICS"
        title="Laboratory Reports"
      >
        <button
          className="btn secondary"
          onClick={() => loadReports(selectedPatientId)}
          disabled={loadingReports}
          title="Refresh reports"
        >
          <RefreshCw size={14} className={loadingReports ? 'spin' : ''} /> Refresh
        </button>
      </PageTitle>

      <Notice />

      {/* Patient Selection Bar */}
      <div
        style={{
          display: 'flex',
          gap: '16px',
          alignItems: 'center',
          background: '#fff',
          padding: '14px 18px',
          borderRadius: '9px',
          border: '1px solid var(--line)',
          marginBottom: '20px',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--ink)', fontWeight: 700, fontSize: '12px' }}>
          <User size={16} color="var(--blue)" />
          <span>Patient Context:</span>
        </div>

        <select
          value={selectedPatientId}
          onChange={(e) => handlePatientChange(e.target.value)}
          disabled={loadingPatients || uploading}
          style={{
            padding: '8px 12px',
            borderRadius: '6px',
            border: '1px solid var(--line)',
            background: '#fff',
            fontSize: '13px',
            color: 'var(--ink)',
            minWidth: '260px',
          }}
        >
          <option value="">-- All Patients --</option>
          {patients.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} (MRN: {p.mrn})
            </option>
          ))}
        </select>

        {selectedPatient && (
          <span style={{ fontSize: '12px', color: 'var(--muted)', marginLeft: 'auto' }}>
            Age: {selectedPatient.age || 'N/A'} · Gender: {selectedPatient.gender || selectedPatient.sex || 'N/A'} · MRN: {selectedPatient.mrn}
          </span>
        )}
      </div>

      {/* Status Messages */}
      {errorMessage && (
        <div
          className="form-error"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '12px 16px',
            background: '#fff0ef',
            border: '1px solid #efc4c1',
            borderRadius: '8px',
            marginBottom: '16px',
          }}
        >
          <AlertCircle size={16} />
          <span>{errorMessage}</span>
        </div>
      )}

      {successMessage && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '12px 16px',
            background: '#effbf9',
            border: '1px solid #bce4df',
            borderRadius: '8px',
            color: 'var(--teal)',
            fontSize: '12px',
            fontWeight: 600,
            marginBottom: '16px',
          }}
        >
          <CheckCircle2 size={16} />
          <span>{successMessage}</span>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 1fr) minmax(400px, 1.6fr)', gap: '20px', alignItems: 'start' }}>
        {/* Left Column: Upload Section */}
        <Panel title="Provide Laboratory Report" label="PDF / PNG / JPEG (Max 50MB)">
          <div style={{ padding: '20px' }}>
            <p className="muted" style={{ marginBottom: '16px' }}>
              Upload authentic diagnostic documents, blood panels, or imaging reports for patient clinical correlation.
            </p>

            {/* Drop Zone */}
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: isDragging ? '2px dashed var(--blue)' : '2px dashed var(--line)',
                borderRadius: '8px',
                padding: '28px 16px',
                textAlign: 'center',
                background: isDragging ? '#edf5ff' : '#f8fafc',
                cursor: 'pointer',
                transition: 'all 0.2s',
                marginBottom: '16px',
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.png,.jpg,.jpeg"
                onChange={handleFileChange}
                style={{ display: 'none' }}
              />

              <div
                style={{
                  width: '44px',
                  height: '44px',
                  borderRadius: '50%',
                  background: '#eaf3ff',
                  color: 'var(--blue)',
                  display: 'grid',
                  placeItems: 'center',
                  margin: '0 auto 12px',
                }}
              >
                <Upload size={22} />
              </div>

              <b style={{ display: 'block', fontSize: '13px', color: 'var(--ink)', marginBottom: '4px' }}>
                {selectedFile ? 'Change Selected File' : 'Click or Drag & Drop Lab File'}
              </b>
              <span className="muted" style={{ fontSize: '11px' }}>
                Supported: PDF, PNG, JPG, JPEG (up to 50MB)
              </span>
            </div>

            {/* Selected File State */}
            {selectedFile && (
              <div
                style={{
                  background: '#f4f8fd',
                  border: '1px solid #d9e5f2',
                  borderRadius: '8px',
                  padding: '14px',
                  marginBottom: '16px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {selectedFile.type.includes('pdf') ? (
                    <FileText size={20} color="var(--blue)" />
                  ) : (
                    <FileImage size={20} color="var(--teal)" />
                  )}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <b style={{ display: 'block', fontSize: '12px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {selectedFile.name}
                    </b>
                    <small className="muted">{formatFileSize(selectedFile.size)}</small>
                  </div>
                </div>

                <div style={{ marginTop: '12px' }}>
                  <label className="field-label" style={{ fontSize: '11px' }}>
                    <span>Report Title / Description</span>
                    <input
                      type="text"
                      value={customTitle}
                      onChange={(e) => setCustomTitle(e.target.value)}
                      placeholder="e.g. Complete Blood Count (CBC) Panel"
                      style={{ fontSize: '12px', padding: '8px 10px' }}
                    />
                  </label>
                </div>
              </div>
            )}

            {validationError && (
              <div
                className="form-error"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  marginBottom: '14px',
                }}
              >
                <AlertCircle size={14} />
                <span>{validationError}</span>
              </div>
            )}

            <button
              className="btn primary"
              style={{ width: '100%' }}
              onClick={handleUpload}
              disabled={!selectedFile || uploading || !selectedPatientId}
            >
              {uploading ? (
                <>
                  <RefreshCw size={15} className="spin" /> Uploading Report...
                </>
              ) : (
                <>
                  <Upload size={15} /> Upload Lab Report
                </>
              )}
            </button>

            {!selectedPatientId && (
              <p className="muted" style={{ fontSize: '11px', marginTop: '8px', textAlign: 'center' }}>
                Please select a patient above before uploading.
              </p>
            )}
          </div>
        </Panel>

        {/* Right Column: Reports List */}
        <Panel
          title={selectedPatient ? `Reports for ${selectedPatient.name}` : 'All Patient Reports'}
          label={`${reports.length} document${reports.length === 1 ? '' : 's'}`}
        >
          {loadingReports ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--muted)' }}>
              <RefreshCw size={24} className="spin" style={{ margin: '0 auto 12px', display: 'block' }} />
              <p>Loading laboratory reports...</p>
            </div>
          ) : reports.length === 0 ? (
            <div className="empty-card" style={{ margin: '20px' }}>
              <FileText size={36} />
              <h3>No laboratory report has been added yet.</h3>
              <p>
                {selectedPatient
                  ? `Upload a diagnostic report above to attach laboratory records for ${selectedPatient.name}.`
                  : 'Select a patient and upload a lab report to view documented investigations.'}
              </p>
            </div>
          ) : (
            <div style={{ padding: '14px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {reports.map((report) => (
                  <div
                    key={report.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '14px',
                      background: '#fff',
                      border: '1px solid var(--line)',
                      borderRadius: '8px',
                      padding: '14px 16px',
                      transition: 'all 0.15s',
                    }}
                  >
                    <div
                      style={{
                        width: '38px',
                        height: '38px',
                        borderRadius: '8px',
                        background: report.file_type === 'pdf' ? '#edf5ff' : '#effbf9',
                        color: report.file_type === 'pdf' ? 'var(--blue)' : 'var(--teal)',
                        display: 'grid',
                        placeItems: 'center',
                        flexShrink: 0,
                      }}
                    >
                      {report.file_type === 'pdf' ? <FileText size={20} /> : <FileImage size={20} />}
                    </div>

                    <div style={{ flex: 1, minWidth: 0 }}>
                      <b style={{ fontSize: '13px', display: 'block', color: 'var(--ink)' }}>
                        {report.title}
                      </b>
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px',
                          fontSize: '11px',
                          color: 'var(--muted)',
                          marginTop: '3px',
                          flexWrap: 'wrap',
                        }}
                      >
                        <span>{report.filename}</span>
                        <span>·</span>
                        <span>{formatFileSize(report.file_size_bytes)}</span>
                        <span>·</span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <Clock size={12} /> {formatDate(report.uploaded_at)}
                        </span>
                        {report.patient_name && !selectedPatientId && (
                          <>
                            <span>·</span>
                            <span style={{ color: 'var(--blue)', fontWeight: 600 }}>
                              Patient: {report.patient_name} (MRN: {report.patient_mrn})
                            </span>
                          </>
                        )}
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                      <a
                        href={labService.getLabDownloadUrl(report.id)}
                        target="_blank"
                        rel="noreferrer"
                        className="btn secondary"
                        style={{ padding: '7px 11px', fontSize: '11px', gap: '5px' }}
                        title="View / Download Report"
                      >
                        <ExternalLink size={13} /> View
                      </a>
                      <button
                        className="icon-button"
                        onClick={() => handleDelete(report.id, report.title)}
                        style={{ color: 'var(--red)', padding: '6px' }}
                        title="Delete Report"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Panel>
      </div>
    </>
  )
}
