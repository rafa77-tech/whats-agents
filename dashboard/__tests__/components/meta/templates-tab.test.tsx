/**
 * Tests for TemplatesTab component
 */

import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import type { MetaTemplateWithAnalytics } from '@/types/meta'

// Stable toast mock — must be same reference across renders
const stableToast = vi.fn()
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: stableToast }),
}))

// Mock metaApi
const mockGetTemplates = vi.fn()
vi.mock('@/lib/api/meta', () => ({
  metaApi: {
    getTemplates: (...args: unknown[]) => mockGetTemplates(...args),
  },
}))

import TemplatesTab from '@/components/meta/tabs/templates-tab'

const mockTemplates: MetaTemplateWithAnalytics[] = [
  {
    id: 't1',
    waba_id: 'waba1',
    template_name: 'discovery_plantao',
    category: 'MARKETING',
    status: 'APPROVED',
    language: 'pt_BR',
    body_text: 'Oi {{1}}',
    variable_mapping: {},
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    analytics: {
      template_name: 'discovery_plantao',
      total_sent: 150,
      total_delivered: 140,
      total_read: 90,
      delivery_rate: 0.93,
      read_rate: 0.6,
      cost_usd_7d: 1.25,
    },
  },
  {
    id: 't2',
    waba_id: 'waba1',
    template_name: 'confirmacao_otp',
    category: 'AUTHENTICATION',
    status: 'PENDING',
    language: 'pt_BR',
    body_text: 'Codigo: {{1}}',
    variable_mapping: {},
    created_at: '2026-01-02T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
  },
]

beforeEach(() => {
  mockGetTemplates.mockReset()
  stableToast.mockReset()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('TemplatesTab', () => {
  it('should show loading state initially', () => {
    mockGetTemplates.mockReturnValue(new Promise(() => {}))
    render(<TemplatesTab />)
    expect(screen.getByText('Carregando templates...')).toBeInTheDocument()
  })

  it('should render templates table after loading', async () => {
    mockGetTemplates.mockResolvedValue(mockTemplates)
    render(<TemplatesTab />)

    await waitFor(() => {
      expect(screen.getByText('discovery_plantao')).toBeInTheDocument()
    })
    expect(screen.getByText('Templates Meta')).toBeInTheDocument()
    expect(screen.getByText('confirmacao_otp')).toBeInTheDocument()
  })

  it('should display template status badges', async () => {
    mockGetTemplates.mockResolvedValue(mockTemplates)
    render(<TemplatesTab />)

    await waitFor(() => {
      expect(screen.getByText('APPROVED')).toBeInTheDocument()
    })
    expect(screen.getByText('PENDING')).toBeInTheDocument()
  })

  it('should display analytics data when available', async () => {
    mockGetTemplates.mockResolvedValue(mockTemplates)
    render(<TemplatesTab />)

    await waitFor(() => {
      expect(screen.getByText('150')).toBeInTheDocument()
    })
    expect(screen.getByText('93%')).toBeInTheDocument()
    expect(screen.getByText('60%')).toBeInTheDocument()
  })

  it('should show dash when analytics not available', async () => {
    mockGetTemplates.mockResolvedValue(mockTemplates)
    render(<TemplatesTab />)

    await waitFor(() => {
      expect(screen.getByRole('table')).toBeInTheDocument()
    })
    const rows = screen.getByRole('table').querySelectorAll('tbody tr')
    const lastRow = rows[1] as HTMLTableRowElement
    expect(lastRow).toBeDefined()
    const cells = lastRow.querySelectorAll('td')
    expect(cells[3]?.textContent).toBe('-')
  })

  it('should show empty state when no templates', async () => {
    mockGetTemplates.mockResolvedValue([])
    render(<TemplatesTab />)

    await waitFor(() => {
      expect(screen.getByText('Nenhum template Meta encontrado.')).toBeInTheDocument()
    })
  })
})
