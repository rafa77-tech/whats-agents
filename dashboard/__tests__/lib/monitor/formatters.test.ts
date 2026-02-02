/**
 * Testes para lib/monitor/formatters
 */

import { describe, it, expect } from 'vitest'
import {
  formatJobStatus,
  formatSystemHealth,
  formatDuration,
  formatDurationShort,
  formatLastRun,
  formatNextRun,
  formatSuccessRate,
  calculateSuccessRate,
  describeCron,
  formatHealthScore,
  getHealthScoreColor,
} from '@/lib/monitor/formatters'

describe('Monitor Formatters', () => {
  describe('formatJobStatus', () => {
    it('deve formatar status running', () => {
      expect(formatJobStatus('running')).toBe('Executando')
    })

    it('deve formatar status success', () => {
      expect(formatJobStatus('success')).toBe('Sucesso')
    })

    it('deve formatar status error', () => {
      expect(formatJobStatus('error')).toBe('Erro')
    })

    it('deve formatar status timeout', () => {
      expect(formatJobStatus('timeout')).toBe('Timeout')
    })
  })

  describe('formatSystemHealth', () => {
    it('deve formatar status healthy', () => {
      expect(formatSystemHealth('healthy')).toBe('Saudavel')
    })

    it('deve formatar status degraded', () => {
      expect(formatSystemHealth('degraded')).toBe('Degradado')
    })

    it('deve formatar status critical', () => {
      expect(formatSystemHealth('critical')).toBe('Critico')
    })
  })

  describe('formatDuration', () => {
    it('deve retornar — para null', () => {
      expect(formatDuration(null)).toBe('—')
    })

    it('deve formatar milissegundos', () => {
      expect(formatDuration(500)).toBe('500ms')
    })

    it('deve formatar segundos', () => {
      expect(formatDuration(5000)).toBe('5s')
    })

    it('deve formatar minutos e segundos', () => {
      expect(formatDuration(125000)).toBe('2m 5s')
    })

    it('deve formatar apenas minutos se sem segundos restantes', () => {
      expect(formatDuration(120000)).toBe('2m')
    })

    it('deve formatar horas e minutos', () => {
      expect(formatDuration(3720000)).toBe('1h 2m')
    })
  })

  describe('formatDurationShort', () => {
    it('deve formatar curto para menos de 1s', () => {
      expect(formatDurationShort(500)).toBe('<1s')
    })

    it('deve formatar segundos', () => {
      expect(formatDurationShort(5000)).toBe('5s')
    })

    it('deve formatar minutos', () => {
      expect(formatDurationShort(120000)).toBe('2m')
    })
  })

  describe('formatLastRun', () => {
    it('deve retornar Nunca para null', () => {
      expect(formatLastRun(null)).toBe('Nunca')
    })

    it('deve retornar Agora para menos de 1 minuto', () => {
      const now = new Date().toISOString()
      expect(formatLastRun(now)).toBe('Agora')
    })

    it('deve formatar minutos', () => {
      const date = new Date(Date.now() - 30 * 60 * 1000).toISOString()
      expect(formatLastRun(date)).toMatch(/\d+ min/)
    })

    it('deve formatar horas', () => {
      const date = new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString()
      expect(formatLastRun(date)).toMatch(/\d+h/)
    })
  })

  describe('formatNextRun', () => {
    it('deve retornar — para null', () => {
      expect(formatNextRun(null)).toBe('—')
    })

    it('deve retornar Agora para tempo passado', () => {
      const past = new Date(Date.now() - 60000).toISOString()
      expect(formatNextRun(past)).toBe('Agora')
    })

    it('deve formatar minutos futuros', () => {
      const future = new Date(Date.now() + 10 * 60 * 1000).toISOString()
      expect(formatNextRun(future)).toMatch(/em \d+ min/)
    })

    it('deve formatar horas futuras', () => {
      const future = new Date(Date.now() + 3 * 60 * 60 * 1000).toISOString()
      expect(formatNextRun(future)).toMatch(/em \d+h/)
    })
  })

  describe('formatSuccessRate', () => {
    it('deve retornar — para total zero', () => {
      expect(formatSuccessRate(0, 0)).toBe('—')
    })

    it('deve calcular e formatar taxa', () => {
      expect(formatSuccessRate(80, 100)).toBe('80%')
      expect(formatSuccessRate(95, 100)).toBe('95%')
    })
  })

  describe('calculateSuccessRate', () => {
    it('deve retornar 0 para total zero', () => {
      expect(calculateSuccessRate(0, 0)).toBe(0)
    })

    it('deve calcular porcentagem correta', () => {
      expect(calculateSuccessRate(80, 100)).toBe(80)
      expect(calculateSuccessRate(50, 200)).toBe(25)
    })
  })

  describe('describeCron', () => {
    it('deve descrever a cada minuto', () => {
      expect(describeCron('* * * * *')).toBe('A cada minuto')
    })

    it('deve descrever a cada N minutos', () => {
      expect(describeCron('*/5 * * * *')).toBe('A cada 5 minutos')
    })

    it('deve descrever a cada hora', () => {
      expect(describeCron('0 * * * *')).toBe('A cada hora')
    })

    it('deve descrever a cada N horas', () => {
      expect(describeCron('0 */2 * * *')).toBe('A cada 2 horas')
    })

    it('deve retornar cron original para formato desconhecido', () => {
      expect(describeCron('0 0 1 * *')).toContain('0 0 1')
    })
  })

  describe('formatHealthScore', () => {
    it('deve formatar score como porcentagem', () => {
      expect(formatHealthScore(85)).toBe('85%')
      expect(formatHealthScore(99.5)).toBe('100%')
    })
  })

  describe('getHealthScoreColor', () => {
    it('deve retornar success para score >= 80', () => {
      expect(getHealthScoreColor(80)).toContain('status-success')
      expect(getHealthScoreColor(100)).toContain('status-success')
    })

    it('deve retornar warning para score >= 50', () => {
      expect(getHealthScoreColor(50)).toContain('status-warning')
      expect(getHealthScoreColor(79)).toContain('status-warning')
    })

    it('deve retornar error para score < 50', () => {
      expect(getHealthScoreColor(49)).toContain('status-error')
      expect(getHealthScoreColor(0)).toContain('status-error')
    })
  })
})
