/**
 * Testes de Integracao - API Market Intelligence Volume
 */

import { GET } from '@/app/api/market-intelligence/volume/route'
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

describe('API /api/market-intelligence/volume', () => {
  describe('Validacao de Parametros', () => {
    it('deve aceitar request sem parametros (usa defaults)', async () => {
      const sampleData = {
        data: [
          {
            data: '2024-01-01',
            mensagens_total: 100,
            mensagens_eh_oferta: 30,
            vagas_extraidas: 20,
            vagas_importadas: 15,
          },
        ],
        error: null,
      }

      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/volume')
      const response = await GET(request)

      expect(response.status).toBe(200)
      const data = await response.json()
      // Default period is 24h, so dias should be 1-2
      expect(data.periodo.dias).toBeGreaterThanOrEqual(1)
      expect(data.periodo.dias).toBeLessThanOrEqual(2)
    })

    it('deve aceitar period=7d', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(emptyResult) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/volume?period=7d')
      const response = await GET(request)

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.periodo.dias).toBeGreaterThanOrEqual(7)
      expect(data.periodo.dias).toBeLessThanOrEqual(8)
    })

    it('deve aceitar granularity=week', async () => {
      const sampleData = {
        data: [
          {
            data: '2024-01-01',
            mensagens_total: 100,
            mensagens_eh_oferta: 30,
            vagas_extraidas: 20,
            vagas_importadas: 15,
          },
          {
            data: '2024-01-02',
            mensagens_total: 110,
            mensagens_eh_oferta: 35,
            vagas_extraidas: 25,
            vagas_importadas: 18,
          },
          {
            data: '2024-01-08',
            mensagens_total: 120,
            mensagens_eh_oferta: 40,
            vagas_extraidas: 30,
            vagas_importadas: 22,
          },
        ],
        error: null,
      }

      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest(
        'http://localhost/api/market-intelligence/volume?granularity=week'
      )
      const response = await GET(request)

      expect(response.status).toBe(200)
      const data = await response.json()
      // Dados devem estar agrupados por semana
      expect(data.dados.length).toBeLessThanOrEqual(5)
    })

    it('deve rejeitar period invalido', async () => {
      const request = new NextRequest(
        'http://localhost/api/market-intelligence/volume?period=invalid'
      )
      const response = await GET(request)

      expect(response.status).toBe(400)
      const data = await response.json()
      expect(data.error).toBe('VALIDATION_ERROR')
    })

    it('deve rejeitar granularity invalido', async () => {
      const request = new NextRequest(
        'http://localhost/api/market-intelligence/volume?granularity=month'
      )
      const response = await GET(request)

      expect(response.status).toBe(400)
      const data = await response.json()
      expect(data.error).toBe('VALIDATION_ERROR')
    })

    it('deve aceitar periodo customizado com datas validas', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(emptyResult) as never)

      const request = new NextRequest(
        'http://localhost/api/market-intelligence/volume?period=custom&startDate=2024-01-01&endDate=2024-01-15'
      )
      const response = await GET(request)

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.periodo.dias).toBeGreaterThan(0)
    })
  })

  describe('Response Structure', () => {
    const sampleData = {
      data: [
        {
          data: '2024-01-01',
          mensagens_total: 100,
          mensagens_eh_oferta: 30,
          vagas_extraidas: 20,
          vagas_importadas: 15,
        },
        {
          data: '2024-01-02',
          mensagens_total: 110,
          mensagens_eh_oferta: 35,
          vagas_extraidas: 25,
          vagas_importadas: 18,
        },
      ],
      error: null,
    }

    it('deve retornar estrutura de periodo correta', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/volume')
      const response = await GET(request)
      const data = await response.json()

      expect(data.periodo).toHaveProperty('inicio')
      expect(data.periodo).toHaveProperty('fim')
      expect(data.periodo).toHaveProperty('dias')
    })

    it('deve retornar array de dados com estrutura correta', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/volume')
      const response = await GET(request)
      const data = await response.json()

      expect(Array.isArray(data.dados)).toBe(true)
      if (data.dados.length > 0) {
        const ponto = data.dados[0]
        expect(ponto).toHaveProperty('data')
        expect(ponto).toHaveProperty('mensagens')
        expect(ponto).toHaveProperty('ofertas')
        expect(ponto).toHaveProperty('vagasExtraidas')
        expect(ponto).toHaveProperty('vagasImportadas')
      }
    })

    it('deve retornar totais agregados', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/volume')
      const response = await GET(request)
      const data = await response.json()

      expect(data.totais).toHaveProperty('mensagens')
      expect(data.totais).toHaveProperty('ofertas')
      expect(data.totais).toHaveProperty('vagasExtraidas')
      expect(data.totais).toHaveProperty('vagasImportadas')
      expect(typeof data.totais.mensagens).toBe('number')
    })

    it('deve retornar medias calculadas', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/volume')
      const response = await GET(request)
      const data = await response.json()

      expect(data.medias).toHaveProperty('mensagensPorDia')
      expect(data.medias).toHaveProperty('ofertasPorDia')
      expect(data.medias).toHaveProperty('vagasExtraidasPorDia')
      expect(data.medias).toHaveProperty('vagasImportadasPorDia')
      expect(typeof data.medias.mensagensPorDia).toBe('number')
    })

    it('deve retornar updatedAt', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/volume')
      const response = await GET(request)
      const data = await response.json()

      expect(data).toHaveProperty('updatedAt')
      expect(new Date(data.updatedAt).toString()).not.toBe('Invalid Date')
    })
  })

  describe('Calculos', () => {
    it('deve calcular totais corretamente', async () => {
      const sampleData = {
        data: [
          {
            data: '2024-01-01',
            mensagens_total: 100,
            mensagens_eh_oferta: 30,
            vagas_extraidas: 20,
            vagas_importadas: 15,
          },
          {
            data: '2024-01-02',
            mensagens_total: 150,
            mensagens_eh_oferta: 45,
            vagas_extraidas: 35,
            vagas_importadas: 25,
          },
        ],
        error: null,
      }

      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/volume')
      const response = await GET(request)
      const data = await response.json()

      expect(data.totais.mensagens).toBe(250)
      expect(data.totais.ofertas).toBe(75)
      expect(data.totais.vagasExtraidas).toBe(55)
      expect(data.totais.vagasImportadas).toBe(40)
    })

    it('deve calcular medias corretamente', async () => {
      const sampleData = {
        data: [
          {
            data: '2024-01-01',
            mensagens_total: 100,
            mensagens_eh_oferta: 30,
            vagas_extraidas: 20,
            vagas_importadas: 10,
          },
          {
            data: '2024-01-02',
            mensagens_total: 200,
            mensagens_eh_oferta: 70,
            vagas_extraidas: 40,
            vagas_importadas: 30,
          },
        ],
        error: null,
      }

      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/volume')
      const response = await GET(request)
      const data = await response.json()

      expect(data.medias.mensagensPorDia).toBe(150)
      expect(data.medias.ofertasPorDia).toBe(50)
    })

    it('deve agrupar por semana corretamente', async () => {
      // Dados de duas semanas diferentes
      const sampleData = {
        data: [
          {
            data: '2024-01-01',
            mensagens_total: 100,
            mensagens_eh_oferta: 30,
            vagas_extraidas: 20,
            vagas_importadas: 15,
          },
          {
            data: '2024-01-02',
            mensagens_total: 100,
            mensagens_eh_oferta: 30,
            vagas_extraidas: 20,
            vagas_importadas: 15,
          },
          {
            data: '2024-01-08',
            mensagens_total: 200,
            mensagens_eh_oferta: 60,
            vagas_extraidas: 40,
            vagas_importadas: 30,
          },
        ],
        error: null,
      }

      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest(
        'http://localhost/api/market-intelligence/volume?granularity=week'
      )
      const response = await GET(request)
      const data = await response.json()

      expect(data.dados.length).toBe(2) // 2 semanas distintas
    })
  })

  describe('Tratamento de Erros', () => {
    it('deve retornar 500 quando Supabase lanca erro', async () => {
      // Mock que lanca excecao
      vi.mocked(createClient).mockRejectedValue(new Error('Connection error'))

      const request = new NextRequest('http://localhost/api/market-intelligence/volume')
      const response = await GET(request)

      expect(response.status).toBe(500)
      const data = await response.json()
      expect(data.error).toBe('INTERNAL_ERROR')
    })
  })

  describe('Dados vazios', () => {
    it('deve retornar estrutura valida mesmo sem dados', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(emptyResult) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/volume')
      const response = await GET(request)

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(Array.isArray(data.dados)).toBe(true)
      expect(data.totais.mensagens).toBe(0)
    })
  })
})
