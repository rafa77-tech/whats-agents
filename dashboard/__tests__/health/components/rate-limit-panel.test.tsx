import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RateLimitPanel } from '@/components/health/rate-limit-panel'

describe('RateLimitPanel', () => {
  const mockRateLimit = {
    hourly: { used: 10, limit: 20 },
    daily: { used: 50, limit: 100 },
  }

  describe('Rendering', () => {
    it('renders panel title', () => {
      render(<RateLimitPanel rateLimit={mockRateLimit} />)
      expect(screen.getByText('Rate Limiting')).toBeInTheDocument()
    })

    it('renders panel description', () => {
      render(<RateLimitPanel rateLimit={mockRateLimit} />)
      expect(screen.getByText('Uso de limite de mensagens')).toBeInTheDocument()
    })

    it('renders hourly section', () => {
      render(<RateLimitPanel rateLimit={mockRateLimit} />)
      expect(screen.getByText('Por Hora')).toBeInTheDocument()
    })

    it('renders daily section', () => {
      render(<RateLimitPanel rateLimit={mockRateLimit} />)
      expect(screen.getByText('Por Dia')).toBeInTheDocument()
    })

    it('renders footer note about WhatsApp', () => {
      render(<RateLimitPanel rateLimit={mockRateLimit} />)
      expect(
        screen.getByText(/Limites configurados para evitar ban do WhatsApp/)
      ).toBeInTheDocument()
    })
  })

  describe('Hourly Display', () => {
    it('displays hourly used/limit values', () => {
      render(<RateLimitPanel rateLimit={mockRateLimit} />)
      expect(screen.getByText('10/20 (50%)')).toBeInTheDocument()
    })

    it('calculates hourly percentage correctly', () => {
      const highUsage = {
        hourly: { used: 18, limit: 20 },
        daily: { used: 50, limit: 100 },
      }
      render(<RateLimitPanel rateLimit={highUsage} />)
      expect(screen.getByText('18/20 (90%)')).toBeInTheDocument()
    })
  })

  describe('Daily Display', () => {
    it('displays daily used/limit values', () => {
      render(<RateLimitPanel rateLimit={mockRateLimit} />)
      expect(screen.getByText('50/100 (50%)')).toBeInTheDocument()
    })

    it('calculates daily percentage correctly', () => {
      const highUsage = {
        hourly: { used: 10, limit: 20 },
        daily: { used: 95, limit: 100 },
      }
      render(<RateLimitPanel rateLimit={highUsage} />)
      expect(screen.getByText('95/100 (95%)')).toBeInTheDocument()
    })
  })

  describe('Warning Messages', () => {
    it('shows hourly warning when >= 80%', () => {
      const highUsage = {
        hourly: { used: 16, limit: 20 },
        daily: { used: 50, limit: 100 },
      }
      render(<RateLimitPanel rateLimit={highUsage} />)
      expect(screen.getByText(/Proximo do limite horario/)).toBeInTheDocument()
      expect(screen.getByText(/20% restante/)).toBeInTheDocument()
    })

    it('shows daily warning when >= 80%', () => {
      const highUsage = {
        hourly: { used: 10, limit: 20 },
        daily: { used: 85, limit: 100 },
      }
      render(<RateLimitPanel rateLimit={highUsage} />)
      expect(screen.getByText(/Proximo do limite diario/)).toBeInTheDocument()
      expect(screen.getByText(/15% restante/)).toBeInTheDocument()
    })

    it('does not show warning when < 80%', () => {
      render(<RateLimitPanel rateLimit={mockRateLimit} />)
      expect(screen.queryByText(/Proximo do limite/)).not.toBeInTheDocument()
    })
  })

  describe('Progress Bar Colors', () => {
    it('shows green progress for low usage', () => {
      const { container } = render(<RateLimitPanel rateLimit={mockRateLimit} />)
      const greenBars = container.querySelectorAll('.bg-green-500')
      expect(greenBars.length).toBeGreaterThanOrEqual(2)
    })

    it('shows yellow progress for medium usage (70-89%)', () => {
      const mediumUsage = {
        hourly: { used: 15, limit: 20 }, // 75%
        daily: { used: 80, limit: 100 }, // 80%
      }
      const { container } = render(<RateLimitPanel rateLimit={mediumUsage} />)
      const yellowBars = container.querySelectorAll('.bg-yellow-500')
      expect(yellowBars.length).toBeGreaterThanOrEqual(2)
    })

    it('shows red progress for high usage (>= 90%)', () => {
      const highUsage = {
        hourly: { used: 19, limit: 20 }, // 95%
        daily: { used: 95, limit: 100 }, // 95%
      }
      const { container } = render(<RateLimitPanel rateLimit={highUsage} />)
      const redBars = container.querySelectorAll('.bg-red-500')
      expect(redBars.length).toBeGreaterThanOrEqual(2)
    })
  })

  describe('Default Values', () => {
    it('uses default values when rateLimit is undefined', () => {
      render(<RateLimitPanel rateLimit={undefined} />)
      expect(screen.getByText('0/20 (0%)')).toBeInTheDocument()
      expect(screen.getByText('0/100 (0%)')).toBeInTheDocument()
    })

    it('uses default values for missing hourly', () => {
      render(<RateLimitPanel rateLimit={undefined} />)
      expect(screen.getByText('Por Hora')).toBeInTheDocument()
    })

    it('uses default values for missing daily', () => {
      render(<RateLimitPanel rateLimit={undefined} />)
      expect(screen.getByText('Por Dia')).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('handles zero limits gracefully', () => {
      const zeroLimits = {
        hourly: { used: 0, limit: 0 },
        daily: { used: 0, limit: 0 },
      }
      render(<RateLimitPanel rateLimit={zeroLimits} />)
      // Both hourly and daily show 0/0 (0%)
      const zeroElements = screen.getAllByText('0/0 (0%)')
      expect(zeroElements).toHaveLength(2)
    })

    it('handles 100% usage', () => {
      const fullUsage = {
        hourly: { used: 20, limit: 20 },
        daily: { used: 100, limit: 100 },
      }
      render(<RateLimitPanel rateLimit={fullUsage} />)
      expect(screen.getByText('20/20 (100%)')).toBeInTheDocument()
      expect(screen.getByText('100/100 (100%)')).toBeInTheDocument()
    })
  })
})
