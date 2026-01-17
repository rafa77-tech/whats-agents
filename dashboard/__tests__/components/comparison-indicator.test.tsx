/**
 * Tests for components/dashboard/comparison-indicator.tsx
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ComparisonIndicator } from '@/components/dashboard/comparison-indicator'

describe('ComparisonIndicator', () => {
  it('should render positive change with green color', () => {
    render(<ComparisonIndicator current={120} previous={100} />)

    const indicator = screen.getByText('+20%')
    expect(indicator).toBeInTheDocument()
    expect(indicator).toHaveClass('text-green-600')
  })

  it('should render negative change with red color', () => {
    render(<ComparisonIndicator current={80} previous={100} />)

    const indicator = screen.getByText('-20%')
    expect(indicator).toBeInTheDocument()
    expect(indicator).toHaveClass('text-red-600')
  })

  it('should render neutral for small changes', () => {
    render(<ComparisonIndicator current={100} previous={100} />)

    const indicator = screen.getByText('0%')
    expect(indicator).toBeInTheDocument()
    expect(indicator).toHaveClass('text-gray-400')
  })

  it('should invert colors when lesserIsBetter is true', () => {
    // Decrease is good when lesserIsBetter
    render(<ComparisonIndicator current={80} previous={100} lesserIsBetter />)

    const indicator = screen.getByText('-20%')
    expect(indicator).toHaveClass('text-green-600')
  })

  it('should show increase as negative when lesserIsBetter', () => {
    render(<ComparisonIndicator current={120} previous={100} lesserIsBetter />)

    const indicator = screen.getByText('+20%')
    expect(indicator).toHaveClass('text-red-600')
  })

  it('should hide value when showValue is false', () => {
    render(<ComparisonIndicator current={120} previous={100} showValue={false} />)

    expect(screen.queryByText('+20%')).not.toBeInTheDocument()
  })

  it('should apply small size classes', () => {
    render(<ComparisonIndicator current={120} previous={100} size="sm" />)

    const indicator = screen.getByText('+20%')
    expect(indicator).toHaveClass('text-xs')
  })

  it('should apply medium size classes by default', () => {
    render(<ComparisonIndicator current={120} previous={100} />)

    const indicator = screen.getByText('+20%')
    expect(indicator).toHaveClass('text-sm')
  })

  it('should return null when previous is zero', () => {
    const { container } = render(<ComparisonIndicator current={100} previous={0} />)

    expect(container.firstChild).toBeNull()
  })
})
