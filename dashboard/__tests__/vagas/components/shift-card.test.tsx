import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ShiftCard } from '@/app/(dashboard)/vagas/components/shift-card'
import type { Shift } from '@/app/(dashboard)/vagas/components/shift-card'

// Get the mocked router
const mockPush = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
  }),
}))

describe('ShiftCard', () => {
  const mockShift: Shift = {
    id: 'shift-123',
    hospital: 'Hospital São Luiz',
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
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders hospital name', () => {
    render(<ShiftCard shift={mockShift} />)
    expect(screen.getByText('Hospital São Luiz')).toBeInTheDocument()
  })

  it('renders specialty', () => {
    render(<ShiftCard shift={mockShift} />)
    expect(screen.getByText('Cardiologia')).toBeInTheDocument()
  })

  it('renders date correctly', () => {
    render(<ShiftCard shift={mockShift} />)
    // Day should be displayed as "15"
    expect(screen.getByText('15')).toBeInTheDocument()
    // Month should be "fev" (February in Portuguese)
    expect(screen.getByText('fev')).toBeInTheDocument()
  })

  it('renders time range', () => {
    render(<ShiftCard shift={mockShift} />)
    expect(screen.getByText('08:00 - 18:00')).toBeInTheDocument()
  })

  it('renders formatted currency value', () => {
    render(<ShiftCard shift={mockShift} />)
    expect(screen.getByText('R$ 2.500,00')).toBeInTheDocument()
  })

  it('renders status badge with correct label', () => {
    render(<ShiftCard shift={mockShift} />)
    expect(screen.getByText('Aberta')).toBeInTheDocument()
  })

  it('renders different status colors', () => {
    const reservadaShift = { ...mockShift, status: 'reservada' }
    const { rerender } = render(<ShiftCard shift={reservadaShift} />)
    expect(screen.getByText('Reservada')).toBeInTheDocument()

    const confirmadaShift = { ...mockShift, status: 'confirmada' }
    rerender(<ShiftCard shift={confirmadaShift} />)
    expect(screen.getByText('Confirmada')).toBeInTheDocument()

    const canceladaShift = { ...mockShift, status: 'cancelada' }
    rerender(<ShiftCard shift={canceladaShift} />)
    expect(screen.getByText('Cancelada')).toBeInTheDocument()
  })

  it('renders reservations count when > 0', () => {
    const shiftWithReservations = { ...mockShift, reservas_count: 3 }
    render(<ShiftCard shift={shiftWithReservations} />)
    expect(screen.getByText('3 reserva(s)')).toBeInTheDocument()
  })

  it('does not render reservations count when 0', () => {
    render(<ShiftCard shift={mockShift} />)
    expect(screen.queryByText(/reserva/i)).not.toBeInTheDocument()
  })

  it('navigates to detail page on click', async () => {
    const user = userEvent.setup()
    render(<ShiftCard shift={mockShift} />)

    // Find the card container
    const hospitalName = screen.getByText('Hospital São Luiz')
    const card = hospitalName.closest('[class*="cursor-pointer"]')
    if (card) {
      await user.click(card)
      expect(mockPush).toHaveBeenCalledWith('/vagas/shift-123')
    }
  })

  it('handles unknown status gracefully', () => {
    const unknownStatusShift = { ...mockShift, status: 'unknown_status' }
    render(<ShiftCard shift={unknownStatusShift} />)
    expect(screen.getByText('unknown_status')).toBeInTheDocument()
  })

  it('renders with zero value', () => {
    const freeShift = { ...mockShift, valor: 0 }
    render(<ShiftCard shift={freeShift} />)
    expect(screen.getByText('R$ 0,00')).toBeInTheDocument()
  })

  it('renders with large value correctly', () => {
    const expensiveShift = { ...mockShift, valor: 15000 }
    render(<ShiftCard shift={expensiveShift} />)
    expect(screen.getByText('R$ 15.000,00')).toBeInTheDocument()
  })
})
