/**
 * Testes para NovaInstrucaoDialog
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { NovaInstrucaoDialog } from '@/components/instrucoes/nova-instrucao-dialog'

// Mock useApiError
vi.mock('@/hooks/use-api-error', () => ({
  useApiError: () => ({
    handleError: vi.fn(),
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

describe('NovaInstrucaoDialog', () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    onSuccess: vi.fn(),
  }

  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch)
    mockFetch.mockReset()

    // Default mocks for hospital and especialidade lists
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/hospitais')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([{ id: '1', nome: 'Hospital A' }]),
        })
      }
      if (url.includes('/api/especialidades')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([{ id: '1', nome: 'Cardiologia' }]),
        })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('deve renderizar titulo do dialog', async () => {
    render(<NovaInstrucaoDialog {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByText('Nova Instrucao')).toBeInTheDocument()
    })
  })

  it('deve renderizar opcoes de tipo de instrucao', async () => {
    render(<NovaInstrucaoDialog {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByText('Tipo de instrucao')).toBeInTheDocument()
      expect(screen.getByText('Margem de Negociacao')).toBeInTheDocument()
      expect(screen.getByText('Regra Especial')).toBeInTheDocument()
      expect(screen.getByText('Informacao Adicional')).toBeInTheDocument()
    })
  })

  it('deve renderizar select de escopo', async () => {
    render(<NovaInstrucaoDialog {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByText('Aplica-se a')).toBeInTheDocument()
    })
  })

  it('deve mostrar campos de margem quando tipo margem_negociacao selecionado', async () => {
    render(<NovaInstrucaoDialog {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByText('Valor maximo (R$)')).toBeInTheDocument()
      expect(screen.getByText('Percentual maximo acima do base (%)')).toBeInTheDocument()
    })
  })

  it('deve mostrar campo de regra quando tipo regra_especial selecionado', async () => {
    render(<NovaInstrucaoDialog {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByText('Margem de Negociacao')).toBeInTheDocument()
    })

    // Selecionar regra especial
    const regraRadio = screen.getByLabelText('Regra Especial')
    fireEvent.click(regraRadio)

    await waitFor(() => {
      expect(screen.getByText('Regra')).toBeInTheDocument()
    })
  })

  it('deve mostrar campo de info quando tipo info_adicional selecionado', async () => {
    render(<NovaInstrucaoDialog {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByText('Margem de Negociacao')).toBeInTheDocument()
    })

    // Selecionar info adicional
    const infoRadio = screen.getByLabelText('Informacao Adicional')
    fireEvent.click(infoRadio)

    await waitFor(() => {
      expect(screen.getByText('Informacao')).toBeInTheDocument()
    })
  })

  it('deve ter campo de expiracao opcional', async () => {
    render(<NovaInstrucaoDialog {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByText('Expira em (opcional)')).toBeInTheDocument()
      expect(screen.getByText('Deixe vazio para nao expirar automaticamente')).toBeInTheDocument()
    })
  })

  it('deve ter botao cancelar', async () => {
    render(<NovaInstrucaoDialog {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /cancelar/i })).toBeInTheDocument()
    })
  })

  it('deve ter botao criar instrucao', async () => {
    render(<NovaInstrucaoDialog {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /criar instrucao/i })).toBeInTheDocument()
    })
  })

  it('deve desabilitar botao criar quando form invalido', async () => {
    render(<NovaInstrucaoDialog {...defaultProps} />)

    await waitFor(() => {
      const createButton = screen.getByRole('button', { name: /criar instrucao/i })
      expect(createButton).toBeDisabled()
    })
  })

  it('deve habilitar botao criar quando form valido', async () => {
    render(<NovaInstrucaoDialog {...defaultProps} />)

    await waitFor(() => {
      expect(screen.getByText('Valor maximo (R$)')).toBeInTheDocument()
    })

    // Preencher valor maximo
    const valorInput = screen.getByPlaceholderText('Ex: 3000')
    fireEvent.change(valorInput, { target: { value: '3000' } })

    await waitFor(() => {
      const createButton = screen.getByRole('button', { name: /criar instrucao/i })
      expect(createButton).not.toBeDisabled()
    })
  })

  it('deve chamar onOpenChange ao clicar em cancelar', async () => {
    const onOpenChange = vi.fn()
    render(<NovaInstrucaoDialog {...defaultProps} onOpenChange={onOpenChange} />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /cancelar/i })).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /cancelar/i }))

    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('deve carregar hospitais e especialidades ao abrir', async () => {
    render(<NovaInstrucaoDialog {...defaultProps} />)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/hospitais')
      expect(mockFetch).toHaveBeenCalledWith('/api/especialidades')
    })
  })

  it('nao deve renderizar quando open=false', () => {
    render(<NovaInstrucaoDialog {...defaultProps} open={false} />)

    expect(screen.queryByText('Nova Instrucao')).not.toBeInTheDocument()
  })
})
