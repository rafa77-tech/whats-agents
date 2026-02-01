/**
 * Tipos para o módulo de Integridade
 */

/**
 * Status de KPI (bom/alerta/ruim)
 */
export type KpiStatus = 'good' | 'warn' | 'bad'

/**
 * Severidade de anomalia
 */
export type AnomalySeverity = 'low' | 'medium' | 'high'

/**
 * Status de resolução de anomalia
 */
export type AnomalyResolutionStatus = 'aberta' | 'resolvida'

/**
 * Tipo de resolução de anomalia
 */
export type AnomalyResolutionType = 'corrigido' | 'falso_positivo'

/**
 * Anomalia detectada no sistema
 */
export interface Anomaly {
  id: string
  tipo: string
  entidade: string
  entidadeId: string
  severidade: AnomalySeverity
  mensagem: string
  criadaEm: string
  resolvida: boolean
}

/**
 * Scores dos componentes do Health Score
 */
export interface ComponentScores {
  pressao: number
  friccao: number
  qualidade: number
  spam: number
}

/**
 * KPIs de integridade
 */
export interface IntegridadeKpis {
  healthScore: number
  conversionRate: number
  timeToFill: number
  componentScores: ComponentScores
  recommendations: string[]
}

/**
 * Resumo de anomalias
 */
export interface AnomaliasSummary {
  abertas: number
  resolvidas: number
  total: number
}

/**
 * Dados completos de integridade
 */
export interface IntegridadeData {
  kpis: IntegridadeKpis
  anomalias: AnomaliasSummary
  violacoes: number
  ultimaAuditoria: string | null
  anomaliasList: Anomaly[]
}

/**
 * Componente de Health Score para exibição
 */
export interface HealthScoreComponent {
  label: string
  key: keyof ComponentScores
}
