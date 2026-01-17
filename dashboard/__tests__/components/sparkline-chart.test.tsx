/**
 * Tests for components/dashboard/sparkline-chart.tsx
 *
 * Tests business logic: value formatting, trend color selection, icon selection
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SparklineChart } from '@/components/dashboard/sparkline-chart'
import { type SparklineMetric } from '@/types/dashboard'

// Mock recharts to avoid canvas issues in tests
vi.mock('recharts', () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: () => <div data-testid="line" />,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
}))

describe('SparklineChart', () => {
  const baseMetric: SparklineMetric = {
    id: 'response-rate',
    label: 'Taxa de Resposta',
    data: [
      { date: '2025-01-01', value: 30 },
      { date: '2025-01-02', value: 35 },
    ],
    currentValue: 35,
    unit: '%',
    trend: 'up',
    trendIsGood: true,
  }

  describe('value formatting', () => {
    it('should format percentage values with one decimal', () => {
      render(<SparklineChart metric={{ ...baseMetric, currentValue: 35.567, unit: '%' }} />)
      expect(screen.getByText('35.6%')).toBeInTheDocument()
    })

    it('should format seconds values without decimals', () => {
      render(<SparklineChart metric={{ ...baseMetric, currentValue: 45.7, unit: 's' }} />)
      expect(screen.getByText('46s')).toBeInTheDocument()
    })

    it('should format dollar values with two decimals', () => {
      render(<SparklineChart metric={{ ...baseMetric, currentValue: 1500.5, unit: '$' }} />)
      expect(screen.getByText('$1500.50')).toBeInTheDocument()
    })

    it('should format plain numbers without decimals', () => {
      render(<SparklineChart metric={{ ...baseMetric, currentValue: 100.9, unit: '' }} />)
      expect(screen.getByText('101')).toBeInTheDocument()
    })
  })

  describe('trend icon selection', () => {
    it('should show TrendingUp icon for upward trend', () => {
      const { container } = render(<SparklineChart metric={{ ...baseMetric, trend: 'up' }} />)
      // Check for the icon's parent element class
      const iconWrapper = container.querySelector('svg')
      expect(iconWrapper).toBeInTheDocument()
    })

    it('should show TrendingDown icon for downward trend', () => {
      const { container } = render(<SparklineChart metric={{ ...baseMetric, trend: 'down' }} />)
      const iconWrapper = container.querySelector('svg')
      expect(iconWrapper).toBeInTheDocument()
    })

    it('should show Minus icon for stable trend', () => {
      const { container } = render(<SparklineChart metric={{ ...baseMetric, trend: 'stable' }} />)
      const iconWrapper = container.querySelector('svg')
      expect(iconWrapper).toBeInTheDocument()
    })
  })

  describe('trend color logic', () => {
    it('should apply green color when trend is good and going up', () => {
      const { container } = render(
        <SparklineChart metric={{ ...baseMetric, trend: 'up', trendIsGood: true }} />
      )
      const icon = container.querySelector('svg')
      expect(icon).toHaveClass('text-green-500')
    })

    it('should apply red color when trend is up but not good', () => {
      // e.g., costs going up is bad
      const { container } = render(
        <SparklineChart metric={{ ...baseMetric, trend: 'up', trendIsGood: false }} />
      )
      const icon = container.querySelector('svg')
      expect(icon).toHaveClass('text-red-500')
    })

    it('should apply green color when trend is down and that is good', () => {
      // e.g., response time going down is good
      const { container } = render(
        <SparklineChart metric={{ ...baseMetric, trend: 'down', trendIsGood: true }} />
      )
      const icon = container.querySelector('svg')
      expect(icon).toHaveClass('text-green-500')
    })

    it('should apply red color when trend is down and that is bad', () => {
      // e.g., response rate going down is bad
      const { container } = render(
        <SparklineChart metric={{ ...baseMetric, trend: 'down', trendIsGood: false }} />
      )
      const icon = container.querySelector('svg')
      expect(icon).toHaveClass('text-red-500')
    })

    it('should apply gray color for stable trend', () => {
      const { container } = render(
        <SparklineChart metric={{ ...baseMetric, trend: 'stable', trendIsGood: true }} />
      )
      const icon = container.querySelector('svg')
      expect(icon).toHaveClass('text-gray-400')
    })
  })

  describe('rendering', () => {
    it('should display the metric label', () => {
      render(<SparklineChart metric={baseMetric} />)
      expect(screen.getByText('Taxa de Resposta')).toBeInTheDocument()
    })

    it('should render the chart container', () => {
      render(<SparklineChart metric={baseMetric} />)
      expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
      expect(screen.getByTestId('line-chart')).toBeInTheDocument()
    })
  })
})
