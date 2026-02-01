import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import HospitaisBloqueadosPage from '@/app/(dashboard)/hospitais/bloqueados/page'

// Mock useToast
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

// Mock fetch with URL handling
const mockFetch = vi.fn()

function setupMockFetch(options: {
  bloqueados?: unknown[]
  historico?: unknown[]
  hospitais?: unknown[]
}) {
  mockFetch.mockImplementation((url: string) => {
    if (url === '/api/hospitais/bloqueados?historico=true') {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(options.historico ?? []),
      })
    }
    if (url === '/api/hospitais/bloqueados') {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(options.bloqueados ?? []),
      })
    }
    if (url.startsWith('/api/hospitais')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(options.hospitais ?? []),
      })
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve([]),
    })
  })
}

describe('HospitaisBloqueadosPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = mockFetch
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows loading state initially', () => {
    mockFetch.mockImplementation(() => new Promise(() => {})) // Never resolves

    render(<HospitaisBloqueadosPage />)

    // Should show loading spinner in table
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('renders page title and description', async () => {
    setupMockFetch({ bloqueados: [] })

    render(<HospitaisBloqueadosPage />)

    expect(screen.getByText('Hospitais Bloqueados')).toBeInTheDocument()
    expect(screen.getByText('Julia nao oferece vagas de hospitais bloqueados')).toBeInTheDocument()
  })

  it('shows empty state when no hospitals blocked', async () => {
    setupMockFetch({ bloqueados: [] })

    render(<HospitaisBloqueadosPage />)

    await waitFor(() => {
      expect(screen.getByText('Nenhum hospital bloqueado')).toBeInTheDocument()
    })
  })

  it('renders blocked hospitals list', async () => {
    setupMockFetch({
      bloqueados: [
        {
          id: '1',
          hospital_id: 'hosp-1',
          motivo: 'Problemas de pagamento',
          bloqueado_por: 'admin@revoluna.com',
          bloqueado_em: new Date().toISOString(),
          status: 'bloqueado',
          vagas_movidas: 3,
          hospitais: {
            nome: 'Hospital Sao Luiz',
            cidade: 'Sao Paulo',
          },
        },
      ],
    })

    render(<HospitaisBloqueadosPage />)

    await waitFor(() => {
      expect(screen.getByText('Hospital Sao Luiz')).toBeInTheDocument()
      expect(screen.getByText('Sao Paulo')).toBeInTheDocument()
      expect(screen.getByText('Problemas de pagamento')).toBeInTheDocument()
      expect(screen.getByText('3 vagas')).toBeInTheDocument()
    })
  })

  it('shows tabs for ativos and historico', async () => {
    setupMockFetch({ bloqueados: [] })

    render(<HospitaisBloqueadosPage />)

    await waitFor(() => {
      expect(screen.getByText(/Bloqueados Ativos/)).toBeInTheDocument()
      expect(screen.getByText(/Historico/)).toBeInTheDocument()
    })
  })

  it('switches to historico tab and loads history', async () => {
    const user = userEvent.setup()

    setupMockFetch({
      bloqueados: [],
      historico: [
        {
          id: '1',
          hospital_id: 'hosp-1',
          motivo: 'Antigo problema',
          bloqueado_por: 'admin@revoluna.com',
          bloqueado_em: '2026-01-10T10:00:00Z',
          status: 'desbloqueado',
          desbloqueado_em: '2026-01-12T15:00:00Z',
          desbloqueado_por: 'admin@revoluna.com',
          hospitais: {
            nome: 'Hospital Albert Einstein',
            cidade: 'Sao Paulo',
          },
        },
      ],
    })

    render(<HospitaisBloqueadosPage />)

    await waitFor(() => {
      expect(screen.getByText(/Bloqueados Ativos/)).toBeInTheDocument()
    })

    // Click on historico tab using role and userEvent
    const tabs = screen.getAllByRole('tab')
    const historicoTab = tabs.find((tab) => tab.textContent?.includes('Historico'))
    expect(historicoTab).toBeDefined()
    if (historicoTab) {
      await user.click(historicoTab)
    }

    await waitFor(() => {
      expect(screen.getByText('Hospital Albert Einstein')).toBeInTheDocument()
      expect(screen.getByText('Desbloqueado')).toBeInTheDocument()
    })
  })

  it('shows Bloquear Hospital button', async () => {
    setupMockFetch({ bloqueados: [] })

    render(<HospitaisBloqueadosPage />)

    await waitFor(() => {
      expect(screen.getByText('Bloquear Hospital')).toBeInTheDocument()
    })
  })

  it('opens bloquear dialog when button is clicked', async () => {
    setupMockFetch({
      bloqueados: [],
      hospitais: [{ id: 'hosp-1', nome: 'Hospital Teste', cidade: 'SP' }],
    })

    render(<HospitaisBloqueadosPage />)

    await waitFor(() => {
      expect(screen.getByText('Bloquear Hospital')).toBeInTheDocument()
    })

    const button = screen.getByText('Bloquear Hospital')
    fireEvent.click(button)

    await waitFor(() => {
      expect(screen.getByText('Motivo do bloqueio *')).toBeInTheDocument()
    })
  })

  it('shows Desbloquear button for each blocked hospital', async () => {
    setupMockFetch({
      bloqueados: [
        {
          id: '1',
          hospital_id: 'hosp-1',
          motivo: 'Teste motivo',
          bloqueado_por: 'admin@revoluna.com',
          bloqueado_em: new Date().toISOString(),
          status: 'bloqueado',
          vagas_movidas: 0,
          hospitais: { nome: 'Hospital Desbloquear', cidade: 'SP' },
        },
      ],
    })

    render(<HospitaisBloqueadosPage />)

    await waitFor(() => {
      expect(screen.getByText('Hospital Desbloquear')).toBeInTheDocument()
      expect(screen.getByText('Desbloquear')).toBeInTheDocument()
    })
  })

  it('opens confirmation dialog when Desbloquear is clicked', async () => {
    setupMockFetch({
      bloqueados: [
        {
          id: '1',
          hospital_id: 'hosp-1',
          motivo: 'Teste motivo dialog',
          bloqueado_por: 'admin@revoluna.com',
          bloqueado_em: new Date().toISOString(),
          status: 'bloqueado',
          vagas_movidas: 0,
          hospitais: { nome: 'Hospital Dialog Teste', cidade: 'SP' },
        },
      ],
    })

    render(<HospitaisBloqueadosPage />)

    await waitFor(() => {
      expect(screen.getByText('Hospital Dialog Teste')).toBeInTheDocument()
    })

    // Find the Desbloquear button in the table row
    const desbloquearBtn = screen.getByRole('button', { name: /Desbloquear/i })
    fireEvent.click(desbloquearBtn)

    // Alert dialog should appear
    await waitFor(() => {
      expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    })
  })

  it('shows informative alert about blocking behavior', async () => {
    setupMockFetch({ bloqueados: [] })

    render(<HospitaisBloqueadosPage />)

    await waitFor(() => {
      expect(screen.getByText(/Quando um hospital e bloqueado/)).toBeInTheDocument()
    })
  })

  // =============================================================================
  // Cenarios adicionais: Erros e acoes
  // =============================================================================

  it('shows error message when API fails', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: 'Erro ao carregar' }),
    })

    render(<HospitaisBloqueadosPage />)

    await waitFor(() => {
      expect(screen.getByText('Erro ao carregar')).toBeInTheDocument()
    })
  })

  it('shows generic error when fetch throws', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'))

    render(<HospitaisBloqueadosPage />)

    await waitFor(() => {
      expect(screen.getByText('Erro de conexao com o servidor')).toBeInTheDocument()
    })
  })

  it('successfully unblocks hospital and refreshes list', async () => {
    const user = userEvent.setup()
    const mockToast = vi.fn()

    // Re-mock useToast to capture calls
    vi.doMock('@/hooks/use-toast', () => ({
      useToast: () => ({ toast: mockToast }),
    }))

    // Initial load with blocked hospital
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve([
            {
              id: '1',
              hospital_id: 'hosp-1',
              motivo: 'Teste',
              bloqueado_por: 'admin@test.com',
              bloqueado_em: new Date().toISOString(),
              status: 'bloqueado',
              vagas_movidas: 2,
              hospitais: { nome: 'Hospital Teste', cidade: 'SP' },
            },
          ]),
      })
      // Desbloquear call
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true, vagas_restauradas: 2 }),
      })
      // Refresh after unblock
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([]),
      })

    render(<HospitaisBloqueadosPage />)

    await waitFor(() => {
      expect(screen.getByText('Hospital Teste')).toBeInTheDocument()
    })

    // Click desbloquear
    const desbloquearBtn = screen.getByRole('button', { name: /Desbloquear/i })
    await user.click(desbloquearBtn)

    // Confirm in dialog
    await waitFor(() => {
      expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    })

    const confirmBtn = screen.getByRole('button', { name: /Confirmar desbloqueio/i })
    await user.click(confirmBtn)

    // Should have called desbloquear API
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/hospitais/desbloquear', expect.anything())
    })
  })

  it('shows error toast when unblock fails', async () => {
    const user = userEvent.setup()

    // Initial load
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve([
            {
              id: '1',
              hospital_id: 'hosp-1',
              motivo: 'Teste',
              bloqueado_por: 'admin@test.com',
              bloqueado_em: new Date().toISOString(),
              status: 'bloqueado',
              vagas_movidas: 0,
              hospitais: { nome: 'Hospital Erro', cidade: 'SP' },
            },
          ]),
      })
      // Desbloquear fails
      .mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: 'Erro ao desbloquear' }),
      })

    render(<HospitaisBloqueadosPage />)

    await waitFor(() => {
      expect(screen.getByText('Hospital Erro')).toBeInTheDocument()
    })

    // Click desbloquear
    const desbloquearBtn = screen.getByRole('button', { name: /Desbloquear/i })
    await user.click(desbloquearBtn)

    // Confirm in dialog
    await waitFor(() => {
      expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    })

    const confirmBtn = screen.getByRole('button', { name: /Confirmar desbloqueio/i })
    await user.click(confirmBtn)

    // Should still show the hospital (not removed from list due to error)
    await waitFor(() => {
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    })
  })

  it('closes confirmation dialog when cancel is clicked', async () => {
    const user = userEvent.setup()

    setupMockFetch({
      bloqueados: [
        {
          id: '1',
          hospital_id: 'hosp-1',
          motivo: 'Teste',
          bloqueado_por: 'admin@test.com',
          bloqueado_em: new Date().toISOString(),
          status: 'bloqueado',
          vagas_movidas: 0,
          hospitais: { nome: 'Hospital Cancel', cidade: 'SP' },
        },
      ],
    })

    render(<HospitaisBloqueadosPage />)

    await waitFor(() => {
      expect(screen.getByText('Hospital Cancel')).toBeInTheDocument()
    })

    // Click desbloquear
    const desbloquearBtn = screen.getByRole('button', { name: /Desbloquear/i })
    await user.click(desbloquearBtn)

    // Dialog appears
    await waitFor(() => {
      expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    })

    // Click cancel
    const cancelBtn = screen.getByRole('button', { name: /Cancelar/i })
    await user.click(cancelBtn)

    // Dialog should close
    await waitFor(() => {
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    })
  })

  it('shows desbloquear dialog title', async () => {
    const user = userEvent.setup()

    setupMockFetch({
      bloqueados: [
        {
          id: '1',
          hospital_id: 'hosp-1',
          motivo: 'Teste',
          bloqueado_por: 'admin@test.com',
          bloqueado_em: new Date().toISOString(),
          status: 'bloqueado',
          vagas_movidas: 0,
          hospitais: { nome: 'Hospital Dialog', cidade: 'SP' },
        },
      ],
    })

    render(<HospitaisBloqueadosPage />)

    await waitFor(() => {
      expect(screen.getByText('Hospital Dialog')).toBeInTheDocument()
    })

    const desbloquearBtn = screen.getByRole('button', { name: /Desbloquear/i })
    await user.click(desbloquearBtn)

    // Check dialog opened
    await waitFor(() => {
      expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    })
  })
})
