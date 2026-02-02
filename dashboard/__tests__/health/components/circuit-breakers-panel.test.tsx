import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CircuitBreakersPanel } from '@/components/health/circuit-breakers-panel'

// Mock useToast
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('CircuitBreakersPanel', () => {
  const mockCircuits = [
    { name: 'evolution', state: 'CLOSED' as const, failures: 0, threshold: 5 },
    { name: 'claude', state: 'HALF_OPEN' as const, failures: 3, threshold: 5 },
    { name: 'supabase', state: 'OPEN' as const, failures: 5, threshold: 5 },
  ]

  const mockOnReset = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch.mockResolvedValue({ ok: true })
  })

  describe('Rendering', () => {
    it('renders panel title', () => {
      render(<CircuitBreakersPanel circuits={mockCircuits} onReset={mockOnReset} />)
      expect(screen.getByText('Circuit Breakers')).toBeInTheDocument()
    })

    it('renders panel description', () => {
      render(<CircuitBreakersPanel circuits={mockCircuits} onReset={mockOnReset} />)
      expect(screen.getByText('Status e controle dos circuit breakers')).toBeInTheDocument()
    })

    it('renders legend', () => {
      render(<CircuitBreakersPanel circuits={mockCircuits} onReset={mockOnReset} />)
      expect(screen.getByText(/CLOSED = operacional/)).toBeInTheDocument()
      expect(screen.getByText(/HALF_OPEN = testando/)).toBeInTheDocument()
      expect(screen.getByText(/OPEN = bloqueado/)).toBeInTheDocument()
    })
  })

  describe('Circuit Display', () => {
    it('displays all circuit names', () => {
      render(<CircuitBreakersPanel circuits={mockCircuits} onReset={mockOnReset} />)
      expect(screen.getByText('evolution')).toBeInTheDocument()
      expect(screen.getByText('claude')).toBeInTheDocument()
      expect(screen.getByText('supabase')).toBeInTheDocument()
    })

    it('displays failure counts', () => {
      render(<CircuitBreakersPanel circuits={mockCircuits} onReset={mockOnReset} />)
      expect(screen.getByText('Falhas: 0/5')).toBeInTheDocument()
      expect(screen.getByText('Falhas: 3/5')).toBeInTheDocument()
      expect(screen.getByText('Falhas: 5/5')).toBeInTheDocument()
    })

    it('displays state badges', () => {
      render(<CircuitBreakersPanel circuits={mockCircuits} onReset={mockOnReset} />)
      expect(screen.getByText('CLOSED')).toBeInTheDocument()
      expect(screen.getByText('HALF_OPEN')).toBeInTheDocument()
      expect(screen.getByText('OPEN')).toBeInTheDocument()
    })
  })

  describe('State Badge Styling', () => {
    it('CLOSED badge has success styling', () => {
      render(<CircuitBreakersPanel circuits={mockCircuits} onReset={mockOnReset} />)
      const closedBadge = screen.getByText('CLOSED')
      expect(closedBadge).toHaveClass('bg-status-success', 'text-status-success-foreground')
    })

    it('HALF_OPEN badge has warning styling', () => {
      render(<CircuitBreakersPanel circuits={mockCircuits} onReset={mockOnReset} />)
      const halfOpenBadge = screen.getByText('HALF_OPEN')
      expect(halfOpenBadge).toHaveClass('bg-status-warning', 'text-status-warning-foreground')
    })

    it('OPEN badge has error styling', () => {
      render(<CircuitBreakersPanel circuits={mockCircuits} onReset={mockOnReset} />)
      const openBadge = screen.getByText('OPEN')
      expect(openBadge).toHaveClass('bg-status-error', 'text-status-error-foreground')
    })
  })

  describe('Reset Button', () => {
    it('shows reset button only for non-CLOSED circuits', () => {
      render(<CircuitBreakersPanel circuits={mockCircuits} onReset={mockOnReset} />)
      const resetButtons = screen.getAllByRole('button')
      // Should have 2 reset buttons (for HALF_OPEN and OPEN)
      expect(resetButtons).toHaveLength(2)
    })

    it('does not show reset button for CLOSED circuit', () => {
      const closedOnly = [{ name: 'test', state: 'CLOSED' as const, failures: 0, threshold: 5 }]
      render(<CircuitBreakersPanel circuits={closedOnly} onReset={mockOnReset} />)
      const resetButtons = screen.queryAllByRole('button')
      expect(resetButtons).toHaveLength(0)
    })

    it('opens confirmation dialog when reset clicked', async () => {
      const user = userEvent.setup()
      render(<CircuitBreakersPanel circuits={mockCircuits} onReset={mockOnReset} />)

      const resetButtons = screen.getAllByRole('button')
      await user.click(resetButtons[0] as HTMLElement)

      await waitFor(() => {
        expect(screen.getByText('Resetar Circuit Breaker?')).toBeInTheDocument()
      })
    })

    it('shows circuit name in confirmation dialog', async () => {
      const user = userEvent.setup()
      const openCircuit = [{ name: 'claude', state: 'OPEN' as const, failures: 5, threshold: 5 }]
      render(<CircuitBreakersPanel circuits={openCircuit} onReset={mockOnReset} />)

      const resetButton = screen.getByRole('button')
      await user.click(resetButton)

      await waitFor(() => {
        // Circuit name appears in both list and dialog (in strong tag)
        const claudeElements = screen.getAllByText('claude')
        expect(claudeElements.length).toBeGreaterThanOrEqual(2)
      })
    })
  })

  describe('Reset Confirmation', () => {
    it('closes dialog on cancel', async () => {
      const user = userEvent.setup()
      render(<CircuitBreakersPanel circuits={mockCircuits} onReset={mockOnReset} />)

      const resetButtons = screen.getAllByRole('button')
      await user.click(resetButtons[0] as HTMLElement)

      await waitFor(() => {
        expect(screen.getByText('Cancelar')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Cancelar'))

      await waitFor(() => {
        expect(screen.queryByText('Resetar Circuit Breaker?')).not.toBeInTheDocument()
      })
    })

    it('calls API on confirm', async () => {
      const user = userEvent.setup()
      const openCircuit = [{ name: 'claude', state: 'OPEN' as const, failures: 5, threshold: 5 }]
      render(<CircuitBreakersPanel circuits={openCircuit} onReset={mockOnReset} />)

      await user.click(screen.getByRole('button'))

      await waitFor(() => {
        expect(screen.getByText('Resetar')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Resetar'))

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          '/api/guardrails/circuits/claude/reset',
          expect.objectContaining({
            method: 'POST',
          })
        )
      })
    })

    it('calls onReset after successful API call', async () => {
      const user = userEvent.setup()
      mockFetch.mockResolvedValueOnce({ ok: true })

      const openCircuit = [{ name: 'test', state: 'OPEN' as const, failures: 5, threshold: 5 }]
      render(<CircuitBreakersPanel circuits={openCircuit} onReset={mockOnReset} />)

      await user.click(screen.getByRole('button'))

      await waitFor(() => {
        expect(screen.getByText('Resetar')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Resetar'))

      await waitFor(() => {
        expect(mockOnReset).toHaveBeenCalled()
      })
    })
  })

  describe('Circuit Row Styling', () => {
    it('CLOSED circuits have success background', () => {
      const closedOnly = [{ name: 'test', state: 'CLOSED' as const, failures: 0, threshold: 5 }]
      const { container } = render(
        <CircuitBreakersPanel circuits={closedOnly} onReset={mockOnReset} />
      )
      // Component uses bg-status-success/10 for CLOSED state
      const row = container.querySelector('.bg-status-success\\/10')
      expect(row).toBeInTheDocument()
    })

    it('HALF_OPEN circuits have warning background', () => {
      const halfOpenOnly = [
        { name: 'test', state: 'HALF_OPEN' as const, failures: 2, threshold: 5 },
      ]
      const { container } = render(
        <CircuitBreakersPanel circuits={halfOpenOnly} onReset={mockOnReset} />
      )
      // Component uses bg-status-warning/10 for HALF_OPEN state
      const row = container.querySelector('.bg-status-warning\\/10')
      expect(row).toBeInTheDocument()
    })

    it('OPEN circuits have error background', () => {
      const openOnly = [{ name: 'test', state: 'OPEN' as const, failures: 5, threshold: 5 }]
      const { container } = render(
        <CircuitBreakersPanel circuits={openOnly} onReset={mockOnReset} />
      )
      // Component uses bg-status-error/10 for OPEN state
      const row = container.querySelector('.bg-status-error\\/10')
      expect(row).toBeInTheDocument()
    })
  })

  describe('Empty State', () => {
    it('renders without errors when circuits is empty', () => {
      render(<CircuitBreakersPanel circuits={[]} onReset={mockOnReset} />)
      expect(screen.getByText('Circuit Breakers')).toBeInTheDocument()
    })
  })
})
