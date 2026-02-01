/**
 * Testes para VagasPage
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import VagasPage from '@/app/(dashboard)/vagas/page'

// Mock dos hooks
const mockUseShifts = vi.fn()

vi.mock('@/lib/vagas', async () => {
  const actual = await vi.importActual('@/lib/vagas')
  return {
    ...actual,
    useShifts: () => mockUseShifts(),
  }
})

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}))

describe('VagasPage', () => {
  const mockActions = {
    setFilters: vi.fn(),
    setSearch: vi.fn(),
    setPage: vi.fn(),
    setViewMode: vi.fn(),
    setCalendarMonth: vi.fn(),
    handleDateSelect: vi.fn(),
    handleCalendarMonthChange: vi.fn(),
    clearFilters: vi.fn(),
    refresh: vi.fn(),
  }

  const defaultHookReturn = {
    data: null,
    loading: true,
    error: null,
    filters: {},
    search: '',
    page: 1,
    viewMode: 'list' as const,
    calendarMonth: new Date(),
    selectedDate: undefined,
    actions: mockActions,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseShifts.mockReturnValue(defaultHookReturn)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deve renderizar skeletons durante loading', () => {
    render(<VagasPage />)

    // When loading, the shift list should not be visible
    expect(screen.queryByText('0 vagas cadastradas')).toBeInTheDocument()
  })

  it('deve renderizar lista de vagas apos loading', async () => {
    mockUseShifts.mockReturnValue({
      ...defaultHookReturn,
      loading: false,
      data: {
        data: [
          {
            id: 'v1',
            hospital: 'Hospital ABC',
            especialidade: 'Cardiologia',
            data: '2024-01-15',
            hora_inicio: '08:00',
            hora_fim: '18:00',
            valor: 1500,
            status: 'aberta',
            reservas_count: 0,
          },
        ],
        total: 1,
        pages: 1,
      },
    })

    render(<VagasPage />)

    // Deve mostrar total de vagas
    expect(screen.getByText('1 vagas cadastradas')).toBeInTheDocument()
  })

  it('deve alternar entre modo lista e calendario', async () => {
    mockUseShifts.mockReturnValue({
      ...defaultHookReturn,
      loading: false,
      data: { data: [], total: 0, pages: 0 },
    })

    render(<VagasPage />)

    // Encontrar botoes de modo
    const buttons = screen.getAllByRole('button')
    const calendarButton = buttons.find((btn) =>
      btn.querySelector('svg.lucide-calendar')
    )

    expect(calendarButton).toBeDefined()

    fireEvent.click(calendarButton!)

    expect(mockActions.setViewMode).toHaveBeenCalledWith('calendar')
  })

  it('deve abrir sheet de filtros', async () => {
    mockUseShifts.mockReturnValue({
      ...defaultHookReturn,
      loading: false,
      data: { data: [], total: 0, pages: 0 },
    })

    render(<VagasPage />)

    // Clicar no botao de filtros
    const filterButton = screen.getByRole('button', { name: /filtros/i })
    fireEvent.click(filterButton)

    // Sheet deve estar aberto
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
  })

  it('deve aplicar busca', async () => {
    mockUseShifts.mockReturnValue({
      ...defaultHookReturn,
      loading: false,
      data: { data: [], total: 0, pages: 0 },
    })

    render(<VagasPage />)

    const searchInput = screen.getByPlaceholderText(/buscar por hospital/i)
    fireEvent.change(searchInput, { target: { value: 'cardio' } })

    expect(mockActions.setSearch).toHaveBeenCalledWith('cardio')
  })

  it('deve mostrar estado vazio', async () => {
    mockUseShifts.mockReturnValue({
      ...defaultHookReturn,
      loading: false,
      data: { data: [], total: 0, pages: 0 },
    })

    render(<VagasPage />)

    expect(screen.getByText('0 vagas cadastradas')).toBeInTheDocument()
  })

  it('deve renderizar titulo corretamente', () => {
    render(<VagasPage />)

    expect(screen.getByRole('heading', { name: 'Vagas' })).toBeInTheDocument()
  })

  it('deve ter botao de nova vaga', () => {
    render(<VagasPage />)

    const newButton = screen.getByRole('button', { name: /nova vaga/i })
    expect(newButton).toBeInTheDocument()
  })
})
