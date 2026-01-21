/**
 * Tests for dashboard header and quality metric card components
 * - components/dashboard/dashboard-header.tsx
 * - components/dashboard/quality-metric-card.tsx
 * - components/dashboard/quality-metrics-section.tsx
 * - components/dashboard/trends-section.tsx
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { DashboardHeader } from '@/components/dashboard/dashboard-header'
import { QualityMetricCard } from '@/components/dashboard/quality-metric-card'
import { type QualityMetricData } from '@/types/dashboard'

describe('DashboardHeader', () => {
  const defaultProps = {
    juliaStatus: 'online' as const,
    lastHeartbeat: new Date(),
    uptime30d: 99.5,
    selectedPeriod: '7d' as const,
    onPeriodChange: vi.fn(),
    onExport: vi.fn(),
  }

  it('should display Julia Online when status is online', () => {
    render(<DashboardHeader {...defaultProps} juliaStatus="online" />)
    expect(screen.getByText('Julia Online')).toBeInTheDocument()
  })

  it('should display Julia Offline when status is offline', () => {
    render(<DashboardHeader {...defaultProps} juliaStatus="offline" />)
    expect(screen.getByText('Julia Offline')).toBeInTheDocument()
  })

  it('should display Julia Degraded when status is degraded', () => {
    render(<DashboardHeader {...defaultProps} juliaStatus="degraded" />)
    expect(screen.getByText('Julia Degraded')).toBeInTheDocument()
  })

  it('should show green indicator for online status', () => {
    render(<DashboardHeader {...defaultProps} juliaStatus="online" />)
    const indicator = document.querySelector('.bg-green-500')
    expect(indicator).toBeInTheDocument()
  })

  it('should show red indicator for offline status', () => {
    render(<DashboardHeader {...defaultProps} juliaStatus="offline" />)
    const indicator = document.querySelector('.bg-red-500')
    expect(indicator).toBeInTheDocument()
  })

  it('should show yellow indicator for degraded status', () => {
    render(<DashboardHeader {...defaultProps} juliaStatus="degraded" />)
    const indicator = document.querySelector('.bg-yellow-500')
    expect(indicator).toBeInTheDocument()
  })

  it('should display uptime percentage', () => {
    render(<DashboardHeader {...defaultProps} uptime30d={99.5} />)
    expect(screen.getByText('99.5%')).toBeInTheDocument()
  })

  it('should show green uptime color when >= 99%', () => {
    render(<DashboardHeader {...defaultProps} uptime30d={99.5} />)
    expect(screen.getByText('99.5%')).toHaveClass('text-green-600')
  })

  it('should show yellow uptime color when between 95% and 99%', () => {
    render(<DashboardHeader {...defaultProps} uptime30d={97.0} />)
    expect(screen.getByText('97.0%')).toHaveClass('text-yellow-600')
  })

  it('should show red uptime color when < 95%', () => {
    render(<DashboardHeader {...defaultProps} uptime30d={90.0} />)
    expect(screen.getByText('90.0%')).toHaveClass('text-red-600')
  })

  it('should render period selector', () => {
    render(<DashboardHeader {...defaultProps} />)
    expect(screen.getByText('7 dias')).toBeInTheDocument()
  })

  it('should render export button', () => {
    render(<DashboardHeader {...defaultProps} />)
    expect(screen.getByText('Exportar')).toBeInTheDocument()
  })

  it('should not render heartbeat when null', () => {
    render(<DashboardHeader {...defaultProps} lastHeartbeat={null} />)
    expect(screen.queryByText(/Ultimo:/)).not.toBeInTheDocument()
  })

  it('should display relative heartbeat time', () => {
    render(<DashboardHeader {...defaultProps} />)
    expect(screen.getByText(/Ultimo:/)).toBeInTheDocument()
  })
})

describe('QualityMetricCard', () => {
  const baseMetric: QualityMetricData = {
    label: 'Taxa de Bloqueio',
    value: 2,
    unit: 'percent',
    threshold: { good: 3, warning: 5 },
    operator: 'lt',
    previousValue: 3,
    tooltip: 'Percentual de mensagens bloqueadas',
  }

  it('should render metric label', () => {
    render(<QualityMetricCard data={baseMetric} />)
    expect(screen.getByText('Taxa de Bloqueio')).toBeInTheDocument()
  })

  it('should format percentage values correctly', () => {
    render(<QualityMetricCard data={baseMetric} />)
    expect(screen.getByText('2.0%')).toBeInTheDocument()
  })

  it('should format seconds values correctly', () => {
    const secondsMetric: QualityMetricData = {
      ...baseMetric,
      value: 15,
      unit: 'seconds',
      threshold: { good: 20, warning: 30 },
    }
    render(<QualityMetricCard data={secondsMetric} />)
    expect(screen.getByText('15s')).toBeInTheDocument()
  })

  it('should show Otimo status when value is good (lt operator)', () => {
    const goodMetric: QualityMetricData = {
      ...baseMetric,
      value: 2, // less than threshold.good of 3
      operator: 'lt',
    }
    render(<QualityMetricCard data={goodMetric} />)
    expect(screen.getByText('Otimo')).toBeInTheDocument()
  })

  it('should show Atencao status when value is warning level (lt operator)', () => {
    const warningMetric: QualityMetricData = {
      ...baseMetric,
      value: 4, // between good (3) and warning (5)
      operator: 'lt',
    }
    render(<QualityMetricCard data={warningMetric} />)
    expect(screen.getByText('Atencao')).toBeInTheDocument()
  })

  it('should show Critico status when value exceeds warning (lt operator)', () => {
    const criticalMetric: QualityMetricData = {
      ...baseMetric,
      value: 6, // above warning threshold of 5
      operator: 'lt',
    }
    render(<QualityMetricCard data={criticalMetric} />)
    expect(screen.getByText('Critico')).toBeInTheDocument()
  })

  it('should show Otimo status when value is good (gt operator)', () => {
    const goodMetric: QualityMetricData = {
      ...baseMetric,
      value: 95,
      threshold: { good: 90, warning: 80 },
      operator: 'gt',
    }
    render(<QualityMetricCard data={goodMetric} />)
    expect(screen.getByText('Otimo')).toBeInTheDocument()
  })

  it('should display meta with correct operator', () => {
    render(<QualityMetricCard data={baseMetric} />)
    expect(screen.getByText(/Meta: < 3.0%/)).toBeInTheDocument()
  })

  it('should display gt operator in meta', () => {
    const gtMetric: QualityMetricData = {
      ...baseMetric,
      operator: 'gt',
    }
    render(<QualityMetricCard data={gtMetric} />)
    expect(screen.getByText(/Meta: > 3.0%/)).toBeInTheDocument()
  })

  it('should show previous value comparison', () => {
    render(<QualityMetricCard data={baseMetric} />)
    expect(screen.getByText(/vs sem\. ant: 3\.0%/)).toBeInTheDocument()
  })

  it('should show improvement trend when value decreased (lt operator)', () => {
    const improvedMetric: QualityMetricData = {
      ...baseMetric,
      value: 2,
      previousValue: 3,
      operator: 'lt',
    }
    render(<QualityMetricCard data={improvedMetric} />)
    // Trend should be green (improvement) since lower is better with lt operator
    const trend = screen.getByText(/-33%/)
    expect(trend).toHaveClass('text-green-600')
  })

  it('should not show trend when diff is less than 1%', () => {
    const stableMetric: QualityMetricData = {
      ...baseMetric,
      value: 3.0,
      previousValue: 3.01,
    }
    render(<QualityMetricCard data={stableMetric} />)
    expect(screen.queryByText(/[+-]\d+%/)).not.toBeInTheDocument()
  })

  it('should render tooltip when provided', () => {
    render(<QualityMetricCard data={baseMetric} />)
    // Info icon should be present
    const infoIcon = document.querySelector('.lucide-info')
    expect(infoIcon).toBeInTheDocument()
  })

  it('should not render tooltip icon when not provided', () => {
    const noTooltipMetric: QualityMetricData = {
      label: 'Taxa sem Tooltip',
      value: 2,
      unit: 'percent',
      threshold: { good: 3, warning: 5 },
      operator: 'lt',
      previousValue: 3,
      // No tooltip field
    }
    render(<QualityMetricCard data={noTooltipMetric} />)
    // Info icon should not be present
    const infoIcon = document.querySelector('.lucide-info')
    expect(infoIcon).not.toBeInTheDocument()
  })
})
