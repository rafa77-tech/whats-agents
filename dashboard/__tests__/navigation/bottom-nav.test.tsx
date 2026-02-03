/**
 * Testes para Bottom Nav
 *
 * Sprint 45: Testes de navegacao mobile (bottom nav)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/dashboard',
}))

// Mock next/link with onClick and className support
vi.mock('next/link', () => ({
  default: ({
    children,
    href,
    onClick,
    className,
  }: {
    children: React.ReactNode
    href: string
    onClick?: () => void
    className?: string
  }) => (
    <a href={href} onClick={onClick} className={className}>
      {children}
    </a>
  ),
}))

describe('BottomNav', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renderiza 4 itens de navegacao mais botao de menu', async () => {
    const { BottomNav } = await import('@/components/dashboard/bottom-nav')
    render(<BottomNav />)

    // Deve ter 4 links de navegacao
    expect(screen.getByText('Home')).toBeInTheDocument()
    expect(screen.getByText('Conversas')).toBeInTheDocument()
    expect(screen.getByText('Campanhas')).toBeInTheDocument()
    expect(screen.getByText('Chips')).toBeInTheDocument()

    // E o botao de menu
    expect(screen.getByText('Menu')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /abrir menu/i })).toBeInTheDocument()
  })

  it('inclui Conversas na navegacao', async () => {
    const { BottomNav } = await import('@/components/dashboard/bottom-nav')
    render(<BottomNav />)

    const conversasLink = screen.getByText('Conversas').closest('a')
    expect(conversasLink).toHaveAttribute('href', '/conversas')
  })

  it('Home aponta para /dashboard', async () => {
    const { BottomNav } = await import('@/components/dashboard/bottom-nav')
    render(<BottomNav />)

    const homeLink = screen.getByText('Home').closest('a')
    expect(homeLink).toHaveAttribute('href', '/dashboard')
  })

  it('abre drawer quando Menu e clicado', async () => {
    const { BottomNav } = await import('@/components/dashboard/bottom-nav')
    render(<BottomNav />)

    const menuButton = screen.getByRole('button', { name: /abrir menu/i })
    fireEvent.click(menuButton)

    // Apos clicar, o drawer deve estar visivel
    // Como o drawer usa Sheet do shadcn, verificamos se ele aparece
    // O drawer mostra grupos como "Operacoes", "Cadastros" etc
    expect(await screen.findByText('Operacoes')).toBeInTheDocument()
  })

  it('destaca item ativo corretamente', async () => {
    // Note: Como usePathname retorna /dashboard no mock,
    // apenas o Home deve estar ativo
    const { BottomNav } = await import('@/components/dashboard/bottom-nav')
    render(<BottomNav />)

    // Verificar que Home tem classe flex (todos os items tem)
    const homeLink = screen.getByText('Home').closest('a')
    expect(homeLink).toHaveClass('flex')

    // Conversas nao deve estar ativo (pathname=/dashboard)
    const conversasLink = screen.getByText('Conversas').closest('a')
    expect(conversasLink).toHaveClass('flex')
    expect(conversasLink).toHaveClass('text-muted-foreground')
  })
})

describe('MobileDrawer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renderiza todos os grupos de navegacao', async () => {
    const { MobileDrawer } = await import('@/components/dashboard/mobile-drawer')
    render(<MobileDrawer open={true} onOpenChange={() => {}} />)

    expect(screen.getByText('Operacoes')).toBeInTheDocument()
    expect(screen.getByText('Cadastros')).toBeInTheDocument()
    expect(screen.getByText('WhatsApp')).toBeInTheDocument()
    expect(screen.getByText('Monitoramento')).toBeInTheDocument()
    expect(screen.getByText('Qualidade')).toBeInTheDocument()
    expect(screen.getByText('Configuracao')).toBeInTheDocument()
  })

  it('Chips aponta para /chips', async () => {
    const { MobileDrawer } = await import('@/components/dashboard/mobile-drawer')
    render(<MobileDrawer open={true} onOpenChange={() => {}} />)

    // Grupos foi consolidado dentro de Chips como uma tab
    const chipsLink = screen.getByText('Chips').closest('a')
    expect(chipsLink).toHaveAttribute('href', '/chips')
  })

  it('fecha ao clicar em item', async () => {
    const onOpenChange = vi.fn()
    const { MobileDrawer } = await import('@/components/dashboard/mobile-drawer')
    render(<MobileDrawer open={true} onOpenChange={onOpenChange} />)

    // Clicar no link do Dashboard
    const dashboardLink = screen.getByRole('link', { name: /dashboard/i })
    fireEvent.click(dashboardLink)

    // O onClick do Link chama onOpenChange(false)
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('renderiza botao Sair', async () => {
    const { MobileDrawer } = await import('@/components/dashboard/mobile-drawer')
    render(<MobileDrawer open={true} onOpenChange={() => {}} />)

    expect(screen.getByText('Sair')).toBeInTheDocument()
  })

  it('mostra logo Jull.ia no header', async () => {
    const { MobileDrawer } = await import('@/components/dashboard/mobile-drawer')
    render(<MobileDrawer open={true} onOpenChange={() => {}} />)

    expect(screen.getByText('J')).toBeInTheDocument()
    expect(screen.getByText('Menu')).toBeInTheDocument()
  })
})
