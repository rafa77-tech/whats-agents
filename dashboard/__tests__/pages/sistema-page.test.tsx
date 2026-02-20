/**
 * Tests for sistema/page.tsx
 *
 * Tests the system config page rendering and interactions.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SistemaPage from '@/app/(dashboard)/sistema/page'

// Mock dependencies
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/sistema',
}))

const mockToast = vi.fn()
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: mockToast }),
}))

vi.mock('@/components/sistema', () => ({
  EditRateLimitModal: ({ onClose }: { onClose: () => void }) => (
    <div data-testid="rate-limit-modal">
      <button onClick={onClose}>Close Rate</button>
    </div>
  ),
  EditScheduleModal: ({ onClose }: { onClose: () => void }) => (
    <div data-testid="schedule-modal">
      <button onClick={onClose}>Close Schedule</button>
    </div>
  ),
  SafeModeCard: () => <div data-testid="safe-mode-card" />,
}))

const mockStatus = {
  pilot_mode: true,
  autonomous_features: {
    discovery_automatico: false,
    oferta_automatica: false,
    reativacao_automatica: true,
    feedback_automatico: false,
  },
  last_changed_by: 'admin@test.com',
  last_changed_at: '2026-02-15T10:00:00Z',
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
    dias: 'Seg-Sex',
  },
  uso_atual: {
    msgs_hora: 5,
    msgs_dia: 30,
    horario_permitido: true,
    hora_atual: '14:30',
  },
}

function mockFetchResponses(statusData = mockStatus, configData = mockConfig) {
  return vi.spyOn(global, 'fetch').mockImplementation(async (url) => {
    const urlStr = typeof url === 'string' ? url : url.toString()
    if (urlStr.includes('/api/sistema/status')) {
      return { ok: true, json: async () => statusData } as Response
    }
    if (urlStr.includes('/api/sistema/config')) {
      return { ok: true, json: async () => configData } as Response
    }
    if (urlStr.includes('/api/sistema/pilot-mode')) {
      return { ok: true, json: async () => ({ success: true }) } as Response
    }
    if (urlStr.includes('/api/sistema/features/')) {
      return { ok: true, json: async () => ({ success: true }) } as Response
    }
    return { ok: false, json: async () => ({}) } as Response
  })
}

describe('SistemaPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    mockToast.mockClear()
  })

  it('deve mostrar loading inicialmente', () => {
    vi.spyOn(global, 'fetch').mockImplementation(() => new Promise(() => {}))
    render(<SistemaPage />)
    expect(screen.getByText('Carregando...')).toBeInTheDocument()
  })

  it('deve renderizar com modo piloto ativo', async () => {
    mockFetchResponses()
    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('ATIVO')).toBeInTheDocument()
      expect(screen.getByText('Modo seguro ativo')).toBeInTheDocument()
    })
  })

  it('deve renderizar com modo piloto desativado', async () => {
    mockFetchResponses({ ...mockStatus, pilot_mode: false })
    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('DESATIVADO')).toBeInTheDocument()
      expect(screen.getByText('Julia autonoma')).toBeInTheDocument()
    })
  })

  it('deve renderizar config de rate limiting', async () => {
    mockFetchResponses()
    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('20')).toBeInTheDocument()
      expect(screen.getByText('100')).toBeInTheDocument()
      expect(screen.getByText('45-180s')).toBeInTheDocument()
    })
  })

  it('deve renderizar uso atual', async () => {
    mockFetchResponses()
    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('5/20')).toBeInTheDocument()
      expect(screen.getByText('30/100')).toBeInTheDocument()
      expect(screen.getByText('Dentro do horario')).toBeInTheDocument()
    })
  })

  it('deve renderizar fora do horario', async () => {
    mockFetchResponses(mockStatus, {
      ...mockConfig,
      uso_atual: { ...mockConfig.uso_atual, horario_permitido: false },
    })
    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('Fora do horario')).toBeInTheDocument()
    })
  })

  it('deve renderizar sem uso_atual', async () => {
    const { uso_atual: _, ...configSemUso } = mockConfig
    mockFetchResponses(mockStatus, configSemUso as typeof mockConfig)
    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('20')).toBeInTheDocument()
      // Uso atual sections should not appear
      expect(screen.queryByText('Esta hora')).not.toBeInTheDocument()
    })
  })

  it('deve renderizar sem config', async () => {
    vi.spyOn(global, 'fetch').mockImplementation(async (url) => {
      const urlStr = typeof url === 'string' ? url : url.toString()
      if (urlStr.includes('/api/sistema/status')) {
        return { ok: true, json: async () => mockStatus } as Response
      }
      if (urlStr.includes('/api/sistema/config')) {
        return { ok: false, json: async () => ({}) } as Response
      }
      return { ok: false, json: async () => ({}) } as Response
    })

    render(<SistemaPage />)

    await waitFor(() => {
      // Should show "Carregando..." in the cards instead of config data
      const loadingTexts = screen.getAllByText('Carregando...')
      expect(loadingTexts.length).toBeGreaterThanOrEqual(2)
    })
  })

  it('deve mostrar horario de operacao formatado', async () => {
    mockFetchResponses()
    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('08h as 20h')).toBeInTheDocument()
      expect(screen.getByText('Seg-Sex')).toBeInTheDocument()
    })
  })

  it('deve mostrar ultima alteracao', async () => {
    mockFetchResponses()
    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText(/Ultima alteracao/)).toBeInTheDocument()
      expect(screen.getByText(/admin@test.com/)).toBeInTheDocument()
    })
  })

  it('deve nao mostrar ultima alteracao quando nao ha', async () => {
    const { last_changed_at: _a, last_changed_by: _b, ...statusSemAlteracao } = mockStatus
    mockFetchResponses(statusSemAlteracao as typeof mockStatus)
    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('Modo Piloto')).toBeInTheDocument()
    })

    expect(screen.queryByText(/Ultima alteracao/)).not.toBeInTheDocument()
  })

  it('deve renderizar features autonomas em modo piloto', async () => {
    mockFetchResponses()
    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('Discovery Automatico')).toBeInTheDocument()
      expect(screen.getByText('Oferta Automatica')).toBeInTheDocument()
      expect(screen.getByText('Reativacao Automatica')).toBeInTheDocument()
      expect(screen.getByText('Feedback Automatico')).toBeInTheDocument()
      expect(
        screen.getByText('Desative o Modo Piloto para controlar individualmente')
      ).toBeInTheDocument()
    })
  })

  it('deve renderizar features sem hint de piloto quando desativado', async () => {
    mockFetchResponses({ ...mockStatus, pilot_mode: false })
    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('Discovery Automatico')).toBeInTheDocument()
    })

    expect(
      screen.queryByText('Desative o Modo Piloto para controlar individualmente')
    ).not.toBeInTheDocument()
  })

  it('deve ativar modo piloto via dialog', async () => {
    const fetchSpy = mockFetchResponses({ ...mockStatus, pilot_mode: false })
    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('DESATIVADO')).toBeInTheDocument()
    })

    // Click the switch to toggle pilot mode
    const switches = screen.getAllByRole('switch')
    await userEvent.click(switches[0]!)

    // Confirm dialog should appear
    await waitFor(() => {
      expect(screen.getByText('Ativar Modo Piloto?')).toBeInTheDocument()
    })

    // Click confirm
    await userEvent.click(screen.getByText('Ativar Modo Piloto'))

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith('/api/sistema/pilot-mode', expect.anything())
    })
  })

  it('deve desativar modo piloto via dialog', async () => {
    const fetchSpy = mockFetchResponses()
    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('ATIVO')).toBeInTheDocument()
    })

    // Click the switch to toggle pilot mode off
    const switches = screen.getAllByRole('switch')
    await userEvent.click(switches[0]!)

    // Confirm dialog should appear
    await waitFor(() => {
      expect(screen.getByText('Desativar Modo Piloto?')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('Desativar Modo Piloto'))

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith('/api/sistema/pilot-mode', expect.anything())
    })
  })

  it('deve mostrar toast de erro ao falhar toggle de modo piloto', async () => {
    vi.spyOn(global, 'fetch').mockImplementation(async (url) => {
      const urlStr = typeof url === 'string' ? url : url.toString()
      if (urlStr.includes('/api/sistema/status')) {
        return { ok: true, json: async () => ({ ...mockStatus, pilot_mode: false }) } as Response
      }
      if (urlStr.includes('/api/sistema/config')) {
        return { ok: true, json: async () => mockConfig } as Response
      }
      if (urlStr.includes('/api/sistema/pilot-mode')) {
        return { ok: false, json: async () => ({}) } as Response
      }
      return { ok: false, json: async () => ({}) } as Response
    })

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('DESATIVADO')).toBeInTheDocument()
    })

    const switches = screen.getAllByRole('switch')
    await userEvent.click(switches[0]!)

    await waitFor(() => {
      expect(screen.getByText('Ativar Modo Piloto?')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByText('Ativar Modo Piloto'))

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({ variant: 'destructive' }))
    })
  })

  it('deve habilitar feature individual quando nao esta em modo piloto', async () => {
    const fetchSpy = mockFetchResponses({ ...mockStatus, pilot_mode: false })
    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('Discovery Automatico')).toBeInTheDocument()
    })

    // Feature switches (skip first which is pilot mode switch)
    const switches = screen.getAllByRole('switch')
    // First switch is pilot mode, next 4 are features
    // discovery_automatico is false, click to enable
    await userEvent.click(switches[1]!)

    await waitFor(() => {
      expect(screen.getByText(/Habilitar.*Discovery Automatico/)).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: 'Habilitar' }))

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        '/api/sistema/features/discovery_automatico',
        expect.anything()
      )
    })
  })

  it('deve desabilitar feature individual', async () => {
    const fetchSpy = mockFetchResponses({ ...mockStatus, pilot_mode: false })
    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('Reativacao Automatica')).toBeInTheDocument()
    })

    // reativacao_automatica is true (index 3 in switches, 0=pilot, 1=discovery, 2=oferta, 3=reativacao)
    const switches = screen.getAllByRole('switch')
    await userEvent.click(switches[3]!)

    await waitFor(() => {
      expect(screen.getByText(/Desabilitar.*Reativacao Automatica/)).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: 'Desabilitar' }))

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        '/api/sistema/features/reativacao_automatica',
        expect.anything()
      )
    })
  })

  it('deve mostrar toast de erro ao falhar toggle de feature', async () => {
    vi.spyOn(global, 'fetch').mockImplementation(async (url) => {
      const urlStr = typeof url === 'string' ? url : url.toString()
      if (urlStr.includes('/api/sistema/status')) {
        return { ok: true, json: async () => ({ ...mockStatus, pilot_mode: false }) } as Response
      }
      if (urlStr.includes('/api/sistema/config')) {
        return { ok: true, json: async () => mockConfig } as Response
      }
      if (urlStr.includes('/api/sistema/features/')) {
        return { ok: false } as Response
      }
      return { ok: false, json: async () => ({}) } as Response
    })

    render(<SistemaPage />)

    await waitFor(() => {
      expect(screen.getByText('Discovery Automatico')).toBeInTheDocument()
    })

    const switches = screen.getAllByRole('switch')
    await userEvent.click(switches[1]!)

    await waitFor(() => {
      expect(screen.getByText(/Habilitar.*Discovery Automatico/)).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: 'Habilitar' }))

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({
          variant: 'destructive',
          description: expect.stringContaining('Discovery Automatico'),
        })
      )
    })
  })

  it('deve lidar com erro de fetch no status', async () => {
    vi.spyOn(global, 'fetch').mockImplementation(async (url) => {
      const urlStr = typeof url === 'string' ? url : url.toString()
      if (urlStr.includes('/api/sistema/status')) {
        throw new Error('Network error')
      }
      if (urlStr.includes('/api/sistema/config')) {
        return { ok: true, json: async () => mockConfig } as Response
      }
      return { ok: false, json: async () => ({}) } as Response
    })

    render(<SistemaPage />)

    // Should still finish loading even with error
    await waitFor(() => {
      expect(screen.queryByText('Carregando...')).not.toBeInTheDocument()
    })
  })

  it('deve renderizar sem last_changed_by', async () => {
    const { last_changed_by: _, ...statusSemBy } = mockStatus
    mockFetchResponses(statusSemBy as typeof mockStatus)

    render(<SistemaPage />)

    await waitFor(() => {
      const altText = screen.getByText(/Ultima alteracao/)
      expect(altText).toBeInTheDocument()
      expect(altText.textContent).not.toContain('por')
    })
  })
})
