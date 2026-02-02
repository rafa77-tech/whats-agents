import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { KpiCard } from '@/components/integridade/kpi-card'
import { Activity, TrendingUp, Clock } from 'lucide-react'

describe('KpiCard', () => {
  describe('Rendering', () => {
    it('renders title', () => {
      render(<KpiCard title="Health Score" value={85} icon={Activity} status="good" />)
      expect(screen.getByText('Health Score')).toBeInTheDocument()
    })

    it('renders numeric value', () => {
      render(<KpiCard title="Test" value={42} icon={Activity} status="good" />)
      expect(screen.getByText('42')).toBeInTheDocument()
    })

    it('renders string value', () => {
      render(<KpiCard title="Test" value="N/A" icon={Activity} status="warn" />)
      expect(screen.getByText('N/A')).toBeInTheDocument()
    })

    it('renders suffix when provided', () => {
      render(<KpiCard title="Test" value={100} suffix="/100" icon={Activity} status="good" />)
      expect(screen.getByText('/100')).toBeInTheDocument()
    })

    it('does not render suffix when not provided', () => {
      render(<KpiCard title="Test" value={100} icon={Activity} status="good" />)
      expect(screen.queryByText('/100')).not.toBeInTheDocument()
    })
  })

  describe('Trend Display', () => {
    it('renders positive trend with + sign', () => {
      render(<KpiCard title="Test" value={50} icon={TrendingUp} status="good" trend={10} />)
      expect(screen.getByText('+10% vs ontem')).toBeInTheDocument()
    })

    it('renders negative trend without + sign', () => {
      render(<KpiCard title="Test" value={50} icon={TrendingUp} status="bad" trend={-5} />)
      expect(screen.getByText('-5% vs ontem')).toBeInTheDocument()
    })

    it('renders zero trend with + sign', () => {
      render(<KpiCard title="Test" value={50} icon={TrendingUp} status="warn" trend={0} />)
      expect(screen.getByText('+0% vs ontem')).toBeInTheDocument()
    })

    it('does not render trend when undefined', () => {
      render(<KpiCard title="Test" value={50} icon={Activity} status="good" />)
      expect(screen.queryByText(/vs ontem/)).not.toBeInTheDocument()
    })
  })

  describe('Status Styling', () => {
    it('applies success border for good status', () => {
      const { container } = render(
        <KpiCard title="Test" value={85} icon={Activity} status="good" />
      )
      const card = container.querySelector('.border-status-success-border')
      expect(card).toBeInTheDocument()
    })

    it('applies warning border for warn status', () => {
      const { container } = render(
        <KpiCard title="Test" value={65} icon={Activity} status="warn" />
      )
      const card = container.querySelector('.border-status-warning-border')
      expect(card).toBeInTheDocument()
    })

    it('applies error border for bad status', () => {
      const { container } = render(<KpiCard title="Test" value={30} icon={Activity} status="bad" />)
      const card = container.querySelector('.border-status-error-border')
      expect(card).toBeInTheDocument()
    })

    it('applies success text to value for good status', () => {
      render(<KpiCard title="Test" value={85} icon={Activity} status="good" />)
      const valueElement = screen.getByText('85')
      expect(valueElement).toHaveClass('text-status-success-foreground')
    })

    it('applies warning text to value for warn status', () => {
      render(<KpiCard title="Test" value={65} icon={Activity} status="warn" />)
      const valueElement = screen.getByText('65')
      expect(valueElement).toHaveClass('text-status-warning-foreground')
    })

    it('applies error text to value for bad status', () => {
      render(<KpiCard title="Test" value={30} icon={Activity} status="bad" />)
      const valueElement = screen.getByText('30')
      expect(valueElement).toHaveClass('text-status-error-foreground')
    })
  })

  describe('Icon Background', () => {
    it('applies success background for good status', () => {
      const { container } = render(
        <KpiCard title="Test" value={85} icon={Activity} status="good" />
      )
      const iconBg = container.querySelector('.bg-status-success')
      expect(iconBg).toBeInTheDocument()
    })

    it('applies warning background for warn status', () => {
      const { container } = render(
        <KpiCard title="Test" value={65} icon={Activity} status="warn" />
      )
      const iconBg = container.querySelector('.bg-status-warning')
      expect(iconBg).toBeInTheDocument()
    })

    it('applies error background for bad status', () => {
      const { container } = render(<KpiCard title="Test" value={30} icon={Activity} status="bad" />)
      const iconBg = container.querySelector('.bg-status-error')
      expect(iconBg).toBeInTheDocument()
    })
  })

  describe('Trend Styling', () => {
    it('applies success text for positive trend', () => {
      render(<KpiCard title="Test" value={50} icon={Clock} status="good" trend={10} />)
      const trendElement = screen.getByText('+10% vs ontem')
      expect(trendElement).toHaveClass('text-status-success-foreground')
    })

    it('applies error text for negative trend', () => {
      render(<KpiCard title="Test" value={50} icon={Clock} status="bad" trend={-10} />)
      const trendElement = screen.getByText('-10% vs ontem')
      expect(trendElement).toHaveClass('text-status-error-foreground')
    })
  })

  describe('Edge Cases', () => {
    it('renders 0 value correctly', () => {
      render(<KpiCard title="Test" value={0} icon={Activity} status="bad" />)
      expect(screen.getByText('0')).toBeInTheDocument()
    })

    it('renders large numbers', () => {
      render(<KpiCard title="Test" value={99999} icon={Activity} status="good" />)
      expect(screen.getByText('99999')).toBeInTheDocument()
    })

    it('renders decimal values', () => {
      render(<KpiCard title="Test" value={45.5} icon={Activity} status="warn" />)
      expect(screen.getByText('45.5')).toBeInTheDocument()
    })
  })
})
