/**
 * Tipos centralizados para o módulo de Group Entry
 */

/**
 * Status possíveis de um link de grupo
 */
export type LinkStatus = 'pending' | 'validated' | 'scheduled' | 'processed' | 'failed'

/**
 * Status possíveis de um item na fila
 */
export type QueueItemStatus = 'queued' | 'processing'

/**
 * Link de grupo WhatsApp
 */
export interface GroupLink {
  id: string
  url: string
  status: LinkStatus
  categoria: string | null
  criado_em: string
}

/**
 * Item na fila de processamento
 */
export interface QueueItem {
  id: string
  link_url: string
  chip_name: string
  scheduled_at: string
  status: QueueItemStatus
}

/**
 * Métricas de links
 */
export interface LinkMetrics {
  total: number
  pending: number
  validated: number
  scheduled: number
  processed: number
}

/**
 * Métricas da fila
 */
export interface QueueMetrics {
  queued: number
  processing: number
}

/**
 * Métricas de processamento do dia
 */
export interface ProcessedTodayMetrics {
  success: number
  failed: number
}

/**
 * Métricas de capacidade
 */
export interface CapacityMetrics {
  used: number
  total: number
}

/**
 * Dashboard consolidado de Group Entry
 */
export interface GroupEntryDashboard {
  links: LinkMetrics
  queue: QueueMetrics
  processedToday: ProcessedTodayMetrics
  capacity: CapacityMetrics
}

/**
 * Configuração do Group Entry
 */
export interface GroupEntryConfig {
  grupos_por_dia: number
  intervalo_min: number
  intervalo_max: number
  horario_inicio: string
  horario_fim: string
  dias_ativos: string[]
  auto_validar: boolean
  auto_agendar: boolean
  notificar_falhas: boolean
}

/**
 * Configuração do Group Entry (formato camelCase para UI)
 */
export interface GroupEntryConfigUI {
  gruposPorDia: number
  intervaloMin: number
  intervaloMax: number
  horarioInicio: string
  horarioFim: string
  diasAtivos: string[]
  autoValidar: boolean
  autoAgendar: boolean
  notificarFalhas: boolean
}

/**
 * Filtros para busca de links
 */
export interface LinkFilters {
  status?: string
  search?: string
  limit?: number
}

/**
 * Resultado de importação de CSV
 */
export interface ImportResult {
  total: number
  valid: number
  duplicates: number
  invalid: number
  errors: ImportError[]
}

/**
 * Erro de importação
 */
export interface ImportError {
  line: number
  error: string
}

/**
 * Resposta da API de links
 */
export interface LinksResponse {
  links: GroupLink[]
  total?: number
}

/**
 * Resposta da API de fila
 */
export interface QueueResponse {
  queue: QueueItem[]
}

/**
 * Dia da semana
 */
export interface DiaSemana {
  key: string
  label: string
}
