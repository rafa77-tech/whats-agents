/**
 * Tests for components/dashboard/rate-limit-bar.tsx
 *
 * CRITICAL: This component shows rate limit status.
 * If colors are wrong, operators may not notice they're close to limits,
 * leading to chip bans (irreversible damage).
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { RateLimitBar } from '@/components/dashboard/rate-limit-bar'
import { type RateLimitData } from '@/types/dashboard'

describe('RateLimitBar', () => {
  describe('getProgressColor - CRITICAL BUSINESS LOGIC', () => {
    it('should show GREEN when usage is below 50%', () => {
      const data: RateLimitData = { current: 10, max: 100, label: 'Msgs/hora' }
      const { container } = render(<RateLimitBar data={data} />)

      const progressBar = container.querySelector('.bg-green-500')
      expect(progressBar).toBeInTheDocument()
    })

    it('should show GREEN at exactly 49%', () => {
      const data: RateLimitData = { current: 49, max: 100, label: 'Msgs/hora' }
      const { container } = render(<RateLimitBar data={data} />)

      expect(container.querySelector('.bg-green-500')).toBeInTheDocument()
      expect(container.querySelector('.bg-yellow-500')).not.toBeInTheDocument()
    })

    it('should show YELLOW when usage is between 50% and 79%', () => {
      const data: RateLimitData = { current: 50, max: 100, label: 'Msgs/hora' }
      const { container } = render(<RateLimitBar data={data} />)

      expect(container.querySelector('.bg-yellow-500')).toBeInTheDocument()
      expect(container.querySelector('.bg-green-500')).not.toBeInTheDocument()
    })

    it('should show YELLOW at exactly 79%', () => {
      const data: RateLimitData = { current: 79, max: 100, label: 'Msgs/hora' }
      const { container } = render(<RateLimitBar data={data} />)

      expect(container.querySelector('.bg-yellow-500')).toBeInTheDocument()
      expect(container.querySelector('.bg-red-500')).not.toBeInTheDocument()
    })

    it('should show RED when usage is 80% or above - DANGER ZONE', () => {
      const data: RateLimitData = { current: 80, max: 100, label: 'Msgs/hora' }
      const { container } = render(<RateLimitBar data={data} />)

      expect(container.querySelector('.bg-red-500')).toBeInTheDocument()
      expect(container.querySelector('.bg-yellow-500')).not.toBeInTheDocument()
    })

    it('should show RED at 100%', () => {
      const data: RateLimitData = { current: 100, max: 100, label: 'Msgs/hora' }
      const { container } = render(<RateLimitBar data={data} />)

      expect(container.querySelector('.bg-red-500')).toBeInTheDocument()
    })

    it('should show RED when over limit (>100%)', () => {
      const data: RateLimitData = { current: 120, max: 100, label: 'Msgs/hora' }
      const { container } = render(<RateLimitBar data={data} />)

      expect(container.querySelector('.bg-red-500')).toBeInTheDocument()
    })
  })

  describe('percentage calculation', () => {
    it('should calculate percentage correctly', () => {
      const data: RateLimitData = { current: 25, max: 100, label: 'Msgs/hora' }
      const { container } = render(<RateLimitBar data={data} />)

      // 25% width
      const progressBar = container.querySelector('[style*="width"]')
      expect(progressBar).toHaveStyle({ width: '25%' })
    })

    it('should cap visual width at 100% even when over limit', () => {
      const data: RateLimitData = { current: 150, max: 100, label: 'Msgs/hora' }
      const { container } = render(<RateLimitBar data={data} />)

      // Should show 100% width, not 150%
      const progressBar = container.querySelector('[style*="width"]')
      expect(progressBar).toHaveStyle({ width: '100%' })
    })
  })

  describe('display', () => {
    it('should display the label', () => {
      const data: RateLimitData = { current: 50, max: 100, label: 'Msgs/hora' }
      render(<RateLimitBar data={data} />)

      expect(screen.getByText('Msgs/hora')).toBeInTheDocument()
    })

    it('should display current/max values', () => {
      const data: RateLimitData = { current: 50, max: 100, label: 'Msgs/hora' }
      render(<RateLimitBar data={data} />)

      expect(screen.getByText('50/100')).toBeInTheDocument()
    })

    it('should handle daily limit format', () => {
      const data: RateLimitData = { current: 500, max: 2000, label: 'Msgs/dia' }
      render(<RateLimitBar data={data} />)

      expect(screen.getByText('Msgs/dia')).toBeInTheDocument()
      expect(screen.getByText('500/2000')).toBeInTheDocument()
    })
  })

  describe('edge cases', () => {
    it('should handle zero current value', () => {
      const data: RateLimitData = { current: 0, max: 100, label: 'Msgs/hora' }
      const { container } = render(<RateLimitBar data={data} />)

      expect(container.querySelector('.bg-green-500')).toBeInTheDocument()
    })

    it('should handle very small percentages', () => {
      const data: RateLimitData = { current: 1, max: 1000, label: 'Msgs/hora' }
      const { container } = render(<RateLimitBar data={data} />)

      expect(container.querySelector('.bg-green-500')).toBeInTheDocument()
    })
  })
})
