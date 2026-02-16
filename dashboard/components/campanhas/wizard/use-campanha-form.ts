/**
 * Campanha Form Hook - Sprint 34 E03/E05
 *
 * Manages form state with draft persistence.
 * Sprint 58: Added initialData support for vagas→campanhas flow.
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import { type CampanhaFormData, INITIAL_FORM_DATA } from './types'
import { validateStep } from './schema'
import { useWizardDraft } from './use-wizard-draft'
import type { WizardInitialData } from '@/lib/vagas/campaign-helpers'

interface UseCampanhaFormOptions {
  initialData?: WizardInitialData | null
}

export function useCampanhaForm(options?: UseCampanhaFormOptions) {
  const { initialData } = options ?? {}

  // When initialData is provided, merge it with defaults
  const startingData: CampanhaFormData = initialData
    ? {
        ...INITIAL_FORM_DATA,
        nome_template: initialData.nome_template,
        tipo_campanha: initialData.tipo_campanha,
        categoria: initialData.categoria,
        corpo: initialData.corpo,
        escopo_vagas: initialData.escopo_vagas,
      }
    : INITIAL_FORM_DATA

  const [step, setStep] = useState(1)
  const [formData, setFormData] = useState<CampanhaFormData>(startingData)
  const [loading, setLoading] = useState(false)
  const isInitialized = useRef(false)

  const { hasDraft, draftStep, loadDraft, saveDraft, clearDraft, dismissDraft } = useWizardDraft()

  // Ignore draft when initialData is present
  const effectiveHasDraft = initialData ? false : hasDraft

  // Auto-save draft when formData or step changes (debounced)
  // Skip draft saving when using initialData (to avoid overwriting the draft with vaga-specific data)
  useEffect(() => {
    if (initialData) return

    // Skip initial render to avoid saving empty state
    if (!isInitialized.current) {
      isInitialized.current = true
      return
    }

    const timer = setTimeout(() => {
      saveDraft(formData, step)
    }, 500)

    return () => clearTimeout(timer)
  }, [formData, step, saveDraft, initialData])

  const updateField = useCallback(
    <K extends keyof CampanhaFormData>(field: K, value: CampanhaFormData[K]) => {
      setFormData((prev) => ({ ...prev, [field]: value }))
    },
    []
  )

  const toggleArrayItem = useCallback(
    (field: 'especialidades' | 'regioes' | 'status_cliente' | 'chips_excluidos', item: string) => {
      setFormData((prev) => {
        const array = prev[field]
        if (array.includes(item)) {
          return { ...prev, [field]: array.filter((i) => i !== item) }
        }
        return { ...prev, [field]: [...array, item] }
      })
    },
    []
  )

  const canProceed = useCallback(() => {
    return validateStep(step, formData)
  }, [step, formData])

  const nextStep = useCallback(() => {
    if (canProceed() && step < 4) {
      setStep((s) => s + 1)
    }
  }, [canProceed, step])

  const prevStep = useCallback(() => {
    if (step > 1) {
      setStep((s) => s - 1)
    }
  }, [step])

  const reset = useCallback(() => {
    setStep(1)
    setFormData(INITIAL_FORM_DATA)
    setLoading(false)
    clearDraft()
  }, [clearDraft])

  const restoreFromDraft = useCallback(() => {
    const draft = loadDraft()
    if (draft) {
      setFormData(draft.formData)
      setStep(draft.step)
    }
  }, [loadDraft])

  const buildPayload = useCallback(() => {
    // Chips excluídos vão sempre no payload (mesmo se audiência for 'todos')
    const chipsExcluidos =
      formData.chips_excluidos.length > 0 ? formData.chips_excluidos : undefined

    return {
      nome_template: formData.nome_template,
      tipo_campanha: formData.tipo_campanha,
      categoria: formData.categoria,
      objetivo: formData.objetivo || null,
      corpo: formData.corpo,
      tom: formData.tom,
      quantidade_alvo: formData.quantidade_alvo,
      modo_selecao: formData.modo_selecao,
      audience_filters:
        formData.audiencia_tipo === 'filtrado'
          ? {
              especialidades: formData.especialidades,
              regioes: formData.regioes,
              status_cliente: formData.status_cliente,
              chips_excluidos: chipsExcluidos,
              quantidade_alvo: formData.quantidade_alvo,
              modo_selecao: formData.modo_selecao,
            }
          : {
              chips_excluidos: chipsExcluidos,
              quantidade_alvo: formData.quantidade_alvo,
              modo_selecao: formData.modo_selecao,
            },
      chips_excluidos: chipsExcluidos, // Também no nível raiz para compatibilidade
      escopo_vagas: formData.escopo_vagas,
      agendar_para:
        formData.agendar && formData.agendar_para
          ? new Date(formData.agendar_para).toISOString()
          : null,
      status: formData.agendar ? 'agendada' : 'rascunho',
    }
  }, [formData])

  return {
    step,
    setStep,
    formData,
    updateField,
    toggleArrayItem,
    canProceed,
    nextStep,
    prevStep,
    reset,
    loading,
    setLoading,
    buildPayload,
    // Draft state
    hasDraft: effectiveHasDraft,
    draftStep,
    restoreFromDraft,
    dismissDraft,
  }
}

export type UseCampanhaFormReturn = ReturnType<typeof useCampanhaForm>
