/**
 * Testes do schema de validação do wizard de campanhas
 */
import { describe, it, expect } from 'vitest'
import { validateStep, requiresCustomMessage } from '@/components/campanhas/wizard/schema'
import { type CampanhaFormData, INITIAL_FORM_DATA } from '@/components/campanhas/wizard/types'

describe('requiresCustomMessage', () => {
  it('retorna false para descoberta (tem mensagem automática)', () => {
    expect(requiresCustomMessage('descoberta')).toBe(false)
  })

  it('retorna false para reativacao (tem template padrão)', () => {
    expect(requiresCustomMessage('reativacao')).toBe(false)
  })

  it('retorna false para followup (tem template padrão)', () => {
    expect(requiresCustomMessage('followup')).toBe(false)
  })

  it('retorna true para oferta_plantao (requer corpo customizado)', () => {
    expect(requiresCustomMessage('oferta_plantao')).toBe(true)
  })

  it('retorna true para tipos desconhecidos', () => {
    expect(requiresCustomMessage('tipo_inventado')).toBe(true)
  })
})

describe('validateStep', () => {
  describe('Step 1 - Configuração', () => {
    it('retorna false se nome_template vazio', () => {
      const data: CampanhaFormData = { ...INITIAL_FORM_DATA, nome_template: '' }
      expect(validateStep(1, data)).toBe(false)
    })

    it('retorna false se nome_template tem menos de 3 caracteres', () => {
      const data: CampanhaFormData = { ...INITIAL_FORM_DATA, nome_template: 'ab' }
      expect(validateStep(1, data)).toBe(false)
    })

    it('retorna true se nome_template tem 3+ caracteres', () => {
      const data: CampanhaFormData = { ...INITIAL_FORM_DATA, nome_template: 'abc' }
      expect(validateStep(1, data)).toBe(true)
    })

    it('ignora espaços em branco no nome_template', () => {
      const data: CampanhaFormData = { ...INITIAL_FORM_DATA, nome_template: '   ab   ' }
      expect(validateStep(1, data)).toBe(false)
    })
  })

  describe('Step 2 - Audiência', () => {
    it('sempre retorna true (audiência é sempre válida)', () => {
      const data: CampanhaFormData = { ...INITIAL_FORM_DATA }
      expect(validateStep(2, data)).toBe(true)
    })

    it('retorna true mesmo sem filtros selecionados', () => {
      const data: CampanhaFormData = {
        ...INITIAL_FORM_DATA,
        audiencia_tipo: 'filtrado',
        especialidades: [],
        regioes: [],
      }
      expect(validateStep(2, data)).toBe(true)
    })
  })

  describe('Step 3 - Mensagem', () => {
    describe('para oferta_plantao (requer corpo)', () => {
      it('retorna false se corpo vazio', () => {
        const data: CampanhaFormData = {
          ...INITIAL_FORM_DATA,
          tipo_campanha: 'oferta_plantao',
          corpo: '',
        }
        expect(validateStep(3, data)).toBe(false)
      })

      it('retorna false se corpo tem menos de 10 caracteres', () => {
        const data: CampanhaFormData = {
          ...INITIAL_FORM_DATA,
          tipo_campanha: 'oferta_plantao',
          corpo: 'curto',
        }
        expect(validateStep(3, data)).toBe(false)
      })

      it('retorna true se corpo tem 10+ caracteres', () => {
        const data: CampanhaFormData = {
          ...INITIAL_FORM_DATA,
          tipo_campanha: 'oferta_plantao',
          corpo: 'Oi Dr {{nome}}! Tenho uma vaga pra vc',
        }
        expect(validateStep(3, data)).toBe(true)
      })

      it('ignora espaços em branco no corpo', () => {
        const data: CampanhaFormData = {
          ...INITIAL_FORM_DATA,
          tipo_campanha: 'oferta_plantao',
          corpo: '         ',
        }
        expect(validateStep(3, data)).toBe(false)
      })
    })

    describe('para descoberta (mensagem automática)', () => {
      it('retorna true mesmo sem corpo', () => {
        const data: CampanhaFormData = {
          ...INITIAL_FORM_DATA,
          tipo_campanha: 'descoberta',
          corpo: '',
        }
        expect(validateStep(3, data)).toBe(true)
      })

      it('retorna true com corpo customizado', () => {
        const data: CampanhaFormData = {
          ...INITIAL_FORM_DATA,
          tipo_campanha: 'descoberta',
          corpo: 'Mensagem customizada',
        }
        expect(validateStep(3, data)).toBe(true)
      })
    })

    describe('para reativacao (tem template padrão)', () => {
      it('retorna true mesmo sem corpo', () => {
        const data: CampanhaFormData = {
          ...INITIAL_FORM_DATA,
          tipo_campanha: 'reativacao',
          corpo: '',
        }
        expect(validateStep(3, data)).toBe(true)
      })
    })

    describe('para followup (tem template padrão)', () => {
      it('retorna true mesmo sem corpo', () => {
        const data: CampanhaFormData = {
          ...INITIAL_FORM_DATA,
          tipo_campanha: 'followup',
          corpo: '',
        }
        expect(validateStep(3, data)).toBe(true)
      })
    })
  })

  describe('Step 4 - Revisão', () => {
    it('sempre retorna true', () => {
      const data: CampanhaFormData = { ...INITIAL_FORM_DATA }
      expect(validateStep(4, data)).toBe(true)
    })
  })

  describe('Step inválido', () => {
    it('retorna false para step 0', () => {
      const data: CampanhaFormData = { ...INITIAL_FORM_DATA }
      expect(validateStep(0, data)).toBe(false)
    })

    it('retorna false para step 5', () => {
      const data: CampanhaFormData = { ...INITIAL_FORM_DATA }
      expect(validateStep(5, data)).toBe(false)
    })

    it('retorna false para step negativo', () => {
      const data: CampanhaFormData = { ...INITIAL_FORM_DATA }
      expect(validateStep(-1, data)).toBe(false)
    })
  })
})
