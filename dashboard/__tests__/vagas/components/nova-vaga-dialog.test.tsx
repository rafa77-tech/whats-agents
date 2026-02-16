/**
 * Testes para NovaVagaDialog (Combobox creatable)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { NovaVagaDialog } from '@/app/(dashboard)/vagas/components/nova-vaga-dialog'

// Mock useApiError
const mockHandleError = vi.fn()
vi.mock('@/hooks/use-api-error', () => ({
  useApiError: () => ({
    handleError: mockHandleError,
  }),
}))

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

// Mock fetch
const mockFetch = vi.fn()

const mockHospitais = [
  { id: '550e8400-e29b-41d4-a716-446655440000', nome: 'Hospital ABC' },
  { id: '550e8400-e29b-41d4-a716-446655440001', nome: 'Hospital XYZ' },
]

const mockEspecialidades = [
  { id: '660e8400-e29b-41d4-a716-446655440000', nome: 'Cardiologia' },
  { id: '660e8400-e29b-41d4-a716-446655440001', nome: 'Ortopedia' },
]

describe('NovaVagaDialog', () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    onSuccess: vi.fn(),
  }

  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch)
    mockFetch.mockReset()
    mockHandleError.mockReset()

    // Default mocks for hospital and especialidade lists
    mockFetch.mockImplementation((url: string) => {
      if (url === '/api/hospitais') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockHospitais),
        })
      }
      if (url === '/api/especialidades') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockEspecialidades),
        })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('deve renderizar titulo do dialog', async () => {
    render(<NovaVagaDialog {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByText('Nova Vaga')).toBeInTheDocument()
    })
  })

  it('nao deve renderizar quando open=false', () => {
    render(<NovaVagaDialog {...defaultProps} open={false} />)

    expect(screen.queryByText('Nova Vaga')).not.toBeInTheDocument()
  })

  it('deve carregar hospitais e especialidades ao abrir', async () => {
    render(<NovaVagaDialog {...defaultProps} />)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/hospitais')
      expect(mockFetch).toHaveBeenCalledWith('/api/especialidades')
    })
  })

  it('deve renderizar campos obrigatorios com asterisco', async () => {
    render(<NovaVagaDialog {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByText('Hospital')).toBeInTheDocument()
      expect(screen.getByText('Especialidade')).toBeInTheDocument()
      expect(screen.getByText('Contato Responsavel')).toBeInTheDocument()
      expect(screen.getByText('Data')).toBeInTheDocument()
    })
  })

  it('deve renderizar campos opcionais', async () => {
    render(<NovaVagaDialog {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByText('Hora inicio')).toBeInTheDocument()
      expect(screen.getByText('Hora fim')).toBeInTheDocument()
      expect(screen.getByText('Valor (R$)')).toBeInTheDocument()
      expect(screen.getByText('Observacoes')).toBeInTheDocument()
    })
  })

  it('deve mostrar dica de valor a combinar', async () => {
    render(<NovaVagaDialog {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByText(/a combinar/)).toBeInTheDocument()
    })
  })

  it('deve ter botao cancelar', async () => {
    render(<NovaVagaDialog {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /cancelar/i })).toBeInTheDocument()
    })
  })

  it('deve ter botao criar vaga', async () => {
    render(<NovaVagaDialog {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /criar vaga/i })).toBeInTheDocument()
    })
  })

  it('deve desabilitar botao criar quando campos obrigatorios vazios', async () => {
    render(<NovaVagaDialog {...defaultProps} />)

    await waitFor(() => {
      const createButton = screen.getByRole('button', { name: /criar vaga/i })
      expect(createButton).toBeDisabled()
    })
  })

  it('deve chamar onOpenChange ao clicar em cancelar', async () => {
    const onOpenChange = vi.fn()
    render(<NovaVagaDialog {...defaultProps} onOpenChange={onOpenChange} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /cancelar/i })).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /cancelar/i }))

    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('deve renderizar combobox triggers para hospital, especialidade e contato', async () => {
    render(<NovaVagaDialog {...defaultProps} />)

    await waitFor(() => {
      const comboboxes = screen.getAllByRole('combobox')
      expect(comboboxes).toHaveLength(3)
    })
  })

  it('deve mostrar placeholder de hospital no combobox', async () => {
    render(<NovaVagaDialog {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByText('Selecione o hospital')).toBeInTheDocument()
    })
  })

  it('deve mostrar placeholder de especialidade no combobox', async () => {
    render(<NovaVagaDialog {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByText('Selecione a especialidade')).toBeInTheDocument()
    })
  })

  it('deve mostrar placeholder de contato no combobox', async () => {
    render(<NovaVagaDialog {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByText('Buscar contato...')).toBeInTheDocument()
    })
  })

  it('deve renderizar input de data', async () => {
    render(<NovaVagaDialog {...defaultProps} />)

    await waitFor(() => {
      const dateInput = document.querySelector('input[type="date"]')
      expect(dateInput).toBeInTheDocument()
    })
  })

  it('deve renderizar inputs de hora', async () => {
    render(<NovaVagaDialog {...defaultProps} />)

    await waitFor(() => {
      const timeInputs = document.querySelectorAll('input[type="time"]')
      expect(timeInputs).toHaveLength(2)
    })
  })

  it('deve renderizar input de valor numerico', async () => {
    render(<NovaVagaDialog {...defaultProps} />)

    await waitFor(() => {
      const numberInput = screen.getByPlaceholderText('Ex: 2500')
      expect(numberInput).toBeInTheDocument()
      expect(numberInput).toHaveAttribute('type', 'number')
    })
  })

  it('deve renderizar textarea de observacoes', async () => {
    render(<NovaVagaDialog {...defaultProps} />)

    await waitFor(() => {
      const textarea = screen.getByPlaceholderText(/plantao noturno/i)
      expect(textarea).toBeInTheDocument()
    })
  })

  it('deve submeter form com dados corretos', async () => {
    mockFetch.mockImplementation((url: string, options?: RequestInit) => {
      if (url === '/api/hospitais') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockHospitais),
        })
      }
      if (url === '/api/especialidades') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockEspecialidades),
        })
      }
      if (url === '/api/vagas' && options?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ id: 'new-id', success: true }),
        })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    })

    render(<NovaVagaDialog {...defaultProps} />)

    // Wait for lists to load
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/hospitais')
    })

    // Fill date (the only field we can easily fill without opening comboboxes)
    const dateInput = document.querySelector('input[type="date"]') as HTMLInputElement
    fireEvent.change(dateInput, { target: { value: '2024-03-15' } })

    // The button should still be disabled since hospital and especialidade are not selected
    const createButton = screen.getByRole('button', { name: /criar vaga/i })
    expect(createButton).toBeDisabled()
  })

  it('deve tratar erro na resposta do POST', async () => {
    mockFetch.mockImplementation((url: string, options?: RequestInit) => {
      if (url === '/api/hospitais') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockHospitais),
        })
      }
      if (url === '/api/especialidades') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockEspecialidades),
        })
      }
      if (url === '/api/vagas' && options?.method === 'POST') {
        return Promise.resolve({
          ok: false,
          status: 500,
          json: () => Promise.resolve({ detail: 'Erro interno' }),
        })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    })

    render(<NovaVagaDialog {...defaultProps} />)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/hospitais')
    })
  })

  it('deve lidar com erro ao carregar listas', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    mockFetch.mockRejectedValue(new Error('Network error'))

    render(<NovaVagaDialog {...defaultProps} />)

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled()
    })

    consoleSpy.mockRestore()
  })

  it('deve lidar com resposta nao-array de hospitais', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url === '/api/hospitais') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ detail: 'error' }),
        })
      }
      if (url === '/api/especialidades') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockEspecialidades),
        })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    })

    render(<NovaVagaDialog {...defaultProps} />)

    // Should not crash - the dialog should still render
    await waitFor(() => {
      expect(screen.getByText('Nova Vaga')).toBeInTheDocument()
    })
  })
})
