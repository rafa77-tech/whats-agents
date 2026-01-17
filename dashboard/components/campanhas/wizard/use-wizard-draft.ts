/**
 * Wizard Draft State Hook - Sprint 34 E05
 *
 * Persists wizard progress to localStorage with recovery.
 */

import { useEffect, useState, useCallback } from 'react'
import { type CampanhaFormData } from './types'

const DRAFT_KEY = 'campanha-wizard-draft'
const DRAFT_EXPIRY_MS = 24 * 60 * 60 * 1000 // 24 hours

interface DraftState {
  formData: CampanhaFormData
  step: number
  savedAt: number
}

interface UseWizardDraftReturn {
  hasDraft: boolean
  draftStep: number
  loadDraft: () => { formData: CampanhaFormData; step: number } | null
  saveDraft: (formData: CampanhaFormData, step: number) => void
  clearDraft: () => void
  dismissDraft: () => void
}

export function useWizardDraft(): UseWizardDraftReturn {
  const [hasDraft, setHasDraft] = useState(false)
  const [draftStep, setDraftStep] = useState(1)
  const [dismissed, setDismissed] = useState(false)

  const getDraft = useCallback((): DraftState | null => {
    if (typeof window === 'undefined') return null

    try {
      const stored = localStorage.getItem(DRAFT_KEY)
      if (!stored) return null

      const draft: DraftState = JSON.parse(stored)

      // Check if draft has expired
      if (Date.now() - draft.savedAt > DRAFT_EXPIRY_MS) {
        localStorage.removeItem(DRAFT_KEY)
        return null
      }

      // Check if draft has meaningful data (not just defaults)
      const hasContent =
        draft.formData.nome_template.trim().length > 0 ||
        draft.formData.corpo.trim().length > 0 ||
        draft.step > 1

      if (!hasContent) {
        localStorage.removeItem(DRAFT_KEY)
        return null
      }

      return draft
    } catch {
      localStorage.removeItem(DRAFT_KEY)
      return null
    }
  }, [])

  // Check for existing draft on mount
  useEffect(() => {
    const draft = getDraft()
    if (draft && !dismissed) {
      setHasDraft(true)
      setDraftStep(draft.step)
    }
  }, [dismissed, getDraft])

  const loadDraft = useCallback((): { formData: CampanhaFormData; step: number } | null => {
    const draft = getDraft()
    if (draft) {
      setHasDraft(false)
      return { formData: draft.formData, step: draft.step }
    }
    return null
  }, [getDraft])

  const saveDraft = useCallback((formData: CampanhaFormData, step: number) => {
    if (typeof window === 'undefined') return

    // Don't save if form is empty
    const hasContent =
      formData.nome_template.trim().length > 0 ||
      formData.corpo.trim().length > 0 ||
      step > 1

    if (!hasContent) return

    try {
      const draft: DraftState = {
        formData,
        step,
        savedAt: Date.now(),
      }
      localStorage.setItem(DRAFT_KEY, JSON.stringify(draft))
    } catch {
      // Ignore storage errors (quota exceeded, etc.)
    }
  }, [])

  const clearDraft = useCallback(() => {
    if (typeof window === 'undefined') return
    localStorage.removeItem(DRAFT_KEY)
    setHasDraft(false)
  }, [])

  const dismissDraft = useCallback(() => {
    clearDraft()
    setDismissed(true)
  }, [clearDraft])

  return {
    hasDraft,
    draftStep,
    loadDraft,
    saveDraft,
    clearDraft,
    dismissDraft,
  }
}
