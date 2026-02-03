/**
 * Testes para Grupos Page
 *
 * Pagina de gestao de entrada em grupos WhatsApp.
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

// Mock GroupEntryPageContent
vi.mock('@/components/group-entry/group-entry-page-content', () => ({
  GroupEntryPageContent: () => <div data-testid="group-entry-content">Grupos Content</div>,
}))

describe('GruposPage', () => {
  it('deve renderizar GroupEntryPageContent', async () => {
    const { default: GruposPage } = await import('@/app/(dashboard)/grupos/page')

    render(<GruposPage />)

    expect(screen.getByTestId('group-entry-content')).toBeInTheDocument()
  })
})
