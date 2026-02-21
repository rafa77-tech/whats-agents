/**
 * Tests for Meta page shell and unified page component
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(''),
  useRouter: () => ({ push: vi.fn() }),
}))

// Mock the lazy-loaded tabs to avoid async complexity
vi.mock('@/components/meta/tabs/templates-tab', () => ({
  default: () => <div data-testid="templates-tab">Templates Content</div>,
}))
vi.mock('@/components/meta/tabs/quality-tab', () => ({
  default: () => <div data-testid="quality-tab">Quality Content</div>,
}))
vi.mock('@/components/meta/tabs/analytics-tab', () => ({
  default: () => <div data-testid="analytics-tab">Analytics Content</div>,
}))
vi.mock('@/components/meta/tabs/flows-tab', () => ({
  default: () => <div data-testid="flows-tab">Flows Content</div>,
}))

import { MetaUnifiedPage } from '@/components/meta/meta-unified-page'

describe('MetaUnifiedPage', () => {
  it('should render tab triggers', () => {
    render(<MetaUnifiedPage />)
    expect(screen.getByRole('tab', { name: 'Templates' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Qualidade' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Custos' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Flows' })).toBeInTheDocument()
  })

  it('should default to templates tab when no search param', () => {
    render(<MetaUnifiedPage />)
    const templatesTab = screen.getByRole('tab', { name: 'Templates' })
    expect(templatesTab).toHaveAttribute('data-state', 'active')
  })

  it('should render the default tab content', async () => {
    render(<MetaUnifiedPage />)
    // Lazy-loaded content may need a tick to resolve
    const tab = await screen.findByTestId('templates-tab')
    expect(tab).toBeInTheDocument()
  })

  it('should have 4 tab triggers in the list', () => {
    render(<MetaUnifiedPage />)
    const tabList = screen.getByRole('tablist')
    const tabs = tabList.querySelectorAll('[role="tab"]')
    expect(tabs).toHaveLength(4)
  })
})
