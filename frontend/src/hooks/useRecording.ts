import { useCallback, useEffect, useRef, useState } from 'react'

export function useRecording() {
  const recorder = useRef<MediaRecorder | null>(null)
  const stream = useRef<MediaStream | null>(null)
  const chunks = useRef<Blob[]>([])
  const startedAt = useRef(0)
  const pauseStartedAt = useRef(0)
  const totalPausedMs = useRef(0)

  const [isRecording, setIsRecording] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [duration, setDuration] = useState(0)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isRecording || isPaused) return
    const timer = window.setInterval(() => {
      const activeMs = Date.now() - startedAt.current - totalPausedMs.current
      setDuration(Math.max(0, Math.floor(activeMs / 1000)))
    }, 250)
    return () => window.clearInterval(timer)
  }, [isRecording, isPaused])

  const startRecording = useCallback(async () => {
    setError(null)
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setError('Recording is not supported in this browser.')
      return
    }

    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      })
      stream.current = mediaStream
      chunks.current = []

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : MediaRecorder.isTypeSupported('audio/ogg')
        ? 'audio/ogg'
        : ''

      const options = mimeType ? { mimeType } : undefined
      const next = new MediaRecorder(mediaStream, options)

      next.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          chunks.current.push(e.data)
        }
      }

      next.onerror = () => {
        setError('The recording stopped unexpectedly.')
      }

      next.onstop = () => {
        const finalBlob = new Blob(chunks.current, {
          type: next.mimeType || 'audio/webm',
        })
        setAudioBlob(finalBlob)
        stream.current?.getTracks().forEach((t) => t.stop())
        stream.current = null
      }

      recorder.current = next
      startedAt.current = Date.now()
      pauseStartedAt.current = 0
      totalPausedMs.current = 0
      setDuration(0)
      setAudioBlob(null)

      // Request data in chunks every 1000ms so no audio is lost
      next.start(1000)
      setIsRecording(true)
      setIsPaused(false)
    } catch {
      setError('Microphone permission was denied or unavailable.')
    }
  }, [])

  const pauseRecording = useCallback(() => {
    if (recorder.current?.state === 'recording') {
      recorder.current.pause()
      pauseStartedAt.current = Date.now()
      setIsPaused(true)
    }
  }, [])

  const resumeRecording = useCallback(() => {
    if (recorder.current?.state === 'paused') {
      recorder.current.resume()
      if (pauseStartedAt.current > 0) {
        totalPausedMs.current += Date.now() - pauseStartedAt.current
        pauseStartedAt.current = 0
      }
      setIsPaused(false)
    }
  }, [])

  const stopRecording = useCallback(() => {
    if (recorder.current && recorder.current.state !== 'inactive') {
      recorder.current.stop()
      setIsRecording(false)
      setIsPaused(false)
    }
  }, [])

  const resetRecording = useCallback(() => {
    if (recorder.current && recorder.current.state !== 'inactive') {
      recorder.current.stop()
    }
    stream.current?.getTracks().forEach((t) => t.stop())
    recorder.current = null
    stream.current = null
    chunks.current = []
    setAudioBlob(null)
    setDuration(0)
    setError(null)
    setIsRecording(false)
    setIsPaused(false)
    startedAt.current = 0
    pauseStartedAt.current = 0
    totalPausedMs.current = 0
  }, [])

  return {
    isRecording,
    isPaused,
    duration,
    audioBlob,
    error,
    startRecording,
    pauseRecording,
    resumeRecording,
    stopRecording,
    resetRecording,
  }
}
