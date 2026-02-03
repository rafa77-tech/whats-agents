/**
 * Testes Unitarios - Hook useMarketIntelligence
 */

import { renderHook, waitFor, act } from '@testing-library/react'
import { useMarketIntelligence } from '@/hooks/use-market-intelligence'
import type {
  MarketOverviewResponse,
  VolumeResponse,
  PipelineResponse,
} from '@/types/market-intelligence'

// =============================================================================
// MOCKS
// =============================================================================

const mockOverviewResponse: MarketOverviewResponse = {
  periodo: { inicio: '2024-01-01', fim: '2024-01-31', dias: 31 },
  kpis: {
    gruposAtivos: {
      valor: 50,
      valorFormatado: '50',
      variacao: 10,
      variacaoTipo: 'up',
      tendencia: [45, 50],
    },
    vagasPorDia: {
      valor: 8.5,
      valorFormatado: '8.5/dia',
      variacao: 5,
      variacaoTipo: 'up',
      tendencia: [8, 8.5],
    },
    taxaConversao: {
      valor: 65,
      valorFormatado: '65%',
      variacao: -2,
      variacaoTipo: 'down',
      tendencia: [67, 65],
    },
    valorMedio: {
      valor: 150000,
      valorFormatado: 'R$ 1.500',
      variacao: null,
      variacaoTipo: null,
      tendencia: [1500],
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

const mockVolumeResponse: VolumeResponse = {
  periodo: { inicio: '2024-01-01', fim: '2024-01-31', dias: 31 },
  dados: [
    {
      data: '2024-01-01',
      mensagens: 150,
      ofertas: 45,
      vagasExtraidas: 30,
      vagasImportadas: 22,
    },
    {
      data: '2024-01-02',
      mensagens: 180,
      ofertas: 52,
      vagasExtraidas: 38,
      vagasImportadas: 28,
    },
  ],
  totais: { mensagens: 330, ofertas: 97, vagasExtraidas: 68, vagasImportadas: 50 },
  medias: {
    mensagensPorDia: 165,
    ofertasPorDia: 48.5,
    vagasExtraidasPorDia: 34,
    vagasImportadasPorDia: 25,
  },
  updatedAt: '2024-01-31T12:00:00Z',
}

const mockPipelineResponse: PipelineResponse = {
  periodo: { inicio: '2024-01-01', fim: '2024-01-31', dias: 31 },
  funil: {
    etapas: [
      { id: 'mensagens', nome: 'Mensagens', valor: 5000, percentual: 100 },
      { id: 'ofertas', nome: 'Ofertas', valor: 500, percentual: 10 },
      { id: 'importadas', nome: 'Importadas', valor: 260, percentual: 5.2 },
    ],
    conversoes: {
      mensagemParaOferta: 10,
      ofertaParaExtracao: 80,
      extracaoParaImportacao: 65,
      totalPipeline: 5.2,
    },
  },
  perdas: { duplicadas: 50, descartadas: 30, revisao: 20, semDadosMinimos: 40 },
  qualidade: {
    confiancaClassificacaoMedia: 0.87,
    confiancaExtracaoMedia: 0.82,
  },
  updatedAt: '2024-01-31T12:00:00Z',
}

// Setup global fetch mock
const mockFetch = vi.fn()
global.fetch = mockFetch

function setupSuccessfulMocks() {
  mockFetch.mockImplementation((url: string) => {
    if (url.includes('/overview')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockOverviewResponse),
      })
    }
    if (url.includes('/volume')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockVolumeResponse),
      })
    }
    if (url.includes('/pipeline')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockPipelineResponse),
      })
    }
    if (url.includes('/groups-ranking')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([]),
      })
    }
    return Promise.reject(new Error('Unknown endpoint'))
  })
}

// =============================================================================
// TESTS
// =============================================================================

