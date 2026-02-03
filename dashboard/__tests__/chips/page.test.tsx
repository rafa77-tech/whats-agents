/**
 * Testes para Chips Page
 *
 * Sprint 45: Pagina unificada com tabs
 */

import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ChipsPage from '@/app/(dashboard)/chips/page'

// Mock ChipsUnifiedPage (componente principal usado pela pagina)
vi.mock('@/components/chips/chips-unified-page', () => ({
  ChipsUnifiedPage: () => <div data-testid="chips-unified-page">Chips Unified Page</div>,
}))

vi.mock('@/components/chips/chips-page-skeleton', () => ({
  ChipsPageSkeleton: () => <div data-testid="chips-skeleton">Loading...</div>,
}))

describe('ChipsPage', () => {
  it('deve renderizar o componente ChipsUnifiedPage', async () => {
    render(<ChipsPage />)
    expect(screen.getByTestId('chips-unified-page')).toBeInTheDocument()
  })

  it('deve renderizar o conteudo da pagina', () => {
    render(<ChipsPage />)
    expect(screen.getByText('Chips Unified Page')).toBeInTheDocument()
  })
})
