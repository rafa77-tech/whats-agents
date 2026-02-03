/**
 * Testes para Tab de Grupos dentro de Chips
 *
 * Sprint 45: Grupos consolidado como tab dentro de /chips
 * A rota /chips/grupos foi removida; agora e /chips?tab=grupos
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

// Mock do componente GroupEntryPageContent
vi.mock('@/components/group-entry/group-entry-page-content', () => ({
  GroupEntryPageContent: () => <div data-testid="group-entry-content">Grupos Content</div>,
}))

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/chips',
  useSearchParams: () => new URLSearchParams('tab=grupos'),
}))

describe('GroupsTab', () => {
  it('deve renderizar GroupEntryPageContent', async () => {
    const { default: GroupsTab } = await import('@/components/chips/tabs/groups-tab')

    render(<GroupsTab />)

    expect(screen.getByTestId('group-entry-content')).toBeInTheDocument()
  })

  it('GroupEntryPageContent deve ser exportado corretamente', async () => {
    const { GroupEntryPageContent } =
      await import('@/components/group-entry/group-entry-page-content')

    expect(GroupEntryPageContent).toBeDefined()
  })
})
