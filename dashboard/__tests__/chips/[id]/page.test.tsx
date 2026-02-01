/**
 * Testes para Chip Detail Page
 */

import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ChipDetailPage from '@/app/(dashboard)/chips/[id]/page'

// Mock components
vi.mock('@/components/chips/chip-detail-content', () => ({
  ChipDetailContent: ({ chipId }: { chipId: string }) => (
    <div data-testid="chip-detail-content">Chip {chipId}</div>
  ),
}))

vi.mock('@/components/chips/chip-detail-skeleton', () => ({
  ChipDetailSkeleton: () => <div data-testid="chip-skeleton">Loading...</div>,
}))

describe('ChipDetailPage', () => {
  it('deve renderizar com o id do chip', async () => {
    render(<ChipDetailPage params={{ id: 'chip-123' }} />)
    expect(screen.getByTestId('chip-detail-content')).toBeInTheDocument()
    expect(screen.getByText('Chip chip-123')).toBeInTheDocument()
  })

  it('deve renderizar dentro do container correto', () => {
    render(<ChipDetailPage params={{ id: 'chip-456' }} />)
    const container = screen.getByTestId('chip-detail-content').parentElement?.parentElement
    expect(container).toHaveClass('min-h-screen')
  })
})
