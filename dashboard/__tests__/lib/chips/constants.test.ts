/**
 * Testes para lib/chips/constants
 */

import { describe, it, expect } from 'vitest'
import {
  CHIP_STATUS_LABELS,
  CHIP_STATUS_COLORS,
  TRUST_LEVEL_LABELS,
  TRUST_LEVEL_COLORS,
  WARMUP_PHASE_LABELS,
  WARMUP_PHASE_ORDER,
  ALERT_SEVERITY_LABELS,
  ALERT_SEVERITY_COLORS,
  ALERT_TYPE_LABELS,
  DEFAULT_PAGE_SIZE,
  PAGE_SIZE_OPTIONS,
  DEFAULT_FILTERS,
} from '@/lib/chips/constants'

describe('Chips Constants', () => {
  describe('CHIP_STATUS_LABELS', () => {
    it('deve ter labels para todos os status', () => {
      expect(CHIP_STATUS_LABELS.active).toBe('Ativo')
      expect(CHIP_STATUS_LABELS.warming).toBe('Aquecendo')
      expect(CHIP_STATUS_LABELS.banned).toBe('Banido')
      expect(CHIP_STATUS_LABELS.ready).toBe('Pronto')
      expect(CHIP_STATUS_LABELS.degraded).toBe('Degradado')
      expect(CHIP_STATUS_LABELS.paused).toBe('Pausado')
      expect(CHIP_STATUS_LABELS.offline).toBe('Offline')
    })
  })

  describe('CHIP_STATUS_COLORS', () => {
    it('deve ter cores para todos os status', () => {
      expect(CHIP_STATUS_COLORS.active).toContain('emerald')
      expect(CHIP_STATUS_COLORS.warming).toContain('yellow')
      expect(CHIP_STATUS_COLORS.banned).toContain('red')
      expect(CHIP_STATUS_COLORS.ready).toContain('green')
    })
  })

  describe('TRUST_LEVEL_LABELS', () => {
    it('deve ter labels para todos os niveis', () => {
      expect(TRUST_LEVEL_LABELS.verde).toBe('Verde')
      expect(TRUST_LEVEL_LABELS.amarelo).toBe('Amarelo')
      expect(TRUST_LEVEL_LABELS.laranja).toBe('Laranja')
      expect(TRUST_LEVEL_LABELS.vermelho).toBe('Vermelho')
      expect(TRUST_LEVEL_LABELS.critico).toBe('Critico')
    })
  })

  describe('TRUST_LEVEL_COLORS', () => {
    it('deve ter cores para todos os niveis', () => {
      expect(TRUST_LEVEL_COLORS.verde).toContain('green')
      expect(TRUST_LEVEL_COLORS.amarelo).toContain('yellow')
      expect(TRUST_LEVEL_COLORS.laranja).toContain('orange')
      expect(TRUST_LEVEL_COLORS.vermelho).toContain('red')
      expect(TRUST_LEVEL_COLORS.critico).toContain('red')
    })
  })

  describe('WARMUP_PHASE_LABELS', () => {
    it('deve ter labels para todas as fases', () => {
      expect(WARMUP_PHASE_LABELS.repouso).toBe('Repouso')
      expect(WARMUP_PHASE_LABELS.setup).toBe('Setup')
      expect(WARMUP_PHASE_LABELS.operacao).toBe('Operacao')
    })
  })

  describe('WARMUP_PHASE_ORDER', () => {
    it('deve ter 7 fases na ordem correta', () => {
      expect(WARMUP_PHASE_ORDER).toHaveLength(7)
      expect(WARMUP_PHASE_ORDER[0]).toBe('repouso')
      expect(WARMUP_PHASE_ORDER[6]).toBe('operacao')
    })
  })

  describe('ALERT_SEVERITY_LABELS', () => {
    it('deve ter labels para todas as severidades', () => {
      expect(ALERT_SEVERITY_LABELS.critico).toBe('Critico')
      expect(ALERT_SEVERITY_LABELS.alerta).toBe('Alerta')
      expect(ALERT_SEVERITY_LABELS.atencao).toBe('Atencao')
      expect(ALERT_SEVERITY_LABELS.info).toBe('Info')
    })
  })

  describe('ALERT_SEVERITY_COLORS', () => {
    it('deve ter cores para todas as severidades', () => {
      expect(ALERT_SEVERITY_COLORS.critico).toContain('red')
      expect(ALERT_SEVERITY_COLORS.alerta).toContain('orange')
      expect(ALERT_SEVERITY_COLORS.atencao).toContain('yellow')
      expect(ALERT_SEVERITY_COLORS.info).toContain('blue')
    })
  })

  describe('ALERT_TYPE_LABELS', () => {
    it('deve ter labels para todos os tipos', () => {
      expect(ALERT_TYPE_LABELS.TRUST_CAINDO).toBe('Trust Caindo')
      expect(ALERT_TYPE_LABELS.DESCONEXAO).toBe('Desconexao')
      expect(ALERT_TYPE_LABELS.ERROS_FREQUENTES).toBe('Erros Frequentes')
    })
  })

  describe('Pagination Constants', () => {
    it('deve ter DEFAULT_PAGE_SIZE = 20', () => {
      expect(DEFAULT_PAGE_SIZE).toBe(20)
    })

    it('deve ter opcoes de tamanho de pagina', () => {
      expect(PAGE_SIZE_OPTIONS).toContain(10)
      expect(PAGE_SIZE_OPTIONS).toContain(20)
      expect(PAGE_SIZE_OPTIONS).toContain(50)
      expect(PAGE_SIZE_OPTIONS).toContain(100)
    })
  })

  describe('DEFAULT_FILTERS', () => {
    it('deve ter valores padrao corretos', () => {
      expect(DEFAULT_FILTERS.search).toBe('')
      expect(DEFAULT_FILTERS.status).toBeNull()
      expect(DEFAULT_FILTERS.trustLevel).toBeNull()
      expect(DEFAULT_FILTERS.sortBy).toBe('trust')
      expect(DEFAULT_FILTERS.order).toBe('desc')
    })
  })
})
