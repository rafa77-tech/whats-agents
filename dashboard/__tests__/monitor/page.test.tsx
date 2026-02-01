/**
 * Testes para Monitor Page
 */

import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import MonitorPage from '@/app/(dashboard)/monitor/page'

// Mock components
vi.mock('@/components/monitor/monitor-page-content', () => ({
  MonitorPageContent: () => <div data-testid="monitor-content">Monitor Content</div>,
}))

describe('MonitorPage', () => {
  it('deve renderizar o componente MonitorPageContent', async () => {
    render(<MonitorPage />)
    expect(screen.getByTestId('monitor-content')).toBeInTheDocument()
  })

  it('deve renderizar dentro do container correto', () => {
    render(<MonitorPage />)
    const container = screen.getByTestId('monitor-content').parentElement?.parentElement
    expect(container).toHaveClass('min-h-screen')
  })
})
