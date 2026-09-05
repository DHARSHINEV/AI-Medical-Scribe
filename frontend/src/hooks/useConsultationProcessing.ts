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

export const STAGE_LABELS: Record<ProcessingStep, string> = {
  idle: 'Ready to process',
  uploading: 'Uploading Audio...',
  transcribing: 'Transcribing Audio...',
  extracting: 'Extracting Clinical Information...',
  generating: 'Generating SOAP Note...',
  safety_check: 'Running Clinical Second Look...',
  review: 'Ready for Review',
  error: 'Processing Error',
}

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
        await clinicalService.getClinicalEntities(id).then(async (entities) => {
          if (!entities || entities.length === 0) {
            await clinicalService.extractClinicalEntities(id)
          }
        }).catch(async () => {
          await clinicalService.extractClinicalEntities(id)
        })

        setStep('generating')
        await clinicalService.getSOAPNote(id).catch(async () => {
          await clinicalService.generateSOAPNote(id)
        })

        setStep('safety_check')
        await safetyService.getSafetySummary(id).then(async (summary) => {
          if (!summary || summary.alert_count === 0) {
            await safetyService.validateConsultation(id).catch(() => {})
          }
        }).catch(async () => {
          await safetyService.validateConsultation(id).catch(() => {})
        })

        setStep('review')
        onStatus('review')
        if (onComplete) {
          await onComplete()
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

  const retry = useCallback(() => {
    setStep('idle')
    setError(null)
  }, [])

  return {
    step,
    stageLabel: STAGE_LABELS[step],
    error,
    process,
    retry,
  }
}

