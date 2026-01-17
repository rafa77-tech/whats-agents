/**
 * Campanha Form Hook - Sprint 34 E03
 */

import { useState, useCallback } from 'react'
import { type CampanhaFormData, INITIAL_FORM_DATA } from './types'
import { validateStep } from './schema'

export function useCampanhaForm() {
  const [step, setStep] = useState(1)
  const [formData, setFormData] = useState<CampanhaFormData>(INITIAL_FORM_DATA)
  const [loading, setLoading] = useState(false)

  const updateField = useCallback(
    <K extends keyof CampanhaFormData>(field: K, value: CampanhaFormData[K]) => {
      setFormData((prev) => ({ ...prev, [field]: value }))
    },
    []
  )

  const toggleArrayItem = useCallback(
    (field: 'especialidades' | 'regioes' | 'status_cliente', item: string) => {
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
  }, [])

  const buildPayload = useCallback(() => {
    return {
      nome_template: formData.nome_template,
      tipo_campanha: formData.tipo_campanha,
      categoria: formData.categoria,
      objetivo: formData.objetivo || null,
      corpo: formData.corpo,
      tom: formData.tom,
      audience_filters:
        formData.audiencia_tipo === 'filtrado'
          ? {
              especialidades: formData.especialidades,
              regioes: formData.regioes,
              status_cliente: formData.status_cliente,
            }
          : {},
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
  }
}

export type UseCampanhaFormReturn = ReturnType<typeof useCampanhaForm>
