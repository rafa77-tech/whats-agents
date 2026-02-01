import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ShiftCalendar } from '@/app/(dashboard)/vagas/components/shift-calendar'
import type { Shift } from '@/app/(dashboard)/vagas/components/shift-card'

describe('ShiftCalendar', () => {
  const mockOnDateSelect = vi.fn()
  const mockOnMonthChange = vi.fn()

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
    },
    {
      id: 'shift-2',
      hospital: 'Hospital B',
      hospital_id: 'hosp-2',
      especialidade: 'Ortopedia',
      especialidade_id: 'esp-2',
      data: '2026-02-15', // Same date, different shift
      hora_inicio: '19:00',
      hora_fim: '07:00',
      valor: 3000,
      status: 'reservada',
      reservas_count: 1,
      created_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 'shift-3',
      hospital: 'Hospital C',
      hospital_id: 'hosp-3',
      especialidade: 'Pediatria',
      especialidade_id: 'esp-3',
      data: '2026-02-20',
      hora_inicio: '08:00',
      hora_fim: '18:00',
      valor: 2000,
      status: 'confirmada',
      reservas_count: 0,
      created_at: '2026-01-01T00:00:00Z',
    },
  ]

  const baseProps = {
    shifts: mockShifts,
    onDateSelect: mockOnDateSelect,
    currentMonth: new Date(2026, 1, 1), // February 2026
    onMonthChange: mockOnMonthChange,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Header', () => {
    it('renders current month and year', () => {
      render(<ShiftCalendar {...baseProps} />)
      expect(screen.getByText(/fevereiro 2026/i)).toBeInTheDocument()
    })

    it('has navigation buttons', () => {
      render(<ShiftCalendar {...baseProps} />)
      const buttons = screen.getAllByRole('button')
      expect(buttons.length).toBeGreaterThanOrEqual(2)
    })

    it('calls onMonthChange with prev when clicking previous', async () => {
      const user = userEvent.setup()
      render(<ShiftCalendar {...baseProps} />)

      // Find the chevron-left button (first navigation button)
      const buttons = screen.getAllByRole('button')
      const prevButton = buttons.find((btn) => btn.querySelector('svg.lucide-chevron-left'))
      if (prevButton) {
        await user.click(prevButton)
        expect(mockOnMonthChange).toHaveBeenCalledWith('prev')
      }
    })

    it('calls onMonthChange with next when clicking next', async () => {
      const user = userEvent.setup()
      render(<ShiftCalendar {...baseProps} />)

      // Find the chevron-right button
      const buttons = screen.getAllByRole('button')
      const nextButton = buttons.find((btn) => btn.querySelector('svg.lucide-chevron-right'))
      if (nextButton) {
        await user.click(nextButton)
        expect(mockOnMonthChange).toHaveBeenCalledWith('next')
      }
    })
  })

  describe('Week Days Header', () => {
    it('renders all week days in Portuguese', () => {
      render(<ShiftCalendar {...baseProps} />)
      expect(screen.getByText('Dom')).toBeInTheDocument()
      expect(screen.getByText('Seg')).toBeInTheDocument()
      expect(screen.getByText('Ter')).toBeInTheDocument()
      expect(screen.getByText('Qua')).toBeInTheDocument()
      expect(screen.getByText('Qui')).toBeInTheDocument()
      expect(screen.getByText('Sex')).toBeInTheDocument()
      expect(screen.getByText('Sab')).toBeInTheDocument()
    })
  })

  describe('Calendar Grid', () => {
    it('renders days of the month', () => {
      render(<ShiftCalendar {...baseProps} />)
      // Calendar shows days from current and adjacent months
      // Check that typical day numbers exist in the grid
      const dayButtons = screen.getAllByRole('button')
      // Should have many day buttons (at least 28 for February + nav buttons)
      expect(dayButtons.length).toBeGreaterThanOrEqual(30)
    })

    it('shows shift count on days with shifts', () => {
      render(<ShiftCalendar {...baseProps} />)
      // Day 15 has 2 shifts
      const dayButtons = screen.getAllByRole('button')
      const day15Button = dayButtons.find((btn) => btn.textContent?.includes('15'))
      expect(day15Button).toBeDefined()
      if (day15Button) {
        expect(day15Button.textContent).toContain('2')
      }
    })

    it('calls onDateSelect when clicking a day', async () => {
      const user = userEvent.setup()
      render(<ShiftCalendar {...baseProps} />)

      // Find day 15 button
      const dayButtons = screen.getAllByRole('button')
      const day15Button = dayButtons.find(
        (btn) => btn.textContent?.includes('15') && !btn.textContent?.includes('2026')
      )
      expect(day15Button).toBeDefined()
      if (day15Button) {
        await user.click(day15Button)
        expect(mockOnDateSelect).toHaveBeenCalled()
        // Check that the date passed is February 15, 2026
        const calledDate = mockOnDateSelect.mock.calls[0]?.[0] as Date | undefined
        expect(calledDate).toBeDefined()
        if (calledDate) {
          expect(calledDate.getFullYear()).toBe(2026)
          expect(calledDate.getMonth()).toBe(1) // February = 1
          expect(calledDate.getDate()).toBe(15)
        }
      }
    })

    it('highlights selected date', () => {
      const selectedDate = new Date(2026, 1, 15) // February 15, 2026
      render(<ShiftCalendar {...baseProps} selectedDate={selectedDate} />)

      // The selected day should have ring-2 ring-primary class
      const dayButtons = screen.getAllByRole('button')
      const day15Button = dayButtons.find((btn) => {
        const text = btn.textContent
        return text?.includes('15') && btn.classList.contains('ring-2')
      })
      expect(day15Button).toBeDefined()
    })
  })

  describe('Legend', () => {
    it('shows status legend', () => {
      render(<ShiftCalendar {...baseProps} />)
      expect(screen.getByText('Aberta')).toBeInTheDocument()
      expect(screen.getByText('Reservada')).toBeInTheDocument()
      expect(screen.getByText('Confirmada')).toBeInTheDocument()
      expect(screen.getByText('Cancelada')).toBeInTheDocument()
      expect(screen.getByText('Realizada')).toBeInTheDocument()
    })
  })

  describe('Empty State', () => {
    it('renders calendar without shifts', () => {
      render(<ShiftCalendar {...baseProps} shifts={[]} />)
      expect(screen.getByText(/fevereiro 2026/i)).toBeInTheDocument()
      // Should still render the calendar grid
      const dayButtons = screen.getAllByRole('button')
      expect(dayButtons.length).toBeGreaterThanOrEqual(30)
    })
  })

  describe('Different Months', () => {
    it('renders January correctly', () => {
      render(<ShiftCalendar {...baseProps} currentMonth={new Date(2026, 0, 1)} shifts={[]} />)
      expect(screen.getByText(/janeiro 2026/i)).toBeInTheDocument()
      // January has 31 days - just verify the header shows correctly
    })

    it('renders December correctly', () => {
      render(<ShiftCalendar {...baseProps} currentMonth={new Date(2026, 11, 1)} shifts={[]} />)
      expect(screen.getByText(/dezembro 2026/i)).toBeInTheDocument()
    })
  })
})
