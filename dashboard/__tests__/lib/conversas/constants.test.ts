/**
 * Testes para lib/conversas/constants
 */

import { describe, it, expect } from 'vitest'
import {
  CONVERSATION_STATUS_LABELS,
  CONVERSATION_STATUS_COLORS,
  CONTROLLED_BY_LABELS,
  CONTROLLED_BY_COLORS,
  MESSAGE_TYPE_LABELS,
  DEFAULT_FILTERS,
  DEFAULT_PAGE_SIZE,
  MAX_PAGE_SIZE,
} from '@/lib/conversas/constants'

describe('Conversas Constants', () => {
  describe('CONVERSATION_STATUS_LABELS', () => {
    it('deve ter labels para status principais', () => {
      expect(CONVERSATION_STATUS_LABELS.ativa).toBe('Ativa')
      expect(CONVERSATION_STATUS_LABELS.pausada).toBe('Pausada')
      expect(CONVERSATION_STATUS_LABELS.encerrada).toBe('Encerrada')
    })
  })

  describe('CONVERSATION_STATUS_COLORS', () => {
    it('deve ter cores para status principais', () => {
      expect(CONVERSATION_STATUS_COLORS.ativa).toContain('green')
      expect(CONVERSATION_STATUS_COLORS.pausada).toContain('yellow')
      expect(CONVERSATION_STATUS_COLORS.encerrada).toContain('gray')
    })
  })

  describe('CONTROLLED_BY_LABELS', () => {
    it('deve ter labels corretos', () => {
      expect(CONTROLLED_BY_LABELS.ai).toBe('Julia')
      expect(CONTROLLED_BY_LABELS.human).toBe('Humano')
    })
  })

  describe('CONTROLLED_BY_COLORS', () => {
    it('deve ter cores corretas', () => {
      expect(CONTROLLED_BY_COLORS.ai).toContain('blue')
      expect(CONTROLLED_BY_COLORS.human).toContain('purple')
    })
  })

  describe('MESSAGE_TYPE_LABELS', () => {
    it('deve ter labels corretos', () => {
      expect(MESSAGE_TYPE_LABELS.entrada).toBe('Recebida')
      expect(MESSAGE_TYPE_LABELS.saida).toBe('Enviada')
    })
  })

  describe('DEFAULT_FILTERS', () => {
    it('deve ter filtros padrao vazios', () => {
      expect(DEFAULT_FILTERS.status).toBeUndefined()
      expect(DEFAULT_FILTERS.controlled_by).toBeUndefined()
      expect(DEFAULT_FILTERS.search).toBe('')
    })
  })

  describe('Pagination Constants', () => {
    it('deve ter valores padrao corretos', () => {
      expect(DEFAULT_PAGE_SIZE).toBe(20)
      expect(MAX_PAGE_SIZE).toBe(100)
    })
  })
})
