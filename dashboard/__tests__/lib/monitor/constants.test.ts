/**
 * Testes para lib/monitor/constants
 */

import { describe, it, expect } from 'vitest'
import {
  JOB_STATUS_LABELS,
  JOB_STATUS_COLORS,
  SYSTEM_HEALTH_LABELS,
  SYSTEM_HEALTH_COLORS,
  JOB_CATEGORY_LABELS,
  STATUS_FILTER_OPTIONS,
  TIME_RANGE_OPTIONS,
  CATEGORY_FILTER_OPTIONS,
  DEFAULT_FILTERS,
  DEFAULT_TABLE_SORT,
} from '@/lib/monitor/constants'

describe('Monitor Constants', () => {
  describe('JOB_STATUS_LABELS', () => {
    it('deve ter labels para todos os status', () => {
      expect(JOB_STATUS_LABELS.running).toBe('Executando')
      expect(JOB_STATUS_LABELS.success).toBe('Sucesso')
      expect(JOB_STATUS_LABELS.error).toBe('Erro')
      expect(JOB_STATUS_LABELS.timeout).toBe('Timeout')
    })
  })

  describe('JOB_STATUS_COLORS', () => {
    it('deve ter cores para todos os status', () => {
      expect(JOB_STATUS_COLORS.running).toContain('blue')
      expect(JOB_STATUS_COLORS.success).toContain('green')
      expect(JOB_STATUS_COLORS.error).toContain('red')
      expect(JOB_STATUS_COLORS.timeout).toContain('yellow')
    })
  })

  describe('SYSTEM_HEALTH_LABELS', () => {
    it('deve ter labels para todos os status de saude', () => {
      expect(SYSTEM_HEALTH_LABELS.healthy).toBe('Saudavel')
      expect(SYSTEM_HEALTH_LABELS.degraded).toBe('Degradado')
      expect(SYSTEM_HEALTH_LABELS.critical).toBe('Critico')
    })
  })

  describe('SYSTEM_HEALTH_COLORS', () => {
    it('deve ter cores para todos os status', () => {
      expect(SYSTEM_HEALTH_COLORS.healthy).toContain('green')
      expect(SYSTEM_HEALTH_COLORS.degraded).toContain('yellow')
      expect(SYSTEM_HEALTH_COLORS.critical).toContain('red')
    })
  })

  describe('JOB_CATEGORY_LABELS', () => {
    it('deve ter labels para todas as categorias', () => {
      expect(JOB_CATEGORY_LABELS.critical).toBe('Critico')
      expect(JOB_CATEGORY_LABELS.frequent).toBe('Frequente')
      expect(JOB_CATEGORY_LABELS.hourly).toBe('Horario')
      expect(JOB_CATEGORY_LABELS.daily).toBe('Diario')
      expect(JOB_CATEGORY_LABELS.weekly).toBe('Semanal')
    })
  })

  describe('STATUS_FILTER_OPTIONS', () => {
    it('deve incluir todas as opcoes de filtro', () => {
      const values = STATUS_FILTER_OPTIONS.map((o) => o.value)
      expect(values).toContain('all')
      expect(values).toContain('running')
      expect(values).toContain('success')
      expect(values).toContain('error')
      expect(values).toContain('stale')
    })
  })

  describe('TIME_RANGE_OPTIONS', () => {
    it('deve incluir todas as opcoes de periodo', () => {
      const values = TIME_RANGE_OPTIONS.map((o) => o.value)
      expect(values).toContain('1h')
      expect(values).toContain('6h')
      expect(values).toContain('24h')
    })
  })

  describe('CATEGORY_FILTER_OPTIONS', () => {
    it('deve incluir todas as categorias mais all', () => {
      const values = CATEGORY_FILTER_OPTIONS.map((o) => o.value)
      expect(values).toContain('all')
      expect(values).toContain('critical')
      expect(values).toContain('daily')
    })
  })

  describe('DEFAULT_FILTERS', () => {
    it('deve ter valores padrao corretos', () => {
      expect(DEFAULT_FILTERS.status).toBe('all')
      expect(DEFAULT_FILTERS.timeRange).toBe('24h')
      expect(DEFAULT_FILTERS.search).toBe('')
      expect(DEFAULT_FILTERS.category).toBe('all')
    })
  })

  describe('DEFAULT_TABLE_SORT', () => {
    it('deve ordenar por lastRun desc por padrao', () => {
      expect(DEFAULT_TABLE_SORT.column).toBe('lastRun')
      expect(DEFAULT_TABLE_SORT.direction).toBe('desc')
    })
  })
})
