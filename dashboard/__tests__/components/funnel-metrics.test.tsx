/**
 * Tests for funnel and metrics section components
 * - components/dashboard/conversion-funnel.tsx
 * - components/dashboard/metrics-section.tsx
 * - components/dashboard/quality-metrics-section.tsx
 * - components/dashboard/trends-section.tsx
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ConversionFunnel } from '@/components/dashboard/conversion-funnel'
import { MetricsSection } from '@/components/dashboard/metrics-section'
import { TrendsSection } from '@/components/dashboard/trends-section'
import { QualityMetricsSection } from '@/components/dashboard/quality-metrics-section'
import {
  type FunnelDataVisual,
  type MetricData,
  type TrendsData,
  type QualityMetricData,
} from '@/types/dashboard'

describe('ConversionFunnel', () => {
  const mockFunnelData: FunnelDataVisual = {
    stages: [
      { id: 'enviadas', label: 'Enviadas', count: 100, previousCount: 90, percentage: 100 },
      { id: 'entregues', label: 'Entregues', count: 95, previousCount: 85, percentage: 95 },
      { id: 'respostas', label: 'Respostas', count: 30, previousCount: 25, percentage: 30 },
      { id: 'interesse', label: 'Interesse', count: 15, previousCount: 12, percentage: 15 },
      { id: 'fechadas', label: 'Fechadas', count: 5, previousCount: 4, percentage: 5 },
    ],
    period: '7 dias',
  }

  it('should render card title', () => {
    const onStageClick = vi.fn()
    render(<ConversionFunnel data={mockFunnelData} onStageClick={onStageClick} />)
    expect(screen.getByText('Funil de Conversao')).toBeInTheDocument()
  })

  it('should display period', () => {
    const onStageClick = vi.fn()
    render(<ConversionFunnel data={mockFunnelData} onStageClick={onStageClick} />)
    expect(screen.getByText('Periodo: 7 dias')).toBeInTheDocument()
  })

  it('should render all funnel stages', () => {
    const onStageClick = vi.fn()
    render(<ConversionFunnel data={mockFunnelData} onStageClick={onStageClick} />)
    // Labels are rendered with colon, e.g., "Enviadas:"
    expect(screen.getByText('Enviadas:')).toBeInTheDocument()
    expect(screen.getByText('Entregues:')).toBeInTheDocument()
    expect(screen.getByText('Respostas:')).toBeInTheDocument()
    expect(screen.getByText('Interesse:')).toBeInTheDocument()
    expect(screen.getByText('Fechadas:')).toBeInTheDocument()
  })

  it('should call onStageClick when stage is clicked', () => {
    const onStageClick = vi.fn()
    render(<ConversionFunnel data={mockFunnelData} onStageClick={onStageClick} />)
    // The stage is a div with onClick, find it by label and click the parent
    const stageLabel = screen.getByText('Enviadas:')
    const clickableDiv = stageLabel.closest('.cursor-pointer')
    if (clickableDiv) {
      fireEvent.click(clickableDiv)
      expect(onStageClick).toHaveBeenCalledWith('enviadas')
    }
  })

  it('should handle empty stages', () => {
    const onStageClick = vi.fn()
    const emptyData: FunnelDataVisual = { stages: [], period: '7 dias' }
    render(<ConversionFunnel data={emptyData} onStageClick={onStageClick} />)
    expect(screen.getByText('Funil de Conversao')).toBeInTheDocument()
  })
})

describe('MetricsSection', () => {
  const mockMetrics: MetricData[] = [
    {
      label: 'Taxa de Resposta',
      value: 35,
      previousValue: 30,
      meta: 30,
      unit: 'percent',
      metaOperator: 'gt',
    },
    {
      label: 'Taxa de Conversao',
      value: 15,
      previousValue: 12,
      meta: 10,
      unit: 'percent',
      metaOperator: 'gt',
    },
    {
      label: 'Custo por Plantao',
      value: 50,
      previousValue: 55,
      meta: 60,
      unit: 'currency',
      metaOperator: 'lt',
    },
  ]

  it('should render all metric cards', () => {
    render(<MetricsSection metrics={mockMetrics} />)
    expect(screen.getByText('Taxa de Resposta')).toBeInTheDocument()
    expect(screen.getByText('Taxa de Conversao')).toBeInTheDocument()
    expect(screen.getByText('Custo por Plantao')).toBeInTheDocument()
  })

  it('should display metric values', () => {
    render(<MetricsSection metrics={mockMetrics} />)
    expect(screen.getByText('35.0%')).toBeInTheDocument()
    expect(screen.getByText('15.0%')).toBeInTheDocument()
  })

  it('should handle empty metrics array', () => {
    render(<MetricsSection metrics={[]} />)
    // Should render empty grid without crashing
    const grid = document.querySelector('.grid')
    expect(grid).toBeInTheDocument()
  })

  it('should render in a responsive grid', () => {
    render(<MetricsSection metrics={mockMetrics} />)
    const grid = document.querySelector('.grid')
    expect(grid).toHaveClass('md:grid-cols-3')
  })
})

describe('TrendsSection', () => {
  const mockTrendsData: TrendsData = {
    metrics: [
      {
        id: 'taxa_resposta',
        label: 'Taxa de Resposta',
        data: [
          { date: '2026-01-14', value: 30 },
          { date: '2026-01-15', value: 32 },
          { date: '2026-01-16', value: 35 },
        ],
        currentValue: 35,
        unit: '%',
        trend: 'up',
        trendIsGood: true,
      },
      {
        id: 'taxa_bloqueio',
        label: 'Taxa de Bloqueio',
        data: [
          { date: '2026-01-14', value: 5 },
          { date: '2026-01-15', value: 4 },
          { date: '2026-01-16', value: 3 },
        ],
        currentValue: 3,
        unit: '%',
        trend: 'down',
        trendIsGood: true,
      },
    ],
    period: '7 dias',
  }

  it('should render card title with period', () => {
    render(<TrendsSection data={mockTrendsData} />)
    expect(screen.getByText(/Tendencias/)).toBeInTheDocument()
    expect(screen.getByText(/7 dias/)).toBeInTheDocument()
  })

  it('should render all sparkline metrics', () => {
    render(<TrendsSection data={mockTrendsData} />)
    expect(screen.getByText('Taxa de Resposta')).toBeInTheDocument()
    expect(screen.getByText('Taxa de Bloqueio')).toBeInTheDocument()
  })

  it('should handle empty metrics array', () => {
    const emptyData: TrendsData = { metrics: [], period: '7 dias' }
    render(<TrendsSection data={emptyData} />)
    expect(screen.getByText(/Tendencias/)).toBeInTheDocument()
  })
})

describe('QualityMetricsSection', () => {
  const mockQualityMetrics: QualityMetricData[] = [
    {
      label: 'Tempo de Resposta',
      value: 15,
      unit: 'seconds',
      threshold: { good: 20, warning: 30 },
      operator: 'lt',
      previousValue: 18,
    },
    {
      label: 'Taxa de Bloqueio',
      value: 2,
      unit: 'percent',
      threshold: { good: 3, warning: 5 },
      operator: 'lt',
      previousValue: 3,
    },
  ]

  it('should render all quality metric cards', () => {
    render(<QualityMetricsSection metrics={mockQualityMetrics} />)
    expect(screen.getByText('Tempo de Resposta')).toBeInTheDocument()
    expect(screen.getByText('Taxa de Bloqueio')).toBeInTheDocument()
  })

  it('should display metric values', () => {
    render(<QualityMetricsSection metrics={mockQualityMetrics} />)
    expect(screen.getByText('15s')).toBeInTheDocument()
    expect(screen.getByText('2.0%')).toBeInTheDocument()
  })

  it('should handle empty metrics array', () => {
    render(<QualityMetricsSection metrics={[]} />)
    const grid = document.querySelector('.grid')
    expect(grid).toBeInTheDocument()
  })

  it('should render in a responsive grid', () => {
    render(<QualityMetricsSection metrics={mockQualityMetrics} />)
    const grid = document.querySelector('.grid')
    expect(grid).toHaveClass('md:grid-cols-3')
  })
})
