/**
 * Testes para SistemaPage
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import SistemaPage from '@/app/(dashboard)/sistema/page'

// Mock useToast
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

const mockFetch = vi.fn()

describe('SistemaPage', () => {
  const mockStatus = {
    pilot_mode: true,
    autonomous_features: {
      discovery_automatico: false,
      oferta_automatica: false,
      reativacao_automatica: false,
      feedback_automatico: false,
    },
    last_changed_by: 'admin@test.com',
    last_changed_at: '2026-01-30T10:00:00Z',
  }

  const mockConfig = {
    rate_limit: {
      msgs_por_hora: 20,
      msgs_por_dia: 100,
      intervalo_min: 45,
      intervalo_max: 180,
    },
    horario: {
      inicio: 8,
      fim: 20,
      dias: 'Segunda a Sexta',
    },
    uso_atual: {
      msgs_hora: 5,
      msgs_dia: 25,
      horario_permitido: true,
      hora_atual: '14:30',
    },
  }

  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = mockFetch
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  function setupMockFetch(options?: { status?: object; config?: object }) {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/sistema/status')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(options?.status ?? mockStatus),
        })
      }
      if (url.includes('/api/sistema/config')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(options?.config ?? mockConfig),
        })
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      })
    })
  }

  it('deve mostrar estado de loading inicialmente', () => {
    mockFetch.mockImplementation(() => new Promise(() => {}))

    render(<SistemaPage />)

    expect(screen.getByText('Carregando...')).toBeInTheDocument()
  })

  it('deve renderizar titulo e descricao', async () => {
    setupMockFetch()

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('Sistema')).toBeInTheDocument()
      expect(screen.getByText('Configuracoes e controles do sistema Julia')).toBeInTheDocument()
    })
  })

  it('deve renderizar card de Modo Piloto', async () => {
    setupMockFetch()

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('Modo Piloto')).toBeInTheDocument()
      expect(screen.getByText('Controla se Julia age autonomamente')).toBeInTheDocument()
    })
  })

  it('deve mostrar badge ATIVO quando pilot_mode e true', async () => {
    setupMockFetch({ status: { ...mockStatus, pilot_mode: true } })

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('ATIVO')).toBeInTheDocument()
    })
  })

  it('deve mostrar badge DESATIVADO quando pilot_mode e false', async () => {
    setupMockFetch({ status: { ...mockStatus, pilot_mode: false } })

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('DESATIVADO')).toBeInTheDocument()
    })
  })

  it('deve renderizar card de Rate Limiting', async () => {
    setupMockFetch()

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('Rate Limiting')).toBeInTheDocument()
      expect(screen.getByText('Limites de envio de mensagens')).toBeInTheDocument()
    })
  })

  it('deve mostrar valores de rate limit', async () => {
    setupMockFetch()

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('20')).toBeInTheDocument() // msgs_por_hora
      expect(screen.getByText('100')).toBeInTheDocument() // msgs_por_dia
    })
  })

  it('deve renderizar card de Horario de Operacao', async () => {
    setupMockFetch()

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('Horario de Operacao')).toBeInTheDocument()
      expect(screen.getByText('Quando Julia pode enviar mensagens')).toBeInTheDocument()
    })
  })

  it('deve mostrar horario configurado', async () => {
    setupMockFetch()

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('08h as 20h')).toBeInTheDocument()
      expect(screen.getByText('Segunda a Sexta')).toBeInTheDocument()
    })
  })

  it('deve renderizar Safe Mode Card', async () => {
    setupMockFetch()

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('Safe Mode Emergencial')).toBeInTheDocument()
    })
  })

  it('deve mostrar todas as features autonomas', async () => {
    setupMockFetch()

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('Discovery Automatico')).toBeInTheDocument()
      expect(screen.getByText('Oferta Automatica')).toBeInTheDocument()
      expect(screen.getByText('Reativacao Automatica')).toBeInTheDocument()
      expect(screen.getByText('Feedback Automatico')).toBeInTheDocument()
    })
  })

  it('deve abrir dialog ao tentar ativar modo piloto', async () => {
    const user = userEvent.setup()
    setupMockFetch({ status: { ...mockStatus, pilot_mode: false } })

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('DESATIVADO')).toBeInTheDocument()
    })

    // Find the switch and click it
    const switches = screen.getAllByRole('switch')
    expect(switches[0]).toBeDefined()
    await user.click(switches[0] as HTMLElement)

    await waitFor(() => {
      expect(screen.getByText('Ativar Modo Piloto?')).toBeInTheDocument()
    })
  })

  it('deve abrir dialog ao tentar desativar modo piloto', async () => {
    const user = userEvent.setup()
    setupMockFetch({ status: { ...mockStatus, pilot_mode: true } })

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('ATIVO')).toBeInTheDocument()
    })

    // Find the switch and click it
    const switches = screen.getAllByRole('switch')
    expect(switches[0]).toBeDefined()
    await user.click(switches[0] as HTMLElement)

    await waitFor(() => {
      expect(screen.getByText('Desativar Modo Piloto?')).toBeInTheDocument()
    })
  })

  it('deve mostrar ultima alteracao quando disponivel', async () => {
    setupMockFetch()

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText(/Ultima alteracao:/)).toBeInTheDocument()
      expect(screen.getByText(/admin@test.com/)).toBeInTheDocument()
    })
  })

  it('deve mostrar uso atual de rate limit', async () => {
    setupMockFetch()

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('5/20')).toBeInTheDocument() // msgs_hora
      expect(screen.getByText('25/100')).toBeInTheDocument() // msgs_dia
    })
  })

  it('deve mostrar status do horario atual', async () => {
    setupMockFetch()

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('Dentro do horario')).toBeInTheDocument()
    })
  })

  it('deve mostrar features desabilitadas quando em modo piloto', async () => {
    setupMockFetch({ status: { ...mockStatus, pilot_mode: true } })

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText(/Desative o Modo Piloto para controlar/)).toBeInTheDocument()
    })
  })
})
