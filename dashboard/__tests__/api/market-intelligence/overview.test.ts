/**
 * Testes de Integracao - API Market Intelligence Overview
 */

import { GET } from '@/app/api/market-intelligence/overview/route'
import { NextRequest } from 'next/server'
import { createClient } from '@/lib/supabase/server'

// Mock do Supabase
vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn(),
}))

// Resultado padrão para queries vazias
const emptyResult = { data: [], error: null }

// Cria um mock chainable do Supabase
function createChainMock(finalResult: unknown = emptyResult) {
  const chain: Record<string, ReturnType<typeof vi.fn>> = {}

  const chainFn = (returnValue: unknown = chain) => vi.fn().mockReturnValue(returnValue)

  chain.from = chainFn()
  chain.select = chainFn()
  chain.gte = chainFn()
  chain.lte = chainFn()
  chain.eq = chainFn()
  chain.order = vi.fn().mockResolvedValue(finalResult)

  return chain
}

describe('API /api/market-intelligence/overview', () => {
  describe('Validacao de Parametros', () => {
    it('deve aceitar request sem parametros (usa defaults)', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(emptyResult) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/overview')
      const response = await GET(request)

      expect(response.status).toBe(200)
      const data = await response.json()
      // O cálculo é inclusivo (início e fim), então 30d = 30 ou 31 dias dependendo do horário
      expect(data.periodo.dias).toBeGreaterThanOrEqual(30)
      expect(data.periodo.dias).toBeLessThanOrEqual(31)
    })

    it('deve aceitar period=7d', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(emptyResult) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/overview?period=7d')
      const response = await GET(request)

      expect(response.status).toBe(200)
      const data = await response.json()
      // O cálculo é inclusivo
      expect(data.periodo.dias).toBeGreaterThanOrEqual(7)
      expect(data.periodo.dias).toBeLessThanOrEqual(8)
    })

    it('deve aceitar period=90d', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(emptyResult) as never)

      const request = new NextRequest(
        'http://localhost/api/market-intelligence/overview?period=90d'
      )
      const response = await GET(request)

      expect(response.status).toBe(200)
      const data = await response.json()
      // O cálculo é inclusivo
      expect(data.periodo.dias).toBeGreaterThanOrEqual(90)
      expect(data.periodo.dias).toBeLessThanOrEqual(91)
    })

    it('deve rejeitar period invalido', async () => {
      const request = new NextRequest(
        'http://localhost/api/market-intelligence/overview?period=invalid'
      )
      const response = await GET(request)

      expect(response.status).toBe(400)
      const data = await response.json()
      expect(data.error).toBe('VALIDATION_ERROR')
    })

    it('deve rejeitar custom sem datas', async () => {
      const request = new NextRequest(
        'http://localhost/api/market-intelligence/overview?period=custom'
      )
      const response = await GET(request)

      expect(response.status).toBe(400)
      const data = await response.json()
      expect(data.error).toBe('VALIDATION_ERROR')
    })

    it('deve aceitar custom com datas validas', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(emptyResult) as never)

      const request = new NextRequest(
        'http://localhost/api/market-intelligence/overview?period=custom&startDate=2024-01-01&endDate=2024-01-15'
      )
      const response = await GET(request)

      expect(response.status).toBe(200)
      const data = await response.json()
      // Verificar que as datas estão presentes e são strings válidas
      expect(data.periodo.inicio).toBeDefined()
      expect(data.periodo.fim).toBeDefined()
      expect(data.periodo.dias).toBeGreaterThan(0)
    })

    it('deve rejeitar data em formato invalido', async () => {
      const request = new NextRequest(
        'http://localhost/api/market-intelligence/overview?period=custom&startDate=01-01-2024&endDate=15-01-2024'
      )
      const response = await GET(request)

      expect(response.status).toBe(400)
    })
  })

  describe('Response Structure', () => {
    const sampleData = {
      data: [
        {
          data: '2024-01-01',
          grupos_ativos: 50,
          mensagens_total: 1000,
          mensagens_com_oferta: 100,
          vagas_extraidas: 80,
          vagas_importadas: 60,
          valor_medio_plantao: 150000,
          taxa_importacao: 0.75,
        },
      ],
      error: null,
    }

    it('deve retornar estrutura correta de periodo', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/overview')
      const response = await GET(request)
      const data = await response.json()

      expect(data.periodo).toHaveProperty('inicio')
      expect(data.periodo).toHaveProperty('fim')
      expect(data.periodo).toHaveProperty('dias')
      expect(typeof data.periodo.dias).toBe('number')
    })

    it('deve retornar todos os KPIs', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/overview')
      const response = await GET(request)
      const data = await response.json()

      expect(data.kpis).toHaveProperty('gruposAtivos')
      expect(data.kpis).toHaveProperty('vagasPorDia')
      expect(data.kpis).toHaveProperty('taxaConversao')
      expect(data.kpis).toHaveProperty('valorMedio')
    })

    it('deve retornar KPI com estrutura correta', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/overview')
      const response = await GET(request)
      const data = await response.json()

      const kpi = data.kpis.gruposAtivos
      expect(kpi).toHaveProperty('valor')
      expect(kpi).toHaveProperty('valorFormatado')
      expect(kpi).toHaveProperty('variacao')
      expect(kpi).toHaveProperty('variacaoTipo')
      expect(kpi).toHaveProperty('tendencia')
      expect(Array.isArray(kpi.tendencia)).toBe(true)
    })

    it('deve retornar resumo com totais', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/overview')
      const response = await GET(request)
      const data = await response.json()

      expect(data.resumo).toHaveProperty('totalMensagens')
      expect(data.resumo).toHaveProperty('totalOfertas')
      expect(data.resumo).toHaveProperty('totalVagasExtraidas')
      expect(data.resumo).toHaveProperty('totalVagasImportadas')
    })

    it('deve retornar updatedAt', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/overview')
      const response = await GET(request)
      const data = await response.json()

      expect(data).toHaveProperty('updatedAt')
      expect(new Date(data.updatedAt).toString()).not.toBe('Invalid Date')
    })
  })

  describe('Calculos', () => {
    it('deve calcular variacao e tipo corretamente', async () => {
      const sampleData = {
        data: [
          {
            vagas_importadas: 100,
            vagas_extraidas: 100,
            grupos_ativos: 50,
          },
        ],
        error: null,
      }

      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/overview?period=7d')
      const response = await GET(request)
      const data = await response.json()

      expect(data.kpis.vagasPorDia).toHaveProperty('variacaoTipo')
    })

    it('deve formatar valor monetario corretamente', async () => {
      const sampleData = {
        data: [{ valor_medio_plantao: 150000 }],
        error: null,
      }

      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/overview')
      const response = await GET(request)
      const data = await response.json()

      expect(data.kpis.valorMedio.valorFormatado).toMatch(/R\$/)
    })
  })

  describe('Tratamento de Erros', () => {
    it('deve retornar 500 quando banco falha', async () => {
      const errorResult = {
        data: null,
        error: { message: 'Database error' },
      }

      vi.mocked(createClient).mockResolvedValue(createChainMock(errorResult) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/overview')
      const response = await GET(request)

      expect(response.status).toBe(500)
      const data = await response.json()
      expect(data.error).toBe('INTERNAL_ERROR')
    })
  })
})
