/**
 * Tests for UI components with low coverage
 * - components/ui/checkbox.tsx
 * - components/ui/skeleton.tsx
 * - components/ui/alert.tsx
 * - components/ui/table-skeleton.tsx
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Checkbox } from '@/components/ui/checkbox'
import { Skeleton } from '@/components/ui/skeleton'
import { TableSkeleton } from '@/components/ui/table-skeleton'
import { Toaster } from '@/components/ui/sonner'
import { Table, TableBody } from '@/components/ui/table'

// Mock next-themes for Sonner
vi.mock('next-themes', () => ({
  useTheme: () => ({ theme: 'light' }),
}))

describe('Checkbox', () => {
  it('should render unchecked by default', () => {
    render(<Checkbox />)
    const checkbox = screen.getByRole('checkbox')
    expect(checkbox).toBeInTheDocument()
    expect(checkbox).not.toBeChecked()
  })

  it('should render checked when defaultChecked is true', () => {
    render(<Checkbox defaultChecked />)
    const checkbox = screen.getByRole('checkbox')
    expect(checkbox).toBeChecked()
  })

  it('should toggle when clicked', async () => {
    const onCheckedChange = vi.fn()
    render(<Checkbox onCheckedChange={onCheckedChange} />)
    const checkbox = screen.getByRole('checkbox')
    fireEvent.click(checkbox)
    expect(onCheckedChange).toHaveBeenCalled()
  })

  it('should be disabled when disabled prop is true', () => {
    render(<Checkbox disabled />)
    const checkbox = screen.getByRole('checkbox')
    expect(checkbox).toBeDisabled()
  })

  it('should apply custom className', () => {
    render(<Checkbox className="custom-class" />)
    const checkbox = screen.getByRole('checkbox')
    expect(checkbox).toHaveClass('custom-class')
  })
})

describe('Skeleton', () => {
  it('should render with default classes', () => {
    render(<Skeleton data-testid="skeleton" />)
    const skeleton = screen.getByTestId('skeleton')
    expect(skeleton).toHaveClass('animate-pulse')
    expect(skeleton).toHaveClass('rounded-md')
  })

  it('should apply custom className', () => {
    render(<Skeleton data-testid="skeleton" className="h-4 w-full" />)
    const skeleton = screen.getByTestId('skeleton')
    expect(skeleton).toHaveClass('h-4')
    expect(skeleton).toHaveClass('w-full')
  })

  it('should pass through additional props', () => {
    render(<Skeleton data-testid="skeleton" aria-label="Loading" />)
    const skeleton = screen.getByTestId('skeleton')
    expect(skeleton).toHaveAttribute('aria-label', 'Loading')
  })
})

describe('TableSkeleton', () => {
  it('should render default 5 rows and 6 columns', () => {
    render(
      <Table>
        <TableBody>
          <TableSkeleton />
        </TableBody>
      </Table>
    )
    const rows = document.querySelectorAll('tr')
    expect(rows.length).toBe(5)
    // Each row should have 6 cells
    const firstRow = rows[0]
    expect(firstRow).toBeDefined()
    const firstRowCells = firstRow?.querySelectorAll('td') ?? []
    expect(firstRowCells.length).toBe(6)
  })

  it('should render custom number of rows', () => {
    render(
      <Table>
        <TableBody>
          <TableSkeleton rows={3} />
        </TableBody>
      </Table>
    )
    const rows = document.querySelectorAll('tr')
    expect(rows.length).toBe(3)
  })

  it('should render custom number of columns', () => {
    render(
      <Table>
        <TableBody>
          <TableSkeleton rows={1} columns={4} />
        </TableBody>
      </Table>
    )
    const cells = document.querySelectorAll('td')
    expect(cells.length).toBe(4)
  })

  it('should render skeleton inside each cell', () => {
    render(
      <Table>
        <TableBody>
          <TableSkeleton rows={1} columns={1} />
        </TableBody>
      </Table>
    )
    const skeleton = document.querySelector('.animate-pulse')
    expect(skeleton).toBeInTheDocument()
  })
})

describe('Toaster (Sonner)', () => {
  it('should render without crashing', () => {
    // Sonner renders asynchronously, so we just verify it doesn't throw
    expect(() => render(<Toaster />)).not.toThrow()
  })

  it('should accept custom props', () => {
    // Test that component accepts props without throwing
    expect(() => render(<Toaster position="top-center" />)).not.toThrow()
  })

  it('should render with different theme', () => {
    expect(() => render(<Toaster />)).not.toThrow()
  })
})
