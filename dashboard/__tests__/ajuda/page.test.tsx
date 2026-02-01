import { render, screen, waitFor, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import CanalAjudaPage from '@/app/(dashboard)/ajuda/page'

// Mock useToast
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

// Store original fetch
const originalFetch = global.fetch

// Mock fetch with URL handling - returns immediately
function setupMockFetch(options: { pedidos?: unknown[] }) {
  const mockFn = vi.fn().mockImplementation((url: string) => {
    if (typeof url === 'string' && url.includes('/api/ajuda')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(options.pedidos ?? []),
      })
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve([]),
    })
  })
  global.fetch = mockFn
  return mockFn
}

// Mock Audio API
class MockAudio {
  play = vi.fn().mockResolvedValue(undefined)
}
global.Audio = MockAudio as unknown as typeof Audio

describe('CanalAjudaPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset fetch to original before each test
    global.fetch = originalFetch
  })

  afterEach(async () => {
    cleanup()
    global.fetch = originalFetch
    // Allow any pending promises to settle
    await new Promise((resolve) => setTimeout(resolve, 0))
  })

  it('shows loading state initially', async () => {
    // Use a delayed promise that we can control
    let resolvePromise: (value: unknown) => void
    const delayedPromise = new Promise((resolve) => {
      resolvePromise = resolve
    })

    global.fetch = vi.fn().mockImplementation(() => delayedPromise)

    render(<CanalAjudaPage />)

    // Check loading state is shown
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()

    // Now resolve the promise to clean up
    resolvePromise!({
      ok: true,
      json: () => Promise.resolve([]),
    })

    // Wait for cleanup
    await new Promise((resolve) => setTimeout(resolve, 10))
  })

  it('renders page title and description', () => {
    setupMockFetch({ pedidos: [] })

    render(<CanalAjudaPage />)

    expect(screen.getByText('Canal de Ajuda')).toBeInTheDocument()
    expect(screen.getByText('Perguntas que Julia nao soube responder')).toBeInTheDocument()
  })

  it('shows empty state when no pending requests', async () => {
    setupMockFetch({ pedidos: [] })

    render(<CanalAjudaPage />)

    // Wait for "Tudo em dia!" to appear (loading must complete)
    await waitFor(
      () => {
        expect(screen.getByText('Tudo em dia!')).toBeInTheDocument()
      },
      { timeout: 5000 }
    )

    expect(screen.getByText('Nenhum pedido pendente no momento.')).toBeInTheDocument()
  })

  it('renders pending requests', async () => {
    setupMockFetch({
      pedidos: [
        {
          id: '1',
          conversa_id: 'conv-1',
          cliente_id: 'cli-1',
          pergunta_original: 'Tem estacionamento?',
          status: 'pendente',
          criado_em: new Date().toISOString(),
          clientes: { nome: 'Dr. Carlos', telefone: '11999999999' },
          hospitais: { nome: 'Hospital X' },
        },
      ],
    })

    render(<CanalAjudaPage />)

    await waitFor(
      () => {
        expect(screen.getByText('Dr. Carlos')).toBeInTheDocument()
      },
      { timeout: 5000 }
    )

    expect(screen.getByText('Tem estacionamento?')).toBeInTheDocument()
  })

  it('shows tabs for pendentes and todos', async () => {
    setupMockFetch({ pedidos: [] })

    render(<CanalAjudaPage />)

    await waitFor(
      () => {
        const tabs = screen.getAllByRole('tab')
        expect(tabs.length).toBe(2)
        expect(tabs[0]?.textContent).toContain('Pendentes')
        expect(tabs[1]?.textContent).toContain('Todos')
      },
      { timeout: 5000 }
    )
  })

  it('shows pending count badge when there are pending requests', async () => {
    setupMockFetch({
      pedidos: [
        {
          id: '1',
          pergunta_original: 'Pergunta 1',
          status: 'pendente',
          criado_em: new Date().toISOString(),
          clientes: { nome: 'Dr. A', telefone: '11111' },
        },
        {
          id: '2',
          pergunta_original: 'Pergunta 2',
          status: 'pendente',
          criado_em: new Date().toISOString(),
          clientes: { nome: 'Dr. B', telefone: '22222' },
        },
      ],
    })

    render(<CanalAjudaPage />)

    await waitFor(
      () => {
        expect(screen.getByText('2')).toBeInTheDocument()
      },
      { timeout: 5000 }
    )
  })

  it('shows alert when there are pending requests', async () => {
    setupMockFetch({
      pedidos: [
        {
          id: '1',
          pergunta_original: 'Pergunta 1',
          status: 'pendente',
          criado_em: new Date().toISOString(),
          clientes: { nome: 'Dr. A', telefone: '11111' },
        },
      ],
    })

    render(<CanalAjudaPage />)

    await waitFor(
      () => {
        expect(screen.getByText('1 pedido(s) aguardando resposta')).toBeInTheDocument()
      },
      { timeout: 5000 }
    )
  })

  it('shows Responder button for pending requests', async () => {
    setupMockFetch({
      pedidos: [
        {
          id: '1',
          pergunta_original: 'Teste?',
          status: 'pendente',
          criado_em: new Date().toISOString(),
          clientes: { nome: 'Dr. Test', telefone: '11111' },
        },
      ],
    })

    render(<CanalAjudaPage />)

    // First wait for content to load (doctor name appears)
    await waitFor(
      () => {
        expect(screen.getByText('Dr. Test')).toBeInTheDocument()
      },
      { timeout: 5000 }
    )

    // Now check for Responder button
    expect(screen.getByRole('button', { name: 'Responder' })).toBeInTheDocument()
  })

  it('shows response form when clicking Responder', async () => {
    const user = userEvent.setup()

    setupMockFetch({
      pedidos: [
        {
          id: '1',
          conversa_id: 'conv-1',
          cliente_id: 'cli-1',
          pergunta_original: 'Tem estacionamento?',
          status: 'pendente',
          criado_em: new Date().toISOString(),
          clientes: { nome: 'Dr. Pedro', telefone: '11999999999' },
          hospitais: { nome: 'Hospital X' },
        },
      ],
    })

    render(<CanalAjudaPage />)

    // First wait for content to load (doctor name appears)
    await waitFor(
      () => {
        expect(screen.getByText('Dr. Pedro')).toBeInTheDocument()
      },
      { timeout: 5000 }
    )

    // Now get the Responder button and click it
    const responderButton = screen.getByRole('button', { name: 'Responder' })
    await user.click(responderButton)

    // Wait for form to appear
    await waitFor(
      () => {
        expect(screen.getByPlaceholderText(/Digite sua resposta/)).toBeInTheDocument()
      },
      { timeout: 5000 }
    )

    expect(screen.getByRole('button', { name: /Enviar Resposta/ })).toBeInTheDocument()
  })

  it('shows Atualizar button', async () => {
    setupMockFetch({ pedidos: [] })

    render(<CanalAjudaPage />)

    await waitFor(
      () => {
        expect(screen.getByText('Atualizar')).toBeInTheDocument()
      },
      { timeout: 5000 }
    )
  })

  it('shows sound toggle', async () => {
    setupMockFetch({ pedidos: [] })

    render(<CanalAjudaPage />)

    await waitFor(
      () => {
        expect(screen.getByText('Som')).toBeInTheDocument()
      },
      { timeout: 5000 }
    )

    expect(screen.getByRole('switch')).toBeInTheDocument()
  })

  it('shows responded request with answer', async () => {
    const user = userEvent.setup()

    setupMockFetch({
      pedidos: [
        {
          id: '1',
          pergunta_original: 'Tem estacionamento?',
          status: 'respondido',
          resposta: 'Sim, o hospital tem estacionamento proprio.',
          respondido_em: new Date().toISOString(),
          criado_em: new Date().toISOString(),
          clientes: { nome: 'Dr. Carlos', telefone: '11999999999' },
        },
      ],
    })

    render(<CanalAjudaPage />)

    // Wait for tabs to appear
    await waitFor(
      () => {
        expect(screen.getAllByRole('tab').length).toBe(2)
      },
      { timeout: 5000 }
    )

    // Switch to todos tab
    const tabs = screen.getAllByRole('tab')
    await user.click(tabs[1] as Element)

    // Wait for content to appear
    await waitFor(
      () => {
        expect(screen.getByText('Sim, o hospital tem estacionamento proprio.')).toBeInTheDocument()
      },
      { timeout: 5000 }
    )
  })
})
