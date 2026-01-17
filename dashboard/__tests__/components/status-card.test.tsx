/**
 * Tests for components/dashboard/status-card.tsx
 *
 * Tests rendering and trend display logic
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { StatusCard } from '@/components/dashboard/status-card'
import { Activity } from 'lucide-react'

describe('StatusCard', () => {
  const defaultProps = {
    title: 'Mensagens Hoje',
    value: '1.234',
    icon: Activity,
  }

  describe('rendering', () => {
    it('should display the title', () => {
      render(<StatusCard {...defaultProps} />)
      expect(screen.getByText('Mensagens Hoje')).toBeInTheDocument()
    })

    it('should display the value', () => {
      render(<StatusCard {...defaultProps} />)
      expect(screen.getByText('1.234')).toBeInTheDocument()
    })

    it('should render the icon', () => {
      const { container } = render(<StatusCard {...defaultProps} />)
      const icon = container.querySelector('svg')
      expect(icon).toBeInTheDocument()
      expect(icon).toHaveClass('text-revoluna-400')
    })
  })

  describe('trend display', () => {
    it('should not show trend when not provided', () => {
      render(<StatusCard {...defaultProps} />)
      expect(screen.queryByText(/%/)).not.toBeInTheDocument()
    })

    it('should show positive trend with green color', () => {
      const { container } = render(
        <StatusCard {...defaultProps} trend={{ value: 15, positive: true }} />
      )
      expect(screen.getByText('15%')).toBeInTheDocument()
      const trendDiv = container.querySelector('.text-green-600')
      expect(trendDiv).toBeInTheDocument()
    })

    it('should show negative trend with red color', () => {
      const { container } = render(
        <StatusCard {...defaultProps} trend={{ value: 10, positive: false }} />
      )
      expect(screen.getByText('10%')).toBeInTheDocument()
      const trendDiv = container.querySelector('.text-red-600')
      expect(trendDiv).toBeInTheDocument()
    })

    it('should show TrendingUp icon for positive trend', () => {
      const { container } = render(
        <StatusCard {...defaultProps} trend={{ value: 15, positive: true }} />
      )
      // There should be 2 SVGs: the main icon and the trend icon
      const icons = container.querySelectorAll('svg')
      expect(icons.length).toBe(2)
    })

    it('should show TrendingDown icon for negative trend', () => {
      const { container } = render(
        <StatusCard {...defaultProps} trend={{ value: 10, positive: false }} />
      )
      const icons = container.querySelectorAll('svg')
      expect(icons.length).toBe(2)
    })
  })

  describe('edge cases', () => {
    it('should handle zero trend value', () => {
      render(<StatusCard {...defaultProps} trend={{ value: 0, positive: true }} />)
      expect(screen.getByText('0%')).toBeInTheDocument()
    })

    it('should handle large values', () => {
      render(<StatusCard {...defaultProps} value="1.000.000" />)
      expect(screen.getByText('1.000.000')).toBeInTheDocument()
    })

    it('should handle empty value', () => {
      render(<StatusCard {...defaultProps} value="" />)
      // Should still render without errors
      expect(screen.getByText('Mensagens Hoje')).toBeInTheDocument()
    })
  })
})
