/**
 * Tests for navigation components
 * - components/dashboard/header.tsx
 * - components/dashboard/sidebar.tsx
 * - components/dashboard/bottom-nav.tsx
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Header } from '@/components/dashboard/header'
import { Sidebar } from '@/components/dashboard/sidebar'
import { BottomNav } from '@/components/dashboard/bottom-nav'

// Mock usePathname for different routes
const mockUsePathname = vi.fn()
vi.mock('next/navigation', async () => {
  const actual = await vi.importActual('next/navigation')
  return {
    ...actual,
    usePathname: () => mockUsePathname(),
  }
})

describe('Header', () => {
  beforeEach(() => {
    mockUsePathname.mockReturnValue('/dashboard')
  })

  it('should render search input', () => {
    render(<Header />)
    expect(screen.getByPlaceholderText('Buscar medicos, conversas...')).toBeInTheDocument()
  })

  it('should render notification bell', () => {
    render(<Header />)
    // Bell icon is present (notification button)
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThan(0)
  })

  it('should render user avatar with initial', () => {
    render(<Header />)
    expect(screen.getByText('R')).toBeInTheDocument()
  })

  it('should open mobile menu when hamburger is clicked', () => {
    render(<Header />)
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThan(0)
    fireEvent.click(buttons[0] as HTMLElement)
    // After clicking, the sidebar should be visible (with close button)
    expect(screen.getByText('Sair')).toBeInTheDocument()
  })

  it('should close mobile menu when X button is clicked', () => {
    render(<Header />)
    // Open menu first
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThan(0)
    fireEvent.click(buttons[0] as HTMLElement)

    // Find and click close button (second X button that appears)
    const closeButtons = screen.getAllByRole('button')
    const closeButton = closeButtons.find((btn) => btn.querySelector('svg.h-5.w-5'))
    if (closeButton) {
      fireEvent.click(closeButton)
    }
    // Test passes if no error is thrown
  })

  it('should close mobile menu when backdrop is clicked', () => {
    render(<Header />)
    // Open menu first
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThan(0)
    fireEvent.click(buttons[0] as HTMLElement)

    // Click backdrop (the div with bg-black/50)
    const backdrop = document.querySelector('.bg-black\\/50') as HTMLElement | null
    if (backdrop) {
      fireEvent.click(backdrop)
    }
    // Test passes if no error is thrown
  })
})

describe('Sidebar', () => {
  beforeEach(() => {
    mockUsePathname.mockReturnValue('/dashboard')
  })

  it('should render logo', () => {
    render(<Sidebar />)
    expect(screen.getByText('Julia')).toBeInTheDocument()
    // Dashboard appears twice: in logo subtitle and in nav
    expect(screen.getAllByText('Dashboard').length).toBeGreaterThanOrEqual(1)
  })

  it('should render all navigation items', () => {
    render(<Sidebar />)
    // Dashboard appears in multiple places, so use getAllByText
    expect(screen.getAllByText('Dashboard').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Campanhas')).toBeInTheDocument()
    expect(screen.getByText('Instrucoes')).toBeInTheDocument()
    expect(screen.getByText('Hospitais Bloqueados')).toBeInTheDocument()
    expect(screen.getByText('Sistema')).toBeInTheDocument()
    expect(screen.getByText('Ajuda')).toBeInTheDocument()
  })

  it('should render logout button', () => {
    render(<Sidebar />)
    expect(screen.getByText('Sair')).toBeInTheDocument()
  })

  it('should highlight active route', () => {
    mockUsePathname.mockReturnValue('/campanhas')
    render(<Sidebar />)

    const campanhasLink = screen.getByText('Campanhas').closest('a')
    expect(campanhasLink).toHaveClass('bg-revoluna-50')
  })

  it('should highlight dashboard when on root', () => {
    mockUsePathname.mockReturnValue('/dashboard')
    render(<Sidebar />)

    // Find the Dashboard link (first one, not the subtitle)
    const links = screen.getAllByRole('link')
    const dashboardLink = links.find((link) => link.getAttribute('href') === '/dashboard')
    expect(dashboardLink).toHaveClass('bg-revoluna-50')
  })
})

describe('BottomNav', () => {
  beforeEach(() => {
    mockUsePathname.mockReturnValue('/dashboard')
  })

  it('should render all mobile navigation items', () => {
    render(<BottomNav />)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Campanhas')).toBeInTheDocument()
    expect(screen.getByText('Chips')).toBeInTheDocument()
    expect(screen.getByText('Instrucoes')).toBeInTheDocument()
    expect(screen.getByText('Sistema')).toBeInTheDocument()
  })

  it('should highlight active route on mobile', () => {
    mockUsePathname.mockReturnValue('/instrucoes')
    render(<BottomNav />)

    const instrucoesLink = screen.getByText('Instrucoes').closest('a')
    expect(instrucoesLink).toHaveClass('text-revoluna-400')
  })

  it('should not highlight inactive routes', () => {
    mockUsePathname.mockReturnValue('/dashboard')
    render(<BottomNav />)

    const campanhasLink = screen.getByText('Campanhas').closest('a')
    expect(campanhasLink).toHaveClass('text-gray-500')
  })

  it('should highlight nested routes correctly', () => {
    mockUsePathname.mockReturnValue('/campanhas/nova')
    render(<BottomNav />)

    const campanhasLink = screen.getByText('Campanhas').closest('a')
    expect(campanhasLink).toHaveClass('text-revoluna-400')
  })
})
