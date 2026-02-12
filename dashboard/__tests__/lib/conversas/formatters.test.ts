/**
 * Testes para lib/conversas/formatters
 */

import { describe, it, expect } from 'vitest'
import {
  formatConversationStatus,
  formatControlledBy,
  formatMessageType,
  formatPhone,
  formatMessageTime,
  formatRelativeTime,
  formatMessagePreview,
  formatClientName,
  getInitials,
} from '@/lib/conversas/formatters'

describe('Conversas Formatters', () => {
  describe('formatConversationStatus', () => {
    it('deve formatar status ativa', () => {
      expect(formatConversationStatus('ativa')).toBe('Ativa')
    })

    it('deve formatar status pausada', () => {
      expect(formatConversationStatus('pausada')).toBe('Pausada')
    })

    it('deve retornar status original se desconhecido', () => {
      expect(formatConversationStatus('unknown')).toBe('unknown')
    })
  })

  describe('formatControlledBy', () => {
    it('deve formatar ai como Julia', () => {
      expect(formatControlledBy('ai')).toBe('Julia')
    })

    it('deve formatar human como Humano', () => {
      expect(formatControlledBy('human')).toBe('Humano')
    })
  })

  describe('formatMessageType', () => {
    it('deve formatar entrada como Recebida', () => {
      expect(formatMessageType('entrada')).toBe('Recebida')
    })

    it('deve formatar saida como Enviada', () => {
      expect(formatMessageType('saida')).toBe('Enviada')
    })
  })

  describe('formatPhone', () => {
    it('deve formatar telefone brasileiro com DDI', () => {
      expect(formatPhone('5511999999999')).toBe('+55 (11) 99999-9999')
    })

    it('deve formatar telefone sem DDI', () => {
      expect(formatPhone('11999999999')).toBe('(11) 99999-9999')
    })

    it('deve retornar telefone original se formato desconhecido', () => {
      expect(formatPhone('12345')).toBe('12345')
    })

    it('deve retornar original para 13 digitos sem prefixo 55', () => {
      expect(formatPhone('4411999999999')).toBe('4411999999999')
    })
  })

  describe('formatMessageTime', () => {
    it('deve formatar hora para mensagem de hoje', () => {
      const now = new Date().toISOString()
      const result = formatMessageTime(now)
      expect(result).toMatch(/\d{2}:\d{2}/)
    })

    it('deve incluir Ontem para mensagem de ontem', () => {
      const yesterday = new Date()
      yesterday.setDate(yesterday.getDate() - 1)
      const result = formatMessageTime(yesterday.toISOString())
      expect(result).toContain('Ontem')
    })

    it('deve formatar data completa para mensagem mais antiga que ontem', () => {
      const oldDate = new Date()
      oldDate.setDate(oldDate.getDate() - 5)
      const result = formatMessageTime(oldDate.toISOString())
      // Deve conter formato dd/mm com hora
      expect(result).toMatch(/\d{2}\/\d{2}/)
    })
  })

  describe('formatRelativeTime', () => {
    it('deve retornar — para undefined', () => {
      expect(formatRelativeTime(undefined)).toBe('—')
    })

    it('deve retornar agora para menos de 1 minuto', () => {
      const now = new Date().toISOString()
      expect(formatRelativeTime(now)).toBe('agora')
    })

    it('deve formatar minutos', () => {
      const date = new Date(Date.now() - 30 * 60 * 1000).toISOString()
      expect(formatRelativeTime(date)).toMatch(/\d+min/)
    })

    it('deve formatar horas', () => {
      const date = new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString()
      expect(formatRelativeTime(date)).toMatch(/\d+h/)
    })

    it('deve retornar ontem para 1 dia', () => {
      const date = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
      expect(formatRelativeTime(date)).toBe('ontem')
    })

    it('deve formatar dias entre 2 e 6', () => {
      const date = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString()
      expect(formatRelativeTime(date)).toBe('3d')
    })

    it('deve formatar data para 7 dias ou mais', () => {
      const date = new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString()
      const result = formatRelativeTime(date)
      // Deve retornar formato dd/mm
      expect(result).toMatch(/\d{2}\/\d{2}/)
    })
  })

  describe('formatMessagePreview', () => {
    it('deve retornar mensagem curta completa', () => {
      expect(formatMessagePreview('Oi')).toBe('Oi')
    })

    it('deve truncar mensagem longa', () => {
      const longMessage = 'a'.repeat(100)
      const result = formatMessagePreview(longMessage, 50)
      expect(result.length).toBe(53) // 50 + '...'
      expect(result.endsWith('...')).toBe(true)
    })
  })

  describe('formatClientName', () => {
    it('deve formatar nome completo como primeiro e ultimo', () => {
      expect(formatClientName('Maria Silva Santos')).toBe('Maria Santos')
    })

    it('deve retornar nome unico como esta', () => {
      expect(formatClientName('Maria')).toBe('Maria')
    })

    it('deve retornar string vazia para nome vazio', () => {
      expect(formatClientName('')).toBe('')
    })
  })

  describe('getInitials', () => {
    it('deve retornar iniciais de nome completo', () => {
      expect(getInitials('Maria Silva')).toBe('MS')
    })

    it('deve retornar uma inicial para nome unico', () => {
      expect(getInitials('Maria')).toBe('M')
    })

    it('deve retornar ? para nome vazio', () => {
      expect(getInitials('')).toBe('?')
    })
  })
})
