/**
 * Testes para AuditoriaPage
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import AuditoriaPage from '@/app/(dashboard)/auditoria/page'

// Mock fetch global
const mockFetch = vi.fn()

beforeEach(() => {
  vi.stubGlobal('fetch', mockFetch)
  mockFetch.mockReset()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('AuditoriaPage', () => {
  const mockResponse = {
    data: [
      {
        id: 'log1',
        action: 'julia_toggle',
        actor_email: 'admin@example.com',
        actor_role: 'admin',
        details: { enabled: true },
        created_at: '2024-01-15T10:00:00Z',
      },
    ],
    total: 1,
    page: 1,
    per_page: 50,
    pages: 1,
  }

  it('deve renderizar skeletons durante loading', () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })

    render(<AuditoriaPage />)

    // Verifica que tem skeletons (classe do componente Skeleton)
    const skeletons = document.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('deve renderizar titulo e descricao', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })

    render(<AuditoriaPage />)

    expect(screen.getByText('Auditoria')).toBeInTheDocument()
    expect(screen.getByText('Historico de acoes no sistema')).toBeInTheDocument()
  })

  it('deve renderizar lista de logs apos loading', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })

    render(<AuditoriaPage />)

    await waitFor(() => {
      expect(screen.getByText('Toggle Julia')).toBeInTheDocument()
    })

    expect(screen.getByText('admin@example.com')).toBeInTheDocument()
  })

  it('deve ter botao de exportar', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })

    render(<AuditoriaPage />)

    const exportButton = screen.getByRole('button', { name: /exportar/i })
    expect(exportButton).toBeInTheDocument()
  })

  it('deve ter campo de busca', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })

    render(<AuditoriaPage />)

    const searchInput = screen.getByPlaceholderText(/buscar por email/i)
    expect(searchInput).toBeInTheDocument()
  })

  it('deve aplicar busca por email', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })

    render(<AuditoriaPage />)

    await waitFor(() => {
      expect(screen.getByText('Toggle Julia')).toBeInTheDocument()
    })

    mockFetch.mockClear()

    const searchInput = screen.getByPlaceholderText(/buscar por email/i)
    fireEvent.change(searchInput, { target: { value: 'admin' } })

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })

    const calledUrl = mockFetch.mock.calls[0]?.[0] as string
    expect(calledUrl).toContain('actor_email=admin')
  })

  it('deve mostrar mensagem quando nao ha logs', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: [], total: 0, page: 1, per_page: 50, pages: 0 }),
    })

    render(<AuditoriaPage />)

    await waitFor(() => {
      expect(screen.getByText(/nenhum log encontrado/i)).toBeInTheDocument()
    })
  })

  it('deve ter botao de filtros', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })

    render(<AuditoriaPage />)

    // Botao de filtro (icon Filter)
    const buttons = screen.getAllByRole('button')
    const filterButton = buttons.find(
      (btn) => btn.querySelector('svg.lucide-filter') !== null
    )
    expect(filterButton).toBeDefined()
  })

  it('deve abrir sheet de filtros ao clicar', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })

    render(<AuditoriaPage />)

    await waitFor(() => {
      expect(screen.getByText('Toggle Julia')).toBeInTheDocument()
    })

    // Encontrar botao de filtro
    const buttons = screen.getAllByRole('button')
    const filterButton = buttons.find(
      (btn) => btn.querySelector('svg.lucide-filter') !== null
    )

    fireEvent.click(filterButton!)

    await waitFor(() => {
      expect(screen.getByText('Filtros')).toBeInTheDocument()
    })
  })

  it('deve mostrar total de registros', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ...mockResponse, total: 42 }),
    })

    render(<AuditoriaPage />)

    await waitFor(() => {
      expect(screen.getByText(/42 registros/)).toBeInTheDocument()
    })
  })
})
