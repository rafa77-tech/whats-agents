import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BloquearHospitalDialog } from '@/components/hospitais/bloquear-dialog'

// Mock useToast
const mockToast = vi.fn()
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: mockToast,
  }),
}))

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('BloquearHospitalDialog', () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    onSuccess: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads hospitals when dialog opens', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve([
          { id: '1', nome: 'Hospital A', cidade: 'SP', vagas_abertas: 5 },
          { id: '2', nome: 'Hospital B', cidade: 'RJ', vagas_abertas: 3 },
        ]),
    })

    render(<BloquearHospitalDialog {...defaultProps} />)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/hospitais?excluir_bloqueados=true')
    })
  })

  it('shows dialog title', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([]),
    })

    render(<BloquearHospitalDialog {...defaultProps} />)

    // Use role to be more specific - dialog title
    expect(screen.getByRole('heading', { name: 'Bloquear Hospital' })).toBeInTheDocument()
  })

  it('shows hospital selector placeholder', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([]),
    })

    render(<BloquearHospitalDialog {...defaultProps} />)

    expect(screen.getByText('Selecione um hospital...')).toBeInTheDocument()
  })

  it('shows motivo textarea', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([]),
    })

    render(<BloquearHospitalDialog {...defaultProps} />)

    expect(screen.getByText('Motivo do bloqueio *')).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Problemas de pagamento/)).toBeInTheDocument()
  })

  it('disables submit button when no hospital selected', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([]),
    })

    render(<BloquearHospitalDialog {...defaultProps} />)

    // Find the Bloquear Hospital submit button (in DialogFooter)
    const submitButton = screen
      .getAllByRole('button')
      .find((b) => b.textContent === 'Bloquear Hospital')

    expect(submitButton).toBeDisabled()
  })

  it('disables submit button when no motivo provided', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve([{ id: '1', nome: 'Hospital A', cidade: 'SP', vagas_abertas: 0 }]),
    })

    render(<BloquearHospitalDialog {...defaultProps} />)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })

    // Submit button should still be disabled because no motivo
    const submitButton = screen
      .getAllByRole('button')
      .find((b) => b.textContent === 'Bloquear Hospital')

    expect(submitButton).toBeDisabled()
  })

  it('shows cancel button', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([]),
    })

    render(<BloquearHospitalDialog {...defaultProps} />)

    expect(screen.getByText('Cancelar')).toBeInTheDocument()
  })

  it('calls onOpenChange(false) when cancel is clicked', async () => {
    const onOpenChange = vi.fn()
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([]),
    })

    render(<BloquearHospitalDialog {...defaultProps} onOpenChange={onOpenChange} />)

    const cancelButton = screen.getByText('Cancelar')
    fireEvent.click(cancelButton)

    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('shows loading state in combobox', async () => {
    mockFetch.mockImplementation(() => new Promise(() => {})) // Never resolves

    render(<BloquearHospitalDialog {...defaultProps} />)

    // Open combobox
    const trigger = screen.getByText('Selecione um hospital...')
    fireEvent.click(trigger)

    await waitFor(() => {
      expect(screen.getByText('Carregando...')).toBeInTheDocument()
    })
  })

  it('does not load hospitals when dialog is closed', () => {
    render(<BloquearHospitalDialog {...defaultProps} open={false} />)

    expect(mockFetch).not.toHaveBeenCalled()
  })
})
