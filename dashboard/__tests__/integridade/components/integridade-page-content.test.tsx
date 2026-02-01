import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { IntegridadePageContent } from '@/components/integridade/integridade-page-content'

// Mock the useIntegridadeData hook
const mockFetchData = vi.fn()
const mockRunAudit = vi.fn()
const mockResolveAnomaly = vi.fn()

vi.mock('@/lib/integridade', async () => {
  const actual = await vi.importActual('@/lib/integridade')
  return {
    ...actual,
    useIntegridadeData: () => mockUseIntegridadeData(),
  }
})

let mockHookState = {
  data: null as ReturnType<typeof createMockData> | null,
  loading: true,
  error: null as string | null,
  fetchData: mockFetchData,
  runAudit: mockRunAudit,
  resolveAnomaly: mockResolveAnomaly,
  runningAudit: false,
}

function mockUseIntegridadeData() {
  return mockHookState
}

function createMockData(overrides = {}) {
  return {
    kpis: {
      healthScore: 85,
      conversionRate: 72,
      timeToFill: 4.2,
      componentScores: {
        pressao: 1,
        friccao: 2,
        qualidade: 0.5,
        spam: 0,
      },
      recommendations: [],
    },
    anomalias: {
      abertas: 2,
      resolvidas: 1,
      total: 3,
    },
    violacoes: 2,
    ultimaAuditoria: '2026-01-15T10:30:00Z',
    anomaliasList: [
      {
        id: 'anomaly-1',
        tipo: 'duplicata_medico',
        entidade: 'medico',
        entidadeId: 'med-123',
        severidade: 'high' as const,
        mensagem: 'Medico duplicado',
        criadaEm: '2026-01-15T10:00:00Z',
        resolvida: false,
      },
      {
        id: 'anomaly-2',
        tipo: 'dado_faltando',
        entidade: 'vaga',
        entidadeId: 'vag-456',
        severidade: 'low' as const,
        mensagem: 'Campo obrigatorio vazio',
        criadaEm: '2026-01-14T08:00:00Z',
        resolvida: false,
      },
    ],
    ...overrides,
  }
}

