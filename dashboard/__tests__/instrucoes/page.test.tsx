import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import InstrucoesPage from '@/app/(dashboard)/instrucoes/page'

// Mock useToast
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

// Mock fetch with URL handling
const mockFetch = vi.fn()

function setupMockFetch(options: {
  diretrizes?: unknown[]
  hospitais?: unknown[]
  especialidades?: unknown[]
}) {
  mockFetch.mockImplementation((url: string) => {
    if (url.startsWith('/api/diretrizes')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(options.diretrizes ?? []),
      })
    }
    if (url.startsWith('/api/hospitais')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(options.hospitais ?? []),
      })
    }
    if (url.startsWith('/api/especialidades')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(options.especialidades ?? []),
      })
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve([]),
    })
  })
}

describe('InstrucoesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = mockFetch
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows loading state initially', () => {
    mockFetch.mockImplementation(() => new Promise(() => {})) // Never resolves

    render(<InstrucoesPage />)

    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('renders page title and description', async () => {
    setupMockFetch({ diretrizes: [] })

    render(<InstrucoesPage />)

    expect(screen.getByText('Instrucoes Ativas')).toBeInTheDocument()
    expect(
      screen.getByText('Diretrizes contextuais que Julia segue nas conversas')
    ).toBeInTheDocument()
  })

  it('shows empty state when no diretrizes', async () => {
    setupMockFetch({ diretrizes: [] })

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText('Nenhuma instrucao encontrada')).toBeInTheDocument()
    })
  })

  it('renders diretrizes list', async () => {
    setupMockFetch({
      diretrizes: [
        {
          id: '1',
          tipo: 'margem_negociacao',
          escopo: 'global',
          conteudo: { valor_maximo: 3000 },
          criado_por: 'admin@revoluna.com',
          criado_em: new Date().toISOString(),
          status: 'ativa',
        },
      ],
    })

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText('Margem de Negociacao')).toBeInTheDocument()
      expect(screen.getByText('Todas as conversas')).toBeInTheDocument()
      expect(screen.getByText('Ate R$ 3.000')).toBeInTheDocument()
    })
  })

  it('shows tabs for ativas and historico', async () => {
    setupMockFetch({ diretrizes: [] })

    render(<InstrucoesPage />)

    await waitFor(() => {
      // Ativas tab includes count so use regex
      const tabs = screen.getAllByRole('tab')
      expect(tabs.length).toBe(2)
      expect(tabs[0]?.textContent).toContain('Ativas')
      expect(tabs[1]?.textContent).toContain('Historico')
    })
  })

  it('shows Nova Instrucao button', async () => {
    setupMockFetch({ diretrizes: [] })

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText('Nova Instrucao')).toBeInTheDocument()
    })
  })

  it('opens Nova Instrucao dialog when button is clicked', async () => {
    setupMockFetch({
      diretrizes: [],
      hospitais: [{ id: '1', nome: 'Hospital A' }],
      especialidades: [{ id: '1', nome: 'Cardiologia' }],
    })

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText('Nova Instrucao')).toBeInTheDocument()
    })

    const button = screen.getByText('Nova Instrucao')
    fireEvent.click(button)

    await waitFor(() => {
      expect(screen.getByText('Tipo de instrucao')).toBeInTheDocument()
    })
  })

  it('shows action button for each diretriz', async () => {
    setupMockFetch({
      diretrizes: [
        {
          id: '1',
          tipo: 'regra_especial',
          escopo: 'hospital',
          conteudo: { regra: 'Teste regra' },
          criado_por: 'admin@revoluna.com',
          criado_em: new Date().toISOString(),
          status: 'ativa',
          hospitais: { nome: 'Hospital Teste' },
        },
      ],
    })

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText('Hospital Teste')).toBeInTheDocument()
      // Should have a button for actions (MoreHorizontal icon)
      expect(screen.getByRole('button', { name: '' })).toBeInTheDocument()
    })
  })

  it('shows informative alert', async () => {
    setupMockFetch({ diretrizes: [] })

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText(/Instrucoes sao regras especificas/)).toBeInTheDocument()
    })
  })

  it('renders different escopo labels correctly', async () => {
    setupMockFetch({
      diretrizes: [
        {
          id: '1',
          tipo: 'margem_negociacao',
          escopo: 'hospital',
          conteudo: { percentual_maximo: 15 },
          criado_por: 'admin@revoluna.com',
          criado_em: new Date().toISOString(),
          status: 'ativa',
          hospitais: { nome: 'Hospital Sao Luiz' },
        },
      ],
    })

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText('Hospital Sao Luiz')).toBeInTheDocument()
      expect(screen.getByText('Ate 15% acima')).toBeInTheDocument()
    })
  })

  it('shows expiration date when set', async () => {
    const futureDate = new Date()
    futureDate.setDate(futureDate.getDate() + 7)

    setupMockFetch({
      diretrizes: [
        {
          id: '1',
          tipo: 'regra_especial',
          escopo: 'global',
          conteudo: { regra: 'Regra com expiracao' },
          criado_por: 'admin@revoluna.com',
          criado_em: new Date().toISOString(),
          expira_em: futureDate.toISOString(),
          status: 'ativa',
        },
      ],
    })

    render(<InstrucoesPage />)

    await waitFor(() => {
      expect(screen.getByText('Regra com expiracao')).toBeInTheDocument()
      // Should show formatted date
      expect(screen.queryByText('Nao expira')).not.toBeInTheDocument()
    })
  })
})
