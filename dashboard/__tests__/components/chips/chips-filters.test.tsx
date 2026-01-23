/**
 * Tests for components/chips/chips-filters.tsx
 *
 * Tests the ChipsFilters component filtering and search functionality.
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ChipsFilters } from '@/components/chips/chips-filters'
import { ChipsListParams } from '@/types/chips'

describe('ChipsFilters', () => {
  const defaultProps = {
    filters: {} as Partial<ChipsListParams>,
    onFiltersChange: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('search functionality', () => {
    it('should render search input', () => {
      render(<ChipsFilters {...defaultProps} />)
      expect(screen.getByPlaceholderText('Buscar por telefone...')).toBeInTheDocument()
    })

    it('should update search value on input change', () => {
      render(<ChipsFilters {...defaultProps} />)
      const input = screen.getByPlaceholderText('Buscar por telefone...')
      fireEvent.change(input, { target: { value: '11999' } })
      expect(input).toHaveValue('11999')
    })

    it('should call onFiltersChange when search button is clicked', () => {
      const onFiltersChange = vi.fn()
      render(<ChipsFilters {...defaultProps} onFiltersChange={onFiltersChange} />)

      const input = screen.getByPlaceholderText('Buscar por telefone...')
      fireEvent.change(input, { target: { value: '11999' } })

      const searchButton = screen.getByText('Buscar')
      fireEvent.click(searchButton)

      expect(onFiltersChange).toHaveBeenCalledWith({ search: '11999' })
    })

    it('should call onFiltersChange on Enter key', () => {
      const onFiltersChange = vi.fn()
      render(<ChipsFilters {...defaultProps} onFiltersChange={onFiltersChange} />)

      const input = screen.getByPlaceholderText('Buscar por telefone...')
      fireEvent.change(input, { target: { value: '11999' } })
      fireEvent.keyDown(input, { key: 'Enter' })

      expect(onFiltersChange).toHaveBeenCalledWith({ search: '11999' })
    })
  })

  describe('filter selects', () => {
    it('should render status filter', () => {
      render(<ChipsFilters {...defaultProps} />)
      expect(screen.getByText('Todos os status')).toBeInTheDocument()
    })

    it('should render trust level filter', () => {
      render(<ChipsFilters {...defaultProps} />)
      expect(screen.getByText('Todos os niveis')).toBeInTheDocument()
    })

    it('should render alert filter', () => {
      render(<ChipsFilters {...defaultProps} />)
      expect(screen.getByText('Todos')).toBeInTheDocument()
    })

    it('should render sort options', () => {
      render(<ChipsFilters {...defaultProps} />)
      expect(screen.getByText('Trust Score')).toBeInTheDocument()
    })
  })

  describe('clear filters', () => {
    it('should not show clear button when no filters are active', () => {
      render(<ChipsFilters {...defaultProps} />)
      expect(screen.queryByText(/Limpar/)).not.toBeInTheDocument()
    })

    it('should show clear button when filters are active', () => {
      render(<ChipsFilters {...defaultProps} filters={{ status: 'active' }} />)
      expect(screen.getByText('Limpar (1)')).toBeInTheDocument()
    })

    it('should call onFiltersChange with empty object when clear is clicked', () => {
      const onFiltersChange = vi.fn()
      render(
        <ChipsFilters
          filters={{ status: 'active', search: 'test' }}
          onFiltersChange={onFiltersChange}
        />
      )

      fireEvent.click(screen.getByText('Limpar (2)'))
      expect(onFiltersChange).toHaveBeenCalledWith({})
    })
  })

  describe('active filter count', () => {
    it('should count status filter', () => {
      render(<ChipsFilters {...defaultProps} filters={{ status: 'active' }} />)
      expect(screen.getByText('Limpar (1)')).toBeInTheDocument()
    })

    it('should count trust level filter', () => {
      render(<ChipsFilters {...defaultProps} filters={{ trustLevel: 'verde' }} />)
      expect(screen.getByText('Limpar (1)')).toBeInTheDocument()
    })

    it('should count hasAlert filter', () => {
      render(<ChipsFilters {...defaultProps} filters={{ hasAlert: true }} />)
      expect(screen.getByText('Limpar (1)')).toBeInTheDocument()
    })

    it('should count search filter', () => {
      render(<ChipsFilters {...defaultProps} filters={{ search: '11999' }} />)
      expect(screen.getByText('Limpar (1)')).toBeInTheDocument()
    })

    it('should count multiple filters', () => {
      render(
        <ChipsFilters
          {...defaultProps}
          filters={{ status: 'active', trustLevel: 'verde', hasAlert: true, search: '11999' }}
        />
      )
      expect(screen.getByText('Limpar (4)')).toBeInTheDocument()
    })
  })
})
