import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AlertsPanel } from '@/components/health/alerts-panel'

describe('AlertsPanel', () => {
  const mockAlerts = [
    {
      id: '1',
      tipo: 'job_stale',
      severity: 'critical' as const,
      message: 'Job X stale',
      source: 'scheduler',
    },
    {
      id: '2',
      tipo: 'job_error',
      severity: 'warn' as const,
      message: 'Job Y errors',
      source: 'scheduler',
    },
    {
      id: '3',
      tipo: 'info_test',
      severity: 'info' as const,
      message: 'Info message',
      source: 'system',
    },
  ]

  describe('Header', () => {
    it('renders alert count in header', () => {
      render(<AlertsPanel alerts={mockAlerts} />)
      expect(screen.getByText('Alertas Ativos: 3')).toBeInTheDocument()
    })

    it('shows critical count badge', () => {
      render(<AlertsPanel alerts={mockAlerts} />)
      expect(screen.getByText('1 critico')).toBeInTheDocument()
    })

    it('shows warn count badge', () => {
      render(<AlertsPanel alerts={mockAlerts} />)
      expect(screen.getByText('1 alerta')).toBeInTheDocument()
    })

    it('shows info count badge', () => {
      render(<AlertsPanel alerts={mockAlerts} />)
      expect(screen.getByText('1 info')).toBeInTheDocument()
    })

    it('pluralizes correctly for multiple', () => {
      const multiCritical = [
        ...mockAlerts,
        {
          id: '4',
          tipo: 'test',
          severity: 'critical' as const,
          message: 'Another critical',
          source: 'test',
        },
      ]
      render(<AlertsPanel alerts={multiCritical} />)
      expect(screen.getByText('2 criticos')).toBeInTheDocument()
    })
  })

  describe('Alert Rendering', () => {
    it('displays alert messages', () => {
      render(<AlertsPanel alerts={mockAlerts} />)
      expect(screen.getByText('Job X stale')).toBeInTheDocument()
      expect(screen.getByText('Job Y errors')).toBeInTheDocument()
      expect(screen.getByText('Info message')).toBeInTheDocument()
    })

    it('displays alert sources', () => {
      render(<AlertsPanel alerts={mockAlerts} />)
      expect(screen.getAllByText('Fonte: scheduler')).toHaveLength(2)
      expect(screen.getByText('Fonte: system')).toBeInTheDocument()
    })

    it('displays severity badges', () => {
      render(<AlertsPanel alerts={mockAlerts} />)
      expect(screen.getByText('Critico')).toBeInTheDocument()
      expect(screen.getByText('Alerta')).toBeInTheDocument()
      expect(screen.getByText('Info')).toBeInTheDocument()
    })
  })

  describe('Sorting', () => {
    it('displays critical alerts first', () => {
      const mixedAlerts = [
        { id: '1', tipo: 'test', severity: 'info' as const, message: 'Info 1', source: 'test' },
        {
          id: '2',
          tipo: 'test',
          severity: 'critical' as const,
          message: 'Critical 1',
          source: 'test',
        },
        { id: '3', tipo: 'test', severity: 'warn' as const, message: 'Warn 1', source: 'test' },
      ]

      const { container } = render(<AlertsPanel alerts={mixedAlerts} />)
      const alertItems = container.querySelectorAll('.rounded-lg.border.p-3')

      // Component uses bg-status-{severity}/20 for alert backgrounds
      // First alert should be critical (error background)
      expect(alertItems[0]).toHaveClass('bg-status-error/20')
      // Second should be warn (warning)
      expect(alertItems[1]).toHaveClass('bg-status-warning/20')
      // Third should be info (info)
      expect(alertItems[2]).toHaveClass('bg-status-info/20')
    })
  })

  describe('Alert Limit', () => {
    it('shows only first 5 alerts', () => {
      const manyAlerts = Array.from({ length: 7 }, (_, i) => ({
        id: `${i}`,
        tipo: 'test',
        severity: 'info' as const,
        message: `Alert ${i}`,
        source: 'test',
      }))

      render(<AlertsPanel alerts={manyAlerts} />)

      // Should show "Alert 0" through "Alert 4"
      expect(screen.getByText('Alert 0')).toBeInTheDocument()
      expect(screen.getByText('Alert 4')).toBeInTheDocument()
      // Should not show "Alert 5" or "Alert 6"
      expect(screen.queryByText('Alert 5')).not.toBeInTheDocument()
      expect(screen.queryByText('Alert 6')).not.toBeInTheDocument()
    })

    it('shows additional alerts count message', () => {
      const manyAlerts = Array.from({ length: 7 }, (_, i) => ({
        id: `${i}`,
        tipo: 'test',
        severity: 'info' as const,
        message: `Alert ${i}`,
        source: 'test',
      }))

      render(<AlertsPanel alerts={manyAlerts} />)
      // Component renders "+ 2 alertas adicional" on one line and "is" on next
      expect(screen.getByText(/\+ 2 alertas/)).toBeInTheDocument()
    })

    it('shows singular form for 1 additional alert', () => {
      const alerts = Array.from({ length: 6 }, (_, i) => ({
        id: `${i}`,
        tipo: 'test',
        severity: 'info' as const,
        message: `Alert ${i}`,
        source: 'test',
      }))

      render(<AlertsPanel alerts={alerts} />)
      // Component renders "+ 1 alerta adicional"
      expect(screen.getByText(/\+ 1 alerta adicional/)).toBeInTheDocument()
    })
  })

  describe('Styling', () => {
    it('applies error border when critical alerts exist', () => {
      const { container } = render(<AlertsPanel alerts={mockAlerts} />)
      const card = container.querySelector('.border-status-error-border')
      expect(card).toBeInTheDocument()
    })

    it('does not apply error border when no critical alerts', () => {
      const nonCriticalAlerts = [
        { id: '1', tipo: 'test', severity: 'warn' as const, message: 'Warn', source: 'test' },
      ]
      const { container } = render(<AlertsPanel alerts={nonCriticalAlerts} />)
      const card = container.querySelector('.border-status-error-border')
      expect(card).not.toBeInTheDocument()
    })
  })

  describe('Links', () => {
    it('renders monitor link for each alert', () => {
      render(<AlertsPanel alerts={mockAlerts} />)
      const links = screen.getAllByRole('link')
      expect(links.length).toBeGreaterThanOrEqual(3)
      links.forEach((link) => {
        expect(link).toHaveAttribute('href', '/monitor')
      })
    })
  })
})
