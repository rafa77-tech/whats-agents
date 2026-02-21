/**
 * Tests for AnalyticsTab component
 */

import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import type { MetaCostSummary, MetaCostByChip, MetaCostByTemplate } from '@/types/meta'

const stableToast = vi.fn()
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: stableToast }),
}))

const mockGetCostSummary = vi.fn()
const mockGetCostByChip = vi.fn()
const mockGetCostByTemplate = vi.fn()

vi.mock('@/lib/api/meta', () => ({
  metaApi: {
    getCostSummary: (...args: unknown[]) => mockGetCostSummary(...args),
    getCostByChip: (...args: unknown[]) => mockGetCostByChip(...args),
    getCostByTemplate: (...args: unknown[]) => mockGetCostByTemplate(...args),
  },
}))

import AnalyticsTab from '@/components/meta/tabs/analytics-tab'

const mockSummary: MetaCostSummary = {
  total_messages: 500,
  free_messages: 100,
  paid_messages: 400,
  total_cost_usd: 12.5,
  by_category: { MARKETING: { count: 300, cost: 10 }, UTILITY: { count: 200, cost: 2.5 } },
}

const mockByChip: MetaCostByChip[] = [
  { chip_id: 'c1', chip_nome: 'Julia-01', total_messages: 250, total_cost_usd: 6.25 },
  { chip_id: 'c2', chip_nome: 'Julia-02', total_messages: 250, total_cost_usd: 6.25 },
]

const mockByTemplate: MetaCostByTemplate[] = [
  { template_name: 'discovery', category: 'MARKETING', total_sent: 300, total_cost_usd: 10 },
]

beforeEach(() => {
  mockGetCostSummary.mockReset()
  mockGetCostByChip.mockReset()
  mockGetCostByTemplate.mockReset()
  stableToast.mockReset()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('AnalyticsTab', () => {
  it('should show loading state initially', () => {
    mockGetCostSummary.mockReturnValue(new Promise(() => {}))
    mockGetCostByChip.mockReturnValue(new Promise(() => {}))
    mockGetCostByTemplate.mockReturnValue(new Promise(() => {}))
    render(<AnalyticsTab />)
    expect(screen.getByText('Carregando custos...')).toBeInTheDocument()
  })

  it('should render summary cards after loading', async () => {
    mockGetCostSummary.mockResolvedValue(mockSummary)
    mockGetCostByChip.mockResolvedValue(mockByChip)
    mockGetCostByTemplate.mockResolvedValue(mockByTemplate)
    render(<AnalyticsTab />)

    await waitFor(() => {
      expect(screen.getByText('Total Mensagens')).toBeInTheDocument()
    })
    expect(screen.getByText('500')).toBeInTheDocument()
    expect(screen.getByText('100')).toBeInTheDocument()
    expect(screen.getByText('400')).toBeInTheDocument()
    expect(screen.getByText('$12.50')).toBeInTheDocument()
  })

  it('should render cost by chip table', async () => {
    mockGetCostSummary.mockResolvedValue(mockSummary)
    mockGetCostByChip.mockResolvedValue(mockByChip)
    mockGetCostByTemplate.mockResolvedValue(mockByTemplate)
    render(<AnalyticsTab />)

    await waitFor(() => {
      expect(screen.getByText('Custo por Chip')).toBeInTheDocument()
    })
    expect(screen.getByText('Julia-01')).toBeInTheDocument()
    expect(screen.getByText('Julia-02')).toBeInTheDocument()
  })

  it('should render cost by template table', async () => {
    mockGetCostSummary.mockResolvedValue(mockSummary)
    mockGetCostByChip.mockResolvedValue(mockByChip)
    mockGetCostByTemplate.mockResolvedValue(mockByTemplate)
    render(<AnalyticsTab />)

    await waitFor(() => {
      expect(screen.getByText('Custo por Template')).toBeInTheDocument()
    })
    expect(screen.getByText('discovery')).toBeInTheDocument()
  })

  it('should show empty state for tables when no data', async () => {
    mockGetCostSummary.mockResolvedValue(mockSummary)
    mockGetCostByChip.mockResolvedValue([])
    mockGetCostByTemplate.mockResolvedValue([])
    render(<AnalyticsTab />)

    await waitFor(() => {
      expect(screen.getByText('Sem dados de custo por chip.')).toBeInTheDocument()
    })
    expect(screen.getByText('Sem dados de custo por template.')).toBeInTheDocument()
  })

  it('should not render summary cards when summary is null', async () => {
    mockGetCostSummary.mockResolvedValue(null)
    mockGetCostByChip.mockResolvedValue([])
    mockGetCostByTemplate.mockResolvedValue([])
    render(<AnalyticsTab />)

    await waitFor(() => {
      expect(screen.getByText('Custo por Chip')).toBeInTheDocument()
    })
    expect(screen.queryByText('Total Mensagens')).not.toBeInTheDocument()
  })
})
