/**
 * Testes para lib/chips/formatters
 */

import { describe, it, expect } from 'vitest'
import {
  formatChipStatus,
  formatTrustLevel,
  formatWarmupPhase,
  formatTrustScore,
  getTrustLevelFromScore,
  getWarmupProgress,
  formatWarmupDay,
  formatResponseRate,
  formatDeliveryRate,
  formatBlockRate,
  formatMessageCount,
  formatMessageUsagePercent,
  formatPhoneNumber,
  formatChipTimestamp,
  formatChipDate,
} from '@/lib/chips/formatters'

describe('Chips Formatters', () => {
  describe('formatChipStatus', () => {
    it('deve formatar status active', () => {
      expect(formatChipStatus('active')).toBe('Ativo')
    })

    it('deve formatar status warming', () => {
      expect(formatChipStatus('warming')).toBe('Aquecendo')
    })

    it('deve formatar status banned', () => {
      expect(formatChipStatus('banned')).toBe('Banido')
    })

    it('deve formatar status ready', () => {
      expect(formatChipStatus('ready')).toBe('Pronto')
    })

    it('deve formatar status degraded', () => {
      expect(formatChipStatus('degraded')).toBe('Degradado')
    })
  })

  describe('formatTrustLevel', () => {
    it('deve formatar nivel verde', () => {
      expect(formatTrustLevel('verde')).toBe('Verde')
    })

    it('deve formatar nivel amarelo', () => {
      expect(formatTrustLevel('amarelo')).toBe('Amarelo')
    })

    it('deve formatar nivel critico', () => {
      expect(formatTrustLevel('critico')).toBe('Critico')
    })
  })

  describe('formatWarmupPhase', () => {
    it('deve retornar — para null', () => {
      expect(formatWarmupPhase(null)).toBe('—')
    })

    it('deve formatar fase repouso', () => {
      expect(formatWarmupPhase('repouso')).toBe('Repouso')
    })

    it('deve formatar fase operacao', () => {
      expect(formatWarmupPhase('operacao')).toBe('Operacao')
    })

    it('deve formatar fase primeiros_contatos', () => {
      expect(formatWarmupPhase('primeiros_contatos')).toBe('Primeiros Contatos')
    })
  })

  describe('formatTrustScore', () => {
    it('deve formatar score sem decimais', () => {
      expect(formatTrustScore(85.7)).toBe('86')
      expect(formatTrustScore(50)).toBe('50')
    })
  })

  describe('getTrustLevelFromScore', () => {
    it('deve retornar verde para score >= 80', () => {
      expect(getTrustLevelFromScore(80)).toBe('verde')
      expect(getTrustLevelFromScore(100)).toBe('verde')
    })

    it('deve retornar amarelo para score >= 60', () => {
      expect(getTrustLevelFromScore(60)).toBe('amarelo')
      expect(getTrustLevelFromScore(79)).toBe('amarelo')
    })

    it('deve retornar laranja para score >= 40', () => {
      expect(getTrustLevelFromScore(40)).toBe('laranja')
      expect(getTrustLevelFromScore(59)).toBe('laranja')
    })

    it('deve retornar vermelho para score >= 20', () => {
      expect(getTrustLevelFromScore(20)).toBe('vermelho')
      expect(getTrustLevelFromScore(39)).toBe('vermelho')
    })

    it('deve retornar critico para score < 20', () => {
      expect(getTrustLevelFromScore(19)).toBe('critico')
      expect(getTrustLevelFromScore(0)).toBe('critico')
    })
  })

  describe('getWarmupProgress', () => {
    it('deve retornar 0 para null', () => {
      expect(getWarmupProgress(null)).toBe(0)
    })

    it('deve retornar progresso para repouso (primeira fase)', () => {
      const progress = getWarmupProgress('repouso')
      expect(progress).toBeGreaterThan(0)
      expect(progress).toBeLessThan(50)
    })

    it('deve retornar 100 para operacao (ultima fase)', () => {
      expect(getWarmupProgress('operacao')).toBe(100)
    })
  })

  describe('formatWarmupDay', () => {
    it('deve retornar — para undefined', () => {
      expect(formatWarmupDay(undefined)).toBe('—')
    })

    it('deve formatar dia', () => {
      expect(formatWarmupDay(5)).toBe('Dia 5')
      expect(formatWarmupDay(1)).toBe('Dia 1')
    })
  })

  describe('formatResponseRate', () => {
    it('deve formatar taxa com uma casa decimal', () => {
      expect(formatResponseRate(85.5)).toBe('85.5%')
      expect(formatResponseRate(100)).toBe('100.0%')
    })
  })

  describe('formatDeliveryRate', () => {
    it('deve formatar taxa com uma casa decimal', () => {
      expect(formatDeliveryRate(95.3)).toBe('95.3%')
    })
  })

  describe('formatBlockRate', () => {
    it('deve formatar taxa com uma casa decimal', () => {
      expect(formatBlockRate(2.5)).toBe('2.5%')
    })
  })

  describe('formatMessageCount', () => {
    it('deve formatar contagem de mensagens', () => {
      expect(formatMessageCount(10, 100)).toBe('10/100')
    })
  })

  describe('formatMessageUsagePercent', () => {
    it('deve calcular porcentagem de uso', () => {
      expect(formatMessageUsagePercent(50, 100)).toBe(50)
    })

    it('deve retornar 0 para limite zero', () => {
      expect(formatMessageUsagePercent(10, 0)).toBe(0)
    })

    it('deve limitar em 100%', () => {
      expect(formatMessageUsagePercent(150, 100)).toBe(100)
    })
  })

  describe('formatPhoneNumber', () => {
    it('deve formatar telefone brasileiro com DDI', () => {
      const result = formatPhoneNumber('5511999999999')
      expect(result).toBe('+55 (11) 99999-9999')
    })

    it('deve formatar telefone sem DDI', () => {
      const result = formatPhoneNumber('11999999999')
      expect(result).toBe('(11) 99999-9999')
    })

    it('deve retornar telefone original se formato desconhecido', () => {
      expect(formatPhoneNumber('12345')).toBe('12345')
    })
  })

  describe('formatChipTimestamp', () => {
    it('deve retornar Nunca para null', () => {
      expect(formatChipTimestamp(null)).toBe('Nunca')
    })

    it('deve retornar Agora para menos de 1 minuto', () => {
      const now = new Date().toISOString()
      expect(formatChipTimestamp(now)).toBe('Agora')
    })

    it('deve retornar minutos para menos de 1 hora', () => {
      const date = new Date(Date.now() - 30 * 60 * 1000).toISOString()
      const result = formatChipTimestamp(date)
      expect(result).toMatch(/\d+min atrás/)
    })
  })

  describe('formatChipDate', () => {
    it('deve formatar data em pt-BR', () => {
      const result = formatChipDate('2026-01-15T10:00:00Z')
      expect(result).toMatch(/\d{2}\/\d{2}\/\d{4}/)
    })
  })
})
