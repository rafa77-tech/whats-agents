/**
 * Testes para lib/dashboard/constants
 */

import { describe, it, expect } from 'vitest'
import {
  DASHBOARD_PERIODS,
  PERIOD_LABELS,
  DEFAULT_OPERATIONAL_STATUS,
  DEFAULT_FUNNEL,
  DEFAULT_TRENDS,
  DEFAULT_ALERTS,
  DEFAULT_ACTIVITY,
  METRIC_CONFIG,
  QUALITY_CONFIG,
  JULIA_STATUS_COLORS,
  ALERT_SEVERITY_COLORS,
} from '@/lib/dashboard/constants'

describe('Dashboard Constants', () => {
  describe('DASHBOARD_PERIODS', () => {
    it('deve conter todos os periodos validos', () => {
      expect(DASHBOARD_PERIODS).toContain('24h')
      expect(DASHBOARD_PERIODS).toContain('7d')
      expect(DASHBOARD_PERIODS).toContain('14d')
      expect(DASHBOARD_PERIODS).toContain('30d')
      expect(DASHBOARD_PERIODS).toHaveLength(4)
    })
  })

  describe('PERIOD_LABELS', () => {
    it('deve ter labels para todos os periodos', () => {
      expect(PERIOD_LABELS['24h']).toBe('24 horas')
      expect(PERIOD_LABELS['7d']).toBe('7 dias')
      expect(PERIOD_LABELS['14d']).toBe('14 dias')
      expect(PERIOD_LABELS['30d']).toBe('30 dias')
    })
  })

  describe('DEFAULT_OPERATIONAL_STATUS', () => {
    it('deve ter rate limits configurados', () => {
      expect(DEFAULT_OPERATIONAL_STATUS.rateLimitHour.max).toBe(20)
      expect(DEFAULT_OPERATIONAL_STATUS.rateLimitDay.max).toBe(100)
    })

    it('deve ter LLM usage configurado', () => {
      expect(DEFAULT_OPERATIONAL_STATUS.llmUsage.haiku).toBe(80)
      expect(DEFAULT_OPERATIONAL_STATUS.llmUsage.sonnet).toBe(20)
    })
  })

  describe('DEFAULT_FUNNEL', () => {
    it('deve ter 5 estagios', () => {
      expect(DEFAULT_FUNNEL.stages).toHaveLength(5)
    })

    it('deve ter estagios na ordem correta', () => {
      expect(DEFAULT_FUNNEL.stages[0]?.id).toBe('enviadas')
      expect(DEFAULT_FUNNEL.stages[4]?.id).toBe('fechadas')
    })
  })

  describe('DEFAULT_TRENDS', () => {
    it('deve ter metrics vazio', () => {
      expect(DEFAULT_TRENDS.metrics).toHaveLength(0)
    })
  })

  describe('DEFAULT_ALERTS', () => {
    it('deve ter contadores zerados', () => {
      expect(DEFAULT_ALERTS.alerts).toHaveLength(0)
      expect(DEFAULT_ALERTS.totalCritical).toBe(0)
      expect(DEFAULT_ALERTS.totalWarning).toBe(0)
    })
  })

  describe('DEFAULT_ACTIVITY', () => {
    it('deve ter events vazio', () => {
      expect(DEFAULT_ACTIVITY.events).toHaveLength(0)
      expect(DEFAULT_ACTIVITY.hasMore).toBe(false)
    })
  })

  describe('METRIC_CONFIG', () => {
    it('deve ter configuracao para responseRate', () => {
      expect(METRIC_CONFIG.responseRate.label).toBe('Taxa de Resposta')
      expect(METRIC_CONFIG.responseRate.unit).toBe('percent')
    })

    it('deve ter configuracao para conversionRate', () => {
      expect(METRIC_CONFIG.conversionRate.label).toBe('Taxa de Conversão')
    })

    it('deve ter configuracao para closingsPerWeek', () => {
      expect(METRIC_CONFIG.closingsPerWeek.unit).toBe('number')
    })
  })

  describe('QUALITY_CONFIG', () => {
    it('deve ter configuracao para botDetection', () => {
      expect(QUALITY_CONFIG.botDetection.threshold.good).toBe(1)
      expect(QUALITY_CONFIG.botDetection.operator).toBe('lt')
    })

    it('deve ter configuracao para avgLatency', () => {
      expect(QUALITY_CONFIG.avgLatency.unit).toBe('seconds')
      expect(QUALITY_CONFIG.avgLatency.threshold.good).toBe(30)
    })

    it('deve ter configuracao para handoffRate', () => {
      expect(QUALITY_CONFIG.handoffRate.tooltip).toBeDefined()
    })
  })

  describe('JULIA_STATUS_COLORS', () => {
    it('deve ter cores semanticas para todos os status', () => {
      expect(JULIA_STATUS_COLORS.online).toContain('status-success')
      expect(JULIA_STATUS_COLORS.offline).toContain('status-error')
      expect(JULIA_STATUS_COLORS.degraded).toContain('status-warning')
    })
  })

  describe('ALERT_SEVERITY_COLORS', () => {
    it('deve ter cores semanticas para todas as severidades', () => {
      expect(ALERT_SEVERITY_COLORS.critical).toContain('status-error')
      expect(ALERT_SEVERITY_COLORS.warning).toContain('status-warning')
      expect(ALERT_SEVERITY_COLORS.info).toContain('status-info')
    })
  })
})
