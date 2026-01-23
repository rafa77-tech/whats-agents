/**
 * Tests for components/chips/status-counter-card.tsx
 *
 * Tests the StatusCounterCard component rendering and status configurations.
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { StatusCounterCard } from '@/components/chips/status-counter-card'
import { ChipStatus } from '@/types/dashboard'

describe('StatusCounterCard', () => {
  describe('rendering', () => {
    it('should display the count', () => {
      render(<StatusCounterCard status="active" count={25} percentage={50} />)
      expect(screen.getByText('25')).toBeInTheDocument()
    })

    it('should display the percentage', () => {
      render(<StatusCounterCard status="active" count={25} percentage={50} />)
      expect(screen.getByText('50.0%')).toBeInTheDocument()
    })

    it('should handle zero count', () => {
      render(<StatusCounterCard status="banned" count={0} percentage={0} />)
      expect(screen.getByText('0')).toBeInTheDocument()
      expect(screen.getByText('0.0%')).toBeInTheDocument()
    })

    it('should handle decimal percentage', () => {
      render(<StatusCounterCard status="warming" count={15} percentage={33.333} />)
      expect(screen.getByText('33.3%')).toBeInTheDocument()
    })
  })

  describe('status labels', () => {
    // Labels use plural form in Portuguese
    const statusLabels: Record<ChipStatus, string> = {
      provisioned: 'Provisionados',
      pending: 'Pendentes',
      warming: 'Aquecendo',
      ready: 'Prontos',
      active: 'Ativos',
      degraded: 'Degradados',
      paused: 'Pausados',
      banned: 'Banidos',
      cancelled: 'Cancelados',
    }

    Object.entries(statusLabels).forEach(([status, label]) => {
      it(`should display correct label for ${status} status`, () => {
        render(<StatusCounterCard status={status as ChipStatus} count={10} percentage={20} />)
        expect(screen.getByText(label)).toBeInTheDocument()
      })
    })
  })

  describe('status styling', () => {
    it('should apply active status color', () => {
      const { container } = render(<StatusCounterCard status="active" count={10} percentage={20} />)
      expect(container.querySelector('.bg-green-50')).toBeInTheDocument()
    })

    it('should apply banned status color', () => {
      const { container } = render(<StatusCounterCard status="banned" count={5} percentage={10} />)
      expect(container.querySelector('.bg-red-50')).toBeInTheDocument()
    })

    it('should apply warming status color', () => {
      const { container } = render(
        <StatusCounterCard status="warming" count={15} percentage={30} />
      )
      expect(container.querySelector('.bg-yellow-50')).toBeInTheDocument()
    })

    it('should apply ready status color', () => {
      const { container } = render(<StatusCounterCard status="ready" count={20} percentage={40} />)
      expect(container.querySelector('.bg-blue-50')).toBeInTheDocument()
    })

    it('should apply degraded status color', () => {
      const { container } = render(<StatusCounterCard status="degraded" count={3} percentage={6} />)
      expect(container.querySelector('.bg-orange-50')).toBeInTheDocument()
    })

    it('should apply paused status color', () => {
      const { container } = render(<StatusCounterCard status="paused" count={8} percentage={16} />)
      expect(container.querySelector('.bg-gray-50')).toBeInTheDocument()
    })

    it('should apply provisioned status color', () => {
      const { container } = render(
        <StatusCounterCard status="provisioned" count={12} percentage={24} />
      )
      expect(container.querySelector('.bg-purple-50')).toBeInTheDocument()
    })
  })

  describe('trend indicator', () => {
    it('should show positive trend with plus sign', () => {
      render(
        <StatusCounterCard status="active" count={25} percentage={50} trend="up" trendValue={5} />
      )
      expect(screen.getByText('+5')).toBeInTheDocument()
    })

    it('should show negative trend with minus sign', () => {
      render(
        <StatusCounterCard status="active" count={25} percentage={50} trend="down" trendValue={3} />
      )
      expect(screen.getByText('-3')).toBeInTheDocument()
    })

    it('should not show trend when value is zero', () => {
      render(
        <StatusCounterCard status="active" count={25} percentage={50} trend="up" trendValue={0} />
      )
      expect(screen.queryByText('+0')).not.toBeInTheDocument()
    })

    it('should not show trend when trendValue is undefined', () => {
      render(<StatusCounterCard status="active" count={25} percentage={50} trend="up" />)
      // No trend should be rendered
      const trendElements = screen.queryByText(/^\+/)
      expect(trendElements).not.toBeInTheDocument()
    })

    it('should apply green color for up trend', () => {
      render(
        <StatusCounterCard status="active" count={25} percentage={50} trend="up" trendValue={5} />
      )
      const trendElement = screen.getByText('+5')
      expect(trendElement).toHaveClass('text-green-600')
    })

    it('should apply red color for down trend', () => {
      render(
        <StatusCounterCard status="active" count={25} percentage={50} trend="down" trendValue={5} />
      )
      const trendElement = screen.getByText('-5')
      expect(trendElement).toHaveClass('text-red-600')
    })
  })

  describe('optional percentage', () => {
    it('should not show percentage when not provided', () => {
      render(<StatusCounterCard status="active" count={25} />)
      expect(screen.queryByText('%')).not.toBeInTheDocument()
    })
  })
})
