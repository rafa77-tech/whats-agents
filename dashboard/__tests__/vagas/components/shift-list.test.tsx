import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ShiftList } from '@/app/(dashboard)/vagas/components/shift-list'
import type { Shift } from '@/app/(dashboard)/vagas/components/shift-card'

// Mock useRouter
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
  }),
}))

describe('ShiftList', () => {
  const mockShifts: Shift[] = [
    {
      id: 'shift-1',
      hospital: 'Hospital A',
      hospital_id: 'hosp-1',
      especialidade: 'Cardiologia',
      especialidade_id: 'esp-1',
      data: '2026-02-15',
      hora_inicio: '08:00',
      hora_fim: '18:00',
      valor: 2500,
      status: 'aberta',
      reservas_count: 0,
      created_at: '2026-01-01T00:00:00Z',
      criticidade: 'normal',
      contato_nome: null,
      contato_whatsapp: null,
    },
    {
      id: 'shift-2',
      hospital: 'Hospital B',
      hospital_id: 'hosp-2',
      especialidade: 'Ortopedia',
      especialidade_id: 'esp-2',
      data: '2026-02-16',
      hora_inicio: '19:00',
      hora_fim: '07:00',
      valor: 3000,
      status: 'reservada',
      reservas_count: 1,
      created_at: '2026-01-01T00:00:00Z',
      criticidade: 'normal',
      contato_nome: null,
      contato_whatsapp: null,
    },
  ]

  const mockOnPageChange = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Empty State', () => {
    it('shows empty message when no shifts', () => {
      render(<ShiftList shifts={[]} total={0} page={1} pages={0} onPageChange={mockOnPageChange} />)
      expect(screen.getByText('Nenhuma vaga encontrada')).toBeInTheDocument()
    })

    it('does not show pagination when empty', () => {
      render(<ShiftList shifts={[]} total={0} page={1} pages={0} onPageChange={mockOnPageChange} />)
      expect(screen.queryByText(/Pagina/)).not.toBeInTheDocument()
    })
  })

  describe('Shift Rendering', () => {
    it('renders all shifts', () => {
      render(
        <ShiftList
          shifts={mockShifts}
          total={2}
          page={1}
          pages={1}
          onPageChange={mockOnPageChange}
        />
      )
      expect(screen.getByText('Hospital A')).toBeInTheDocument()
      expect(screen.getByText('Hospital B')).toBeInTheDocument()
    })

    it('renders specialties', () => {
      render(
        <ShiftList
          shifts={mockShifts}
          total={2}
          page={1}
          pages={1}
          onPageChange={mockOnPageChange}
        />
      )
      expect(screen.getByText('Cardiologia')).toBeInTheDocument()
      expect(screen.getByText('Ortopedia')).toBeInTheDocument()
    })
  })

  describe('Pagination', () => {
    it('shows pagination info when multiple pages', () => {
      render(
        <ShiftList
          shifts={mockShifts}
          total={40}
          page={1}
          pages={2}
          onPageChange={mockOnPageChange}
        />
      )
      expect(screen.getByText('Pagina 1 de 2 (40 vagas)')).toBeInTheDocument()
    })

    it('does not show pagination when single page', () => {
      render(
        <ShiftList
          shifts={mockShifts}
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
        <ShiftList
          shifts={mockShifts}
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
        <ShiftList
          shifts={mockShifts}
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
        <ShiftList
          shifts={mockShifts}
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
        <ShiftList
          shifts={mockShifts}
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
        <ShiftList
          shifts={mockShifts}
          total={100}
          page={3}
          pages={5}
          onPageChange={mockOnPageChange}
        />
      )
      expect(screen.getByText('Pagina 3 de 5 (100 vagas)')).toBeInTheDocument()
    })
  })

  describe('Selection mode (Sprint 58)', () => {
    it('renders checkboxes when selectable', () => {
      render(
        <ShiftList
          shifts={mockShifts}
          total={2}
          page={1}
          pages={1}
          onPageChange={mockOnPageChange}
          selectable
          selectedIds={new Set()}
          onSelectChange={vi.fn()}
        />
      )
      const checkboxes = screen.getAllByRole('checkbox')
      expect(checkboxes).toHaveLength(2)
    })

    it('does not render checkboxes when not selectable', () => {
      render(
        <ShiftList
          shifts={mockShifts}
          total={2}
          page={1}
          pages={1}
          onPageChange={mockOnPageChange}
        />
      )
      expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
    })

    it('marks selected shifts as checked', () => {
      render(
        <ShiftList
          shifts={mockShifts}
          total={2}
          page={1}
          pages={1}
          onPageChange={mockOnPageChange}
          selectable
          selectedIds={new Set(['shift-1'])}
          onSelectChange={vi.fn()}
        />
      )
      const checkboxes = screen.getAllByRole('checkbox')
      expect(checkboxes[0]).toHaveAttribute('data-state', 'checked')
      expect(checkboxes[1]).toHaveAttribute('data-state', 'unchecked')
    })

    it('calls onSelectChange when checkbox clicked', async () => {
      const onSelectChange = vi.fn()
      const user = userEvent.setup()
      render(
        <ShiftList
          shifts={mockShifts}
          total={2}
          page={1}
          pages={1}
          onPageChange={mockOnPageChange}
          selectable
          selectedIds={new Set()}
          onSelectChange={onSelectChange}
        />
      )
      const checkboxes = screen.getAllByRole('checkbox')
      await user.click(checkboxes[0]!)
      expect(onSelectChange).toHaveBeenCalledWith('shift-1', true)
    })
  })
})
