/**
 * Testes para o componente SuggestionsList
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { SuggestionsList } from '@/components/qualidade/suggestions-list'

// =============================================================================
// Mocks
// =============================================================================

const mockFetch = vi.fn()

beforeEach(() => {
  vi.stubGlobal('fetch', mockFetch)
  mockFetch.mockReset()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

// =============================================================================
// Tests
// =============================================================================

describe('SuggestionsList', () => {
  it('deve mostrar loading inicialmente', () => {
    mockFetch.mockReturnValue(new Promise(() => {})) // Never resolves

    const { container } = render(<SuggestionsList />)

    // Verifica que o spinner de loading esta presente
    const spinner = container.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  it('deve exibir lista de sugestoes', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          sugestoes: [
            {
              id: 'sug1',
              tipo: 'tom',
              descricao: 'Usar tom mais informal',
              status: 'pending',
              criada_em: '2024-01-15T10:00:00Z',
            },
            {
              id: 'sug2',
              tipo: 'objecao',
              descricao: 'Tratar objecao de preco',
              status: 'approved',
              criada_em: '2024-01-14T08:00:00Z',
            },
          ],
        }),
    })

    render(<SuggestionsList />)

    await waitFor(() => {
      expect(screen.getByText('Usar tom mais informal')).toBeInTheDocument()
    })

    expect(screen.getByText('Tratar objecao de preco')).toBeInTheDocument()
    expect(screen.getByText('2 sugestoes encontradas')).toBeInTheDocument()
  })

  it('deve exibir mensagem de lista vazia', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ sugestoes: [] }),
    })

    render(<SuggestionsList />)

    await waitFor(() => {
      expect(screen.getByText('Nenhuma sugestao encontrada')).toBeInTheDocument()
    })
  })

  it('deve exibir badges de tipo corretamente', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          sugestoes: [
            {
              id: 'sug1',
              tipo: 'tom',
              descricao: 'Teste',
              status: 'pending',
              criada_em: '2024-01-15T10:00:00Z',
            },
          ],
        }),
    })

    render(<SuggestionsList />)

    await waitFor(() => {
      expect(screen.getByText('tom')).toBeInTheDocument()
    })
  })

  it('deve exibir badges de status corretamente', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          sugestoes: [
            {
              id: 'sug1',
              tipo: 'tom',
              descricao: 'Teste',
              status: 'pending',
              criada_em: '2024-01-15T10:00:00Z',
            },
          ],
        }),
    })

    render(<SuggestionsList />)

    await waitFor(() => {
      expect(screen.getByText('Pendente')).toBeInTheDocument()
    })
  })

  it('deve ter botao de nova sugestao', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ sugestoes: [] }),
    })

    render(<SuggestionsList />)

    await waitFor(() => {
      expect(screen.getByText('Nova Sugestao')).toBeInTheDocument()
    })
  })

  it('deve ter botoes de aprovar e rejeitar para sugestoes pendentes', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          sugestoes: [
            {
              id: 'sug1',
              tipo: 'tom',
              descricao: 'Teste',
              status: 'pending',
              criada_em: '2024-01-15T10:00:00Z',
            },
          ],
        }),
    })

    render(<SuggestionsList />)

    await waitFor(() => {
      // Verifica que existem botoes de acao (X e Check)
      const buttons = screen.getAllByRole('button')
      // Deve ter: Nova Sugestao + 2 botoes de acao
      expect(buttons.length).toBeGreaterThanOrEqual(3)
    })
  })

  it('nao deve ter botoes de acao para sugestoes aprovadas', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          sugestoes: [
            {
              id: 'sug1',
              tipo: 'tom',
              descricao: 'Teste',
              status: 'approved',
              criada_em: '2024-01-15T10:00:00Z',
            },
          ],
        }),
    })

    render(<SuggestionsList />)

    await waitFor(() => {
      expect(screen.getByText('Aprovada')).toBeInTheDocument()
    })

    // Apenas o botao "Nova Sugestao" deve estar visivel
    const buttons = screen.getAllByRole('button')
    expect(buttons).toHaveLength(1)
  })

  it('deve chamar API ao aprovar sugestao', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            sugestoes: [
              {
                id: 'sug1',
                tipo: 'tom',
                descricao: 'Teste',
                status: 'pending',
                criada_em: '2024-01-15T10:00:00Z',
              },
            ],
          }),
      })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ sugestoes: [] }),
      })

    render(<SuggestionsList />)

    await waitFor(() => {
      expect(screen.getByText('Teste')).toBeInTheDocument()
    })

    // Encontra o botao de aprovar (Check icon)
    const buttons = screen.getAllByRole('button')
    const approveButton = buttons[buttons.length - 1] // Ultimo botao e o de aprovar

    fireEvent.click(approveButton!)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/admin/sugestoes/sug1',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ status: 'approved' }),
        })
      )
    })
  })

  it('deve filtrar por status pendente por padrao', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ sugestoes: [] }),
    })

    render(<SuggestionsList />)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('status=pending'))
    })
  })
})