describe('useMarketIntelligence', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Inicializacao', () => {
    it('deve iniciar com estado de loading quando autoFetch=true', async () => {
      setupSuccessfulMocks()
      const { result } = renderHook(() => useMarketIntelligence())

      expect(result.current.isLoading).toBe(true)
      expect(result.current.overview).toBeNull()
      expect(result.current.volume).toBeNull()
      expect(result.current.pipeline).toBeNull()

      await waitFor(() => expect(result.current.isLoading).toBe(false))
    })

    it('nao deve fazer fetch quando autoFetch=false', async () => {
      setupSuccessfulMocks()
      const { result } = renderHook(() => useMarketIntelligence({ autoFetch: false }))

      expect(result.current.isLoading).toBe(false)
      expect(mockFetch).not.toHaveBeenCalled()
    })

    it('deve usar periodo default de 24h', async () => {
      setupSuccessfulMocks()
      const { result } = renderHook(() => useMarketIntelligence())

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(result.current.period).toBe('24h')
    })

    it('deve aceitar periodo inicial customizado', async () => {
      setupSuccessfulMocks()
      const { result } = renderHook(() => useMarketIntelligence({ period: '7d' }))

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(result.current.period).toBe('7d')
      expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('period=7d'))
    })
  })

  describe('Fetch de Dados', () => {
    it('deve buscar todos os 4 endpoints em paralelo', async () => {
      setupSuccessfulMocks()
      const { result } = renderHook(() => useMarketIntelligence())

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(mockFetch).toHaveBeenCalledTimes(4)
      expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('/overview'))
      expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('/volume'))
      expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('/pipeline'))
      expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('/groups-ranking'))
    })

    it('deve popular dados corretamente apos fetch', async () => {
      setupSuccessfulMocks()
      const { result } = renderHook(() => useMarketIntelligence())

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(result.current.overview).toEqual(mockOverviewResponse)
      expect(result.current.volume).toEqual(mockVolumeResponse)
      expect(result.current.pipeline).toEqual(mockPipelineResponse)
    })

    it('deve atualizar lastUpdated apos fetch', async () => {
      setupSuccessfulMocks()
      const { result } = renderHook(() => useMarketIntelligence())

      expect(result.current.lastUpdated).toBeNull()

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(result.current.lastUpdated).toBeInstanceOf(Date)
    })
  })

  describe('Tratamento de Erros', () => {
    it('deve setar error quando fetch falha', async () => {
      mockFetch.mockRejectedValue(new Error('Network error'))

      const { result } = renderHook(() => useMarketIntelligence())

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(result.current.error).not.toBeNull()
      expect(result.current.error?.message).toBe('Network error')
    })

    it('deve setar error quando API retorna erro', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({ message: 'API Error' }),
      })

      const { result } = renderHook(() => useMarketIntelligence())

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(result.current.error).not.toBeNull()
    })

    it('deve manter dados anteriores quando refresh falha', async () => {
      setupSuccessfulMocks()
      const { result } = renderHook(() => useMarketIntelligence())

      await waitFor(() => expect(result.current.isLoading).toBe(false))
      const overviewBeforeError = result.current.overview

      // Fazer proximo fetch falhar
      mockFetch.mockRejectedValue(new Error('Refresh error'))

      await act(async () => {
        await result.current.refresh()
      })

      // Dados devem ser mantidos (nao apagados)
      expect(result.current.overview).toEqual(overviewBeforeError)
    })
  })

  describe('Refresh', () => {
    it('deve setar isRefreshing=true durante refresh', async () => {
      setupSuccessfulMocks()
      const { result } = renderHook(() => useMarketIntelligence())

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      // Inicia refresh sem await
      act(() => {
        result.current.refresh()
      })

      // Verifica que isRefreshing esta true durante o refresh
      await waitFor(() => expect(result.current.isRefreshing).toBe(true))

      // Espera finalizar
      await waitFor(() => expect(result.current.isRefreshing).toBe(false))
    })

    it('deve manter isLoading=false durante refresh', async () => {
      setupSuccessfulMocks()
      const { result } = renderHook(() => useMarketIntelligence())

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      await act(async () => {
        result.current.refresh()
        expect(result.current.isLoading).toBe(false)
      })
    })

    it('deve chamar APIs novamente no refresh', async () => {
      setupSuccessfulMocks()
      const { result } = renderHook(() => useMarketIntelligence())

      await waitFor(() => expect(result.current.isLoading).toBe(false))
      expect(mockFetch).toHaveBeenCalledTimes(4)

      await act(async () => {
        await result.current.refresh()
      })

      expect(mockFetch).toHaveBeenCalledTimes(8) // 4 inicial + 4 refresh
    })
  })

  describe('Mudanca de Periodo', () => {
    it('deve refazer fetch quando periodo muda', async () => {
      setupSuccessfulMocks()
      const { result } = renderHook(() => useMarketIntelligence())

      await waitFor(() => expect(result.current.isLoading).toBe(false))
      mockFetch.mockClear()

      await act(async () => {
        result.current.setPeriod('7d')
      })

      await waitFor(() => expect(mockFetch).toHaveBeenCalled())

      expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('period=7d'))
    })

    it('deve atualizar estado do periodo', async () => {
      setupSuccessfulMocks()
      const { result } = renderHook(() => useMarketIntelligence())

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(result.current.period).toBe('24h')

      await act(async () => {
        result.current.setPeriod('90d')
      })

      expect(result.current.period).toBe('90d')
    })

    it('deve limpar customDates quando muda para periodo nao-custom', async () => {
      setupSuccessfulMocks()
      const { result } = renderHook(() =>
        useMarketIntelligence({
          period: 'custom',
          startDate: '2024-01-01',
          endDate: '2024-01-15',
        })
      )

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      expect(result.current.customDates).not.toBeNull()

      await act(async () => {
        result.current.setPeriod('30d')
      })

      expect(result.current.customDates).toBeNull()
    })
  })

  describe('Periodo Customizado', () => {
    it('deve setar customDates e period=custom', async () => {
      setupSuccessfulMocks()
      const { result } = renderHook(() => useMarketIntelligence())

      await waitFor(() => expect(result.current.isLoading).toBe(false))

      await act(async () => {
        result.current.setCustomPeriod('2024-01-01', '2024-01-15')
      })

      expect(result.current.period).toBe('custom')
      expect(result.current.customDates).toEqual({
        startDate: '2024-01-01',
        endDate: '2024-01-15',
      })
    })

    it('deve passar datas para APIs quando period=custom', async () => {
      setupSuccessfulMocks()
      const { result } = renderHook(() => useMarketIntelligence())

      await waitFor(() => expect(result.current.isLoading).toBe(false))
      mockFetch.mockClear()

      await act(async () => {
        result.current.setCustomPeriod('2024-01-01', '2024-01-15')
      })

      await waitFor(() => expect(mockFetch).toHaveBeenCalled())

      expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('startDate=2024-01-01'))
      expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('endDate=2024-01-15'))
    })
  })

  describe('Performance', () => {
    it('nao deve refazer fetch se periodo nao mudou', async () => {
      setupSuccessfulMocks()
      const { result, rerender } = renderHook(() => useMarketIntelligence({ period: '30d' }))

      await waitFor(() => expect(result.current.isLoading).toBe(false))
      const initialCallCount = mockFetch.mock.calls.length

      rerender()

      // Nao deve ter feito novas chamadas
      expect(mockFetch.mock.calls.length).toBe(initialCallCount)
    })
  })
})
