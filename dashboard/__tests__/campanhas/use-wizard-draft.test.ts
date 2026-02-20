/**
 * Tests for use-wizard-draft.ts
 *
 * Tests the localStorage-based draft persistence hook.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useWizardDraft } from '@/components/campanhas/wizard/use-wizard-draft'
import { INITIAL_FORM_DATA, type CampanhaFormData } from '@/components/campanhas/wizard/types'

const DRAFT_KEY = 'campanha-wizard-draft'

function makeFormData(overrides: Partial<CampanhaFormData> = {}): CampanhaFormData {
  return { ...INITIAL_FORM_DATA, ...overrides }
}

describe('useWizardDraft', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  afterEach(() => {
    localStorage.clear()
  })

  describe('initial state', () => {
    it('deve retornar hasDraft=false quando nao ha rascunho', () => {
      const { result } = renderHook(() => useWizardDraft())
      expect(result.current.hasDraft).toBe(false)
      expect(result.current.draftStep).toBe(1)
    })

    it('deve retornar hasDraft=true quando ha rascunho valido', () => {
      const draft = {
        formData: makeFormData({ nome_template: 'Test Campaign' }),
        step: 2,
        savedAt: Date.now(),
      }
      localStorage.setItem(DRAFT_KEY, JSON.stringify(draft))

      const { result } = renderHook(() => useWizardDraft())
      expect(result.current.hasDraft).toBe(true)
      expect(result.current.draftStep).toBe(2)
    })

    it('deve ignorar rascunho expirado (>24h)', () => {
      const draft = {
        formData: makeFormData({ nome_template: 'Old Campaign' }),
        step: 3,
        savedAt: Date.now() - 25 * 60 * 60 * 1000, // 25 hours ago
      }
      localStorage.setItem(DRAFT_KEY, JSON.stringify(draft))

      const { result } = renderHook(() => useWizardDraft())
      expect(result.current.hasDraft).toBe(false)
      // Expired draft should be removed from storage
      expect(localStorage.getItem(DRAFT_KEY)).toBeNull()
    })

    it('deve ignorar rascunho sem conteudo significativo', () => {
      const draft = {
        formData: makeFormData(), // All defaults, empty strings
        step: 1,
        savedAt: Date.now(),
      }
      localStorage.setItem(DRAFT_KEY, JSON.stringify(draft))

      const { result } = renderHook(() => useWizardDraft())
      expect(result.current.hasDraft).toBe(false)
      expect(localStorage.getItem(DRAFT_KEY)).toBeNull()
    })

    it('deve considerar rascunho valido se step > 1 mesmo sem conteudo', () => {
      const draft = {
        formData: makeFormData(), // Empty form
        step: 2, // But advanced past step 1
        savedAt: Date.now(),
      }
      localStorage.setItem(DRAFT_KEY, JSON.stringify(draft))

      const { result } = renderHook(() => useWizardDraft())
      expect(result.current.hasDraft).toBe(true)
      expect(result.current.draftStep).toBe(2)
    })

    it('deve considerar rascunho valido com corpo preenchido', () => {
      const draft = {
        formData: makeFormData({ corpo: 'Oi doutor!' }),
        step: 1,
        savedAt: Date.now(),
      }
      localStorage.setItem(DRAFT_KEY, JSON.stringify(draft))

      const { result } = renderHook(() => useWizardDraft())
      expect(result.current.hasDraft).toBe(true)
    })

    it('deve lidar com JSON invalido no localStorage', () => {
      localStorage.setItem(DRAFT_KEY, 'invalid-json{{{')

      const { result } = renderHook(() => useWizardDraft())
      expect(result.current.hasDraft).toBe(false)
      expect(localStorage.getItem(DRAFT_KEY)).toBeNull()
    })
  })

  describe('saveDraft', () => {
    it('deve salvar rascunho com conteudo', () => {
      const { result } = renderHook(() => useWizardDraft())

      act(() => {
        result.current.saveDraft(makeFormData({ nome_template: 'Minha Campanha' }), 2)
      })

      const stored = JSON.parse(localStorage.getItem(DRAFT_KEY)!)
      expect(stored.formData.nome_template).toBe('Minha Campanha')
      expect(stored.step).toBe(2)
      expect(stored.savedAt).toBeGreaterThan(0)
    })

    it('deve nao salvar rascunho vazio', () => {
      const { result } = renderHook(() => useWizardDraft())

      act(() => {
        result.current.saveDraft(makeFormData(), 1) // Empty form, step 1
      })

      expect(localStorage.getItem(DRAFT_KEY)).toBeNull()
    })

    it('deve salvar rascunho quando step > 1 mesmo sem conteudo', () => {
      const { result } = renderHook(() => useWizardDraft())

      act(() => {
        result.current.saveDraft(makeFormData(), 2)
      })

      expect(localStorage.getItem(DRAFT_KEY)).not.toBeNull()
    })

    it('deve salvar rascunho com corpo preenchido', () => {
      const { result } = renderHook(() => useWizardDraft())

      act(() => {
        result.current.saveDraft(makeFormData({ corpo: 'Conteudo da mensagem' }), 1)
      })

      const stored = JSON.parse(localStorage.getItem(DRAFT_KEY)!)
      expect(stored.formData.corpo).toBe('Conteudo da mensagem')
    })

    it('deve lidar com erro de localStorage (quota excedida)', () => {
      const setItemSpy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
        throw new DOMException('QuotaExceededError')
      })

      const { result } = renderHook(() => useWizardDraft())

      // Should not throw
      act(() => {
        result.current.saveDraft(makeFormData({ nome_template: 'Test' }), 2)
      })

      setItemSpy.mockRestore()
    })
  })

  describe('loadDraft', () => {
    it('deve carregar rascunho existente', () => {
      const draft = {
        formData: makeFormData({ nome_template: 'Loaded Campaign', corpo: 'Body text' }),
        step: 3,
        savedAt: Date.now(),
      }
      localStorage.setItem(DRAFT_KEY, JSON.stringify(draft))

      const { result } = renderHook(() => useWizardDraft())

      let loaded: { formData: CampanhaFormData; step: number } | null = null
      act(() => {
        loaded = result.current.loadDraft()
      })

      expect(loaded).not.toBeNull()
      expect(loaded!.formData.nome_template).toBe('Loaded Campaign')
      expect(loaded!.step).toBe(3)
      // After loading, hasDraft should be false
      expect(result.current.hasDraft).toBe(false)
    })

    it('deve retornar null quando nao ha rascunho', () => {
      const { result } = renderHook(() => useWizardDraft())

      let loaded: { formData: CampanhaFormData; step: number } | null = null
      act(() => {
        loaded = result.current.loadDraft()
      })

      expect(loaded).toBeNull()
    })
  })

  describe('clearDraft', () => {
    it('deve limpar rascunho do localStorage', () => {
      const draft = {
        formData: makeFormData({ nome_template: 'To Clear' }),
        step: 2,
        savedAt: Date.now(),
      }
      localStorage.setItem(DRAFT_KEY, JSON.stringify(draft))

      const { result } = renderHook(() => useWizardDraft())
      expect(result.current.hasDraft).toBe(true)

      act(() => {
        result.current.clearDraft()
      })

      expect(result.current.hasDraft).toBe(false)
      expect(localStorage.getItem(DRAFT_KEY)).toBeNull()
    })
  })

  describe('dismissDraft', () => {
    it('deve limpar e marcar como dismissed', () => {
      const draft = {
        formData: makeFormData({ nome_template: 'To Dismiss' }),
        step: 2,
        savedAt: Date.now(),
      }
      localStorage.setItem(DRAFT_KEY, JSON.stringify(draft))

      const { result } = renderHook(() => useWizardDraft())
      expect(result.current.hasDraft).toBe(true)

      act(() => {
        result.current.dismissDraft()
      })

      expect(result.current.hasDraft).toBe(false)
      expect(localStorage.getItem(DRAFT_KEY)).toBeNull()
    })
  })
})
