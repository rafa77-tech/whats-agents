/**
 * Funções de formatação e cálculo para o módulo de Integridade
 */

import {
  KPI_STATUS_COLORS,
  ANOMALY_SEVERITY_COLORS,
  ANOMALY_SEVERITY_LABELS,
  ANOMALY_SEVERITY_ORDER,
  ANOMALY_RESOLUTION_COLORS,
  ANOMALY_RESOLUTION_LABELS,
  HEALTH_SCORE_THRESHOLDS,
  CONVERSION_RATE_THRESHOLDS,
  TIME_TO_FILL_THRESHOLDS,
  PROGRESS_THRESHOLDS,
  PROGRESS_COLORS,
} from './constants'
import type { KpiStatus, AnomalySeverity, Anomaly } from './types'

/**
 * Cores padrão para status desconhecido
 */
const DEFAULT_KPI_COLORS = {
  border: 'border-gray-200',
  text: 'text-gray-600',
  bg: 'bg-gray-100',
  icon: 'text-gray-600',
}

/**
 * Cores padrão para severidade desconhecida
 */
const DEFAULT_SEVERITY_COLORS = {
  bg: 'bg-gray-50',
  text: 'text-gray-800',
  icon: 'text-gray-500',
  badge: 'bg-gray-100 text-gray-800',
}

/**
 * Retorna as cores para um status de KPI
 * @param status - Status do KPI
 * @returns Objeto com cores (border, text, bg, icon)
 */
export function getKpiStatusColors(status: KpiStatus | string) {
  if (status in KPI_STATUS_COLORS) {
    return KPI_STATUS_COLORS[status as KpiStatus]
  }
  return DEFAULT_KPI_COLORS
}

/**
 * Retorna as cores para uma severidade de anomalia
 * @param severity - Severidade da anomalia
 * @returns Objeto com cores (bg, text, icon, badge)
 */
export function getAnomalySeverityColors(severity: AnomalySeverity | string) {
  if (severity in ANOMALY_SEVERITY_COLORS) {
    return ANOMALY_SEVERITY_COLORS[severity as AnomalySeverity]
  }
  return DEFAULT_SEVERITY_COLORS
}

/**
 * Retorna o label para uma severidade de anomalia
 * @param severity - Severidade da anomalia
 * @returns Label traduzido (Alta, Media, Baixa)
 */
export function getAnomalySeverityLabel(severity: AnomalySeverity | string): string {
  if (severity in ANOMALY_SEVERITY_LABELS) {
    return ANOMALY_SEVERITY_LABELS[severity as AnomalySeverity]
  }
  return String(severity)
}

/**
 * Retorna as cores para status de resolução de anomalia
 * @param resolvida - Se a anomalia está resolvida
 * @returns Objeto com cores (bg, text, icon)
 */
export function getAnomalyResolutionColors(resolvida: boolean) {
  return resolvida ? ANOMALY_RESOLUTION_COLORS.resolvida : ANOMALY_RESOLUTION_COLORS.aberta
}

/**
 * Retorna o label para status de resolução de anomalia
 * @param resolvida - Se a anomalia está resolvida
 * @returns Label (Resolvida ou Aberta)
 */
export function getAnomalyResolutionLabel(resolvida: boolean): string {
  return resolvida ? ANOMALY_RESOLUTION_LABELS.resolvida : ANOMALY_RESOLUTION_LABELS.aberta
}

/**
 * Calcula o status do KPI baseado no Health Score
 * @param score - Health Score (0-100)
 * @returns Status (good, warn, bad)
 */
export function getHealthScoreStatus(score: number): KpiStatus {
  if (score >= HEALTH_SCORE_THRESHOLDS.GOOD) return 'good'
  if (score >= HEALTH_SCORE_THRESHOLDS.WARN) return 'warn'
  return 'bad'
}

/**
 * Calcula o status do KPI baseado na Taxa de Conversão
 * @param rate - Taxa de conversão (%)
 * @returns Status (good, warn, bad)
 */
export function getConversionRateStatus(rate: number): KpiStatus {
  if (rate >= CONVERSION_RATE_THRESHOLDS.GOOD) return 'good'
  if (rate >= CONVERSION_RATE_THRESHOLDS.WARN) return 'warn'
  return 'bad'
}

