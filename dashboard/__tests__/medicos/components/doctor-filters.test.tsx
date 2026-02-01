import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DoctorFilters } from '@/app/(dashboard)/medicos/components/doctor-filters'

describe('DoctorFilters', () => {
  const mockOnApply = vi.fn()
  const mockOnClear = vi.fn()

  const baseProps = {
    filters: {},
    onApply: mockOnApply,
    onClear: mockOnClear,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders stage select', () => {
      render(<DoctorFilters {...baseProps} />)
      expect(screen.getByText('Etapa do Funil')).toBeInTheDocument()
    })

    it('renders specialty select', () => {
      render(<DoctorFilters {...baseProps} />)
      expect(screen.getByText('Especialidade')).toBeInTheDocument()
    })

    it('renders opt-out toggle', () => {
      render(<DoctorFilters {...baseProps} />)
      expect(screen.getByText('Apenas Opt-out')).toBeInTheDocument()
    })

    it('renders apply and clear buttons', () => {
      render(<DoctorFilters {...baseProps} />)
      expect(screen.getByText('Aplicar')).toBeInTheDocument()
      expect(screen.getByText('Limpar')).toBeInTheDocument()
    })
  })

  describe('Initial Values', () => {
    it('shows initial stage filter', () => {
      render(
        <DoctorFilters
          {...baseProps}
          filters={{ stage_jornada: 'novo' }}
        />
      )
      expect(screen.getByText('Etapa do Funil')).toBeInTheDocument()
    })

    it('shows opt-out toggle state', () => {
      render(
        <DoctorFilters
          {...baseProps}
          filters={{ opt_out: true }}
        />
      )
      const toggle = screen.getByRole('switch')
      expect(toggle).toBeChecked()
    })
  })

  describe('Actions', () => {
    it('calls onApply when clicking apply button', async () => {
      const user = userEvent.setup()
      render(<DoctorFilters {...baseProps} />)

      const applyButton = screen.getByText('Aplicar')
      await user.click(applyButton)

      expect(mockOnApply).toHaveBeenCalled()
    })

    it('calls onClear when clicking clear button', async () => {
      const user = userEvent.setup()
      render(<DoctorFilters {...baseProps} />)

      const clearButton = screen.getByText('Limpar')
      await user.click(clearButton)

      expect(mockOnClear).toHaveBeenCalled()
    })

    it('applies filters with current values', async () => {
      const user = userEvent.setup()
      render(<DoctorFilters {...baseProps} filters={{ stage_jornada: 'respondeu' }} />)

      const applyButton = screen.getByText('Aplicar')
      await user.click(applyButton)

      expect(mockOnApply).toHaveBeenCalledWith(
        expect.objectContaining({
          stage_jornada: 'respondeu',
        })
      )
    })

    it('toggles opt-out filter', async () => {
      const user = userEvent.setup()
      render(<DoctorFilters {...baseProps} />)

      const toggle = screen.getByRole('switch')
      await user.click(toggle)

      const applyButton = screen.getByText('Aplicar')
      await user.click(applyButton)

      expect(mockOnApply).toHaveBeenCalledWith(
        expect.objectContaining({
          opt_out: true,
        })
      )
    })
  })
})
