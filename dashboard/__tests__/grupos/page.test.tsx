/**
 * Testes para Grupos Page
 */

import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import GruposPage from '@/app/(dashboard)/grupos/page'

// Mock group-entry component
vi.mock('@/components/group-entry/group-entry-page-content', () => ({
  GroupEntryPageContent: () => <div data-testid="group-entry-content">Group Entry Content</div>,
}))

describe('GruposPage', () => {
  it('deve renderizar o componente GroupEntryPageContent', () => {
    render(<GruposPage />)
    expect(screen.getByTestId('group-entry-content')).toBeInTheDocument()
  })
})