/**
 * Calcula o status do KPI baseado no Time-to-Fill (menor é melhor)
 * @param hours - Tempo em horas
 * @returns Status (good, warn, bad)
 */
export function getTimeToFillStatus(hours: number): KpiStatus {
  if (hours <= TIME_TO_FILL_THRESHOLDS.GOOD) return 'good'
  if (hours <= TIME_TO_FILL_THRESHOLDS.WARN) return 'warn'
  return 'bad'
}

/**
 * Calcula a cor da barra de progresso baseado na porcentagem
 * @param percentage - Porcentagem (0-100)
 * @returns Classe CSS de cor
 */
export function getProgressColor(percentage: number): string {
  if (percentage >= PROGRESS_THRESHOLDS.GOOD) return PROGRESS_COLORS.GOOD
  if (percentage >= PROGRESS_THRESHOLDS.WARN) return PROGRESS_COLORS.WARN
  return PROGRESS_COLORS.BAD
}

/**
 * Converte score de componente para porcentagem (menor score = melhor)
 * @param value - Valor do componente
 * @returns Porcentagem (0-100)
 */
export function convertComponentScoreToPercentage(value: number): number {
  return Math.max(0, Math.min(100, 100 - value * 10))
}

/**
 * Ordena anomalias por severidade (high primeiro)
 * @param anomalies - Array de anomalias
 * @returns Array ordenado por severidade
 */
export function sortAnomaliesBySeverity<T extends { severidade: AnomalySeverity }>(
  anomalies: T[]
): T[] {
  return [...anomalies].sort((a, b) => {
    return ANOMALY_SEVERITY_ORDER[a.severidade] - ANOMALY_SEVERITY_ORDER[b.severidade]
  })
}

/**
 * Conta anomalias por severidade
 * @param anomalies - Array de anomalias
 * @returns Objeto com contagem por severidade
 */
export function countAnomaliesBySeverity(anomalies: Anomaly[]): Record<AnomalySeverity, number> {
  return {
    high: anomalies.filter((a) => a.severidade === 'high').length,
    medium: anomalies.filter((a) => a.severidade === 'medium').length,
    low: anomalies.filter((a) => a.severidade === 'low').length,
  }
}

/**
 * Filtra anomalias abertas
 * @param anomalies - Array de anomalias
 * @returns Anomalias não resolvidas
 */
export function filterOpenAnomalies<T extends { resolvida: boolean }>(anomalies: T[]): T[] {
  return anomalies.filter((a) => !a.resolvida)
}

/**
 * Filtra anomalias resolvidas
 * @param anomalies - Array de anomalias
 * @returns Anomalias resolvidas
 */
export function filterResolvedAnomalies<T extends { resolvida: boolean }>(anomalies: T[]): T[] {
  return anomalies.filter((a) => a.resolvida)
}

/**
 * Formata data para exibição em português
 * @param dateString - String de data ISO
 * @returns Data formatada (ex: "01/02/2026")
 */
export function formatDateBR(dateString: string): string {
  return new Date(dateString).toLocaleDateString('pt-BR')
}

/**
 * Formata data e hora para exibição em português
 * @param dateString - String de data ISO
 * @returns Data e hora formatada (ex: "01/02/2026 14:30")
 */
export function formatDateTimeBR(dateString: string): string {
  return new Date(dateString).toLocaleString('pt-BR')
}

/**
 * Gera notas completas para resolução de anomalia
 * @param tipo - Tipo de resolução (corrigido ou falso_positivo)
 * @param notas - Notas adicionais
 * @returns Notas formatadas
 */
export function formatResolutionNotes(
  tipo: 'corrigido' | 'falso_positivo',
  notas: string
): string {
  const prefix = tipo === 'falso_positivo' ? '[Falso Positivo]' : '[Corrigido]'
  return `${prefix} ${notas}`
}

/**
 * Trunca ID de anomalia para exibição
 * @param id - ID completo
 * @param length - Comprimento desejado (padrão: 8)
 * @returns ID truncado
 */
export function truncateAnomalyId(id: string, length: number = 8): string {
  return id.slice(0, length)
}
