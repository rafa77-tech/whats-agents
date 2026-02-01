import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CapacityBar } from '@/components/group-entry/capacity-bar'

describe('CapacityBar', () => {
  it('renders capacity text correctly', () => {
    render(<CapacityBar used={50} total={100} />)
    expect(screen.getByText('Capacidade: 50/100 grupos')).toBeInTheDocument()
    expect(screen.getByText('50%')).toBeInTheDocument()
  })

  it('renders 0% when used is 0', () => {
    render(<CapacityBar used={0} total={100} />)
    expect(screen.getByText('Capacidade: 0/100 grupos')).toBeInTheDocument()
    expect(screen.getByText('0%')).toBeInTheDocument()
  })

  it('renders 100% when at full capacity', () => {
    render(<CapacityBar used={100} total={100} />)
    expect(screen.getByText('100%')).toBeInTheDocument()
  })

  it('shows warning message when capacity is at 80% or above', () => {
    render(<CapacityBar used={80} total={100} />)
    expect(
      screen.getByText('Capacidade quase no limite. Considere adicionar mais chips.')
    ).toBeInTheDocument()
  })

  it('shows warning message at 90%', () => {
    render(<CapacityBar used={90} total={100} />)
    expect(
      screen.getByText('Capacidade quase no limite. Considere adicionar mais chips.')
    ).toBeInTheDocument()
  })

  it('does not show warning message below 80%', () => {
    render(<CapacityBar used={79} total={100} />)
    expect(
      screen.queryByText('Capacidade quase no limite. Considere adicionar mais chips.')
    ).not.toBeInTheDocument()
  })

  it('handles zero total gracefully', () => {
    render(<CapacityBar used={0} total={0} />)
    expect(screen.getByText('0%')).toBeInTheDocument()
  })

  it('handles edge case with used > total', () => {
    render(<CapacityBar used={120} total={100} />)
    // Should show the actual values
    expect(screen.getByText('Capacidade: 120/100 grupos')).toBeInTheDocument()
  })

  it('renders progress bar element', () => {
    const { container } = render(<CapacityBar used={50} total={100} />)
    const progressBar = container.querySelector('[style*="width: 50%"]')
    expect(progressBar).toBeInTheDocument()
  })

  it('applies green color for low usage', () => {
    const { container } = render(<CapacityBar used={50} total={100} />)
    const progressBar = container.querySelector('.bg-green-500')
    expect(progressBar).toBeInTheDocument()
  })

  it('applies yellow color for warning level (80-89%)', () => {
    const { container } = render(<CapacityBar used={85} total={100} />)
    const progressBar = container.querySelector('.bg-yellow-500')
    expect(progressBar).toBeInTheDocument()
  })

  it('applies red color for danger level (90%+)', () => {
    const { container } = render(<CapacityBar used={95} total={100} />)
    const progressBar = container.querySelector('.bg-red-500')
    expect(progressBar).toBeInTheDocument()
  })
})
