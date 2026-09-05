import { useRef, type ChangeEvent } from 'react'
import { Mic, Pause, Play, RotateCcw, Square, Upload } from 'lucide-react'
import { Button } from '../layout/AppShell'

interface RecordingProps {
  isRecording: boolean
  isPaused: boolean
  audioBlob: Blob | null
  error: string | null
  startRecording: () => void
  pauseRecording: () => void
  resumeRecording: () => void
  stopRecording: () => void
  resetRecording: () => void
  onFileSelect?: (file: File) => void
  selectedFileName?: string | null
}

export function RecordingControls({ recording }: { recording: RecordingProps }) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && recording.onFileSelect) {
      recording.onFileSelect(file)
    }
  }

  return (
    <div className="recording-controls">
      <Button primary disabled={recording.isRecording} onClick={recording.startRecording}>
        <Mic size={15} /> Start Recording
      </Button>
      <Button disabled={!recording.isRecording || recording.isPaused} onClick={recording.pauseRecording}>
        <Pause size={15} /> Pause
      </Button>
      <Button disabled={!recording.isRecording || !recording.isPaused} onClick={recording.resumeRecording}>
        <Play size={15} /> Resume
      </Button>
      <Button disabled={!recording.isRecording} onClick={recording.stopRecording}>
        <Square size={15} /> Stop
      </Button>
      <Button disabled={!recording.isRecording && !recording.audioBlob && !recording.selectedFileName} onClick={recording.resetRecording}>
        <RotateCcw size={15} /> Reset
      </Button>

      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept="audio/*,.wav,.webm,.mp3,.m4a,.ogg"
        style={{ display: 'none' }}
      />
      <Button
        disabled={recording.isRecording}
        onClick={() => fileInputRef.current?.click()}
      >
        <Upload size={15} /> Choose Audio File
      </Button>

      {recording.selectedFileName && (
        <span className="recording-ready">File: {recording.selectedFileName}</span>
      )}
      {!recording.selectedFileName && recording.audioBlob && (
        <span className="recording-ready">Captured mic audio ready</span>
      )}
      {recording.error && <span className="form-error">{recording.error}</span>}
    </div>
  )
}
