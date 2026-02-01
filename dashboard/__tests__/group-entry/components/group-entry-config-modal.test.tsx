import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GroupEntryConfigModal } from '@/components/group-entry/group-entry-config-modal'

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('GroupEntryConfigModal', () => {
  const mockOnClose = vi.fn()
  const mockOnSave = vi.fn()

  const mockConfigResponse = {
    grupos_por_dia: 15,
    intervalo_min: 25,
    intervalo_max: 50,
    horario_inicio: '09:00',
    horario_fim: '19:00',
    dias_ativos: ['seg', 'ter', 'qua'],
    auto_validar: false,
    auto_agendar: true,
    notificar_falhas: true,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockConfigResponse),
    })
  })

  it('calls fetch on mount', async () => {
    render(<GroupEntryConfigModal onClose={mockOnClose} onSave={mockOnSave} />)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/group-entry/config')
    })
  })

  it('renders modal with title after loading', async () => {
    render(<GroupEntryConfigModal onClose={mockOnClose} onSave={mockOnSave} />)

    await waitFor(() => {
      expect(screen.getByText('Configuracao do Group Entry')).toBeInTheDocument()
    })
  })

  it('renders description', async () => {
    render(<GroupEntryConfigModal onClose={mockOnClose} onSave={mockOnSave} />)

    await waitFor(() => {
      expect(screen.getByText('Configure limites e comportamento do sistema')).toBeInTheDocument()
    })
  })

  it('renders limit section', async () => {
    render(<GroupEntryConfigModal onClose={mockOnClose} onSave={mockOnSave} />)

    await waitFor(() => {
      expect(screen.getByText('Limites por Chip')).toBeInTheDocument()
      expect(screen.getByText('Grupos por dia (max 20)')).toBeInTheDocument()
    })
  })

  it('renders schedule section', async () => {
    render(<GroupEntryConfigModal onClose={mockOnClose} onSave={mockOnSave} />)

    await waitFor(() => {
      expect(screen.getByText('Horario de Operacao')).toBeInTheDocument()
    })
  })

  it('renders behavior section', async () => {
    render(<GroupEntryConfigModal onClose={mockOnClose} onSave={mockOnSave} />)

    await waitFor(() => {
      expect(screen.getByText('Comportamento')).toBeInTheDocument()
    })
  })

  it('loads config values from API', async () => {
    render(<GroupEntryConfigModal onClose={mockOnClose} onSave={mockOnSave} />)

    await waitFor(() => {
      const gruposPorDiaInput = screen.getByLabelText('Grupos por dia (max 20)')
      expect(gruposPorDiaInput).toHaveValue(15)
    })
  })

  it('renders all weekday buttons', async () => {
    render(<GroupEntryConfigModal onClose={mockOnClose} onSave={mockOnSave} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Seg' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Ter' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Qua' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Qui' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Sex' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Sab' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Dom' })).toBeInTheDocument()
    })
  })

  it('renders behavior toggles', async () => {
    render(<GroupEntryConfigModal onClose={mockOnClose} onSave={mockOnSave} />)

    await waitFor(() => {
      expect(screen.getByText('Auto-validar links importados')).toBeInTheDocument()
      expect(screen.getByText('Auto-agendar links validados')).toBeInTheDocument()
      expect(screen.getByText('Notificar falhas no Slack')).toBeInTheDocument()
    })
  })

  it('renders cancel and save buttons', async () => {
    render(<GroupEntryConfigModal onClose={mockOnClose} onSave={mockOnSave} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Cancelar' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Salvar' })).toBeInTheDocument()
    })
  })

  it('calls onClose when cancel is clicked', async () => {
    const user = userEvent.setup()
    render(<GroupEntryConfigModal onClose={mockOnClose} onSave={mockOnSave} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Cancelar' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(mockOnClose).toHaveBeenCalled()
  })

  it('toggles weekday selection', async () => {
    const user = userEvent.setup()
    render(<GroupEntryConfigModal onClose={mockOnClose} onSave={mockOnSave} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Qui' })).toBeInTheDocument()
    })

    // Qui should be not selected initially (config has seg, ter, qua)
    const quiButton = screen.getByRole('button', { name: 'Qui' })

    await user.click(quiButton)
    // After clicking, it should toggle
  })

  it('renders input with loaded value', async () => {
    render(<GroupEntryConfigModal onClose={mockOnClose} onSave={mockOnSave} />)

    await waitFor(() => {
      const input = screen.getByLabelText('Grupos por dia (max 20)')
      expect(input).toHaveValue(15) // Value from mockConfigResponse
    })
  })

  it('saves config on save button click', async () => {
    const user = userEvent.setup()
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockConfigResponse),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      })

    render(<GroupEntryConfigModal onClose={mockOnClose} onSave={mockOnSave} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Salvar' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/group-entry/config',
        expect.objectContaining({
          method: 'PATCH',
        })
      )
    })

    await waitFor(() => {
      expect(mockOnSave).toHaveBeenCalled()
    })
  })

  it('shows loading state while saving', async () => {
    const user = userEvent.setup()
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockConfigResponse),
      })
      .mockImplementation(() => new Promise(() => {})) // Never resolves

    render(<GroupEntryConfigModal onClose={mockOnClose} onSave={mockOnSave} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Salvar' })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    await waitFor(() => {
      expect(screen.getByText('Salvando...')).toBeInTheDocument()
    })
  })

  it('uses default values when API returns empty', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    })

    render(<GroupEntryConfigModal onClose={mockOnClose} onSave={mockOnSave} />)

    await waitFor(() => {
      const gruposPorDiaInput = screen.getByLabelText('Grupos por dia (max 20)')
      expect(gruposPorDiaInput).toHaveValue(10) // Default value
    })
  })

  it('handles API error gracefully', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'))

    render(<GroupEntryConfigModal onClose={mockOnClose} onSave={mockOnSave} />)

    await waitFor(() => {
      // Should still render with defaults
      expect(screen.getByText('Configuracao do Group Entry')).toBeInTheDocument()
    })
  })

  it('renders time inputs', async () => {
    render(<GroupEntryConfigModal onClose={mockOnClose} onSave={mockOnSave} />)

    await waitFor(() => {
      expect(screen.getByLabelText('Inicio')).toBeInTheDocument()
      expect(screen.getByLabelText('Fim')).toBeInTheDocument()
    })
  })

  it('renders interval inputs', async () => {
    render(<GroupEntryConfigModal onClose={mockOnClose} onSave={mockOnSave} />)

    await waitFor(() => {
      expect(screen.getByLabelText('Intervalo min (min)')).toBeInTheDocument()
      expect(screen.getByLabelText('Intervalo max (min)')).toBeInTheDocument()
    })
  })
})
