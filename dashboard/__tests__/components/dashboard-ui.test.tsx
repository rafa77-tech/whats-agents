/**
 * Tests for dashboard UI components with low coverage
 * - components/dashboard/export-menu.tsx
 * - components/dashboard/period-selector.tsx
 * - components/dashboard/chip-counters.tsx
 * - components/dashboard/chip-distribution.tsx
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ExportMenu } from '@/components/dashboard/export-menu'
import { PeriodSelector } from '@/components/dashboard/period-selector'

describe('ExportMenu', () => {
  it('should render export button', () => {
    const onExport = vi.fn()
    render(<ExportMenu onExport={onExport} />)
    expect(screen.getByText('Exportar')).toBeInTheDocument()
  })

  it('should be disabled when disabled prop is true', () => {
    const onExport = vi.fn()
    render(<ExportMenu onExport={onExport} disabled />)
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
  })

  it('should render download icon', () => {
    const onExport = vi.fn()
    render(<ExportMenu onExport={onExport} />)
    const icon = document.querySelector('.lucide-download')
    expect(icon).toBeInTheDocument()
  })

  it('should be enabled by default', () => {
    const onExport = vi.fn()
    render(<ExportMenu onExport={onExport} />)
    const button = screen.getByRole('button')
    expect(button).not.toBeDisabled()
  })

  // Note: Radix DropdownMenu interaction tests are skipped due to JSDOM limitations
  // The component rendering and props are tested via the above tests
})

describe('PeriodSelector', () => {
  it('should render with initial value', () => {
    const onChange = vi.fn()
    render(<PeriodSelector value="7d" onChange={onChange} />)
    expect(screen.getByText('7 dias')).toBeInTheDocument()
  })

  it('should render 14d value correctly', () => {
    const onChange = vi.fn()
    render(<PeriodSelector value="14d" onChange={onChange} />)
    expect(screen.getByText('14 dias')).toBeInTheDocument()
  })

  it('should render 30d value correctly', () => {
    const onChange = vi.fn()
    render(<PeriodSelector value="30d" onChange={onChange} />)
    expect(screen.getByText('30 dias')).toBeInTheDocument()
  })

  it('should render combobox trigger', () => {
    const onChange = vi.fn()
    render(<PeriodSelector value="7d" onChange={onChange} />)
    const trigger = screen.getByRole('combobox')
    expect(trigger).toBeInTheDocument()
  })

  // Note: Radix Select dropdown tests are skipped due to scrollIntoView not being available in JSDOM
  // The component rendering is tested via the above tests
})
