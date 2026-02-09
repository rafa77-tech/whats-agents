/**
 * API client para o sistema de extraction/insights.
 *
 * Sprint 54: Insights Dashboard & Relatório Julia.
 */

import { api } from './client'

// Types
export interface CampaignReportMetrics {
  total_respostas: number
  interesse_positivo: number
  interesse_negativo: number
  interesse_neutro: number
  interesse_incerto: number
  taxa_interesse_pct: number
  interesse_score_medio: number
  total_objecoes: number
  objecao_mais_comum: string | null
  prontos_para_vagas: number
  para_followup: number
  para_escalar: number
}

export interface MedicoDestaque {
  cliente_id: string
  nome: string
  interesse: string
  interesse_score: number
  proximo_passo: string
  insight: string | null
  especialidade: string | null
}

export interface ObjecaoAgregada {
  tipo: string
  quantidade: number
  exemplo: string | null
}

export interface CampaignReport {
  campaign_id: number
  campaign_name: string
  generated_at: string
  metrics: CampaignReportMetrics
  medicos_destaque: MedicoDestaque[]
  objecoes_encontradas: ObjecaoAgregada[]
  preferencias_comuns: string[]
  relatorio_julia: string
  tokens_usados: number
  cached: boolean
}

// API Functions
export async function fetchCampaignReport(
  campaignId: number,
  forceRefresh = false
): Promise<CampaignReport> {
  const params = forceRefresh ? '?force_refresh=true' : ''
  return api.get<CampaignReport>(`/extraction/campaign/${campaignId}/report${params}`)
}

// Labels de tradução
export const interesseLabels: Record<string, string> = {
  positivo: 'Positivo',
  negativo: 'Negativo',
  neutro: 'Neutro',
  incerto: 'Incerto',
}

export const proximoPassoLabels: Record<string, string> = {
  enviar_vagas: 'Enviar Vagas',
  agendar_followup: 'Agendar Follow-up',
  aguardar_resposta: 'Aguardar Resposta',
  escalar_humano: 'Escalar para Humano',
  marcar_inativo: 'Marcar Inativo',
  sem_acao: 'Sem Ação',
}

export const objecaoLabels: Record<string, string> = {
  preco: 'Preço',
  tempo: 'Tempo',
  confianca: 'Confiança',
  distancia: 'Distância',
  disponibilidade: 'Disponibilidade',
  empresa_atual: 'Empresa Atual',
  pessoal: 'Pessoal',
  outro: 'Outro',
}

// Types para Oportunidades
export interface Opportunity {
  id: number
  cliente_id: string
  conversation_id: string
  campaign_id: number | null
  interesse: string
  interesse_score: number
  proximo_passo: string
  especialidade_mencionada: string | null
  disponibilidade_mencionada: string | null
  preferencias: string[]
  objecao_tipo: string | null
  objecao_descricao: string | null
  confianca: number
  created_at: string
  cliente_nome: string
  cliente_especialidade: string | null
  cliente_telefone: string | null
  campanha_nome: string | null
}

export interface OpportunitiesResponse {
  enviar_vagas: Opportunity[]
  agendar_followup: Opportunity[]
  escalar_humano: Opportunity[]
  total: number
}

export async function fetchOpportunities(
  limit = 50,
  proximoPasso?: string
): Promise<OpportunitiesResponse> {
  const params = new URLSearchParams()
  params.set('limit', String(limit))
  if (proximoPasso) {
    params.set('proximo_passo', proximoPasso)
  }
  return api.get<OpportunitiesResponse>(`/extraction/opportunities?${params}`)
}
