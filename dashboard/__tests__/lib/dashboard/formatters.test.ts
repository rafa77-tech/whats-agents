/**
 * Testes para lib/dashboard/formatters
 */

import { describe, it, expect } from 'vitest'
import {
  formatExportDate,
  formatExportDateTime,
  formatValue,
  calculateChange,
  getMetaStatus,
  getStatusColor,
  escapeCSV,
  formatMetricValue,
  formatQualityValue,
  formatPeriodLabel,
  formatPeriodDates,
  formatLastHeartbeat,
  formatActivityTimestamp,
  formatRateLimit,
  calculateRateLimitPercent,
  formatUptime,
  getUptimeStatus,
} from '@/lib/dashboard/formatters'

describe('Dashboard Formatters', () => {
  describe('formatExportDate', () => {
    it('deve formatar data ISO para pt-BR', () => {
      const result = formatExportDate('2026-01-15T10:30:00Z')
      expect(result).toMatch(/\d{2}\/\d{2}\/\d{4}/)
    })
  })

  describe('formatExportDateTime', () => {
    it('deve formatar data e hora para pt-BR', () => {
      const date = new Date('2026-01-15T10:30:00Z')
      const result = formatExportDateTime(date)
      expect(result).toBeDefined()
      expect(typeof result).toBe('string')
    })
  })

  describe('formatValue', () => {
    it('deve formatar porcentagem', () => {
      expect(formatValue(75.5, 'percent')).toBe('75.5%')
      expect(formatValue(75.5, '%')).toBe('75.5%')
    })

    it('deve formatar segundos', () => {
      expect(formatValue(30, 's')).toBe('30s')
      expect(formatValue(30, 'seconds')).toBe('30s')
    })

    it('deve formatar moeda', () => {
      expect(formatValue(100, 'currency')).toBe('R$ 100.00')
    })

    it('deve retornar string para outros casos', () => {
      expect(formatValue(42, '')).toBe('42')
    })
  })

  describe('calculateChange', () => {
    it('deve calcular variacao positiva', () => {
      expect(calculateChange(110, 100)).toBe('+10%')
    })

    it('deve calcular variacao negativa', () => {
      expect(calculateChange(90, 100)).toBe('-10%')
    })

    it('deve retornar N/A quando anterior e zero', () => {
      expect(calculateChange(100, 0)).toBe('N/A')
    })
  })

  describe('getMetaStatus', () => {
    it('deve retornar Atingida quando valor >= meta', () => {
      expect(getMetaStatus(100, 80)).toBe('Atingida')
      expect(getMetaStatus(80, 80)).toBe('Atingida')
    })

    it('deve retornar Abaixo quando valor < meta', () => {
      expect(getMetaStatus(70, 80)).toBe('Abaixo')
    })
  })

  describe('getStatusColor', () => {
    it('deve retornar cor para active', () => {
      expect(getStatusColor('active')).toBe('#16a34a')
    })

    it('deve retornar cor para ready', () => {
      expect(getStatusColor('ready')).toBe('#1e40af')
    })

    it('deve retornar cor para warming', () => {
      expect(getStatusColor('warming')).toBe('#ca8a04')
    })

    it('deve retornar cor para degraded', () => {
      expect(getStatusColor('degraded')).toBe('#dc2626')
    })

    it('deve retornar cor muted para status desconhecido', () => {
      expect(getStatusColor('unknown')).toBe('#6b7280')
    })
  })

  describe('escapeCSV', () => {
    it('deve escapar strings com virgula', () => {
      expect(escapeCSV('valor,com,virgulas')).toBe('"valor,com,virgulas"')
    })

    it('deve escapar strings com aspas', () => {
      expect(escapeCSV('valor"com"aspas')).toBe('"valor""com""aspas"')
    })

    it('deve escapar strings com quebra de linha', () => {
      expect(escapeCSV('valor\ncom\nlinha')).toBe('"valor\ncom\nlinha"')
    })

    it('nao deve escapar strings simples', () => {
      expect(escapeCSV('valor simples')).toBe('valor simples')
    })
  })

  describe('formatMetricValue', () => {
    it('deve formatar porcentagem', () => {
      expect(formatMetricValue(75.5, 'percent')).toBe('75.5%')
    })

    it('deve formatar moeda', () => {
      const result = formatMetricValue(1500, 'currency')
      expect(result).toContain('R$')
    })

    it('deve formatar numero', () => {
      expect(formatMetricValue(1500, 'number')).toMatch(/1\.?500/)
    })
  })

  describe('formatQualityValue', () => {
    it('deve formatar porcentagem', () => {
      expect(formatQualityValue(85.3, 'percent')).toBe('85.3%')
    })

    it('deve formatar segundos', () => {
      expect(formatQualityValue(30.5, 'seconds')).toBe('30.5s')
    })
  })

  describe('formatPeriodLabel', () => {
    it('deve retornar label para 7d', () => {
      expect(formatPeriodLabel('7d')).toBe('7 dias')
    })

    it('deve retornar label para 14d', () => {
      expect(formatPeriodLabel('14d')).toBe('14 dias')
    })

    it('deve retornar label para 30d', () => {
      expect(formatPeriodLabel('30d')).toBe('30 dias')
    })
  })

  describe('formatPeriodDates', () => {
    it('deve retornar datas de inicio e fim', () => {
      const result = formatPeriodDates('7d')
      expect(result.start).toBeInstanceOf(Date)
      expect(result.end).toBeInstanceOf(Date)
      expect(result.end.getTime()).toBeGreaterThan(result.start.getTime())
    })
  })

  describe('formatLastHeartbeat', () => {
    it('deve retornar Nunca para null', () => {
      expect(formatLastHeartbeat(null)).toBe('Nunca')
    })

    it('deve retornar Agora para menos de 1 minuto', () => {
      const now = new Date()
      expect(formatLastHeartbeat(now)).toBe('Agora')
    })

    it('deve retornar minutos para menos de 1 hora', () => {
      const date = new Date(Date.now() - 30 * 60 * 1000)
      const result = formatLastHeartbeat(date)
      expect(result).toMatch(/\d+m atrás/)
    })

    it('deve retornar horas para menos de 24 horas', () => {
      const date = new Date(Date.now() - 5 * 60 * 60 * 1000)
      const result = formatLastHeartbeat(date)
      expect(result).toMatch(/\d+h atrás/)
    })

    it('deve retornar dias para mais de 24 horas', () => {
      const date = new Date(Date.now() - 48 * 60 * 60 * 1000)
      const result = formatLastHeartbeat(date)
      expect(result).toMatch(/\d+d atrás/)
    })
  })

  describe('formatActivityTimestamp', () => {
    it('deve retornar agora para menos de 1 minuto', () => {
      const now = new Date().toISOString()
      expect(formatActivityTimestamp(now)).toBe('agora')
    })

    it('deve retornar minutos para menos de 1 hora', () => {
      const date = new Date(Date.now() - 30 * 60 * 1000).toISOString()
      const result = formatActivityTimestamp(date)
      expect(result).toMatch(/\d+min/)
    })
  })

  describe('formatRateLimit', () => {
    it('deve formatar rate limit', () => {
      expect(formatRateLimit(5, 20)).toBe('5/20')
    })
  })

  describe('calculateRateLimitPercent', () => {
    it('deve calcular porcentagem', () => {
      expect(calculateRateLimitPercent(5, 20)).toBe(25)
    })

    it('deve retornar 0 para max zero', () => {
      expect(calculateRateLimitPercent(5, 0)).toBe(0)
    })

    it('deve limitar em 100%', () => {
      expect(calculateRateLimitPercent(25, 20)).toBe(100)
    })
  })

  describe('formatUptime', () => {
    it('deve formatar uptime', () => {
      expect(formatUptime(99.5)).toBe('99.5%')
    })
  })

  describe('getUptimeStatus', () => {
    it('deve retornar good para >= 99%', () => {
      expect(getUptimeStatus(99)).toBe('good')
      expect(getUptimeStatus(100)).toBe('good')
    })

    it('deve retornar warning para >= 95%', () => {
      expect(getUptimeStatus(95)).toBe('warning')
      expect(getUptimeStatus(98)).toBe('warning')
    })

    it('deve retornar critical para < 95%', () => {
      expect(getUptimeStatus(94)).toBe('critical')
      expect(getUptimeStatus(80)).toBe('critical')
    })
  })
})
