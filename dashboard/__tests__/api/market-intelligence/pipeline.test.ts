/**
 * Testes de Integracao - API Market Intelligence Pipeline
 */

import { GET } from '@/app/api/market-intelligence/pipeline/route'
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
  chain.lte = vi.fn().mockResolvedValue(finalResult)

  return chain
}

describe('API /api/market-intelligence/pipeline', () => {
  describe('Validacao de Parametros', () => {
    it('deve aceitar request sem parametros (usa defaults)', async () => {
      const sampleData = {
        data: [
          {
            data: '2024-01-01',
            mensagens_total: 1000,
            mensagens_processadas: 900,
            mensagens_passou_heuristica: 500,
            mensagens_eh_oferta: 300,
            vagas_extraidas: 200,
            vagas_dados_ok: 180,
            vagas_duplicadas: 20,
            vagas_importadas: 150,
            vagas_revisao: 10,
            vagas_descartadas: 20,
            confianca_classificacao_media: 0.85,
            confianca_extracao_media: 0.9,
          },
        ],
        error: null,
      }

      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/pipeline')
      const response = await GET(request)

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.periodo.dias).toBeGreaterThanOrEqual(30)
    })

    it('deve aceitar period=7d', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(emptyResult) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/pipeline?period=7d')
      const response = await GET(request)

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.periodo.dias).toBeGreaterThanOrEqual(7)
      expect(data.periodo.dias).toBeLessThanOrEqual(8)
    })

    it('deve aceitar period=90d', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(emptyResult) as never)

      const request = new NextRequest(
        'http://localhost/api/market-intelligence/pipeline?period=90d'
      )
      const response = await GET(request)

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.periodo.dias).toBeGreaterThanOrEqual(90)
    })

    it('deve rejeitar period invalido', async () => {
      const request = new NextRequest(
        'http://localhost/api/market-intelligence/pipeline?period=invalid'
      )
      const response = await GET(request)

      expect(response.status).toBe(400)
      const data = await response.json()
      expect(data.error).toBe('VALIDATION_ERROR')
    })

    it('deve aceitar periodo customizado com datas validas', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(emptyResult) as never)

      const request = new NextRequest(
        'http://localhost/api/market-intelligence/pipeline?period=custom&startDate=2024-01-01&endDate=2024-01-15'
      )
      const response = await GET(request)

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.periodo.dias).toBeGreaterThan(0)
    })

    it('deve rejeitar periodo customizado sem datas', async () => {
      const request = new NextRequest(
        'http://localhost/api/market-intelligence/pipeline?period=custom'
      )
      const response = await GET(request)

      expect(response.status).toBe(400)
      const data = await response.json()
      expect(data.error).toBe('VALIDATION_ERROR')
    })
  })

  describe('Response Structure', () => {
    const sampleData = {
      data: [
        {
          data: '2024-01-01',
          mensagens_total: 1000,
          mensagens_processadas: 900,
          mensagens_passou_heuristica: 500,
          mensagens_eh_oferta: 300,
          vagas_extraidas: 200,
          vagas_dados_ok: 180,
          vagas_duplicadas: 20,
          vagas_importadas: 150,
          vagas_revisao: 10,
          vagas_descartadas: 20,
          confianca_classificacao_media: 0.85,
          confianca_extracao_media: 0.9,
        },
      ],
      error: null,
    }

    it('deve retornar estrutura de periodo correta', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/pipeline')
      const response = await GET(request)
      const data = await response.json()

      expect(data.periodo).toHaveProperty('inicio')
      expect(data.periodo).toHaveProperty('fim')
      expect(data.periodo).toHaveProperty('dias')
    })

    it('deve retornar funil com etapas', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/pipeline')
      const response = await GET(request)
      const data = await response.json()

      expect(data.funil).toHaveProperty('etapas')
      expect(Array.isArray(data.funil.etapas)).toBe(true)
      expect(data.funil.etapas.length).toBe(6) // 6 etapas do funil
    })

    it('deve retornar etapas com estrutura correta', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/pipeline')
      const response = await GET(request)
      const data = await response.json()

      const etapa = data.funil.etapas[0]
      expect(etapa).toHaveProperty('id')
      expect(etapa).toHaveProperty('nome')
      expect(etapa).toHaveProperty('valor')
      expect(etapa).toHaveProperty('percentual')
    })

    it('deve retornar conversoes', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/pipeline')
      const response = await GET(request)
      const data = await response.json()

      expect(data.funil).toHaveProperty('conversoes')
      expect(data.funil.conversoes).toHaveProperty('mensagemParaOferta')
      expect(data.funil.conversoes).toHaveProperty('ofertaParaExtracao')
      expect(data.funil.conversoes).toHaveProperty('extracaoParaImportacao')
      expect(data.funil.conversoes).toHaveProperty('totalPipeline')
    })

    it('deve retornar perdas', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/pipeline')
      const response = await GET(request)
      const data = await response.json()

      expect(data).toHaveProperty('perdas')
      expect(data.perdas).toHaveProperty('duplicadas')
      expect(data.perdas).toHaveProperty('descartadas')
      expect(data.perdas).toHaveProperty('revisao')
      expect(data.perdas).toHaveProperty('semDadosMinimos')
    })

    it('deve retornar qualidade', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/pipeline')
      const response = await GET(request)
      const data = await response.json()

      expect(data).toHaveProperty('qualidade')
      expect(data.qualidade).toHaveProperty('confiancaClassificacaoMedia')
      expect(data.qualidade).toHaveProperty('confiancaExtracaoMedia')
    })

    it('deve retornar updatedAt', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/pipeline')
      const response = await GET(request)
      const data = await response.json()

      expect(data).toHaveProperty('updatedAt')
      expect(new Date(data.updatedAt).toString()).not.toBe('Invalid Date')
    })
  })

  describe('Calculos do Funil', () => {
    it('deve calcular etapas do funil corretamente', async () => {
      const sampleData = {
        data: [
          {
            data: '2024-01-01',
            mensagens_total: 1000,
            mensagens_passou_heuristica: 500,
            mensagens_eh_oferta: 300,
            vagas_extraidas: 200,
            vagas_dados_ok: 180,
            vagas_importadas: 150,
            vagas_duplicadas: 20,
            vagas_revisao: 10,
            vagas_descartadas: 20,
          },
        ],
        error: null,
      }

      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/pipeline')
      const response = await GET(request)
      const data = await response.json()

      // Primeira etapa deve ser 100%
      expect(data.funil.etapas[0].percentual).toBe(100)
      expect(data.funil.etapas[0].valor).toBe(1000)

      // Ultima etapa (importadas)
      const ultimaEtapa = data.funil.etapas[data.funil.etapas.length - 1]
      expect(ultimaEtapa.valor).toBe(150)
      expect(ultimaEtapa.percentual).toBe(15) // 150/1000 = 15%
    })

    it('deve calcular taxas de conversao corretamente', async () => {
      const sampleData = {
        data: [
          {
            data: '2024-01-01',
            mensagens_total: 1000,
            mensagens_passou_heuristica: 500,
            mensagens_eh_oferta: 200, // 20% do total
            vagas_extraidas: 100, // 50% das ofertas
            vagas_dados_ok: 80,
            vagas_importadas: 50, // 50% das extraidas
            vagas_duplicadas: 10,
            vagas_revisao: 5,
            vagas_descartadas: 15,
          },
        ],
        error: null,
      }

      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/pipeline')
      const response = await GET(request)
      const data = await response.json()

      expect(data.funil.conversoes.mensagemParaOferta).toBe(20) // 200/1000
      expect(data.funil.conversoes.ofertaParaExtracao).toBe(50) // 100/200
      expect(data.funil.conversoes.extracaoParaImportacao).toBe(50) // 50/100
      expect(data.funil.conversoes.totalPipeline).toBe(5) // 50/1000
    })

    it('deve calcular perdas corretamente', async () => {
      const sampleData = {
        data: [
          {
            data: '2024-01-01',
            mensagens_total: 1000,
            mensagens_passou_heuristica: 500,
            mensagens_eh_oferta: 200,
            vagas_extraidas: 100,
            vagas_dados_ok: 70, // 30 sem dados minimos
            vagas_importadas: 50,
            vagas_duplicadas: 15,
            vagas_revisao: 10,
            vagas_descartadas: 25,
          },
        ],
        error: null,
      }

      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/pipeline')
      const response = await GET(request)
      const data = await response.json()

      expect(data.perdas.duplicadas).toBe(15)
      expect(data.perdas.descartadas).toBe(25)
      expect(data.perdas.revisao).toBe(10)
      expect(data.perdas.semDadosMinimos).toBe(30) // 100 - 70
    })

    it('deve agregar dados de multiplos dias', async () => {
      const sampleData = {
        data: [
          {
            data: '2024-01-01',
            mensagens_total: 500,
            mensagens_passou_heuristica: 250,
            mensagens_eh_oferta: 100,
            vagas_extraidas: 50,
            vagas_dados_ok: 40,
            vagas_importadas: 30,
            vagas_duplicadas: 5,
            vagas_revisao: 3,
            vagas_descartadas: 7,
          },
          {
            data: '2024-01-02',
            mensagens_total: 500,
            mensagens_passou_heuristica: 250,
            mensagens_eh_oferta: 100,
            vagas_extraidas: 50,
            vagas_dados_ok: 40,
            vagas_importadas: 30,
            vagas_duplicadas: 5,
            vagas_revisao: 2,
            vagas_descartadas: 8,
          },
        ],
        error: null,
      }

      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/pipeline')
      const response = await GET(request)
      const data = await response.json()

      // Valores devem ser somados
      expect(data.funil.etapas[0].valor).toBe(1000) // 500 + 500
      expect(data.perdas.duplicadas).toBe(10) // 5 + 5
      expect(data.perdas.revisao).toBe(5) // 3 + 2
    })
  })

  describe('Qualidade', () => {
    it('deve calcular media de confianca corretamente', async () => {
      const sampleData = {
        data: [
          {
            data: '2024-01-01',
            mensagens_total: 100,
            mensagens_passou_heuristica: 50,
            mensagens_eh_oferta: 30,
            vagas_extraidas: 20,
            vagas_dados_ok: 18,
            vagas_importadas: 15,
            vagas_duplicadas: 2,
            vagas_revisao: 1,
            vagas_descartadas: 2,
            confianca_classificacao_media: 0.85,
            confianca_extracao_media: 0.9,
          },
          {
            data: '2024-01-02',
            mensagens_total: 100,
            mensagens_passou_heuristica: 50,
            mensagens_eh_oferta: 30,
            vagas_extraidas: 20,
            vagas_dados_ok: 18,
            vagas_importadas: 15,
            vagas_duplicadas: 2,
            vagas_revisao: 1,
            vagas_descartadas: 2,
            confianca_classificacao_media: 0.75,
            confianca_extracao_media: 0.8,
          },
        ],
        error: null,
      }

      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/pipeline')
      const response = await GET(request)
      const data = await response.json()

      // Media de 0.85 e 0.75 = 0.80
      expect(data.qualidade.confiancaClassificacaoMedia).toBe(0.8)
      // Media de 0.9 e 0.8 = 0.85
      expect(data.qualidade.confiancaExtracaoMedia).toBe(0.85)
    })

    it('deve retornar null quando nao ha dados de confianca', async () => {
      const sampleData = {
        data: [
          {
            data: '2024-01-01',
            mensagens_total: 100,
            mensagens_passou_heuristica: 50,
            mensagens_eh_oferta: 30,
            vagas_extraidas: 20,
            vagas_dados_ok: 18,
            vagas_importadas: 15,
            vagas_duplicadas: 2,
            vagas_revisao: 1,
            vagas_descartadas: 2,
            confianca_classificacao_media: null,
            confianca_extracao_media: null,
          },
        ],
        error: null,
      }

      vi.mocked(createClient).mockResolvedValue(createChainMock(sampleData) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/pipeline')
      const response = await GET(request)
      const data = await response.json()

      expect(data.qualidade.confiancaClassificacaoMedia).toBeNull()
      expect(data.qualidade.confiancaExtracaoMedia).toBeNull()
    })
  })

  describe('Tratamento de Erros', () => {
    it('deve retornar 500 quando Supabase lanca erro', async () => {
      vi.mocked(createClient).mockRejectedValue(new Error('Connection error'))

      const request = new NextRequest('http://localhost/api/market-intelligence/pipeline')
      const response = await GET(request)

      expect(response.status).toBe(500)
      const data = await response.json()
      expect(data.error).toBe('INTERNAL_ERROR')
    })
  })

  describe('Dados vazios', () => {
    it('deve retornar estrutura valida mesmo sem dados', async () => {
      vi.mocked(createClient).mockResolvedValue(createChainMock(emptyResult) as never)

      const request = new NextRequest('http://localhost/api/market-intelligence/pipeline')
      const response = await GET(request)

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.funil.etapas[0].valor).toBe(0)
      expect(data.funil.conversoes.totalPipeline).toBe(0)
    })
  })
})
