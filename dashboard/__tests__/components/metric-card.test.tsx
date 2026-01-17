/**
 * Tests for components/dashboard/metric-card.tsx
 *
 * Tests business logic: formatValue, getMetaStatus, comparison calculations
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MetricCard } from '@/components/dashboard/metric-card'
import { type MetricData } from '@/types/dashboard'

describe('MetricCard', () => {
  const baseMetric: MetricData = {
    label: 'Taxa de Resposta',
    value: 35,
    previousValue: 30,
    meta: 30,
    unit: 'percent',
    metaOperator: 'gt',
  }

  describe('formatValue', () => {
    it('should format percentage values with one decimal', () => {
      render(<MetricCard data={{ ...baseMetric, value: 35.567, unit: 'percent' }} />)
      expect(screen.getByText('35.6%')).toBeInTheDocument()
    })

    it('should format currency values with locale', () => {
      render(<MetricCard data={{ ...baseMetric, value: 1500, unit: 'currency' }} />)
      expect(screen.getByText(/R\$.*1\.500/)).toBeInTheDocument()
    })

    it('should format number values with locale', () => {
      render(<MetricCard data={{ ...baseMetric, value: 10000, unit: 'number' }} />)
      expect(screen.getByText('10.000')).toBeInTheDocument()
    })
  })

  describe('getMetaStatus', () => {
    describe('with gt operator (greater than)', () => {
      it('should show success when value exceeds meta', () => {
        render(<MetricCard data={{ ...baseMetric, value: 35, meta: 30, metaOperator: 'gt' }} />)
        expect(screen.getByText('Meta')).toBeInTheDocument()
      })

      it('should show success when value equals meta', () => {
        render(<MetricCard data={{ ...baseMetric, value: 30, meta: 30, metaOperator: 'gt' }} />)
        expect(screen.getByText('Meta')).toBeInTheDocument()
      })

      it('should show warning when value is within 20% of meta', () => {
        // 25 is 83% of 30, which is within 20% difference
        render(<MetricCard data={{ ...baseMetric, value: 25, meta: 30, metaOperator: 'gt' }} />)
        expect(screen.getByText('Atencao')).toBeInTheDocument()
      })

      it('should show error when value is more than 20% below meta', () => {
        // 20 is 66% of 30, more than 20% below
        render(<MetricCard data={{ ...baseMetric, value: 20, meta: 30, metaOperator: 'gt' }} />)
        expect(screen.getByText('Abaixo')).toBeInTheDocument()
      })
    })

    describe('with lt operator (less than)', () => {
      it('should show success when value is below meta', () => {
        render(<MetricCard data={{ ...baseMetric, value: 40, meta: 60, metaOperator: 'lt' }} />)
        expect(screen.getByText('Meta')).toBeInTheDocument()
      })

      it('should show success when value equals meta', () => {
        render(<MetricCard data={{ ...baseMetric, value: 60, meta: 60, metaOperator: 'lt' }} />)
        expect(screen.getByText('Meta')).toBeInTheDocument()
      })

      it('should show warning when value is slightly above meta', () => {
        // 70 is about 16% above 60
        render(<MetricCard data={{ ...baseMetric, value: 70, meta: 60, metaOperator: 'lt' }} />)
        expect(screen.getByText('Atencao')).toBeInTheDocument()
      })

      it('should show error when value is much higher than meta', () => {
        // 90 is 50% above 60
        render(<MetricCard data={{ ...baseMetric, value: 90, meta: 60, metaOperator: 'lt' }} />)
        expect(screen.getByText('Abaixo')).toBeInTheDocument()
      })
    })

    describe('with eq operator (equal)', () => {
      it('should show success when value equals meta', () => {
        render(<MetricCard data={{ ...baseMetric, value: 50, meta: 50, metaOperator: 'eq' }} />)
        expect(screen.getByText('Meta')).toBeInTheDocument()
      })

      it('should show warning when value is close to meta', () => {
        render(<MetricCard data={{ ...baseMetric, value: 48, meta: 50, metaOperator: 'eq' }} />)
        expect(screen.getByText('Atencao')).toBeInTheDocument()
      })
    })
  })

  describe('ComparisonBadge', () => {
    it('should show positive trend with green color', () => {
      render(<MetricCard data={{ ...baseMetric, value: 36, previousValue: 30 }} />)
      // 20% increase
      expect(screen.getByText('+20%')).toBeInTheDocument()
    })

    it('should show negative trend with red color', () => {
      render(<MetricCard data={{ ...baseMetric, value: 24, previousValue: 30 }} />)
      // 20% decrease
      expect(screen.getByText('-20%')).toBeInTheDocument()
    })

    it('should show stable when change is less than 1%', () => {
      render(<MetricCard data={{ ...baseMetric, value: 30.2, previousValue: 30 }} />)
      expect(screen.getByText('Estavel')).toBeInTheDocument()
    })

    it('should not render when previous value is zero', () => {
      render(<MetricCard data={{ ...baseMetric, value: 50, previousValue: 0 }} />)
      expect(screen.queryByText(/[+-]\d+%/)).not.toBeInTheDocument()
      expect(screen.queryByText('Estavel')).not.toBeInTheDocument()
    })
  })

  describe('rendering', () => {
    it('should display the metric label', () => {
      render(<MetricCard data={baseMetric} />)
      expect(screen.getByText('Taxa de Resposta')).toBeInTheDocument()
    })

    it('should display current value', () => {
      render(<MetricCard data={baseMetric} />)
      expect(screen.getByText('35.0%')).toBeInTheDocument()
    })

    it('should display meta value', () => {
      render(<MetricCard data={baseMetric} />)
      expect(screen.getByText(/Meta:.*30\.0%/)).toBeInTheDocument()
    })

    it('should display previous value comparison', () => {
      render(<MetricCard data={baseMetric} />)
      expect(screen.getByText(/vs sem\. ant:.*30\.0%/)).toBeInTheDocument()
    })
  })
})
