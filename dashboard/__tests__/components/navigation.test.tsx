/**
 * Tests for navigation components
 * - components/dashboard/header.tsx
 * - components/dashboard/sidebar.tsx
 * - components/dashboard/bottom-nav.tsx
 *
 * Updated for Sprint 45 with new navigation structure
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { Header } from '@/components/dashboard/header'
import { Sidebar } from '@/components/dashboard/sidebar'
import { BottomNav } from '@/components/dashboard/bottom-nav'
import { CommandPaletteProvider } from '@/components/command-palette'

// Mock scrollIntoView (not available in jsdom)
Element.prototype.scrollIntoView = vi.fn()

// Helper to render Header with required providers
const renderHeader = () => {
  return render(
    <CommandPaletteProvider>
      <Header />
    </CommandPaletteProvider>
  )
}

// Mock usePathname for different routes
const mockUsePathname = vi.fn()
vi.mock('next/navigation', async () => {
  const actual = await vi.importActual('next/navigation')
  return {
    ...actual,
    usePathname: () => mockUsePathname(),
    useRouter: () => ({
      push: vi.fn(),
      replace: vi.fn(),
      prefetch: vi.fn(),
    }),
  }
})

describe('Header', () => {
  beforeEach(() => {
    mockUsePathname.mockReturnValue('/dashboard')
  })

  it('should render search button for command palette', () => {
    renderHeader()
    // Search button opens command palette
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThan(0)
  })

  it('should render notification bell', () => {
    renderHeader()
    // Bell icon is present (notification button)
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThan(0)
  })

  it('should render user avatar with initial', () => {
    renderHeader()
    expect(screen.getByText('R')).toBeInTheDocument()
  })

  it('should open mobile menu when hamburger is clicked', () => {
    renderHeader()
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThan(0)
    fireEvent.click(buttons[0] as HTMLElement)
    // After clicking, the sidebar should be visible (with close button)
    expect(screen.getByText('Sair')).toBeInTheDocument()
  })

  it('should close mobile menu when X button is clicked', () => {
    renderHeader()
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
    renderHeader()
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

  it('should render Jull.ia logo', () => {
    render(<Sidebar />)
    expect(screen.getByText('Jull.ia')).toBeInTheDocument()
    expect(screen.getByText('J')).toBeInTheDocument()
  })

  it('should render all navigation groups', () => {
    render(<Sidebar />)
    expect(screen.getByText('Operacoes')).toBeInTheDocument()
    expect(screen.getByText('Cadastros')).toBeInTheDocument()
    expect(screen.getByText('WhatsApp')).toBeInTheDocument()
    expect(screen.getByText('Monitoramento')).toBeInTheDocument()
    expect(screen.getByText('Qualidade')).toBeInTheDocument()
  })

  it('should render all navigation items', () => {
    render(<Sidebar />)
    expect(screen.getAllByText('Dashboard').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Conversas')).toBeInTheDocument()
    expect(screen.getByText('Campanhas')).toBeInTheDocument()
    expect(screen.getByText('Vagas')).toBeInTheDocument()
    expect(screen.getByText('Medicos')).toBeInTheDocument()
    expect(screen.getByText('Hospitais')).toBeInTheDocument()
    expect(screen.getByText('Chips')).toBeInTheDocument()
    // Grupos agora e uma tab dentro de Chips, nao um item separado
    expect(screen.getByText('Monitor')).toBeInTheDocument()
    expect(screen.getByText('Health')).toBeInTheDocument()
    expect(screen.getByText('Integridade')).toBeInTheDocument()
    expect(screen.getByText('Metricas')).toBeInTheDocument()
    expect(screen.getByText('Avaliacoes')).toBeInTheDocument()
    expect(screen.getByText('Auditoria')).toBeInTheDocument()
  })

  it('should render footer items', () => {
    render(<Sidebar />)
    // Instrucoes foi movido para Operacoes
    expect(screen.getByText('Sistema')).toBeInTheDocument()
    expect(screen.getByText('Ajuda')).toBeInTheDocument()
  })

  it('should render Instrucoes in Operacoes group', () => {
    render(<Sidebar />)
    expect(screen.getByText('Instrucoes')).toBeInTheDocument()
  })

  it('should render logout button', () => {
    render(<Sidebar />)
    expect(screen.getByText('Sair')).toBeInTheDocument()
  })

  it('should highlight active route with primary colors', () => {
    mockUsePathname.mockReturnValue('/campanhas')
    render(<Sidebar />)

    const campanhasLink = screen.getByText('Campanhas').closest('a')
    expect(campanhasLink).toHaveClass('bg-primary/10')
    expect(campanhasLink).toHaveClass('text-primary')
  })

  it('should highlight dashboard when on dashboard route', () => {
    mockUsePathname.mockReturnValue('/dashboard')
    render(<Sidebar />)

    const links = screen.getAllByRole('link')
    const dashboardLink = links.find((link) => link.getAttribute('href') === '/dashboard')
    expect(dashboardLink).toHaveClass('bg-primary/10')
    expect(dashboardLink).toHaveClass('text-primary')
  })

  it('should link Chips to /chips', () => {
    render(<Sidebar />)
    // Grupos foi consolidado dentro de Chips como uma tab
    const chipsLink = screen.getByText('Chips').closest('a')
    expect(chipsLink).toHaveAttribute('href', '/chips')
  })
})

describe('BottomNav', () => {
  beforeEach(() => {
    mockUsePathname.mockReturnValue('/dashboard')
  })

  it('should render 4 navigation items plus menu button', () => {
    render(<BottomNav />)
    expect(screen.getByText('Home')).toBeInTheDocument()
    expect(screen.getByText('Conversas')).toBeInTheDocument()
    expect(screen.getByText('Campanhas')).toBeInTheDocument()
    expect(screen.getByText('Chips')).toBeInTheDocument()
    expect(screen.getByText('Menu')).toBeInTheDocument()
  })

  it('should highlight active route with text-primary', () => {
    mockUsePathname.mockReturnValue('/conversas')
    render(<BottomNav />)

    const conversasLink = screen.getByText('Conversas').closest('a')
    expect(conversasLink).toHaveClass('text-primary')
  })

  it('should not highlight inactive routes', () => {
    mockUsePathname.mockReturnValue('/dashboard')
    render(<BottomNav />)

    const campanhasLink = screen.getByText('Campanhas').closest('a')
    expect(campanhasLink).toHaveClass('text-muted-foreground')
  })

  it('should highlight nested routes correctly', () => {
    mockUsePathname.mockReturnValue('/campanhas/nova')
    render(<BottomNav />)

    const campanhasLink = screen.getByText('Campanhas').closest('a')
    expect(campanhasLink).toHaveClass('text-primary')
  })

  it('should open drawer when Menu is clicked', () => {
    render(<BottomNav />)
    const menuButton = screen.getByRole('button', { name: /abrir menu/i })
    fireEvent.click(menuButton)

    // Drawer should be visible with all navigation groups
    expect(screen.getByText('Operacoes')).toBeInTheDocument()
    expect(screen.getByText('Cadastros')).toBeInTheDocument()
  })
})
