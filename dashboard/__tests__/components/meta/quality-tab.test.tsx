/**
 * Tests for QualityTab component
 */

import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import type { MetaQualityOverview } from '@/types/meta'

const stableToast = vi.fn()
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: stableToast }),
}))

const mockGetQualityOverview = vi.fn()
vi.mock('@/lib/api/meta', () => ({
  metaApi: {
    getQualityOverview: (...args: unknown[]) => mockGetQualityOverview(...args),
  },
}))

import QualityTab from '@/components/meta/tabs/quality-tab'

const mockOverview: MetaQualityOverview = {
  total: 5,
  green: 3,
  yellow: 1,
  red: 1,
  unknown: 0,
  chips: [
    {
      chip_id: 'c1',
      chip_nome: 'Julia-01',
      waba_id: 'waba1',
      quality_rating: 'GREEN',
      trust_score: 95,
      status: 'active',
    },
    {
      chip_id: 'c2',
      chip_nome: 'Julia-02',
      waba_id: 'waba1',
      quality_rating: 'RED',
      trust_score: 30,
      status: 'active',
    },
  ],
}

beforeEach(() => {
  mockGetQualityOverview.mockReset()
  stableToast.mockReset()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('QualityTab', () => {
  it('should show loading state initially', () => {
    mockGetQualityOverview.mockReturnValue(new Promise(() => {}))
    render(<QualityTab />)
    expect(screen.getByText('Carregando qualidade...')).toBeInTheDocument()
  })

  it('should render overview cards with counts', async () => {
    mockGetQualityOverview.mockResolvedValue(mockOverview)
    render(<QualityTab />)

    await waitFor(() => {
      expect(screen.getByText('Total Chips')).toBeInTheDocument()
    })
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('should render chip list with names', async () => {
    mockGetQualityOverview.mockResolvedValue(mockOverview)
    render(<QualityTab />)

    await waitFor(() => {
      expect(screen.getByText('Julia-01')).toBeInTheDocument()
    })
    expect(screen.getByText('Julia-02')).toBeInTheDocument()
  })

  it('should display trust scores', async () => {
    mockGetQualityOverview.mockResolvedValue(mockOverview)
    render(<QualityTab />)

    await waitFor(() => {
      expect(screen.getByText('Trust: 95')).toBeInTheDocument()
    })
    expect(screen.getByText('Trust: 30')).toBeInTheDocument()
  })

  it('should display quality rating badges', async () => {
    mockGetQualityOverview.mockResolvedValue(mockOverview)
    render(<QualityTab />)

    await waitFor(() => {
      // "Verde" appears in both the overview card label and the chip badge
      expect(screen.getAllByText('Verde')).toHaveLength(2)
    })
    expect(screen.getAllByText('Vermelho')).toHaveLength(2)
  })

  it('should show unavailable state when no data', async () => {
    mockGetQualityOverview.mockResolvedValue(null)
    render(<QualityTab />)

    await waitFor(() => {
      expect(screen.getByText('Dados de qualidade indisponiveis.')).toBeInTheDocument()
    })
  })
})
