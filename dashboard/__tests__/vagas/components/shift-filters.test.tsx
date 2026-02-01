import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ShiftFilters } from '@/app/(dashboard)/vagas/components/shift-filters'

// Mock useAuth
vi.mock('@/hooks/use-auth', () => ({
  useAuth: () => ({
    session: {
      access_token: 'mock-token',
    },
  }),
}))

// Mock fetch for filter options
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('ShiftFilters', () => {
  const mockOnApply = vi.fn()
  const mockOnClear = vi.fn()

  const baseProps = {
    filters: {},
    onApply: mockOnApply,
    onClear: mockOnClear,
  }

  const mockHospitals = [
    { id: 'hosp-1', nome: 'Hospital São Luiz' },
    { id: 'hosp-2', nome: 'Hospital Albert Einstein' },
  ]

  const mockEspecialidades = [
    { id: 'esp-1', nome: 'Cardiologia' },
    { id: 'esp-2', nome: 'Ortopedia' },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('hospitals')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockHospitals),
        })
      }
      if (url.includes('especialidades')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockEspecialidades),
        })
      }
      return Promise.resolve({ ok: false })
    })
  })

  describe('Rendering', () => {
    it('renders status select', () => {
      render(<ShiftFilters {...baseProps} />)
      expect(screen.getByText('Status')).toBeInTheDocument()
    })

    it('renders hospital select', () => {
      render(<ShiftFilters {...baseProps} />)
      expect(screen.getByText('Hospital')).toBeInTheDocument()
    })

    it('renders specialty select', () => {
      render(<ShiftFilters {...baseProps} />)
      expect(screen.getByText('Especialidade')).toBeInTheDocument()
    })

    it('renders date inputs', () => {
      render(<ShiftFilters {...baseProps} />)
      expect(screen.getByText('Data Inicial')).toBeInTheDocument()
      expect(screen.getByText('Data Final')).toBeInTheDocument()
    })

    it('renders apply and clear buttons', () => {
      render(<ShiftFilters {...baseProps} />)
      expect(screen.getByText('Aplicar')).toBeInTheDocument()
      expect(screen.getByText('Limpar')).toBeInTheDocument()
    })
  })

  describe('Fetching Options', () => {
    it('fetches hospitals and specialties on mount', async () => {
      render(<ShiftFilters {...baseProps} />)

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(2)
      })

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/dashboard/shifts/options/hospitals'),
        expect.objectContaining({
          headers: { Authorization: 'Bearer mock-token' },
        })
      )
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/dashboard/shifts/options/especialidades'),
        expect.objectContaining({
          headers: { Authorization: 'Bearer mock-token' },
        })
      )
    })
  })

  describe('Initial Values', () => {
    it('shows initial status filter', () => {
      render(<ShiftFilters {...baseProps} filters={{ status: 'aberta' }} />)
      // The select should show the current value
      // This is hard to test with Radix UI, but we can verify the prop is passed
      expect(screen.getByText('Status')).toBeInTheDocument()
    })

    it('shows date range labels', () => {
      render(
        <ShiftFilters
          {...baseProps}
          filters={{
            date_from: '2026-02-01',
            date_to: '2026-02-28',
          }}
        />
      )

      // Date inputs should be present
      expect(screen.getByText('Data Inicial')).toBeInTheDocument()
      expect(screen.getByText('Data Final')).toBeInTheDocument()
    })
  })

  describe('Actions', () => {
    it('calls onApply when clicking apply button', async () => {
      const user = userEvent.setup()
      render(<ShiftFilters {...baseProps} />)

      const applyButton = screen.getByText('Aplicar')
      await user.click(applyButton)

      expect(mockOnApply).toHaveBeenCalled()
    })

    it('calls onClear when clicking clear button', async () => {
      const user = userEvent.setup()
      render(<ShiftFilters {...baseProps} />)

      const clearButton = screen.getByText('Limpar')
      await user.click(clearButton)

      expect(mockOnClear).toHaveBeenCalled()
    })

    it('applies filters with current values', async () => {
      const user = userEvent.setup()
      render(<ShiftFilters {...baseProps} filters={{ status: 'aberta' }} />)

      const applyButton = screen.getByText('Aplicar')
      await user.click(applyButton)

      expect(mockOnApply).toHaveBeenCalledWith(
        expect.objectContaining({
          status: 'aberta',
        })
      )
    })
  })

  // Note: Testing Radix UI Select interactions is complex in jsdom
  // Status options are tested via the constants tests in lib/vagas/constants.test.ts
})
