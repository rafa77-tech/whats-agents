import { render, screen, waitFor, fireEvent, cleanup } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import CampanhasPage from '@/app/(dashboard)/campanhas/page'

// Mock useToast
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

// Store original fetch
const originalFetch = global.fetch

// Mock fetch
function setupMockFetch(options: { campanhas?: unknown[] }) {
  global.fetch = vi.fn().mockImplementation((url: string) => {
    if (typeof url === 'string' && url.includes('/api/campanhas')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(options.campanhas ?? []),
      })
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve([]),
    })
  })
}

describe('CampanhasPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
    global.fetch = originalFetch
  })

  it('mostra estado de loading inicialmente', () => {
    global.fetch = vi.fn().mockImplementation(() => new Promise(() => {}))

    render(<CampanhasPage />)

    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('renderiza titulo e descricao da pagina', () => {
    setupMockFetch({ campanhas: [] })

    render(<CampanhasPage />)

    expect(screen.getByText('Campanhas')).toBeInTheDocument()
    expect(screen.getByText('Gerencie campanhas de prospecção e reativacao')).toBeInTheDocument()
  })

  it('mostra estado vazio quando nao ha campanhas', async () => {
    setupMockFetch({ campanhas: [] })

    render(<CampanhasPage />)

    expect(
      await screen.findByText('Nenhuma campanha ativa', {}, { timeout: 10000 })
    ).toBeInTheDocument()
  })

  it('renderiza lista de campanhas', async () => {
    setupMockFetch({
      campanhas: [
        {
          id: 1,
          nome_template: 'Campanha Cardio ABC',
          tipo_campanha: 'oferta_plantao',
          categoria: 'marketing',
          status: 'rascunho',
          total_destinatarios: 100,
          enviados: 50,
          entregues: 45,
          respondidos: 10,
          created_at: new Date().toISOString(),
        },
      ],
    })

    render(<CampanhasPage />)

    expect(
      await screen.findByText('Campanha Cardio ABC', {}, { timeout: 10000 })
    ).toBeInTheDocument()
    expect(screen.getByText('Rascunho')).toBeInTheDocument()
  })

  it('mostra tabs de ativas e historico', async () => {
    setupMockFetch({ campanhas: [] })

    render(<CampanhasPage />)

    await waitFor(
      () => {
        const tabs = screen.getAllByRole('tab')
        expect(tabs.length).toBe(2)
        expect(tabs[0]?.textContent).toContain('Ativas')
        expect(tabs[1]?.textContent).toContain('Historico')
      },
      { timeout: 5000 }
    )
  })

  it('mostra botao Nova Campanha', async () => {
    setupMockFetch({ campanhas: [] })

    render(<CampanhasPage />)

    expect(await screen.findByText('Nova Campanha', {}, { timeout: 5000 })).toBeInTheDocument()
  })

  it('mostra botao Atualizar', async () => {
    setupMockFetch({ campanhas: [] })

    render(<CampanhasPage />)

    expect(await screen.findByText('Atualizar', {}, { timeout: 5000 })).toBeInTheDocument()
  })

  it('mostra cards de metricas', async () => {
    setupMockFetch({
      campanhas: [
        {
          id: 1,
          nome_template: 'Test',
          tipo_campanha: 'oferta_plantao',
          status: 'ativa',
          total_destinatarios: 100,
          enviados: 50,
          entregues: 45,
          respondidos: 10,
          created_at: new Date().toISOString(),
        },
      ],
    })

    render(<CampanhasPage />)

    // Verifica labels dos cards de metricas
    expect(await screen.findByText('Campanhas Ativas', {}, { timeout: 10000 })).toBeInTheDocument()
    expect(screen.getByText('Total Enviados')).toBeInTheDocument()
    expect(screen.getByText('Total Entregues')).toBeInTheDocument()
    // "Respostas" pode existir em multiplos lugares, verificar label apenas
    expect(screen.getAllByText('Respostas').length).toBeGreaterThan(0)
  })

  it('abre wizard ao clicar em Nova Campanha', async () => {
    setupMockFetch({ campanhas: [] })

    render(<CampanhasPage />)

    const novaButton = await screen.findByText('Nova Campanha', {}, { timeout: 5000 })

    fireEvent.click(novaButton)

    await waitFor(
      () => {
        expect(screen.getByText('Configuracao')).toBeInTheDocument()
      },
      { timeout: 5000 }
    )
  })

  it('mostra metricas corretas na campanha', async () => {
    setupMockFetch({
      campanhas: [
        {
          id: 1,
          nome_template: 'Campanha Teste',
          tipo_campanha: 'oferta_plantao',
          categoria: 'marketing',
          status: 'ativa',
          total_destinatarios: 200,
          enviados: 150,
          entregues: 140,
          respondidos: 35,
          created_at: new Date().toISOString(),
        },
      ],
    })

    render(<CampanhasPage />)

    await waitFor(
      () => {
        expect(screen.getByText('Campanha Teste')).toBeInTheDocument()
      },
      { timeout: 10000 }
    )

    // Verifica que a campanha foi renderizada com metricas
    // Valores podem aparecer em multiplos lugares (cards + campanha)
    expect(screen.getAllByText('200').length).toBeGreaterThan(0)
    expect(screen.getAllByText('150').length).toBeGreaterThan(0)
  })

  it('mostra status correto da campanha', async () => {
    setupMockFetch({
      campanhas: [
        {
          id: 1,
          nome_template: 'Campanha Agendada',
          tipo_campanha: 'oferta_plantao',
          status: 'agendada',
          total_destinatarios: 50,
          enviados: 0,
          entregues: 0,
          respondidos: 0,
          agendar_para: new Date(Date.now() + 86400000).toISOString(),
          created_at: new Date().toISOString(),
        },
      ],
    })

    render(<CampanhasPage />)

    expect(await screen.findByText('Agendada', {}, { timeout: 10000 })).toBeInTheDocument()
  })
})
