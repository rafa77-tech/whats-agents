import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import SistemaPage from '@/app/(dashboard)/sistema/page'

// Mock useToast
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

const mockStatusData = (
  pilotMode: boolean,
  features: Record<string, boolean> = {
    discovery_automatico: !pilotMode,
    oferta_automatica: !pilotMode,
    reativacao_automatica: !pilotMode,
    feedback_automatico: !pilotMode,
  }
) => ({
  pilot_mode: pilotMode,
  autonomous_features: features,
})

const mockConfigData = {
  rate_limit: {
    msgs_por_hora: 20,
    msgs_por_dia: 100,
    intervalo_min: 45,
    intervalo_max: 180,
  },
  horario: {
    inicio: 8,
    fim: 20,
    dias: 'Segunda a Sexta',
  },
}

const setupMock = (
  statusData: ReturnType<typeof mockStatusData> | null,
  configData: typeof mockConfigData | null = mockConfigData
) => {
  mockFetch.mockImplementation((url: string) => {
    if (url.includes('/api/sistema/status')) {
      if (!statusData) {
        return Promise.reject(new Error('Network error'))
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(statusData),
      })
    }
    if (url.includes('/api/sistema/config')) {
      if (!configData) {
        return Promise.reject(new Error('Network error'))
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(configData),
      })
    }
    return Promise.reject(new Error('Unknown URL'))
  })
}

describe('SistemaPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', () => {
    mockFetch.mockImplementation(() => new Promise(() => {})) // Never resolves

    render(<SistemaPage />)

    expect(screen.getByText('Carregando...')).toBeInTheDocument()
  })

  it('renders pilot mode ACTIVE status correctly', async () => {
    setupMock(mockStatusData(true))

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('ATIVO')).toBeInTheDocument()
      expect(screen.getByText('Modo seguro ativo')).toBeInTheDocument()
    })
  })

  it('renders pilot mode INACTIVE status correctly', async () => {
    setupMock(mockStatusData(false))

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('DESATIVADO')).toBeInTheDocument()
      expect(screen.getByText('Julia autonoma')).toBeInTheDocument()
    })
  })

  it('shows all autonomous feature cards', async () => {
    setupMock(mockStatusData(false))

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('Discovery Automatico')).toBeInTheDocument()
      expect(screen.getByText('Oferta Automatica')).toBeInTheDocument()
      expect(screen.getByText('Reativacao Automatica')).toBeInTheDocument()
      expect(screen.getByText('Feedback Automatico')).toBeInTheDocument()
    })
  })

  it('shows rate limiting card', async () => {
    setupMock(mockStatusData(true))

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('Rate Limiting')).toBeInTheDocument()
      expect(screen.getByText('20')).toBeInTheDocument() // msgs por hora
      expect(screen.getByText('100')).toBeInTheDocument() // msgs por dia
    })
  })

  it('shows operating hours card', async () => {
    setupMock(mockStatusData(true))

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('Horario de Operacao')).toBeInTheDocument()
      expect(screen.getByText('08h as 20h')).toBeInTheDocument()
      expect(screen.getByText('Segunda a Sexta')).toBeInTheDocument()
    })
  })

  it('opens enable confirmation dialog when switch is toggled', async () => {
    setupMock(mockStatusData(false))

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('DESATIVADO')).toBeInTheDocument()
    })

    // Find the pilot mode switch (first switch in the document)
    const switches = screen.getAllByRole('switch')
    expect(switches.length).toBeGreaterThan(0)
    fireEvent.click(switches[0]!)

    await waitFor(() => {
      expect(screen.getByText('Ativar Modo Piloto?')).toBeInTheDocument()
    })
  })

  it('opens disable confirmation dialog when switch is toggled', async () => {
    setupMock(mockStatusData(true))

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('ATIVO')).toBeInTheDocument()
    })

    // Find the pilot mode switch (first switch in the document)
    const switches = screen.getAllByRole('switch')
    expect(switches.length).toBeGreaterThan(0)
    fireEvent.click(switches[0]!)

    await waitFor(() => {
      expect(screen.getByText('Desativar Modo Piloto?')).toBeInTheDocument()
      expect(screen.getByText(/Atencao: acao significativa/)).toBeInTheDocument()
    })
  })

  it('shows last changed info when available', async () => {
    const statusWithMeta = {
      ...mockStatusData(true),
      last_changed_at: '2026-01-16T10:00:00Z',
      last_changed_by: 'admin@revoluna.com',
    }
    setupMock(statusWithMeta)

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText(/Ultima alteracao:/)).toBeInTheDocument()
      expect(screen.getByText(/admin@revoluna.com/)).toBeInTheDocument()
    })
  })

  it('handles API error gracefully', async () => {
    setupMock(null)

    render(<SistemaPage />)

    // Should still show the page after loading (empty state from error)
    await waitFor(() => {
      expect(screen.queryByText('Carregando...')).not.toBeInTheDocument()
    })
  })

  it('disables feature switches when pilot mode is active', async () => {
    setupMock(mockStatusData(true))

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('ATIVO')).toBeInTheDocument()
    })

    // All feature switches should be disabled
    const switches = screen.getAllByRole('switch')
    // First switch is pilot mode, remaining are feature toggles
    for (let i = 1; i < switches.length; i++) {
      expect(switches[i]).toBeDisabled()
    }
  })

  it('enables feature switches when pilot mode is inactive', async () => {
    setupMock(mockStatusData(false))

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('DESATIVADO')).toBeInTheDocument()
    })

    // All feature switches should be enabled
    const switches = screen.getAllByRole('switch')
    // First switch is pilot mode, remaining are feature toggles
    for (let i = 1; i < switches.length; i++) {
      expect(switches[i]).not.toBeDisabled()
    }
  })
})
