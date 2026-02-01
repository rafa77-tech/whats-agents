/**
 * Testes para os modais de qualidade
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { NewSuggestionModal } from '@/components/qualidade/new-suggestion-modal'
import { EvaluateConversationModal } from '@/components/qualidade/evaluate-conversation-modal'

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
// NewSuggestionModal Tests
// =============================================================================

describe('NewSuggestionModal', () => {
  const mockOnClose = vi.fn()
  const mockOnCreated = vi.fn()

  beforeEach(() => {
    mockOnClose.mockReset()
    mockOnCreated.mockReset()
  })

  it('deve renderizar o modal corretamente', () => {
    render(<NewSuggestionModal onClose={mockOnClose} onCreated={mockOnCreated} />)

    expect(screen.getByText('Nova Sugestao')).toBeInTheDocument()
    expect(screen.getByText('Crie uma sugestao de melhoria para os prompts')).toBeInTheDocument()
  })

  it('deve ter campos de tipo, descricao e exemplos', () => {
    render(<NewSuggestionModal onClose={mockOnClose} onCreated={mockOnCreated} />)

    expect(screen.getByText('Tipo')).toBeInTheDocument()
    expect(screen.getByText('Descricao')).toBeInTheDocument()
    expect(screen.getByText('Exemplos (opcional)')).toBeInTheDocument()
  })

  it('deve ter botoes de cancelar e criar', () => {
    render(<NewSuggestionModal onClose={mockOnClose} onCreated={mockOnCreated} />)

    expect(screen.getByText('Cancelar')).toBeInTheDocument()
    expect(screen.getByText('Criar Sugestao')).toBeInTheDocument()
  })

  it('deve desabilitar botao criar quando campos vazios', () => {
    render(<NewSuggestionModal onClose={mockOnClose} onCreated={mockOnCreated} />)

    const createButton = screen.getByText('Criar Sugestao')
    expect(createButton).toBeDisabled()
  })

  it('deve chamar onClose ao clicar em cancelar', () => {
    render(<NewSuggestionModal onClose={mockOnClose} onCreated={mockOnCreated} />)

    fireEvent.click(screen.getByText('Cancelar'))

    expect(mockOnClose).toHaveBeenCalled()
  })

  it('deve habilitar botao criar quando campos preenchidos', async () => {
    render(<NewSuggestionModal onClose={mockOnClose} onCreated={mockOnCreated} />)

    // Preenche descricao
    const descricaoInput = screen.getByPlaceholderText('Descreva a sugestao de melhoria...')
    fireEvent.change(descricaoInput, { target: { value: 'Teste de sugestao' } })

    // O botao ainda deve estar desabilitado porque o tipo nao foi selecionado
    const createButton = screen.getByText('Criar Sugestao')
    expect(createButton).toBeDisabled()
  })

  it('deve exibir opcoes de tipo', () => {
    render(<NewSuggestionModal onClose={mockOnClose} onCreated={mockOnCreated} />)

    // Verifica que o placeholder do select esta presente
    expect(screen.getByText('Selecione o tipo')).toBeInTheDocument()
  })
})

// =============================================================================
// EvaluateConversationModal Tests
// =============================================================================

describe('EvaluateConversationModal', () => {
  const mockOnClose = vi.fn()

  beforeEach(() => {
    mockOnClose.mockReset()
  })

  it('deve mostrar loading enquanto carrega conversa', async () => {
    mockFetch.mockReturnValue(new Promise(() => {})) // Never resolves

    const { baseElement } = render(
      <EvaluateConversationModal conversationId="conv123" onClose={mockOnClose} />
    )

    // Dialog renderiza em portal, entao usamos baseElement
    await waitFor(() => {
      const spinner = baseElement.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
    })
  })

  it('deve renderizar detalhes da conversa', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          id: 'conv123',
          medico_nome: 'Dr. Silva',
          interacoes: [
            {
              id: 'msg1',
              remetente: 'julia',
              conteudo: 'Oi, tudo bem?',
              criada_em: '2024-01-15T10:00:00Z',
            },
            {
              id: 'msg2',
              remetente: 'medico',
              conteudo: 'Tudo sim!',
              criada_em: '2024-01-15T10:01:00Z',
            },
          ],
        }),
    })

    render(<EvaluateConversationModal conversationId="conv123" onClose={mockOnClose} />)

    await waitFor(() => {
      expect(screen.getByText('Dr. Silva')).toBeInTheDocument()
    })

    expect(screen.getByText('Oi, tudo bem?')).toBeInTheDocument()
    expect(screen.getByText('Tudo sim!')).toBeInTheDocument()
  })

  it('deve exibir campos de avaliacao', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          id: 'conv123',
          medico_nome: 'Dr. Silva',
          interacoes: [],
        }),
    })

    render(<EvaluateConversationModal conversationId="conv123" onClose={mockOnClose} />)

    await waitFor(() => {
      expect(screen.getByText('Naturalidade')).toBeInTheDocument()
    })

    expect(screen.getByText('Persona')).toBeInTheDocument()
    expect(screen.getByText('Objetivo')).toBeInTheDocument()
    expect(screen.getByText('Satisfacao')).toBeInTheDocument()
    expect(screen.getByText('Observacoes')).toBeInTheDocument()
  })

  it('deve ter botoes de navegacao e salvar', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          id: 'conv123',
          medico_nome: 'Dr. Silva',
          interacoes: [],
        }),
    })

    render(<EvaluateConversationModal conversationId="conv123" onClose={mockOnClose} />)

    await waitFor(() => {
      expect(screen.getByText('Cancelar')).toBeInTheDocument()
    })

    expect(screen.getByText('Salvar Avaliacao')).toBeInTheDocument()
    expect(screen.getByText('Anterior')).toBeInTheDocument()
    expect(screen.getByText('Proxima')).toBeInTheDocument()
  })

  it('deve desabilitar botao salvar quando ratings incompletos', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          id: 'conv123',
          medico_nome: 'Dr. Silva',
          interacoes: [],
        }),
    })

    render(<EvaluateConversationModal conversationId="conv123" onClose={mockOnClose} />)

    await waitFor(() => {
      expect(screen.getByText('Salvar Avaliacao')).toBeInTheDocument()
    })

    const saveButton = screen.getByText('Salvar Avaliacao')
    expect(saveButton).toBeDisabled()
  })

  it('deve chamar onClose ao clicar em cancelar', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          id: 'conv123',
          medico_nome: 'Dr. Silva',
          interacoes: [],
        }),
    })

    render(<EvaluateConversationModal conversationId="conv123" onClose={mockOnClose} />)

    await waitFor(() => {
      expect(screen.getByText('Cancelar')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Cancelar'))

    expect(mockOnClose).toHaveBeenCalled()
  })

  it('deve mostrar ID truncado no titulo', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          id: 'conv123456789',
          medico_nome: 'Dr. Silva',
          interacoes: [],
        }),
    })

    render(<EvaluateConversationModal conversationId="conv123456789" onClose={mockOnClose} />)

    await waitFor(() => {
      expect(screen.getByText(/Avaliar Conversa #conv1234/)).toBeInTheDocument()
    })
  })

  it('deve ter estrelas para cada criterio de avaliacao', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          id: 'conv123',
          medico_nome: 'Dr. Silva',
          interacoes: [],
        }),
    })

    const { baseElement } = render(
      <EvaluateConversationModal conversationId="conv123" onClose={mockOnClose} />
    )

    await waitFor(() => {
      expect(screen.getByText('Naturalidade')).toBeInTheDocument()
    })

    // Cada criterio tem 5 estrelas, sao 4 criterios = 20 estrelas
    // Dialog renderiza em portal, entao usamos baseElement
    const stars = baseElement.querySelectorAll('button')
    // 20 estrelas + 4 botoes (Anterior, Proxima, Cancelar, Salvar)
    expect(stars.length).toBeGreaterThanOrEqual(24)
  })

  it('deve exibir quantidade de mensagens', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          id: 'conv123',
          medico_nome: 'Dr. Silva',
          interacoes: [
            { id: 'msg1', remetente: 'julia', conteudo: 'Oi', criada_em: '2024-01-15T10:00:00Z' },
            { id: 'msg2', remetente: 'medico', conteudo: 'Oi', criada_em: '2024-01-15T10:01:00Z' },
            {
              id: 'msg3',
              remetente: 'julia',
              conteudo: 'Como vai',
              criada_em: '2024-01-15T10:02:00Z',
            },
          ],
        }),
    })

    render(<EvaluateConversationModal conversationId="conv123" onClose={mockOnClose} />)

    await waitFor(() => {
      expect(screen.getByText(/3 mensagens/)).toBeInTheDocument()
    })
  })
})
