/**
 * Testes para FunnelDrilldownModal - Sprint 34 E04
 *
 * Modal que mostra lista de médicos em cada estágio do funil.
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { FunnelDrilldownModal } from '@/components/dashboard/funnel-drilldown-modal'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'

// Mock de fetch global
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('FunnelDrilldownModal', () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    stage: 'responderam',
    period: '7d',
  }

  const mockDrilldownData = {
    stage: 'responderam',
    stageLabel: 'Responderam',
    total: 25,
    page: 1,
    pageSize: 10,
    items: [
      {
        id: '1',
        conversaId: 'conv-1',
        nome: 'Dr. João Silva',
        telefone: '5511999999999',
        especialidade: 'Cardiologia',
        ultimoContato: new Date().toISOString(),
        chipName: 'julia_01',
        chatwootUrl: 'https://chatwoot.example.com/conversations/1',
      },
      {
        id: '2',
        conversaId: 'conv-2',
        nome: 'Dra. Maria Santos',
        telefone: '5511888888888',
        especialidade: 'Pediatria',
        ultimoContato: new Date().toISOString(),
        chipName: 'julia_02',
        chatwootUrl: null,
      },
    ],
  }

  const mockMessages = {
    messages: [
      {
        id: 'msg-1',
        tipo: 'saida',
        conteudo: 'Oi Dr. João! Tudo bem?',
        timestamp: new Date().toISOString(),
        deliveryStatus: 'read',
        isFromJulia: true,
      },
      {
        id: 'msg-2',
        tipo: 'entrada',
        conteudo: 'Olá, tudo bem sim!',
        timestamp: new Date().toISOString(),
        deliveryStatus: null,
        isFromJulia: false,
      },
    ],
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockDrilldownData),
    })
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  describe('Renderização básica', () => {
    it('renderiza modal quando aberto', async () => {
      render(<FunnelDrilldownModal {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByText(/Medicos em/i)).toBeInTheDocument()
      })
    })

    it('não renderiza conteúdo quando fechado', () => {
      render(<FunnelDrilldownModal {...defaultProps} open={false} />)

      expect(screen.queryByText(/Medicos em/i)).not.toBeInTheDocument()
    })

    it('mostra título com stage label e total', async () => {
      render(<FunnelDrilldownModal {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByText(/Responderam/i)).toBeInTheDocument()
        // Total aparece no título do dialog
        expect(screen.getByRole('heading')).toHaveTextContent('25')
      })
    })

    it('mostra campo de busca', async () => {
      render(<FunnelDrilldownModal {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Buscar por nome...')).toBeInTheDocument()
      })
    })
  })

  describe('Tabela de médicos', () => {
    it('renderiza headers da tabela', async () => {
      render(<FunnelDrilldownModal {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByText('Nome')).toBeInTheDocument()
        expect(screen.getByText('Telefone')).toBeInTheDocument()
        expect(screen.getByText('Especialidade')).toBeInTheDocument()
        expect(screen.getByText('Ultimo Contato')).toBeInTheDocument()
        expect(screen.getByText('Chip')).toBeInTheDocument()
      })
    })

    it('renderiza dados dos médicos', async () => {
      render(<FunnelDrilldownModal {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByText('Dr. João Silva')).toBeInTheDocument()
        expect(screen.getByText('Dra. Maria Santos')).toBeInTheDocument()
        expect(screen.getByText('Cardiologia')).toBeInTheDocument()
        expect(screen.getByText('Pediatria')).toBeInTheDocument()
      })
    })

    it('mostra link para Chatwoot quando disponível', async () => {
      render(<FunnelDrilldownModal {...defaultProps} />)

      await waitFor(() => {
        const links = screen.getAllByRole('link')
        expect(links.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Busca', () => {
    it('filtra por nome com debounce', async () => {
      const user = userEvent.setup()
      render(<FunnelDrilldownModal {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Buscar por nome...')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText('Buscar por nome...')
      await user.type(searchInput, 'João')

      // Esperar debounce (300ms) + fetch
      await waitFor(
        () => {
          expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('search=Jo%C3%A3o'))
        },
        { timeout: 500 }
      )
    })

    it('mostra botão de limpar busca quando tem texto', async () => {
      const user = userEvent.setup()
      render(<FunnelDrilldownModal {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Buscar por nome...')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText('Buscar por nome...')
      await user.type(searchInput, 'João')

      expect(screen.getByLabelText('Limpar busca')).toBeInTheDocument()
    })

    it('limpa busca ao clicar no X', async () => {
      const user = userEvent.setup()
      render(<FunnelDrilldownModal {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Buscar por nome...')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText('Buscar por nome...')
      await user.type(searchInput, 'João')

      const clearButton = screen.getByLabelText('Limpar busca')
      await user.click(clearButton)

      expect(searchInput).toHaveValue('')
    })

    it('mostra mensagem quando busca não encontra resultados', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            ...mockDrilldownData,
            items: [],
            total: 0,
          }),
      })

      const user = userEvent.setup()
      render(<FunnelDrilldownModal {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Buscar por nome...')).toBeInTheDocument()
      })

      // Simular busca sem resultados
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            ...mockDrilldownData,
            items: [],
            total: 0,
          }),
      })

      const searchInput = screen.getByPlaceholderText('Buscar por nome...')
      await user.type(searchInput, 'NomeInexistente')

      await waitFor(
        () => {
          expect(screen.getByText(/Nenhum medico encontrado/i)).toBeInTheDocument()
        },
        { timeout: 500 }
      )
    })
  })

  describe('Paginação', () => {
    it('mostra controles de paginação quando há mais de uma página', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            ...mockDrilldownData,
            total: 25,
            pageSize: 10,
          }),
      })

      render(<FunnelDrilldownModal {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByText('Anterior')).toBeInTheDocument()
        expect(screen.getByText('Proximo')).toBeInTheDocument()
        expect(screen.getByText('1 / 3')).toBeInTheDocument()
      })
    })

    it('mostra range de itens', async () => {
      render(<FunnelDrilldownModal {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByText(/Mostrando 1-10 de 25/i)).toBeInTheDocument()
      })
    })

    it('desabilita botão Anterior na primeira página', async () => {
      render(<FunnelDrilldownModal {...defaultProps} />)

      await waitFor(() => {
        const prevButton = screen.getByText('Anterior')
        expect(prevButton).toBeDisabled()
      })
    })

    it('navega para próxima página', async () => {
      const user = userEvent.setup()
      render(<FunnelDrilldownModal {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByText('Proximo')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Proximo'))

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('page=2'))
      })
    })
  })

  describe('Expansão de mensagens', () => {
    it('expande linha ao clicar para mostrar mensagens', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockDrilldownData),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockMessages),
        })

      const user = userEvent.setup()
      render(<FunnelDrilldownModal {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByText('Dr. João Silva')).toBeInTheDocument()
      })

      // Clicar na linha para expandir
      await user.click(screen.getByText('Dr. João Silva'))

      await waitFor(() => {
        expect(screen.getByText('Oi Dr. João! Tudo bem?')).toBeInTheDocument()
        expect(screen.getByText('Olá, tudo bem sim!')).toBeInTheDocument()
      })
    })

    it('mostra loading enquanto carrega mensagens', async () => {
      let resolveMessages: (value: unknown) => void
      const messagesPromise = new Promise((resolve) => {
        resolveMessages = resolve
      })

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockDrilldownData),
        })
        .mockImplementationOnce(() => ({
          ok: true,
          json: () => messagesPromise,
        }))

      const user = userEvent.setup()
      render(<FunnelDrilldownModal {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByText('Dr. João Silva')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Dr. João Silva'))

      expect(screen.getByText('Carregando mensagens...')).toBeInTheDocument()

      // Resolver mensagens
      resolveMessages!({ ok: true, json: () => Promise.resolve(mockMessages) })
    })

    it('colapsa linha ao clicar novamente', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockDrilldownData),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockMessages),
        })

      const user = userEvent.setup()
      render(<FunnelDrilldownModal {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByText('Dr. João Silva')).toBeInTheDocument()
      })

      // Expandir
      await user.click(screen.getByText('Dr. João Silva'))

      await waitFor(() => {
        expect(screen.getByText('Oi Dr. João! Tudo bem?')).toBeInTheDocument()
      })

      // Colapsar - nome aparece múltiplas vezes quando expandido (tabela + mensagens)
      const nameElements = screen.getAllByText('Dr. João Silva')
      const firstElement = nameElements[0]
      if (firstElement) {
        await user.click(firstElement) // Clicar na célula da tabela
      }

      await waitFor(() => {
        expect(screen.queryByText('Oi Dr. João! Tudo bem?')).not.toBeInTheDocument()
      })
    })
  })

  describe('Estados de loading', () => {
    it('mostra skeleton durante carregamento inicial', async () => {
      let resolveFetch: (value: unknown) => void
      const fetchPromise = new Promise((resolve) => {
        resolveFetch = resolve
      })

      mockFetch.mockImplementationOnce(() => fetchPromise)

      render(<FunnelDrilldownModal {...defaultProps} />)

      // Skeleton deve estar visível
      expect(document.querySelector('.animate-pulse')).toBeInTheDocument()

      // Resolver fetch
      resolveFetch!({
        ok: true,
        json: () => Promise.resolve(mockDrilldownData),
      })
    })

    it('mostra overlay durante paginação', async () => {
      const user = userEvent.setup()

      let resolveFetch: (value: unknown) => void
      const fetchPromise = new Promise((resolve) => {
        resolveFetch = resolve
      })

      render(<FunnelDrilldownModal {...defaultProps} />)

      await waitFor(() => {
        expect(screen.getByText('Proximo')).toBeInTheDocument()
      })

      mockFetch.mockImplementationOnce(() => fetchPromise)

      await user.click(screen.getByText('Proximo'))

      expect(screen.getByText('Carregando...')).toBeInTheDocument()

      resolveFetch!({
        ok: true,
        json: () => Promise.resolve(mockDrilldownData),
      })
    })
  })

  describe('Reset de estado ao fechar', () => {
    it('limpa estado ao fechar modal', async () => {
      const user = userEvent.setup()
      const onOpenChange = vi.fn()

      const { rerender } = render(
        <FunnelDrilldownModal {...defaultProps} onOpenChange={onOpenChange} />
      )

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Buscar por nome...')).toBeInTheDocument()
      })

      // Digitar busca
      const searchInput = screen.getByPlaceholderText('Buscar por nome...')
      await user.type(searchInput, 'João')

      // Fechar modal
      rerender(<FunnelDrilldownModal {...defaultProps} open={false} onOpenChange={onOpenChange} />)

      // Reabrir modal
      rerender(<FunnelDrilldownModal {...defaultProps} open={true} onOpenChange={onOpenChange} />)

      await waitFor(() => {
        const newSearchInput = screen.getByPlaceholderText('Buscar por nome...')
        expect(newSearchInput).toHaveValue('')
      })
    })
  })
})
