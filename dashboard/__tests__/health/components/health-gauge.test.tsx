import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { HealthGauge } from '@/components/health/health-gauge'

describe('HealthGauge', () => {
  describe('Score Display', () => {
    it('displays score value', () => {
      render(<HealthGauge score={75} status="healthy" />)
      expect(screen.getByText('75')).toBeInTheDocument()
    })

    it('displays /100 suffix', () => {
      render(<HealthGauge score={50} status="degraded" />)
      expect(screen.getByText('/100')).toBeInTheDocument()
    })

    it('displays 0 score', () => {
      render(<HealthGauge score={0} status="critical" />)
      expect(screen.getByText('0')).toBeInTheDocument()
    })

    it('displays 100 score', () => {
      render(<HealthGauge score={100} status="healthy" />)
      expect(screen.getByText('100')).toBeInTheDocument()
    })
  })

  describe('SVG Rendering', () => {
    it('renders svg element', () => {
      const { container } = render(<HealthGauge score={50} status="healthy" />)
      const svg = container.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })

    it('renders two circle elements', () => {
      const { container } = render(<HealthGauge score={50} status="healthy" />)
      const circles = container.querySelectorAll('circle')
      expect(circles).toHaveLength(2)
    })

    it('progress circle has correct stroke color for healthy', () => {
      const { container } = render(<HealthGauge score={75} status="healthy" />)
      const circles = container.querySelectorAll('circle')
      // Second circle is the progress arc
      const progressCircle = circles[1]
      expect(progressCircle).toHaveAttribute('stroke', '#22c55e')
    })

    it('progress circle has correct stroke color for degraded', () => {
      const { container } = render(<HealthGauge score={60} status="degraded" />)
      const circles = container.querySelectorAll('circle')
      const progressCircle = circles[1]
      expect(progressCircle).toHaveAttribute('stroke', '#eab308')
    })

    it('progress circle has correct stroke color for critical', () => {
      const { container } = render(<HealthGauge score={30} status="critical" />)
      const circles = container.querySelectorAll('circle')
      const progressCircle = circles[1]
      expect(progressCircle).toHaveAttribute('stroke', '#ef4444')
    })
  })

  describe('Text Styling', () => {
    it('applies green text for healthy status', () => {
      render(<HealthGauge score={90} status="healthy" />)
      const scoreElement = screen.getByText('90')
      expect(scoreElement).toHaveClass('text-green-600')
    })

    it('applies yellow text for degraded status', () => {
      render(<HealthGauge score={60} status="degraded" />)
      const scoreElement = screen.getByText('60')
      expect(scoreElement).toHaveClass('text-yellow-600')
    })

    it('applies red text for critical status', () => {
      render(<HealthGauge score={20} status="critical" />)
      const scoreElement = screen.getByText('20')
      expect(scoreElement).toHaveClass('text-red-600')
    })
  })

  describe('Gauge Calculations', () => {
    it('background circle has strokeWidth 8', () => {
      const { container } = render(<HealthGauge score={50} status="healthy" />)
      const circles = container.querySelectorAll('circle')
      expect(circles[0]).toHaveAttribute('stroke-width', '8')
    })

    it('progress circle has strokeWidth 8', () => {
      const { container } = render(<HealthGauge score={50} status="healthy" />)
      const circles = container.querySelectorAll('circle')
      expect(circles[1]).toHaveAttribute('stroke-width', '8')
    })

    it('circles have correct radius', () => {
      const { container } = render(<HealthGauge score={50} status="healthy" />)
      const circles = container.querySelectorAll('circle')
      expect(circles[0]).toHaveAttribute('r', '45')
      expect(circles[1]).toHaveAttribute('r', '45')
    })
  })
})