describe('IntegridadePageContent', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockHookState = {
      data: null,
      loading: true,
      error: null,
      fetchData: mockFetchData,
      runAudit: mockRunAudit,
      resolveAnomaly: mockResolveAnomaly,
      runningAudit: false,
    }
    mockResolveAnomaly.mockResolvedValue(undefined)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Loading State', () => {
    it('shows loading spinner when loading', () => {
      mockHookState.loading = true
      mockHookState.data = null

      render(<IntegridadePageContent />)

      expect(screen.getByText('Carregando dados de integridade...')).toBeInTheDocument()
    })

    it('shows loading spinner animation', () => {
      mockHookState.loading = true
      mockHookState.data = null

      const { container } = render(<IntegridadePageContent />)

      expect(container.querySelector('.animate-spin')).toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    it('shows error message when error occurs and no data', () => {
      mockHookState.loading = false
      mockHookState.error = 'Erro ao carregar dados'
      mockHookState.data = null

      render(<IntegridadePageContent />)

      expect(screen.getByText('Erro ao carregar dados')).toBeInTheDocument()
    })

    it('shows retry button on error', () => {
      mockHookState.loading = false
      mockHookState.error = 'Erro de rede'
      mockHookState.data = null

      render(<IntegridadePageContent />)

      expect(screen.getByText('Tentar novamente')).toBeInTheDocument()
    })

    it('calls fetchData when retry button clicked', async () => {
      const user = userEvent.setup()
      mockHookState.loading = false
      mockHookState.error = 'Erro de rede'
      mockHookState.data = null

      render(<IntegridadePageContent />)

      await user.click(screen.getByText('Tentar novamente'))

      expect(mockFetchData).toHaveBeenCalled()
    })

    it('shows error banner when error with data', () => {
      mockHookState.loading = false
      mockHookState.error = 'Erro parcial'
      mockHookState.data = createMockData()

      render(<IntegridadePageContent />)

      // Should show error banner but also render data
      expect(screen.getByText('Erro parcial')).toBeInTheDocument()
      expect(screen.getByText('Integridade dos Dados')).toBeInTheDocument()
    })
  })

  describe('Data Rendering', () => {
    beforeEach(() => {
      mockHookState.loading = false
      mockHookState.data = createMockData()
    })

    it('renders page title', () => {
      render(<IntegridadePageContent />)

      expect(screen.getByText('Integridade dos Dados')).toBeInTheDocument()
      expect(screen.getByText('Monitoramento de anomalias e saude do funil')).toBeInTheDocument()
    })

    it('renders Health Score KPI card', () => {
      render(<IntegridadePageContent />)

      expect(screen.getByText('Health Score')).toBeInTheDocument()
      expect(screen.getByText('85')).toBeInTheDocument()
      expect(screen.getByText('/100')).toBeInTheDocument()
    })

    it('renders Taxa de Conversao KPI card', () => {
      render(<IntegridadePageContent />)

      expect(screen.getByText('Taxa de Conversao')).toBeInTheDocument()
      expect(screen.getByText('72')).toBeInTheDocument()
    })

    it('renders Time-to-Fill KPI card', () => {
      render(<IntegridadePageContent />)

      expect(screen.getByText('Time-to-Fill')).toBeInTheDocument()
      expect(screen.getByText('4.2')).toBeInTheDocument()
    })

    it('renders anomalias abertas counter', () => {
      render(<IntegridadePageContent />)

      expect(screen.getByText('Anomalias Abertas')).toBeInTheDocument()
      // Value is shown within the card - find it via yellow text color
      const abertasValue = screen.getByText('2', { selector: '.text-yellow-600' })
      expect(abertasValue).toBeInTheDocument()
    })

    it('renders violacoes counter', () => {
      render(<IntegridadePageContent />)

      expect(screen.getByText('Violacoes')).toBeInTheDocument()
      // Value is shown within the card - find it via red text color
      const violacoesValue = screen.getByText('2', { selector: '.text-red-600' })
      expect(violacoesValue).toBeInTheDocument()
    })

    it('renders ultima auditoria', () => {
      render(<IntegridadePageContent />)

      expect(screen.getByText('Ultima Auditoria')).toBeInTheDocument()
      // Date formatted in pt-BR with time (datetime format includes comma separator)
      expect(screen.getByText(/15\/01\/2026,/)).toBeInTheDocument()
    })

    it('renders anomalies table', () => {
      render(<IntegridadePageContent />)

      expect(screen.getByText('Lista de Anomalias')).toBeInTheDocument()
      expect(screen.getByText('2 abertas de 3 total')).toBeInTheDocument()
    })

    it('renders anomaly rows', () => {
      render(<IntegridadePageContent />)

      expect(screen.getByText('duplicata_medico')).toBeInTheDocument()
      expect(screen.getByText('dado_faltando')).toBeInTheDocument()
    })

    it('renders severity badges', () => {
      render(<IntegridadePageContent />)

      expect(screen.getByText('Alta')).toBeInTheDocument()
      expect(screen.getByText('Baixa')).toBeInTheDocument()
    })

    it('renders status badges', () => {
      render(<IntegridadePageContent />)

      const abertaBadges = screen.getAllByText('Aberta')
      expect(abertaBadges.length).toBe(2)
    })
  })

  describe('Empty State', () => {
    it('shows empty message when no anomalies', () => {
      mockHookState.loading = false
      mockHookState.data = createMockData({
        anomaliasList: [],
        anomalias: { abertas: 0, resolvidas: 0, total: 0 },
      })

      render(<IntegridadePageContent />)

      expect(screen.getByText('Nenhuma anomalia encontrada')).toBeInTheDocument()
    })
  })

  describe('User Interactions', () => {
    beforeEach(() => {
      mockHookState.loading = false
      mockHookState.data = createMockData()
    })

    it('calls fetchData when Atualizar button clicked', async () => {
      const user = userEvent.setup()

      render(<IntegridadePageContent />)

      await user.click(screen.getByText('Atualizar'))

      expect(mockFetchData).toHaveBeenCalled()
    })

    it('calls runAudit when audit button clicked', async () => {
      const user = userEvent.setup()

      const { container } = render(<IntegridadePageContent />)

      // Find the button with Play icon inside the Ultima Auditoria card
      const playIcon = container.querySelector('.lucide-play')
      const auditButton = playIcon?.closest('button')

      if (auditButton) {
        await user.click(auditButton)
        expect(mockRunAudit).toHaveBeenCalled()
      } else {
        // If button not found, fail the test explicitly
        expect(auditButton).not.toBeNull()
      }
    })

    it('disables audit button when running', () => {
      mockHookState.runningAudit = true

      render(<IntegridadePageContent />)

      // When running, the button should be disabled
      // Find the card with "Ultima Auditoria" and get its button
      const auditLabel = screen.getByText('Ultima Auditoria')
      const cardContent = auditLabel.closest('div')?.parentElement
      const button = cardContent?.querySelector('button')

      expect(button).not.toBeNull()
      expect(button).toBeDisabled()
    })
  })

  describe('Tab Switching', () => {
    beforeEach(() => {
      mockHookState.loading = false
      mockHookState.data = createMockData()
    })

    it('shows anomalias tab by default', () => {
      render(<IntegridadePageContent />)

      expect(screen.getByText('Lista de Anomalias')).toBeInTheDocument()
    })

    it('switches to KPIs tab', async () => {
      const user = userEvent.setup()

      render(<IntegridadePageContent />)

      await user.click(screen.getByRole('tab', { name: 'KPIs Detalhados' }))

      expect(screen.getByText('Breakdown dos indicadores de saude')).toBeInTheDocument()
    })

    it('shows health score components in KPIs tab', async () => {
      const user = userEvent.setup()

      render(<IntegridadePageContent />)

      await user.click(screen.getByRole('tab', { name: 'KPIs Detalhados' }))

      expect(screen.getByText('Pressao de Vagas')).toBeInTheDocument()
      expect(screen.getByText('Friccao no Funil')).toBeInTheDocument()
      expect(screen.getByText('Qualidade Respostas')).toBeInTheDocument()
      expect(screen.getByText('Score de Spam')).toBeInTheDocument()
    })

    it('shows recommendations in KPIs tab', async () => {
      const user = userEvent.setup()
      mockHookState.data = createMockData({
        kpis: {
          ...createMockData().kpis,
          recommendations: ['Aumentar taxa de conversao', 'Reduzir tempo de resposta'],
        },
      })

      render(<IntegridadePageContent />)

      await user.click(screen.getByRole('tab', { name: 'KPIs Detalhados' }))

      expect(screen.getByText('Aumentar taxa de conversao')).toBeInTheDocument()
      expect(screen.getByText('Reduzir tempo de resposta')).toBeInTheDocument()
    })

    it('shows healthy message when no recommendations', async () => {
      const user = userEvent.setup()

      render(<IntegridadePageContent />)

      await user.click(screen.getByRole('tab', { name: 'KPIs Detalhados' }))

      expect(
        screen.getByText('Nenhuma recomendacao no momento. Sistema saudavel!')
      ).toBeInTheDocument()
    })
  })

  describe('Modal Integration', () => {
    beforeEach(() => {
      mockHookState.loading = false
      mockHookState.data = createMockData()
    })

    it('opens modal when view button clicked', async () => {
      const user = userEvent.setup()

      const { container } = render(<IntegridadePageContent />)

      // Click on the first Eye icon button
      const eyeIcon = container.querySelector('.lucide-eye')
      const eyeButton = eyeIcon?.closest('button')

      expect(eyeButton).not.toBeNull()
      if (eyeButton) {
        await user.click(eyeButton)

        // Modal should be open
        await waitFor(() => {
          expect(screen.getByText(/Anomalia #/)).toBeInTheDocument()
        })
      }
    })

    it('closes modal when close button clicked', async () => {
      const user = userEvent.setup()

      const { container } = render(<IntegridadePageContent />)

      // Open modal
      const eyeIcon = container.querySelector('.lucide-eye')
      const eyeButton = eyeIcon?.closest('button')

      expect(eyeButton).not.toBeNull()
      if (eyeButton) {
        await user.click(eyeButton)

        await waitFor(() => {
          expect(screen.getByText(/Anomalia #/)).toBeInTheDocument()
        })

        // Close modal
        await user.click(screen.getByText('Fechar'))

        await waitFor(() => {
          expect(screen.queryByText(/Anomalia #anomaly/)).not.toBeInTheDocument()
        })
      }
    })

    it('calls resolveAnomaly when marking as corrigido', async () => {
      const user = userEvent.setup()

      const { container } = render(<IntegridadePageContent />)

      // Open modal
      const eyeIcon = container.querySelector('.lucide-eye')
      const eyeButton = eyeIcon?.closest('button')

      expect(eyeButton).not.toBeNull()
      if (eyeButton) {
        await user.click(eyeButton)

        await waitFor(() => {
          expect(screen.getByText(/Anomalia #/)).toBeInTheDocument()
        })

        // Type notes
        const textarea = screen.getByPlaceholderText(/Descreva a causa/)
        await user.type(textarea, 'Fixed the issue')

        // Click resolve
        await user.click(screen.getByText('Marcar Corrigido'))

        await waitFor(() => {
          expect(mockResolveAnomaly).toHaveBeenCalledWith(
            'anomaly-1',
            '[Corrigido] Fixed the issue'
          )
        })
      }
    })
  })

  describe('Status Colors', () => {
    it('applies good status for high health score', () => {
      mockHookState.loading = false
      mockHookState.data = createMockData({ kpis: { ...createMockData().kpis, healthScore: 90 } })

      const { container } = render(<IntegridadePageContent />)

      // Health Score card should have green border
      const greenBorder = container.querySelector('.border-green-200')
      expect(greenBorder).toBeInTheDocument()
    })

    it('applies warn status for medium health score', () => {
      mockHookState.loading = false
      mockHookState.data = createMockData({ kpis: { ...createMockData().kpis, healthScore: 65 } })

      const { container } = render(<IntegridadePageContent />)

      const yellowBorder = container.querySelector('.border-yellow-200')
      expect(yellowBorder).toBeInTheDocument()
    })

    it('applies bad status for low health score', () => {
      mockHookState.loading = false
      mockHookState.data = createMockData({ kpis: { ...createMockData().kpis, healthScore: 40 } })

      const { container } = render(<IntegridadePageContent />)

      const redBorder = container.querySelector('.border-red-200')
      expect(redBorder).toBeInTheDocument()
    })
  })
})
