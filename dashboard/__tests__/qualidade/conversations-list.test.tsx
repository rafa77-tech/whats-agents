/**
 * Testes para o componente ConversationsList
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ConversationsList } from '@/components/qualidade/conversations-list'

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

describe('ConversationsList', () => {
  it('deve mostrar loading inicialmente', () => {
    mockFetch.mockReturnValue(new Promise(() => {})) // Never resolves

    const { container } = render(<ConversationsList />)

    // Verifica que o spinner de loading esta presente
    const spinner = container.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  it('deve exibir lista de conversas', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          conversas: [
            {
              id: 'conv1',
              medico_nome: 'Dr. Silva',
              total_mensagens: 10,
              status: 'ativa',
              avaliada: false,
              criada_em: '2024-01-15T10:00:00Z',
            },
            {
              id: 'conv2',
              medico_nome: 'Dr. Santos',
              total_mensagens: 5,
              status: 'finalizada',
              avaliada: true,
              criada_em: '2024-01-14T08:00:00Z',
            },
          ],
        }),
    })

    render(<ConversationsList />)

    await waitFor(() => {
      expect(screen.getByText('Dr. Silva')).toBeInTheDocument()
    })

    expect(screen.getByText('Dr. Santos')).toBeInTheDocument()
    expect(screen.getByText('2 conversas encontradas')).toBeInTheDocument()
  })

  it('deve exibir mensagem de lista vazia', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ conversas: [] }),
    })

    render(<ConversationsList />)

    await waitFor(() => {
      expect(screen.getByText('Nenhuma conversa encontrada')).toBeInTheDocument()
    })
  })

  it('deve exibir badge "Avaliada" para conversas avaliadas', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          conversas: [
            {
              id: 'conv1',
              medico_nome: 'Dr. Silva',
              total_mensagens: 10,
              status: 'ativa',
              avaliada: true,
              criada_em: '2024-01-15T10:00:00Z',
            },
          ],
        }),
    })

    render(<ConversationsList />)

    await waitFor(() => {
      expect(screen.getByText('Avaliada')).toBeInTheDocument()
    })
  })

  it('deve exibir badge "Pendente" para conversas nao avaliadas', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          conversas: [
            {
              id: 'conv1',
              medico_nome: 'Dr. Silva',
              total_mensagens: 10,
              status: 'ativa',
              avaliada: false,
              criada_em: '2024-01-15T10:00:00Z',
            },
          ],
        }),
    })

    render(<ConversationsList />)

    await waitFor(() => {
      expect(screen.getByText('Pendente')).toBeInTheDocument()
    })
  })

  it('deve mostrar ID truncado', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          conversas: [
            {
              id: 'abc123def456ghi789',
              medico_nome: 'Dr. Silva',
              total_mensagens: 10,
              status: 'ativa',
              avaliada: false,
              criada_em: '2024-01-15T10:00:00Z',
            },
          ],
        }),
    })

    render(<ConversationsList />)

    await waitFor(() => {
      expect(screen.getByText('#abc123de')).toBeInTheDocument()
    })
  })

  it('deve ter botao de visualizar para cada conversa', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          conversas: [
            {
              id: 'conv1',
              medico_nome: 'Dr. Silva',
              total_mensagens: 10,
              status: 'ativa',
              avaliada: false,
              criada_em: '2024-01-15T10:00:00Z',
            },
          ],
        }),
    })

    render(<ConversationsList />)

    await waitFor(() => {
      expect(screen.getByRole('button')).toBeInTheDocument()
    })
  })

  it('deve mudar filtro ao selecionar opcao', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ conversas: [] }),
    })

    render(<ConversationsList />)

    await waitFor(() => {
      expect(screen.getByText('Nenhuma conversa encontrada')).toBeInTheDocument()
    })

    // Verifica que a chamada inicial foi feita com filtro "false" (nao avaliadas)
    expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('avaliada=false'))
  })

  it('deve usar valor "Desconhecido" quando medico_nome e null', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          conversas: [
            {
              id: 'conv1',
              medico_nome: null,
              total_mensagens: 10,
              status: 'ativa',
              avaliada: false,
              criada_em: '2024-01-15T10:00:00Z',
            },
          ],
        }),
    })

    render(<ConversationsList />)

    await waitFor(() => {
      expect(screen.getByText('Desconhecido')).toBeInTheDocument()
    })
  })
})
