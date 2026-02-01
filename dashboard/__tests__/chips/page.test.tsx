/**
 * Testes para Chips Page
 */

import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ChipsPage from '@/app/(dashboard)/chips/page'

// Mock Suspense and components
vi.mock('@/components/chips/chips-page-content', () => ({
  ChipsPageContent: () => <div data-testid="chips-page-content">Chips Content</div>,
}))

vi.mock('@/components/chips/chips-page-skeleton', () => ({
  ChipsPageSkeleton: () => <div data-testid="chips-skeleton">Loading...</div>,
}))

describe('ChipsPage', () => {
  it('deve renderizar o componente ChipsPageContent', async () => {
    render(<ChipsPage />)
    expect(screen.getByTestId('chips-page-content')).toBeInTheDocument()
  })

  it('deve renderizar dentro do container correto', () => {
    render(<ChipsPage />)
    const container = screen.getByTestId('chips-page-content').parentElement?.parentElement
    expect(container).toHaveClass('min-h-screen')
  })
})
