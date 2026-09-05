import { useCallback, useState } from 'react'
import { clinicalService, safetyService, transcriptionService } from '../services/domainServices'
import type { TranscriptSegment } from '../types/consultation'

export type ProcessingStep =
  | 'idle'
  | 'uploading'
  | 'transcribing'
  | 'extracting'
  | 'generating'
  | 'safety_check'
  | 'review'
  | 'error'

export function useConsultationProcessing(
  id: string | number,
  onTranscript: (segments: TranscriptSegment[]) => void,
  onStatus: (status: 'processing' | 'review' | 'error') => void,
  onComplete?: () => void
) {
  const [step, setStep] = useState<ProcessingStep>('idle')
  const [error, setError] = useState<string | null>(null)

  const process = useCallback(
    async (fileOrBlob: Blob | File) => {
      setError(null)
      onStatus('processing')
      try {
        setStep('uploading')
        await transcriptionService.uploadConsultationAudio(id, fileOrBlob)

        setStep('transcribing')
        const transcript = await transcriptionService.transcribeConsultation(id)
        onTranscript(transcript)

        setStep('extracting')
        await clinicalService.getClinicalEntities(id).catch(() => clinicalService.extractClinicalEntities(id))

        setStep('generating')
        await clinicalService.getSOAPNote(id).catch(() => clinicalService.generateSOAPNote(id))

        setStep('safety_check')
        await safetyService.getSafetySummary(id).catch(() => safetyService.validateConsultation(id))

        setStep('review')
        onStatus('review')
        if (onComplete) {
          onComplete()
        }
      } catch (cause) {
        setStep('error')
        onStatus('error')
        const message = cause instanceof Error ? cause.message : 'Processing failed'
        setError(message)
      }
    },
    [id, onStatus, onTranscript, onComplete]
  )

  return {
    step,
    error,
    process,
    retry: () => setStep('idle'),
  }
}
