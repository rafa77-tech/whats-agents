/**
 * Testes para Dashboard Page
 */

import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import DashboardPage from '@/app/(dashboard)/dashboard/page'

// Mock all dashboard components
vi.mock('@/components/dashboard/dashboard-header', () => ({
  DashboardHeader: ({ juliaStatus, selectedPeriod }: any) => (
    <div data-testid="dashboard-header">
      <span data-testid="julia-status">{juliaStatus}</span>
      <span data-testid="selected-period">{selectedPeriod}</span>
    </div>
  ),
}))

vi.mock('@/components/dashboard/metrics-section', () => ({
  MetricsSection: () => <div data-testid="metrics-section">Metrics</div>,
}))

vi.mock('@/components/dashboard/quality-metrics-section', () => ({
  QualityMetricsSection: () => <div data-testid="quality-section">Quality</div>,
}))

vi.mock('@/components/dashboard/opportunities-widget', () => ({
  OpportunitiesWidget: () => <div data-testid="opportunities-widget">Opportunities</div>,
}))

vi.mock('@/components/dashboard/operational-status', () => ({
  OperationalStatus: () => <div data-testid="operational-status">Operational</div>,
}))

vi.mock('@/components/dashboard/chip-pool-overview', () => ({
  ChipPoolOverview: () => <div data-testid="chip-pool">Chip Pool</div>,
}))

vi.mock('@/components/dashboard/chip-list-table', () => ({
  ChipListTable: () => <div data-testid="chip-list">Chip List</div>,
}))

vi.mock('@/components/dashboard/conversion-funnel', () => ({
  ConversionFunnel: () => <div data-testid="funnel">Funnel</div>,
}))

vi.mock('@/components/dashboard/funnel-drilldown-modal', () => ({
  FunnelDrilldownModal: () => null,
}))

vi.mock('@/components/dashboard/trends-section', () => ({
  TrendsSection: () => <div data-testid="trends">Trends</div>,
}))

vi.mock('@/components/dashboard/alerts-list', () => ({
  AlertsList: () => <div data-testid="alerts">Alerts</div>,
}))

vi.mock('@/components/dashboard/activity-feed', () => ({
  ActivityFeed: () => <div data-testid="activity">Activity</div>,
}))

vi.mock('@/components/dashboard/message-flow', () => ({
  MessageFlowWidget: ({ data }: any) => (
    <div data-testid="message-flow-widget">
      {data ? `${data.chips?.length ?? 0} chips` : 'no data'}
    </div>
  ),
}))

vi.mock('@/components/shared', () => ({
  CriticalAlertsBanner: () => <div data-testid="critical-alerts">Critical Alerts</div>,
}))

const mockFetch = vi.fn()

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = mockFetch
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function setupMockFetch() {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/dashboard/status')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              status: 'online',
              lastHeartbeat: new Date().toISOString(),
              uptime30d: 99.5,
            }),
        })
      }
      if (url.includes('/api/dashboard/chips/list')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              chips: [{ id: '1', name: 'Chip 1' }],
            }),
        })
      }
      if (url.includes('/api/dashboard/chips')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              byStatus: { active: 5 },
              byTrustLevel: { verde: 5 },
              totalMessagesSent: 100,
            }),
        })
      }
      if (url.includes('/api/dashboard/metrics')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              metrics: {
                responseRate: { value: 85, previous: 80, meta: 70 },
                conversionRate: { value: 25, previous: 20, meta: 20 },
              },
            }),
        })
      }
      if (url.includes('/api/dashboard/quality')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              metrics: {
                botDetection: { value: 0.5, previous: 1 },
                avgLatency: { value: 25, previous: 30 },
              },
            }),
        })
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      })
    })
  }

  it('deve mostrar loading inicialmente', () => {
    mockFetch.mockImplementation(() => new Promise(() => {}))
    render(<DashboardPage />)
    expect(screen.getByText('Carregando dashboard...')).toBeInTheDocument()
  })

  it('deve renderizar header apos carregar', async () => {
    setupMockFetch()
    render(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByTestId('dashboard-header')).toBeInTheDocument()
    })
  })

  it('deve mostrar status online', async () => {
    setupMockFetch()
    render(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByTestId('julia-status')).toHaveTextContent('online')
    })
  })

  it('deve mostrar periodo selecionado padrao 7d', async () => {
    setupMockFetch()
    render(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByTestId('selected-period')).toHaveTextContent('7d')
    })
  })

  it('deve renderizar banner de alertas criticos', async () => {
    setupMockFetch()
    render(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByTestId('critical-alerts')).toBeInTheDocument()
    })
  })

  it('deve renderizar secao de metricas quando tiver dados', async () => {
    setupMockFetch()
    render(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByTestId('metrics-section')).toBeInTheDocument()
    })
  })

  it('deve renderizar secao de qualidade quando tiver dados', async () => {
    setupMockFetch()
    render(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByTestId('quality-section')).toBeInTheDocument()
    })
  })

  it('deve renderizar status operacional', async () => {
    setupMockFetch()
    render(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByTestId('operational-status')).toBeInTheDocument()
    })
  })

  it('deve renderizar pool de chips', async () => {
    setupMockFetch()
    render(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByTestId('chip-pool')).toBeInTheDocument()
    })
  })

  it('deve renderizar lista de chips', async () => {
    setupMockFetch()
    render(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByTestId('chip-list')).toBeInTheDocument()
    })
  })

  it('deve renderizar funil de conversao', async () => {
    setupMockFetch()
    render(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByTestId('funnel')).toBeInTheDocument()
    })
  })

  it('deve renderizar lista de alertas', async () => {
    setupMockFetch()
    render(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByTestId('alerts')).toBeInTheDocument()
    })
  })

  it('deve renderizar feed de atividades', async () => {
    setupMockFetch()
    render(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByTestId('activity')).toBeInTheDocument()
    })
  })

  it('deve fazer fetch de todas as APIs ao montar', async () => {
    setupMockFetch()
    render(<DashboardPage />)
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('/api/dashboard/status'))
      expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('/api/dashboard/chips'))
      expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('/api/dashboard/metrics'))
    })
  })

  it('deve lidar com erro na API graciosamente', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/dashboard/status')) {
        return Promise.resolve({
          ok: false,
          status: 500,
          json: () => Promise.resolve({ error: 'Internal error' }),
        })
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      })
    })

    render(<DashboardPage />)

    // Deve ainda renderizar o dashboard mesmo com erros
    await waitFor(() => {
      expect(screen.getByTestId('dashboard-header')).toBeInTheDocument()
    })
  })
})
