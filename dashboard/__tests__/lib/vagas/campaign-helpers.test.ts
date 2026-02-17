/**
 * Testes para campaign-helpers - Sprint 58
 * buildCampaignInitialData, nome automático, corpo da mensagem, escopo_vagas
 */

import { describe, it, expect } from 'vitest'
import { buildCampaignInitialData } from '@/lib/vagas/campaign-helpers'
import type { Shift } from '@/lib/vagas/types'

function makeShift(overrides: Partial<Shift> = {}): Shift {
  return {
    id: 'shift-1',
    hospital: 'Hospital São Luiz',
    hospital_id: 'hosp-1',
    especialidade: 'Cardiologia',
    especialidade_id: 'esp-1',
    data: '2026-03-15',
    hora_inicio: '08:00',
    hora_fim: '18:00',
    valor: 2500,
    status: 'aberta',
    criticidade: 'normal',
    reservas_count: 0,
    created_at: '2026-01-01T00:00:00Z',
    contato_nome: null,
    contato_whatsapp: null,
    ...overrides,
  }
}

describe('buildCampaignInitialData', () => {
  describe('validação de entrada', () => {
    it('lança erro quando array de vagas está vazio', () => {
      expect(() => buildCampaignInitialData([])).toThrow('Pelo menos uma vaga deve ser selecionada')
    })
  })

  describe('campos fixos', () => {
    it('tipo_campanha é sempre oferta_plantao', () => {
      const result = buildCampaignInitialData([makeShift()])
      expect(result.tipo_campanha).toBe('oferta_plantao')
    })

    it('categoria é sempre operacional', () => {
      const result = buildCampaignInitialData([makeShift()])
      expect(result.categoria).toBe('operacional')
    })
  })

  describe('nome automático - vaga única', () => {
    it('gera nome com hospital, especialidade e data', () => {
      const result = buildCampaignInitialData([makeShift()])
      expect(result.nome_template).toBe('Oferta Hospital São Luiz - Cardiologia 15/03')
    })

    it('gera nome com data correta para outro mês', () => {
      const result = buildCampaignInitialData([makeShift({ data: '2026-12-25' })])
      expect(result.nome_template).toContain('25/12')
    })
  })

  describe('nome automático - múltiplas vagas', () => {
    it('gera nome com hospital único e contagem quando mesmo hospital', () => {
      const vagas = [makeShift({ id: 's1' }), makeShift({ id: 's2', data: '2026-03-16' })]
      const result = buildCampaignInitialData(vagas)
      expect(result.nome_template).toBe('Oferta Hospital São Luiz - 2 vagas')
    })

    it('gera nome com contagem de vagas e hospitais quando hospitais diferentes', () => {
      const vagas = [
        makeShift({ id: 's1', hospital: 'Hospital A' }),
        makeShift({ id: 's2', hospital: 'Hospital B' }),
        makeShift({ id: 's3', hospital: 'Hospital C' }),
      ]
      const result = buildCampaignInitialData(vagas)
      expect(result.nome_template).toBe('Oferta 3 vagas - 3 hospitais')
    })

    it('deduplica hospitais na contagem', () => {
      const vagas = [
        makeShift({ id: 's1', hospital: 'Hospital A' }),
        makeShift({ id: 's2', hospital: 'Hospital A' }),
        makeShift({ id: 's3', hospital: 'Hospital B' }),
      ]
      const result = buildCampaignInitialData(vagas)
      expect(result.nome_template).toBe('Oferta 3 vagas - 2 hospitais')
    })
  })

  describe('corpo da mensagem - vaga única', () => {
    it('contém saudação com variável {{nome}}', () => {
      const result = buildCampaignInitialData([makeShift()])
      expect(result.corpo).toContain('Oi {{nome}}! Tudo bem?')
    })

    it('contém especialidade em minúsculo', () => {
      const result = buildCampaignInitialData([makeShift()])
      expect(result.corpo).toContain('cardiologia')
    })

    it('contém nome do hospital', () => {
      const result = buildCampaignInitialData([makeShift()])
      expect(result.corpo).toContain('Hospital São Luiz')
    })

    it('contém horário da vaga', () => {
      const result = buildCampaignInitialData([makeShift()])
      expect(result.corpo).toContain('08:00')
      expect(result.corpo).toContain('18:00')
    })

    it('contém valor formatado em BRL', () => {
      const result = buildCampaignInitialData([makeShift()])
      expect(result.corpo).toContain('R$')
      expect(result.corpo).toContain('2.500')
    })

    it('contém pergunta de interesse', () => {
      const result = buildCampaignInitialData([makeShift()])
      expect(result.corpo).toContain('Tem interesse?')
    })

    it('contém data formatada com dia da semana', () => {
      const result = buildCampaignInitialData([makeShift({ data: '2026-03-15' })])
      // 15/03/2026 é um domingo
      expect(result.corpo).toMatch(/15\/03/)
    })
  })

  describe('corpo da mensagem - múltiplas vagas', () => {
    it('contém contagem de vagas', () => {
      const vagas = [makeShift({ id: 's1' }), makeShift({ id: 's2', hospital: 'Hospital B' })]
      const result = buildCampaignInitialData(vagas)
      expect(result.corpo).toContain('2 vagas disponiveis')
    })

    it('lista cada vaga com hospital e especialidade', () => {
      const vagas = [
        makeShift({ id: 's1', hospital: 'Hospital A', especialidade: 'Cardiologia' }),
        makeShift({ id: 's2', hospital: 'Hospital B', especialidade: 'Ortopedia' }),
      ]
      const result = buildCampaignInitialData(vagas)
      expect(result.corpo).toContain('Hospital A (cardiologia)')
      expect(result.corpo).toContain('Hospital B (ortopedia)')
    })

    it('contém pergunta de interesse genérica', () => {
      const vagas = [makeShift({ id: 's1' }), makeShift({ id: 's2' })]
      const result = buildCampaignInitialData(vagas)
      expect(result.corpo).toContain('Alguma te interessa?')
    })

    it('contém valor de cada vaga', () => {
      const vagas = [makeShift({ id: 's1', valor: 2500 }), makeShift({ id: 's2', valor: 3000 })]
      const result = buildCampaignInitialData(vagas)
      expect(result.corpo).toContain('R$')
    })
  })

  describe('escopo_vagas', () => {
    it('contém vaga_ids com todos os IDs', () => {
      const vagas = [makeShift({ id: 'abc-123' }), makeShift({ id: 'def-456' })]
      const result = buildCampaignInitialData(vagas)
      expect(result.escopo_vagas.vaga_ids).toEqual(['abc-123', 'def-456'])
    })

    it('contém resumo de cada vaga sem campos extras', () => {
      const vaga = makeShift({
        id: 'v1',
        hospital: 'Hosp A',
        especialidade: 'Cardio',
        data: '2026-03-15',
        hora_inicio: '08:00',
        hora_fim: '18:00',
        valor: 2500,
      })
      const result = buildCampaignInitialData([vaga])

      expect(result.escopo_vagas.vagas).toHaveLength(1)
      const resumo = result.escopo_vagas.vagas[0]
      expect(resumo).toEqual({
        id: 'v1',
        hospital: 'Hosp A',
        especialidade: 'Cardio',
        data: '2026-03-15',
        hora_inicio: '08:00',
        hora_fim: '18:00',
        valor: 2500,
      })
    })

    it('não inclui campos extras como status, reservas_count, etc', () => {
      const result = buildCampaignInitialData([makeShift()])
      const resumo = result.escopo_vagas.vagas[0]!
      expect(resumo).not.toHaveProperty('status')
      expect(resumo).not.toHaveProperty('reservas_count')
      expect(resumo).not.toHaveProperty('created_at')
      expect(resumo).not.toHaveProperty('hospital_id')
      expect(resumo).not.toHaveProperty('especialidade_id')
      expect(resumo).not.toHaveProperty('contato_nome')
    })
  })

  describe('corpo da mensagem tem tamanho suficiente para validação', () => {
    it('corpo de vaga única tem 10+ caracteres (passa validateStep 3)', () => {
      const result = buildCampaignInitialData([makeShift()])
      expect(result.corpo.trim().length).toBeGreaterThanOrEqual(10)
    })

    it('corpo de múltiplas vagas tem 10+ caracteres', () => {
      const vagas = [makeShift({ id: 's1' }), makeShift({ id: 's2' })]
      const result = buildCampaignInitialData(vagas)
      expect(result.corpo.trim().length).toBeGreaterThanOrEqual(10)
    })
  })
})
