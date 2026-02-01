import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DoctorList } from '@/app/(dashboard)/medicos/components/doctor-list'
import type { Doctor } from '@/app/(dashboard)/medicos/components/doctor-card'

// Mock useRouter
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
  }),
}))

describe('DoctorList', () => {
  const mockDoctors: Doctor[] = [
    {
      id: 'doctor-1',
      nome: 'João Silva',
      telefone: '11999998888',
      especialidade: 'Cardiologia',
      cidade: 'São Paulo',
      stage_jornada: 'novo',
      opt_out: false,
      created_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 'doctor-2',
      nome: 'Maria Santos',
      telefone: '11999997777',
      especialidade: 'Ortopedia',
      cidade: 'Rio de Janeiro',
      stage_jornada: 'respondeu',
      opt_out: true,
      created_at: '2026-01-02T00:00:00Z',
    },
  ]

  const mockOnPageChange = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Empty State', () => {
    it('shows empty message when no doctors', () => {
      render(
        <DoctorList
          doctors={[]}
          total={0}
          page={1}
          pages={0}
          onPageChange={mockOnPageChange}
        />
      )
      expect(screen.getByText('Nenhum medico encontrado')).toBeInTheDocument()
    })

    it('does not show pagination when empty', () => {
      render(
        <DoctorList
          doctors={[]}
          total={0}
          page={1}
          pages={0}
          onPageChange={mockOnPageChange}
        />
      )
      expect(screen.queryByText(/Pagina/)).not.toBeInTheDocument()
    })
  })

  describe('Doctor Rendering', () => {
    it('renders all doctors', () => {
      render(
        <DoctorList
          doctors={mockDoctors}
          total={2}
          page={1}
          pages={1}
          onPageChange={mockOnPageChange}
        />
      )
      expect(screen.getByText('João Silva')).toBeInTheDocument()
      expect(screen.getByText('Maria Santos')).toBeInTheDocument()
    })

    it('renders specialties', () => {
      render(
        <DoctorList
          doctors={mockDoctors}
          total={2}
          page={1}
          pages={1}
          onPageChange={mockOnPageChange}
        />
      )
      expect(screen.getByText('Cardiologia')).toBeInTheDocument()
      expect(screen.getByText('Ortopedia')).toBeInTheDocument()
    })

    it('renders stage badges', () => {
      render(
        <DoctorList
          doctors={mockDoctors}
          total={2}
          page={1}
          pages={1}
          onPageChange={mockOnPageChange}
        />
      )
      expect(screen.getByText('Novo')).toBeInTheDocument()
      expect(screen.getByText('Respondeu')).toBeInTheDocument()
    })
  })

  describe('Pagination', () => {
    it('shows pagination info when multiple pages', () => {
      render(
        <DoctorList
          doctors={mockDoctors}
          total={40}
          page={1}
          pages={2}
          onPageChange={mockOnPageChange}
        />
      )
      expect(screen.getByText('Pagina 1 de 2 (40 medicos)')).toBeInTheDocument()
    })

    it('does not show pagination when single page', () => {
      render(
        <DoctorList
          doctors={mockDoctors}
          total={2}
          page={1}
          pages={1}
          onPageChange={mockOnPageChange}
        />
      )
      expect(screen.queryByText(/Pagina/)).not.toBeInTheDocument()
    })

    it('disables previous button on first page', () => {
      render(
        <DoctorList
          doctors={mockDoctors}
          total={40}
          page={1}
          pages={2}
          onPageChange={mockOnPageChange}
        />
      )
      const buttons = screen.getAllByRole('button')
      const prevButton = buttons[0]
      expect(prevButton).toBeDisabled()
    })

    it('disables next button on last page', () => {
      render(
        <DoctorList
          doctors={mockDoctors}
          total={40}
          page={2}
          pages={2}
          onPageChange={mockOnPageChange}
        />
      )
      const buttons = screen.getAllByRole('button')
      const nextButton = buttons[buttons.length - 1]
      expect(nextButton).toBeDisabled()
    })

    it('calls onPageChange when clicking previous', async () => {
      const user = userEvent.setup()
      render(
        <DoctorList
          doctors={mockDoctors}
          total={60}
          page={2}
          pages={3}
          onPageChange={mockOnPageChange}
        />
      )
      const buttons = screen.getAllByRole('button')
      expect(buttons.length).toBeGreaterThan(0)
      const prevButton = buttons[0]
      if (prevButton) {
        await user.click(prevButton)
        expect(mockOnPageChange).toHaveBeenCalledWith(1)
      }
    })

    it('calls onPageChange when clicking next', async () => {
      const user = userEvent.setup()
      render(
        <DoctorList
          doctors={mockDoctors}
          total={60}
          page={2}
          pages={3}
          onPageChange={mockOnPageChange}
        />
      )
      const buttons = screen.getAllByRole('button')
      expect(buttons.length).toBeGreaterThan(0)
      const nextButton = buttons[buttons.length - 1]
      if (nextButton) {
        await user.click(nextButton)
        expect(mockOnPageChange).toHaveBeenCalledWith(3)
      }
    })

    it('shows correct page info for middle page', () => {
      render(
        <DoctorList
          doctors={mockDoctors}
          total={100}
          page={3}
          pages={5}
          onPageChange={mockOnPageChange}
        />
      )
      expect(screen.getByText('Pagina 3 de 5 (100 medicos)')).toBeInTheDocument()
    })
  })
})
