import { useCallback, useEffect, useRef, useState } from 'react'
import { API_BASE_URL, getStoredToken } from '../services/api'
import type { TranscriptSegment } from '../types/consultation'

export type AmbientState =
  | 'idle'
  | 'recording'
  | 'paused'
  | 'resuming'
  | 'stopping'
  | 'processing'
  | 'completed'
  | 'error'

export interface AmbientSegment {
  id: string | number
  sequence: number
  speaker: string
  text: string
  start_ms: number
  end_ms: number
  is_final?: boolean
}

export interface AmbientTimingMetrics {
  captureStart: number | null
  firstChunkSent: number | null
  firstPartialReceived: number | null
  firstFinalReceived: number | null
  finalizationStart: number | null
  finalTranscriptCompleted: number | null
  firstPartialLatencyS: number | null
  firstFinalLatencyS: number | null
}

export function useAmbientDocumentation(
  consultationId: string | number,
  onFinalized?: (segments: TranscriptSegment[]) => void
) {
  const [state, setState] = useState<AmbientState>('idle')
  const [isConnected, setIsConnected] = useState(false)
  const [duration, setDuration] = useState(0)
  const [partialSegment, setPartialSegment] = useState<AmbientSegment | null>(null)
  const [finalSegments, setFinalSegments] = useState<AmbientSegment[]>([])
  const [error, setError] = useState<string | null>(null)
  const [timing, setTiming] = useState<AmbientTimingMetrics>({
    captureStart: null,
    firstChunkSent: null,
    firstPartialReceived: null,
    firstFinalReceived: null,
    finalizationStart: null,
    finalTranscriptCompleted: null,
    firstPartialLatencyS: null,
    firstFinalLatencyS: null,
  })

  const wsRef = useRef<WebSocket | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const processorNodeRef = useRef<ScriptProcessorNode | null>(null)
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null)

  const startedAtRef = useRef(0)
  const pauseStartedAtRef = useRef(0)
  const totalPausedMsRef = useRef(0)
  const finalizeResolverRef = useRef<((value: AmbientSegment[]) => void) | null>(null)

  // Timer for active recording duration
  useEffect(() => {
    if (state !== 'recording') return
    const timer = window.setInterval(() => {
      const activeMs = Date.now() - startedAtRef.current - totalPausedMsRef.current
      setDuration(Math.max(0, Math.floor(activeMs / 1000)))
    }, 250)
    return () => window.clearInterval(timer)
  }, [state])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanupAudio()
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [])

  const cleanupAudio = () => {
    if (processorNodeRef.current) {
      processorNodeRef.current.disconnect()
      processorNodeRef.current = null
    }
    if (sourceNodeRef.current) {
      sourceNodeRef.current.disconnect()
      sourceNodeRef.current = null
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop())
      mediaStreamRef.current = null
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close().catch(() => {})
      audioContextRef.current = null
    }
  }

  // Convert Float32 audio buffer from microphone to 16kHz 16-bit Mono PCM
  const downsampleTo16kPCM = (inputBuffer: Float32Array, inputSampleRate: number): ArrayBuffer => {
    if (inputSampleRate === 16000) {
      const pcm16 = new Int16Array(inputBuffer.length)
      for (let i = 0; i < inputBuffer.length; i++) {
        const s = Math.max(-1, Math.min(1, inputBuffer[i]))
        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff
      }
      return pcm16.buffer
    }

    const ratio = inputSampleRate / 16000
    const newLength = Math.round(inputBuffer.length / ratio)
    const pcm16 = new Int16Array(newLength)

    for (let i = 0; i < newLength; i++) {
      const idx = Math.round(i * ratio)
      const s = Math.max(-1, Math.min(1, inputBuffer[idx] || 0))
      pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff
    }

    return pcm16.buffer
  }

  const startAmbient = useCallback(async () => {
    setError(null)
    setPartialSegment(null)
    setFinalSegments([])
    setDuration(0)
    startedAtRef.current = Date.now()
    pauseStartedAtRef.current = 0
    totalPausedMsRef.current = 0

    const initialTiming: AmbientTimingMetrics = {
      captureStart: Date.now(),
      firstChunkSent: null,
      firstPartialReceived: null,
      firstFinalReceived: null,
      finalizationStart: null,
      finalTranscriptCompleted: null,
      firstPartialLatencyS: null,
      firstFinalLatencyS: null,
    }
    setTiming(initialTiming)

    const token = getStoredToken() || ''
    const wsUrl = `${API_BASE_URL.replace(/^http/, 'ws')}/ws/consultations/${consultationId}/ambient?token=${encodeURIComponent(token)}`

    try {
      // 1. Initialize Microphone Audio Stream
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
      mediaStreamRef.current = stream

      const audioCtx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)({
        sampleRate: 16000,
      })
      audioContextRef.current = audioCtx

      const source = audioCtx.createMediaStreamSource(stream)
      sourceNodeRef.current = source

      // Buffer size 4096 gives ~250ms chunks at 16kHz
      const processor = audioCtx.createScriptProcessor(4096, 1, 1)
      processorNodeRef.current = processor

      // 2. Open WebSocket
      const ws = new WebSocket(wsUrl)
      ws.binaryType = 'arraybuffer'
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        setState('recording')
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          const now = Date.now()

          if (msg.type === 'transcript_partial') {
            setPartialSegment({
              id: msg.segment_id,
              sequence: msg.sequence,
              speaker: msg.speaker,
              text: msg.text,
              start_ms: msg.start_ms,
              end_ms: msg.end_ms,
              is_final: false,
            })

            setTiming((prev) => {
              if (prev.firstPartialReceived) return prev
              const latency = (now - (prev.captureStart || now)) / 1000
              return {
                ...prev,
                firstPartialReceived: now,
                firstPartialLatencyS: Number(latency.toFixed(2)),
              }
            })
          } else if (msg.type === 'transcript_final') {
            const newFinal: AmbientSegment = {
              id: msg.segment_id,
              sequence: msg.sequence,
              speaker: msg.speaker,
              text: msg.text,
              start_ms: msg.start_ms,
              end_ms: msg.end_ms,
              is_final: true,
            }

            setFinalSegments((prev) => {
              // Deduplicate if already present
              if (prev.some((s) => s.text.trim().toLowerCase() === msg.text.trim().toLowerCase())) {
                return prev
              }
              return [...prev, newFinal]
            })

            // Clear partial hypothesis once finalized
            setPartialSegment(null)

            setTiming((prev) => {
              if (prev.firstFinalReceived) return prev
              const latency = (now - (prev.captureStart || now)) / 1000
              return {
                ...prev,
                firstFinalReceived: now,
                firstFinalLatencyS: Number(latency.toFixed(2)),
              }
            })
          } else if (msg.type === 'finalizing') {
            setState('stopping')
          } else if (msg.type === 'completed') {
            setState('completed')
            cleanupAudio()
            if (wsRef.current) {
              wsRef.current.close()
              wsRef.current = null
            }
            setIsConnected(false)

            setTiming((prev) => ({
              ...prev,
              finalTranscriptCompleted: now,
            }))

            if (finalizeResolverRef.current) {
              finalizeResolverRef.current(finalSegments)
              finalizeResolverRef.current = null
            }

            // Convert to TranscriptSegment domain objects
            const domainSegments: TranscriptSegment[] = finalSegments.map((seg, idx) => ({
              id: idx + 1,
              time: `${Math.floor(seg.start_ms / 60000)}:${String(Math.floor((seg.start_ms % 60000) / 1000)).padStart(2, '0')}`,
              speaker: seg.speaker,
              text: seg.text,
            }))

            if (onFinalized) {
              onFinalized(domainSegments)
            }
          } else if (msg.type === 'error') {
            setError(msg.message || 'Ambient documentation error')
            setState('error')
          }
        } catch {
          // non-json message ignored
        }
      }

      ws.onerror = () => {
        setError('WebSocket connection error')
        setState('error')
        cleanupAudio()
      }

      ws.onclose = () => {
        setIsConnected(false)
        if (state === 'recording' || state === 'stopping') {
          cleanupAudio()
        }
      }

      // 3. Audio chunk forwarding
      processor.onaudioprocess = (e) => {
        if (stateRef.current !== 'recording') return
        const channelData = e.inputBuffer.getChannelData(0)
        const pcmBuffer = downsampleTo16kPCM(channelData, audioCtx.sampleRate)

        if (ws.readyState === WebSocket.OPEN) {
          ws.send(pcmBuffer)
          setTiming((prev) => (prev.firstChunkSent ? prev : { ...prev, firstChunkSent: Date.now() }))
        }
      }

      source.connect(processor)
      processor.connect(audioCtx.destination)
    } catch (err) {
      cleanupAudio()
      setState('error')
      setError(err instanceof Error ? err.message : 'Failed to access microphone or start ambient session')
    }
  }, [consultationId, onFinalized])

  const stateRef = useRef(state)
  stateRef.current = state

  const pauseAmbient = useCallback(() => {
    if (state === 'recording') {
      setState('paused')
      pauseStartedAtRef.current = Date.now()
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'pause' }))
      }
    }
  }, [state])

  const resumeAmbient = useCallback(() => {
    if (state === 'paused') {
      setState('recording')
      if (pauseStartedAtRef.current > 0) {
        totalPausedMsRef.current += Date.now() - pauseStartedAtRef.current
        pauseStartedAtRef.current = 0
      }
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'resume' }))
      }
    }
  }, [state])

  const stopAmbient = useCallback((): Promise<AmbientSegment[]> => {
    return new Promise((resolve) => {
      finalizeResolverRef.current = resolve
      setState('stopping')
      cleanupAudio()

      setTiming((prev) => ({
        ...prev,
        finalizationStart: Date.now(),
      }))

      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'stop' }))
      } else {
        setState('completed')
        resolve(finalSegments)
      }
    })
  }, [finalSegments])

  const resetAmbient = useCallback(() => {
    cleanupAudio()
    if (wsRef.current) {
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'reset' }))
      }
      wsRef.current.close()
      wsRef.current = null
    }
    setState('idle')
    setIsConnected(false)
    setDuration(0)
    setPartialSegment(null)
    setFinalSegments([])
    setError(null)
    startedAtRef.current = 0
    pauseStartedAtRef.current = 0
    totalPausedMsRef.current = 0
    setTiming({
      captureStart: null,
      firstChunkSent: null,
      firstPartialReceived: null,
      firstFinalReceived: null,
      finalizationStart: null,
      finalTranscriptCompleted: null,
      firstPartialLatencyS: null,
      firstFinalLatencyS: null,
    })
  }, [])

  return {
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
  }
}
