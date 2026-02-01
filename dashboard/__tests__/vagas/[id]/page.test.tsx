/**
 * Testes para ShiftDetailPage
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ShiftDetailPage from '@/app/(dashboard)/vagas/[id]/page'
import { toast } from 'sonner'

// Mock dos hooks
const mockUseShiftDetail = vi.fn()
const mockUseDoctorSearch = vi.fn()

vi.mock('@/lib/vagas', async () => {
  const actual = await vi.importActual('@/lib/vagas')
  return {
    ...actual,
    useShiftDetail: (id: string) => mockUseShiftDetail(id),
    useDoctorSearch: () => mockUseDoctorSearch(),
  }
})

// Mock next/navigation
const mockPush = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useParams: () => ({ id: 'v1' }),
}))

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('ShiftDetailPage', () => {
  const mockShiftActions = {
    refresh: vi.fn(),
    deleteShift: vi.fn(),
    assignDoctor: vi.fn(),
  }

  const mockDoctorSearchReturn = {
    search: '',
    doctors: [],
    searching: false,
    setSearch: vi.fn(),
    clear: vi.fn(),
  }

  const defaultShiftReturn = {
    shift: null,
    loading: true,
    error: null,
    deleting: false,
    assigning: false,
    actions: mockShiftActions,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseShiftDetail.mockReturnValue(defaultShiftReturn)
    mockUseDoctorSearch.mockReturnValue(mockDoctorSearchReturn)
    // Mock window.confirm
    vi.stubGlobal(
      'confirm',
      vi.fn(() => true)
    )
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('deve renderizar estado de loading', () => {
    render(<ShiftDetailPage />)

    // When loading, the shift detail content should not be visible
    expect(screen.queryByText('Informacoes do Plantao')).not.toBeInTheDocument()
  })

  it('deve renderizar detalhes da vaga', async () => {
    mockUseShiftDetail.mockReturnValue({
      ...defaultShiftReturn,
      loading: false,
      shift: {
        id: 'v1',
        hospital: 'Hospital ABC',
        especialidade: 'Cardiologia',
        data: '2024-01-15',
        hora_inicio: '08:00',
        hora_fim: '18:00',
        valor: 1500,
        status: 'aberta',
        setor: 'UTI',
        cliente_id: null,
        cliente_nome: null,
        created_at: '2024-01-10T10:00:00Z',
        updated_at: null,
      },
    })

    render(<ShiftDetailPage />)

    // Use getAllByText since the hospital name may appear multiple times
    expect(screen.getAllByText('Hospital ABC').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Cardiologia').length).toBeGreaterThan(0)
    expect(screen.getByText('Aberta')).toBeInTheDocument()
  })

  it('deve renderizar erro 404', async () => {
    mockUseShiftDetail.mockReturnValue({
      ...defaultShiftReturn,
      loading: false,
      error: 'Vaga nao encontrada',
    })

    render(<ShiftDetailPage />)

    expect(screen.getByText('Vaga nao encontrada')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /voltar/i })).toBeInTheDocument()
  })

  it('deve navegar de volta ao clicar no botao voltar', async () => {
    mockUseShiftDetail.mockReturnValue({
      ...defaultShiftReturn,
      loading: false,
      error: 'Vaga nao encontrada',
    })

    render(<ShiftDetailPage />)

    const backButton = screen.getByRole('button', { name: /voltar/i })
    fireEvent.click(backButton)

    expect(mockPush).toHaveBeenCalledWith('/vagas')
  })

  it('deve abrir dialog de atribuir medico', async () => {
    mockUseShiftDetail.mockReturnValue({
      ...defaultShiftReturn,
      loading: false,
      shift: {
        id: 'v1',
        hospital: 'Hospital ABC',
        especialidade: 'Cardiologia',
        data: '2024-01-15',
        hora_inicio: '08:00',
        hora_fim: '18:00',
        valor: 1500,
        status: 'aberta',
        setor: null,
        cliente_id: null,
        cliente_nome: null,
        created_at: '2024-01-10T10:00:00Z',
        updated_at: null,
      },
    })

    render(<ShiftDetailPage />)

    const assignButton = screen.getByRole('button', { name: /atribuir medico/i })
    fireEvent.click(assignButton)

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
  })

  it('deve confirmar antes de deletar', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)

    mockUseShiftDetail.mockReturnValue({
      ...defaultShiftReturn,
      loading: false,
      shift: {
        id: 'v1',
        hospital: 'Hospital ABC',
        especialidade: 'Cardiologia',
        data: '2024-01-15',
        hora_inicio: '08:00',
        hora_fim: '18:00',
        valor: 1500,
        status: 'aberta',
        setor: null,
        cliente_id: null,
        cliente_nome: null,
        created_at: '2024-01-10T10:00:00Z',
        updated_at: null,
      },
    })

    render(<ShiftDetailPage />)

    // Find delete button by its destructive class
    const deleteButtons = screen.getAllByRole('button')
    const deleteButton = deleteButtons.find((btn) => btn.className.includes('destructive'))

    expect(deleteButton).toBeDefined()
    fireEvent.click(deleteButton!)

    expect(confirmSpy).toHaveBeenCalled()
    expect(mockShiftActions.deleteShift).not.toHaveBeenCalled()
  })

  it('deve mostrar toast de sucesso ao deletar', async () => {
    mockShiftActions.deleteShift.mockResolvedValue(true)

    mockUseShiftDetail.mockReturnValue({
      ...defaultShiftReturn,
      loading: false,
      shift: {
        id: 'v1',
        hospital: 'Hospital ABC',
        especialidade: 'Cardiologia',
        data: '2024-01-15',
        hora_inicio: '08:00',
        hora_fim: '18:00',
        valor: 1500,
        status: 'aberta',
        setor: null,
        cliente_id: null,
        cliente_nome: null,
        created_at: '2024-01-10T10:00:00Z',
        updated_at: null,
      },
    })

    render(<ShiftDetailPage />)

    // Find delete button by its destructive class
    const deleteButtons = screen.getAllByRole('button')
    const deleteButton = deleteButtons.find((btn) => btn.className.includes('destructive'))

    expect(deleteButton).toBeDefined()
    fireEvent.click(deleteButton!)

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Vaga excluida com sucesso')
    })

    expect(mockPush).toHaveBeenCalledWith('/vagas')
  })

  it('deve mostrar toast de erro ao falhar delete', async () => {
    mockShiftActions.deleteShift.mockRejectedValue(new Error('Erro ao excluir'))

    mockUseShiftDetail.mockReturnValue({
      ...defaultShiftReturn,
      loading: false,
      shift: {
        id: 'v1',
        hospital: 'Hospital ABC',
        especialidade: 'Cardiologia',
        data: '2024-01-15',
        hora_inicio: '08:00',
        hora_fim: '18:00',
        valor: 1500,
        status: 'aberta',
        setor: null,
        cliente_id: null,
        cliente_nome: null,
        created_at: '2024-01-10T10:00:00Z',
        updated_at: null,
      },
    })

    render(<ShiftDetailPage />)

    // Find delete button by its destructive class
    const deleteButtons = screen.getAllByRole('button')
    const deleteButton = deleteButtons.find((btn) => btn.className.includes('destructive'))

    expect(deleteButton).toBeDefined()
    fireEvent.click(deleteButton!)

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Erro ao excluir')
    })
  })

  it('deve mostrar medico atribuido', async () => {
    mockUseShiftDetail.mockReturnValue({
      ...defaultShiftReturn,
      loading: false,
      shift: {
        id: 'v1',
        hospital: 'Hospital ABC',
        especialidade: 'Cardiologia',
        data: '2024-01-15',
        hora_inicio: '08:00',
        hora_fim: '18:00',
        valor: 1500,
        status: 'reservada',
        setor: null,
        cliente_id: 'c1',
        cliente_nome: 'Dr. Carlos Silva',
        created_at: '2024-01-10T10:00:00Z',
        updated_at: null,
      },
    })

    render(<ShiftDetailPage />)

    expect(screen.getByText('Dr. Carlos Silva')).toBeInTheDocument()
    expect(screen.getByText('Ver perfil')).toBeInTheDocument()
  })

  it('deve mostrar valor formatado', async () => {
    mockUseShiftDetail.mockReturnValue({
      ...defaultShiftReturn,
      loading: false,
      shift: {
        id: 'v1',
        hospital: 'Hospital ABC',
        especialidade: 'Cardiologia',
        data: '2024-01-15',
        hora_inicio: '08:00',
        hora_fim: '18:00',
        valor: 1500,
        status: 'aberta',
        setor: null,
        cliente_id: null,
        cliente_nome: null,
        created_at: '2024-01-10T10:00:00Z',
        updated_at: null,
      },
    })

    render(<ShiftDetailPage />)

    // Valor deve estar formatado em BRL
    expect(screen.getByText(/R\$\s*1\.500,00/)).toBeInTheDocument()
  })
})
