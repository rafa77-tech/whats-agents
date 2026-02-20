/**
 * Tests for components/chips/pool-metric-card.tsx
 *
 * Tests the PoolMetricCard component rendering and status colors.
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { PoolMetricCard } from '@/components/chips/pool-metric-card'
import { Cpu } from 'lucide-react'

describe('PoolMetricCard', () => {
  const defaultProps = {
    title: 'Total de Chips',
    value: 100,
    subtitle: '50 ativos',
    icon: <Cpu className="h-6 w-6" />,
    status: 'neutral' as const,
  }

  describe('rendering', () => {
    it('should display the title', () => {
      render(<PoolMetricCard {...defaultProps} />)
      expect(screen.getByText('Total de Chips')).toBeInTheDocument()
    })

    it('should display numeric value', () => {
      render(<PoolMetricCard {...defaultProps} value={100} />)
      expect(screen.getByText('100')).toBeInTheDocument()
    })

    it('should display string value', () => {
      render(<PoolMetricCard {...defaultProps} value="75.5" />)
      expect(screen.getByText('75.5')).toBeInTheDocument()
    })

    it('should display the subtitle', () => {
      render(<PoolMetricCard {...defaultProps} />)
      expect(screen.getByText('50 ativos')).toBeInTheDocument()
    })

    it('should render the icon', () => {
      render(<PoolMetricCard {...defaultProps} />)
      // Icon should be present in the DOM
      const card = screen.getByText('Total de Chips').closest('div')
      expect(card).toBeInTheDocument()
    })

    it('should not render subtitle when not provided', () => {
      const { subtitle: _subtitle, ...propsWithoutSubtitle } = defaultProps
      render(<PoolMetricCard {...propsWithoutSubtitle} />)
      expect(screen.queryByText('50 ativos')).not.toBeInTheDocument()
    })
  })

  describe('status colors', () => {
    it('should apply success status styling', () => {
      const { container } = render(<PoolMetricCard {...defaultProps} status="success" />)
      // Success status should have green left border
      expect(container.querySelector('.border-l-status-success-solid')).toBeInTheDocument()
    })

    it('should apply warning status styling', () => {
      const { container } = render(<PoolMetricCard {...defaultProps} status="warning" />)
      expect(container.querySelector('.border-l-status-warning-solid')).toBeInTheDocument()
    })

    it('should apply danger status styling', () => {
      const { container } = render(<PoolMetricCard {...defaultProps} status="danger" />)
      expect(container.querySelector('.border-l-status-error-solid')).toBeInTheDocument()
    })

    it('should apply neutral status styling', () => {
      const { container } = render(<PoolMetricCard {...defaultProps} status="neutral" />)
      expect(container.querySelector('.border-l-border')).toBeInTheDocument()
    })

    it('should default to neutral status when not specified', () => {
      const { status: _status, ...propsWithoutStatus } = defaultProps
      const { container } = render(<PoolMetricCard {...propsWithoutStatus} />)
      expect(container.querySelector('.border-l-border')).toBeInTheDocument()
    })
  })

  describe('trend indicator', () => {
    it('should show positive trend with plus sign', () => {
      render(<PoolMetricCard {...defaultProps} trend={{ direction: 'up', value: 15 }} />)
      expect(screen.getByText('+15.0%')).toBeInTheDocument()
    })

    it('should show negative trend with minus sign', () => {
      render(<PoolMetricCard {...defaultProps} trend={{ direction: 'down', value: 10 }} />)
      expect(screen.getByText('-10.0%')).toBeInTheDocument()
    })

    it('should show stable trend without sign', () => {
      render(<PoolMetricCard {...defaultProps} trend={{ direction: 'stable', value: 0 }} />)
      expect(screen.getByText('0.0%')).toBeInTheDocument()
    })

    it('should show trend label when provided', () => {
      render(
        <PoolMetricCard
          {...defaultProps}
          trend={{ direction: 'up', value: 15, label: 'vs ontem' }}
        />
      )
      expect(screen.getByText('vs ontem')).toBeInTheDocument()
    })

    it('should apply green color for up trend', () => {
      render(<PoolMetricCard {...defaultProps} trend={{ direction: 'up', value: 15 }} />)
      const trendElement = screen.getByText('+15.0%').closest('div')
      expect(trendElement).toHaveClass('text-status-success-foreground')
    })

    it('should apply red color for down trend', () => {
      render(<PoolMetricCard {...defaultProps} trend={{ direction: 'down', value: 10 }} />)
      const trendElement = screen.getByText('-10.0%').closest('div')
      expect(trendElement).toHaveClass('text-status-error-foreground')
    })

    it('should apply gray color for stable trend', () => {
      render(<PoolMetricCard {...defaultProps} trend={{ direction: 'stable', value: 0 }} />)
      const trendElement = screen.getByText('0.0%').closest('div')
      expect(trendElement).toHaveClass('text-muted-foreground')
    })
  })
})
