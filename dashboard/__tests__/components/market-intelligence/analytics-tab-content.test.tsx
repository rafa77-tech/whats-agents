/**
 * Testes de Integracao - AnalyticsTabContent
 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AnalyticsTabContent } from '@/components/market-intelligence/analytics-tab-content'

// Mock do hasPointerCapture para JSDOM
beforeAll(() => {
  HTMLElement.prototype.hasPointerCapture = vi.fn(() => false)
  HTMLElement.prototype.setPointerCapture = vi.fn()
  HTMLElement.prototype.releasePointerCapture = vi.fn()
})

// Mock do hook
vi.mock('@/hooks/use-market-intelligence', () => ({
  useMarketIntelligence: vi.fn(),
}))

// Mock dos componentes filhos para simplificar testes
vi.mock('@/components/market-intelligence/kpi-card', () => ({
  KPICard: ({ titulo, valorFormatado }: { titulo: string; valorFormatado: string }) => (
    <div data-testid="kpi-card">
      <span>{titulo}</span>
      <span>{valorFormatado}</span>
    </div>
  ),
}))

vi.mock('@/components/market-intelligence/volume-chart', () => ({
  VolumeChart: ({ isLoading }: { isLoading: boolean }) => (
    <div data-testid="volume-chart" data-loading={isLoading} />
  ),
}))

vi.mock('@/components/market-intelligence/pipeline-funnel', () => ({
  PipelineFunnel: ({ title }: { title?: string }) => (
    <div data-testid="pipeline-funnel">{title}</div>
  ),
}))

vi.mock('@/components/market-intelligence/groups-ranking', () => ({
  GroupsRanking: ({ title }: { title?: string }) => <div data-testid="groups-ranking">{title}</div>,
}))

vi.mock('@/components/market-intelligence/period-selector', () => ({
  PeriodSelector: ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <select data-testid="period-selector" value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="7d">Ultimos 7 dias</option>
      <option value="30d">Ultimos 30 dias</option>
      <option value="90d">Ultimos 90 dias</option>
      <option value="custom">Personalizado</option>
    </select>
  ),
}))

import { useMarketIntelligence } from '@/hooks/use-market-intelligence'

// =============================================================================
// TEST DATA
// =============================================================================

const mockOverview = {
  periodo: {
    inicio: '2024-01-01',
    fim: '2024-01-31',
    dias: 30,
  },
  kpis: {
    gruposAtivos: {
      valor: 50,
      valorFormatado: '50',
      variacao: 10,
      variacaoTipo: 'up' as const,
      tendencia: [45, 50],
    },
    vagasPorDia: {
      valor: 8.5,
      valorFormatado: '8.5/dia',
      variacao: 5,
      variacaoTipo: 'up' as const,
      tendencia: [8, 8.5],
    },
    taxaConversao: {
      valor: 65,
      valorFormatado: '65%',
      variacao: -2,
      variacaoTipo: 'down' as const,
      tendencia: [67, 65],
    },
    valorMedio: {
      valor: 1500,
      valorFormatado: 'R$ 1.500',
      variacao: null,
      variacaoTipo: null,
      tendencia: [1500],
    },
  },
  resumo: {
    totalMensagens: 1000,
    totalOfertas: 300,
    totalVagasExtraidas: 200,
    totalVagasImportadas: 150,
  },
  updatedAt: '2024-01-31T12:00:00Z',
}

const mockVolume = {
  periodo: {
    inicio: '2024-01-01',
    fim: '2024-01-31',
    dias: 30,
  },
  dados: [
    {
      data: '2024-01-01',
      mensagens: 100,
      ofertas: 30,
      vagasExtraidas: 20,
      vagasImportadas: 15,
    },
  ],
  totais: {
    mensagens: 1000,
    ofertas: 300,
    vagasExtraidas: 200,
    vagasImportadas: 150,
  },
  medias: {
    mensagensPorDia: 33.3,
    ofertasPorDia: 10,
    vagasExtraidasPorDia: 6.6,
    vagasImportadasPorDia: 5,
  },
  updatedAt: '2024-01-31T12:00:00Z',
}

const mockPipeline = {
  periodo: {
    inicio: '2024-01-01',
    fim: '2024-01-31',
    dias: 30,
  },
  funil: {
    etapas: [{ id: 'mensagens', nome: 'Mensagens', valor: 1000, percentual: 100 }],
    conversoes: {
      mensagemParaOferta: 30,
      ofertaParaExtracao: 66,
      extracaoParaImportacao: 75,
      totalPipeline: 15,
    },
  },
  perdas: { duplicadas: 10, descartadas: 5, revisao: 3, semDadosMinimos: 7 },
  qualidade: {
    confiancaClassificacaoMedia: 0.85,
    confiancaExtracaoMedia: 0.9,
  },
  updatedAt: '2024-01-31T12:00:00Z',
}

const mockHookReturn = {
  overview: mockOverview,
  volume: mockVolume,
  pipeline: mockPipeline,
  groupsRanking: [
    {
      grupoId: '1',
      grupoNome: 'Grupo Teste',
      grupoTipo: 'plantoes',
      grupoRegiao: 'SP',
      grupoAtivo: true,
      mensagens30d: 100,
      ofertas30d: 50,
      vagasExtraidas30d: 30,
      vagasImportadas30d: 20,
      confiancaMedia30d: 0.85,
      valorMedio30d: 150000,
      scoreQualidade: 75,
      ultimaMensagemEm: '2024-01-31T10:00:00Z',
      ultimaVagaEm: '2024-01-30T15:00:00Z',
      calculatedAt: '2024-01-31T12:00:00Z',
    },
  ],
  isLoading: false,
  isRefreshing: false,
  error: null,
  refresh: vi.fn(),
  setPeriod: vi.fn(),
  setCustomPeriod: vi.fn(),
  lastUpdated: new Date('2024-01-31T12:00:00Z'),
  period: '24h' as const,
  customDates: null,
}

// =============================================================================
// TESTS
// =============================================================================

describe('AnalyticsTabContent', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useMarketIntelligence).mockReturnValue(mockHookReturn)
  })

  describe('Renderizacao', () => {
    it('deve renderizar todos os componentes principais', () => {
      render(<AnalyticsTabContent />)

      // KPI Cards
      expect(screen.getAllByTestId('kpi-card')).toHaveLength(4)

      // Charts
      expect(screen.getByTestId('volume-chart')).toBeInTheDocument()

      // Pipeline (2x: um no grid de charts, outro detalhado)
      expect(screen.getAllByTestId('pipeline-funnel')).toHaveLength(2)

      // Ranking
      expect(screen.getByTestId('groups-ranking')).toBeInTheDocument()
    })

    it('deve renderizar o seletor de periodo', () => {
      render(<AnalyticsTabContent />)

      expect(screen.getByTestId('period-selector')).toBeInTheDocument()
    })

    it('deve renderizar o botao de refresh', () => {
      render(<AnalyticsTabContent />)

      expect(screen.getByRole('button', { name: /atualizar/i })).toBeInTheDocument()
    })

    it('deve exibir horario da ultima atualizacao', () => {
      render(<AnalyticsTabContent />)

      expect(screen.getByText(/atualizado as/i)).toBeInTheDocument()
    })

    it('deve aplicar className customizado', () => {
      const { container } = render(<AnalyticsTabContent className="custom-class" />)

      expect(container.firstChild).toHaveClass('custom-class')
    })
  })

  describe('Loading State', () => {
    it('deve mostrar loading quando isLoading=true e nao tem dados', () => {
      vi.mocked(useMarketIntelligence).mockReturnValue({
        ...mockHookReturn,
        isLoading: true,
        overview: null,
      })

      render(<AnalyticsTabContent />)

      // Nao deve mostrar componentes, deve mostrar skeletons
      expect(screen.queryByTestId('kpi-card')).not.toBeInTheDocument()
    })

    it('deve mostrar skeletons durante loading', () => {
      vi.mocked(useMarketIntelligence).mockReturnValue({
        ...mockHookReturn,
        isLoading: true,
        overview: null,
      })

      const { container } = render(<AnalyticsTabContent />)

      // Verificar presenca de skeletons
      const skeletons = container.querySelectorAll('[class*="animate-pulse"]')
      expect(skeletons.length).toBeGreaterThan(0)
    })
  })

  describe('Error State', () => {
    it('deve mostrar erro quando ha erro e nao tem dados', () => {
      vi.mocked(useMarketIntelligence).mockReturnValue({
        ...mockHookReturn,
        error: new Error('Falha na API'),
        overview: null,
      })

      render(<AnalyticsTabContent />)

      expect(screen.getByText(/erro ao carregar dados/i)).toBeInTheDocument()
      expect(screen.getByText(/falha na api/i)).toBeInTheDocument()
    })

    it('deve ter botao de retry no erro', async () => {
      const mockRefresh = vi.fn()
      vi.mocked(useMarketIntelligence).mockReturnValue({
        ...mockHookReturn,
        error: new Error('Falha'),
        overview: null,
        refresh: mockRefresh,
      })

      const user = userEvent.setup()
      render(<AnalyticsTabContent />)

      const retryBtn = screen.getByRole('button', { name: /tentar novamente/i })
      await user.click(retryBtn)

      expect(mockRefresh).toHaveBeenCalled()
    })
  })

  describe('Refresh', () => {
    it('deve chamar refresh ao clicar no botao', async () => {
      const mockRefresh = vi.fn()
      vi.mocked(useMarketIntelligence).mockReturnValue({
        ...mockHookReturn,
        refresh: mockRefresh,
      })

      const user = userEvent.setup()
      render(<AnalyticsTabContent />)

      const refreshBtn = screen.getByRole('button', { name: /atualizar/i })
      await user.click(refreshBtn)

      expect(mockRefresh).toHaveBeenCalled()
    })

    it('deve desabilitar botao durante refresh', () => {
      vi.mocked(useMarketIntelligence).mockReturnValue({
        ...mockHookReturn,
        isRefreshing: true,
      })

      render(<AnalyticsTabContent />)

      const refreshBtn = screen.getByRole('button', { name: /atualizando/i })
      expect(refreshBtn).toBeDisabled()
    })

    it('deve mostrar texto durante refresh', () => {
      vi.mocked(useMarketIntelligence).mockReturnValue({
        ...mockHookReturn,
        isRefreshing: true,
      })

      render(<AnalyticsTabContent />)

      expect(screen.getByText('Atualizando...')).toBeInTheDocument()
    })
  })

  describe('Period Selector', () => {
    it('deve chamar setPeriod ao mudar periodo', async () => {
      const mockSetPeriod = vi.fn()
      vi.mocked(useMarketIntelligence).mockReturnValue({
        ...mockHookReturn,
        setPeriod: mockSetPeriod,
      })

      const user = userEvent.setup()
      render(<AnalyticsTabContent />)

      const select = screen.getByTestId('period-selector')
      await user.selectOptions(select, '7d')

      expect(mockSetPeriod).toHaveBeenCalledWith('7d')
    })
  })

  describe('KPI Cards', () => {
    it('deve passar valores corretos para KPI cards', () => {
      render(<AnalyticsTabContent />)

      const kpiCards = screen.getAllByTestId('kpi-card')
      expect(kpiCards).toHaveLength(4)

      expect(screen.getByText('Grupos Ativos')).toBeInTheDocument()
      expect(screen.getByText('50')).toBeInTheDocument()
      expect(screen.getByText('Vagas por Dia')).toBeInTheDocument()
      expect(screen.getByText('8.5/dia')).toBeInTheDocument()
    })

    it('deve exibir todos os titulos de KPIs', () => {
      render(<AnalyticsTabContent />)

      expect(screen.getByText('Grupos Ativos')).toBeInTheDocument()
      expect(screen.getByText('Vagas por Dia')).toBeInTheDocument()
      expect(screen.getByText('Taxa de Conversao')).toBeInTheDocument()
      expect(screen.getByText('Valor Medio')).toBeInTheDocument()
    })
  })

  describe('Layout Responsivo', () => {
    it('deve usar grid para KPIs', () => {
      const { container } = render(<AnalyticsTabContent />)

      const kpiContainer = container.querySelector('.grid.sm\\:grid-cols-2.lg\\:grid-cols-4')
      expect(kpiContainer).toBeInTheDocument()
    })

    it('deve usar grid para charts', () => {
      const { container } = render(<AnalyticsTabContent />)

      const chartContainer = container.querySelector('.grid.lg\\:grid-cols-3')
      expect(chartContainer).toBeInTheDocument()
    })

    it('deve usar grid para pipeline + ranking', () => {
      const { container } = render(<AnalyticsTabContent />)

      const bottomContainer = container.querySelector('.grid.lg\\:grid-cols-2')
      expect(bottomContainer).toBeInTheDocument()
    })
  })

  describe('Titulos dos Componentes', () => {
    it('deve exibir titulo do pipeline detalhado', () => {
      render(<AnalyticsTabContent />)

      expect(screen.getByText('Detalhes do Pipeline')).toBeInTheDocument()
    })

    it('deve exibir titulo do ranking', () => {
      render(<AnalyticsTabContent />)

      expect(screen.getByText('Top 5 Grupos')).toBeInTheDocument()
    })
  })

  describe('Sem Dados', () => {
    it('deve renderizar com overview null apos loading', () => {
      vi.mocked(useMarketIntelligence).mockReturnValue({
        ...mockHookReturn,
        isLoading: false,
        overview: null,
        error: null,
      })

      render(<AnalyticsTabContent />)

      // Deve renderizar os componentes mesmo com dados null
      expect(screen.getAllByTestId('kpi-card')).toHaveLength(4)
    })
  })

  describe('Data/Hora de Atualizacao', () => {
    it('deve formatar hora corretamente', () => {
      vi.mocked(useMarketIntelligence).mockReturnValue({
        ...mockHookReturn,
        lastUpdated: new Date('2024-01-31T15:30:00Z'),
      })

      render(<AnalyticsTabContent />)

      // Deve exibir alguma indicacao de atualizacao
      expect(screen.getByText(/atualizado as/i)).toBeInTheDocument()
    })

    it('nao deve mostrar hora quando lastUpdated e null', () => {
      vi.mocked(useMarketIntelligence).mockReturnValue({
        ...mockHookReturn,
        lastUpdated: null,
      })

      render(<AnalyticsTabContent />)

      expect(screen.queryByText(/atualizado as/i)).not.toBeInTheDocument()
    })
  })
})
