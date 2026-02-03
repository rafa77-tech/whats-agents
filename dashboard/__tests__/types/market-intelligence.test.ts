/**
 * Testes para tipos de Market Intelligence
 */

import {
  isAnalyticsPeriod,
  isVagaGroupStatus,
  isKPIMetric,
  isAPIError,
  type KPIMetric,
  type MarketOverviewResponse,
} from '@/types/market-intelligence'

describe('Market Intelligence Types', () => {
  describe('isAnalyticsPeriod', () => {
    it('deve retornar true para periodos validos', () => {
      expect(isAnalyticsPeriod('7d')).toBe(true)
      expect(isAnalyticsPeriod('30d')).toBe(true)
      expect(isAnalyticsPeriod('90d')).toBe(true)
      expect(isAnalyticsPeriod('custom')).toBe(true)
    })

    it('deve retornar false para valores invalidos', () => {
      expect(isAnalyticsPeriod('1d')).toBe(false)
      expect(isAnalyticsPeriod('invalid')).toBe(false)
      expect(isAnalyticsPeriod(null)).toBe(false)
      expect(isAnalyticsPeriod(undefined)).toBe(false)
      expect(isAnalyticsPeriod(123)).toBe(false)
      expect(isAnalyticsPeriod({})).toBe(false)
    })
  })

  describe('isVagaGroupStatus', () => {
    it('deve retornar true para status validos', () => {
      expect(isVagaGroupStatus('pendente')).toBe(true)
      expect(isVagaGroupStatus('processando')).toBe(true)
      expect(isVagaGroupStatus('importada')).toBe(true)
      expect(isVagaGroupStatus('revisao')).toBe(true)
      expect(isVagaGroupStatus('descartada')).toBe(true)
      expect(isVagaGroupStatus('duplicada')).toBe(true)
    })

    it('deve retornar false para valores invalidos', () => {
      expect(isVagaGroupStatus('ativa')).toBe(false)
      expect(isVagaGroupStatus('')).toBe(false)
      expect(isVagaGroupStatus(null)).toBe(false)
    })
  })

  describe('isKPIMetric', () => {
    it('deve retornar true para KPIMetric valida', () => {
      const validMetric: KPIMetric = {
        valor: 100,
        valorFormatado: '100',
        variacao: 10,
        variacaoTipo: 'up',
        tendencia: [90, 95, 100],
      }
      expect(isKPIMetric(validMetric)).toBe(true)
    })

    it('deve retornar true para KPIMetric com valores null', () => {
      const metricWithNulls: KPIMetric = {
        valor: 50,
        valorFormatado: '50',
        variacao: null,
        variacaoTipo: null,
        tendencia: [],
      }
      expect(isKPIMetric(metricWithNulls)).toBe(true)
    })

    it('deve retornar false para objetos invalidos', () => {
      expect(isKPIMetric(null)).toBe(false)
      expect(isKPIMetric(undefined)).toBe(false)
      expect(isKPIMetric({})).toBe(false)
      expect(isKPIMetric({ valor: '100' })).toBe(false) // valor deve ser number
      expect(isKPIMetric({ valor: 100, valorFormatado: 100 })).toBe(false) // valorFormatado deve ser string
    })
  })

  describe('isAPIError', () => {
    it('deve retornar true para erro de API valido', () => {
      const error = {
        error: 'VALIDATION_ERROR',
        message: 'Periodo invalido',
      }
      expect(isAPIError(error)).toBe(true)
    })

    it('deve retornar true para erro com details', () => {
      const error = {
        error: 'VALIDATION_ERROR',
        message: 'Campos invalidos',
        details: { field: 'period', reason: 'required' },
      }
      expect(isAPIError(error)).toBe(true)
    })

    it('deve retornar false para objetos que nao sao erro', () => {
      expect(isAPIError(null)).toBe(false)
      expect(isAPIError({ data: 'success' })).toBe(false)
      expect(isAPIError({ error: 123 })).toBe(false)
    })
  })

  describe('Type Inference', () => {
    it('deve permitir criar MarketOverviewResponse tipado', () => {
      const response: MarketOverviewResponse = {
        periodo: {
          inicio: '2024-01-01',
          fim: '2024-01-31',
          dias: 31,
        },
        kpis: {
          gruposAtivos: {
            valor: 50,
            valorFormatado: '50',
            variacao: 10,
            variacaoTipo: 'up',
            tendencia: [45, 47, 50],
          },
          vagasPorDia: {
            valor: 25,
            valorFormatado: '25/dia',
            variacao: -5,
            variacaoTipo: 'down',
            tendencia: [30, 28, 25],
          },
          taxaConversao: {
            valor: 0.65,
            valorFormatado: '65%',
            variacao: 2,
            variacaoTipo: 'up',
            tendencia: [0.6, 0.63, 0.65],
          },
          valorMedio: {
            valor: 150000,
            valorFormatado: 'R$ 1.500',
            variacao: null,
            variacaoTipo: null,
            tendencia: [],
          },
        },
        resumo: {
          totalMensagens: 5000,
          totalOfertas: 500,
          totalVagasExtraidas: 400,
          totalVagasImportadas: 260,
        },
        updatedAt: '2024-01-31T12:00:00Z',
      }

      // Se compilar, o teste passou
      expect(response.kpis.gruposAtivos.valor).toBe(50)
    })
  })
})
