import { Mic, Pause, Play, RotateCcw, Square, Wifi, Zap } from 'lucide-react'
import { Button } from '../layout/AppShell'
import type { useAmbientDocumentation } from '../../hooks/useAmbientDocumentation'

interface AmbientRecorderProps {
  ambient: ReturnType<typeof useAmbientDocumentation>
  onProcessAI?: () => void
  isProcessingAI?: boolean
}

export function AmbientRecorder({
  ambient,
  onProcessAI,
  isProcessingAI,
}: AmbientRecorderProps) {
  const {
    state,
    isConnected,
    duration,
    partialSegment,
    finalSegments,
    error,
    timing,
    startAmbient,
    pauseAmbient,
    resumeAmbient,
    stopAmbient,
    resetAmbient,
  } = ambient

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  }

  const isRecording = state === 'recording'
  const isPaused = state === 'paused'
  const isStopping = state === 'stopping'
  const isCompleted = state === 'completed'

  return (
    <div className="ambient-recorder-panel">
      {/* Top Ambient Status Header */}
      <div className="ambient-header">
        <div className="ambient-badge-group">
          <span className={`ambient-live-indicator ${isRecording ? 'pulse' : isPaused ? 'paused' : ''}`}>
            ● {isRecording ? 'Ambient Documentation Active' : isPaused ? 'Ambient Paused' : isStopping ? 'Finalizing Ambient Stream...' : isCompleted ? 'Ambient Capture Complete' : 'Ghost Viewer Ready'}
          </span>
          <span className={`ambient-conn-badge ${isConnected ? 'connected' : 'disconnected'}`}>
            <Wifi size={12} style={{ verticalAlign: 'middle', marginRight: '4px' }} />
            {isConnected ? 'Streaming Connected' : 'Disconnected'}
          </span>
        </div>

        <div className="ambient-timer">
          <b>{formatTime(duration)}</b>
        </div>
      </div>

      {/* Control Action Bar */}
      <div className="recording-controls" style={{ marginTop: '12px', marginBottom: '12px' }}>
        <Button
          primary
          disabled={isRecording || isPaused || isStopping}
          onClick={startAmbient}
        >
          <Mic size={15} /> Start Ambient Mode
        </Button>
        <Button
          disabled={!isRecording}
          onClick={pauseAmbient}
        >
          <Pause size={15} /> Pause
        </Button>
        <Button
          disabled={!isPaused}
          onClick={resumeAmbient}
        >
          <Play size={15} /> Resume
        </Button>
        <Button
          disabled={(!isRecording && !isPaused) || isStopping}
          onClick={() => stopAmbient()}
        >
          <Square size={15} /> Stop & Finalize
        </Button>
        <Button
          disabled={state === 'idle'}
          onClick={resetAmbient}
        >
          <RotateCcw size={15} /> Reset
        </Button>
      </div>

      {error && (
        <div className="form-error" style={{ marginBottom: '12px' }}>
          <b>Ambient Error:</b> {error}
        </div>
      )}

      {/* Latency Instrumentation Bar */}
      {(timing.firstPartialLatencyS != null || timing.firstFinalLatencyS != null) && (
        <div className="ambient-latency-bar">
          <Zap size={13} color="#2563eb" />
          <span>
            <b>Measured Latency:</b>{' '}
            {timing.firstPartialLatencyS != null && `First Partial: ${timing.firstPartialLatencyS}s`}
            {timing.firstFinalLatencyS != null && ` · First Final: ${timing.firstFinalLatencyS}s`}
          </span>
        </div>
      )}

      {/* Live Streaming Transcript Stream */}
      <div className="ambient-transcript-feed">
        {finalSegments.length === 0 && !partialSegment && (
          <div className="ambient-empty-hint">
            <p>Ready for consultation. Click &quot;Start Ambient Mode&quot; and converse naturally.</p>
            <small className="muted">Audio is streamed via WebSocket to Faster-Whisper and rendered in real-time.</small>
          </div>
        )}

        {finalSegments.map((seg) => (
          <div className="transcript-line ambient-line-final" key={seg.id}>
            <time>
              {Math.floor(seg.start_ms / 60000)}:{String(Math.floor((seg.start_ms % 60000) / 1000)).padStart(2, '0')}
            </time>
            <b className={`speaker ${seg.speaker.toLowerCase() === 'patient' ? 'patient' : ''}`}>
              {seg.speaker}
            </b>
            <p>{seg.text}</p>
          </div>
        ))}

        {/* Live Interim Candidate Hypothesis */}
        {partialSegment && (
          <div className="transcript-line ambient-line-partial">
            <time>Live</time>
            <b className={`speaker ${partialSegment.speaker.toLowerCase() === 'patient' ? 'patient' : ''}`}>
              {partialSegment.speaker}
            </b>
            <p className="ambient-partial-text">
              {partialSegment.text} <span className="ambient-cursor">▍</span>
            </p>
          </div>
        )}
      </div>

      {/* Post-Ambient Processing Action */}
      {isCompleted && finalSegments.length > 0 && onProcessAI && (
        <div className="ambient-handoff-banner">
          <div>
            <b>{finalSegments.length} transcript segments captured.</b>
            <p>Run clinical entity extraction, SOAP synthesis, and safety checks on this encounter.</p>
          </div>
          <Button primary disabled={isProcessingAI} onClick={onProcessAI}>
            {isProcessingAI ? 'Running Clinical AI Pipeline...' : 'Process with Clinical AI'}
          </Button>
        </div>
      )}

      {/* Heuristic Diarization Footnote */}
      <div style={{ padding: '8px 14px', borderTop: '1px solid var(--line)', background: '#fcfdfe' }}>
        <small style={{ color: 'var(--muted)', fontSize: '10px' }}>
          ℹ Speaker labels are heuristic (alternating speaker turn hypothesis for assistive review).
        </small>
      </div>
    </div>
  )
}
