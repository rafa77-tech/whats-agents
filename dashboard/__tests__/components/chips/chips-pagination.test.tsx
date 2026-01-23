/**
 * Tests for components/chips/chips-pagination.tsx
 *
 * Tests the ChipsPagination component rendering and navigation.
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ChipsPagination } from '@/components/chips/chips-pagination'

describe('ChipsPagination', () => {
  const defaultProps = {
    page: 1,
    pageSize: 20,
    total: 100,
    onPageChange: vi.fn(),
    onPageSizeChange: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('rendering', () => {
    it('should display total count', () => {
      render(<ChipsPagination {...defaultProps} />)
      expect(screen.getByText(/de 100 chips/)).toBeInTheDocument()
    })

    it('should display current page range', () => {
      render(<ChipsPagination {...defaultProps} />)
      expect(screen.getByText('1-20 de 100')).toBeInTheDocument()
    })

    it('should display correct range for middle pages', () => {
      render(<ChipsPagination {...defaultProps} page={3} />)
      expect(screen.getByText('41-60 de 100')).toBeInTheDocument()
    })

    it('should display correct range for last page', () => {
      render(<ChipsPagination {...defaultProps} page={5} />)
      expect(screen.getByText('81-100 de 100')).toBeInTheDocument()
    })

    it('should display page number', () => {
      render(<ChipsPagination {...defaultProps} />)
      expect(screen.getByText('Pagina 1 de 5')).toBeInTheDocument()
    })

    it('should handle zero total', () => {
      render(<ChipsPagination {...defaultProps} total={0} />)
      expect(screen.getByText('0-0 de 0')).toBeInTheDocument()
      expect(screen.getByText('Pagina 1 de 1')).toBeInTheDocument()
    })
  })

  describe('navigation buttons', () => {
    it('should disable previous buttons on first page', () => {
      render(<ChipsPagination {...defaultProps} page={1} />)
      const buttons = screen.getAllByRole('button')
      // First and second buttons (first page, previous page) should be disabled
      expect(buttons[0]).toBeDisabled()
      expect(buttons[1]).toBeDisabled()
    })

    it('should enable previous buttons when not on first page', () => {
      render(<ChipsPagination {...defaultProps} page={2} />)
      const buttons = screen.getAllByRole('button')
      expect(buttons[0]).not.toBeDisabled()
      expect(buttons[1]).not.toBeDisabled()
    })

    it('should disable next buttons on last page', () => {
      render(<ChipsPagination {...defaultProps} page={5} />)
      const buttons = screen.getAllByRole('button')
      // Third and fourth buttons (next page, last page) should be disabled
      expect(buttons[2]).toBeDisabled()
      expect(buttons[3]).toBeDisabled()
    })

    it('should enable next buttons when not on last page', () => {
      render(<ChipsPagination {...defaultProps} page={3} />)
      const buttons = screen.getAllByRole('button')
      expect(buttons[2]).not.toBeDisabled()
      expect(buttons[3]).not.toBeDisabled()
    })
  })

  describe('page navigation', () => {
    it('should call onPageChange with 1 when first page button is clicked', () => {
      const onPageChange = vi.fn()
      render(<ChipsPagination {...defaultProps} page={3} onPageChange={onPageChange} />)

      const buttons = screen.getAllByRole('button')
      fireEvent.click(buttons[0]!) // First page button

      expect(onPageChange).toHaveBeenCalledWith(1)
    })

    it('should call onPageChange with previous page when prev button is clicked', () => {
      const onPageChange = vi.fn()
      render(<ChipsPagination {...defaultProps} page={3} onPageChange={onPageChange} />)

      const buttons = screen.getAllByRole('button')
      fireEvent.click(buttons[1]!) // Previous button

      expect(onPageChange).toHaveBeenCalledWith(2)
    })

    it('should call onPageChange with next page when next button is clicked', () => {
      const onPageChange = vi.fn()
      render(<ChipsPagination {...defaultProps} page={3} onPageChange={onPageChange} />)

      const buttons = screen.getAllByRole('button')
      fireEvent.click(buttons[2]!) // Next button

      expect(onPageChange).toHaveBeenCalledWith(4)
    })

    it('should call onPageChange with last page when last page button is clicked', () => {
      const onPageChange = vi.fn()
      render(<ChipsPagination {...defaultProps} page={3} onPageChange={onPageChange} />)

      const buttons = screen.getAllByRole('button')
      fireEvent.click(buttons[3]!) // Last page button

      expect(onPageChange).toHaveBeenCalledWith(5)
    })
  })

  describe('page size', () => {
    it('should display current page size', () => {
      render(<ChipsPagination {...defaultProps} pageSize={20} />)
      expect(screen.getByText('20')).toBeInTheDocument()
    })

    it('should have page size options', () => {
      render(<ChipsPagination {...defaultProps} />)
      expect(screen.getByText('Exibindo')).toBeInTheDocument()
    })
  })

  describe('calculations', () => {
    it('should calculate total pages correctly', () => {
      render(<ChipsPagination {...defaultProps} total={95} pageSize={20} />)
      expect(screen.getByText('Pagina 1 de 5')).toBeInTheDocument()
    })

    it('should handle partial last page', () => {
      render(<ChipsPagination {...defaultProps} page={5} total={95} pageSize={20} />)
      expect(screen.getByText('81-95 de 95')).toBeInTheDocument()
    })
  })
})
