/**
 * Custom hooks para o modulo de Instrucoes (Diretrizes)
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import type {
  Diretriz,
  Hospital,
  Especialidade,
  UseInstrucoesReturn,
  UseNovaInstrucaoReturn,
  CriarDiretrizPayload,
} from './types'
import {
  API_ENDPOINTS,
  DEFAULT_STATUS_ATIVAS,
  DEFAULT_STATUS_HISTORICO,
} from './constants'
import { buildDiretrizesUrl, buildDiretrizUrl } from './formatters'

// =============================================================================
// Hook: useInstrucoes
// =============================================================================

/**
 * Hook para gerenciar lista de instrucoes (diretrizes)
 */
export function useInstrucoes(): UseInstrucoesReturn {
  const [diretrizes, setDiretrizes] = useState<Diretriz[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTabState] = useState<'ativas' | 'historico'>('ativas')

  const carregarDiretrizes = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const status = tab === 'ativas' ? DEFAULT_STATUS_ATIVAS : DEFAULT_STATUS_HISTORICO
      const url = buildDiretrizesUrl(API_ENDPOINTS.diretrizes, status)
      const response = await fetch(url)
      const data = await response.json()

      if (!response.ok) {
        setError(data.detail || 'Erro ao carregar diretrizes')
        setDiretrizes([])
        return
      }

      setDiretrizes(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Erro ao carregar diretrizes:', err)
      setError('Erro de conexao com o servidor')
      setDiretrizes([])
    } finally {
      setLoading(false)
    }
  }, [tab])

  useEffect(() => {
    carregarDiretrizes()
    return undefined
  }, [carregarDiretrizes])

  const setTab = useCallback((newTab: 'ativas' | 'historico') => {
    setTabState(newTab)
  }, [])

  const cancelar = useCallback(async (diretriz: Diretriz) => {
    const url = buildDiretrizUrl(API_ENDPOINTS.diretrizes, diretriz.id)

    const response = await fetch(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'cancelada' }),
    })

    if (!response.ok) {
      throw new Error('Erro ao cancelar diretriz')
    }

    // Recarregar lista apos cancelar
    await carregarDiretrizes()
  }, [carregarDiretrizes])

  return {
    diretrizes,
    loading,
    error,
    tab,
    actions: {
      setTab,
      refresh: carregarDiretrizes,
      cancelar,
    },
  }
}

// =============================================================================
// Hook: useNovaInstrucao
// =============================================================================

/**
 * Hook para criar nova instrucao
 */
export function useNovaInstrucao(): UseNovaInstrucaoReturn {
  const [loading, setLoading] = useState(false)
  const [hospitais, setHospitais] = useState<Hospital[]>([])
  const [especialidades, setEspecialidades] = useState<Especialidade[]>([])
  const [loadingListas, setLoadingListas] = useState(false)

  const carregarListas = useCallback(async () => {
    setLoadingListas(true)

    try {
      const [hospitaisRes, especialidadesRes] = await Promise.all([
        fetch(API_ENDPOINTS.hospitais),
        fetch(API_ENDPOINTS.especialidades),
      ])

      const [hospitaisData, especialidadesData] = await Promise.all([
        hospitaisRes.json(),
        especialidadesRes.json(),
      ])

      setHospitais(Array.isArray(hospitaisData) ? hospitaisData : [])
      setEspecialidades(Array.isArray(especialidadesData) ? especialidadesData : [])
    } catch (err) {
      console.error('Erro ao carregar listas:', err)
    } finally {
      setLoadingListas(false)
    }
  }, [])

  // Carregar listas ao montar
  useEffect(() => {
    carregarListas()
    return undefined
  }, [carregarListas])

  const criar = useCallback(async (payload: CriarDiretrizPayload): Promise<boolean> => {
    setLoading(true)

    try {
      const response = await fetch(API_ENDPOINTS.diretrizes, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        return false
      }

      return true
    } catch (err) {
      console.error('Erro ao criar diretriz:', err)
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    loading,
    hospitais,
    especialidades,
    loadingListas,
    criar,
  }
}

// =============================================================================
// Hook: useInstrucaoForm
// =============================================================================

/**
 * Estado inicial do form
 */
export interface InstrucaoFormState {
  tipo: 'margem_negociacao' | 'regra_especial' | 'info_adicional'
  escopo: 'vaga' | 'medico' | 'hospital' | 'especialidade' | 'global'
  hospitalId: string
  especialidadeId: string
  valorMaximo: string
  percentualMaximo: string
  regra: string
  info: string
  expiraEm: string
}

const INITIAL_FORM_STATE: InstrucaoFormState = {
  tipo: 'margem_negociacao',
  escopo: 'global',
  hospitalId: '',
  especialidadeId: '',
  valorMaximo: '',
  percentualMaximo: '',
  regra: '',
  info: '',
  expiraEm: '',
}

/**
 * Hook para gerenciar form de nova instrucao
 */
export function useInstrucaoForm() {
  const [form, setForm] = useState<InstrucaoFormState>(INITIAL_FORM_STATE)

  const updateField = useCallback(<K extends keyof InstrucaoFormState>(
    field: K,
    value: InstrucaoFormState[K]
  ) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }, [])

  const reset = useCallback(() => {
    setForm(INITIAL_FORM_STATE)
  }, [])

  const canSubmit = useCallback((): boolean => {
    // Validar escopo
    if (form.escopo === 'hospital' && !form.hospitalId) return false
    if (form.escopo === 'especialidade' && !form.especialidadeId) return false

    // Validar conteudo
    if (form.tipo === 'margem_negociacao' && !form.valorMaximo && !form.percentualMaximo) {
      return false
    }
    if (form.tipo === 'regra_especial' && !form.regra.trim()) return false
    if (form.tipo === 'info_adicional' && !form.info.trim()) return false

    return true
  }, [form])

  const buildPayload = useCallback((): CriarDiretrizPayload => {
    const conteudo: Record<string, unknown> = {}

    if (form.tipo === 'margem_negociacao') {
      if (form.valorMaximo) conteudo.valor_maximo = Number(form.valorMaximo)
      if (form.percentualMaximo) conteudo.percentual_maximo = Number(form.percentualMaximo)
    } else if (form.tipo === 'regra_especial') {
      conteudo.regra = form.regra
    } else if (form.tipo === 'info_adicional') {
      conteudo.info = form.info
    }

    const payload: CriarDiretrizPayload = {
      tipo: form.tipo,
      escopo: form.escopo,
      conteudo,
    }

    if (form.escopo === 'hospital' && form.hospitalId) {
      payload.hospital_id = form.hospitalId
    }
    if (form.escopo === 'especialidade' && form.especialidadeId) {
      payload.especialidade_id = form.especialidadeId
    }
    if (form.expiraEm) {
      payload.expira_em = new Date(form.expiraEm).toISOString()
    }

    return payload
  }, [form])

  return {
    form,
    updateField,
    reset,
    canSubmit,
    buildPayload,
  }
}
