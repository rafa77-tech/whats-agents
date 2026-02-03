/**
 * Testes para Sidebar Navigation
 *
 * Sprint 45: Testes de navegacao da sidebar desktop
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/dashboard',
}))

// Mock next/link
vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}))

describe('Sidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renderiza todos os grupos de navegacao', async () => {
    const { Sidebar } = await import('@/components/dashboard/sidebar')
    render(<Sidebar />)

    // Verificar grupos
    expect(screen.getByText('Operacoes')).toBeInTheDocument()
    expect(screen.getByText('Cadastros')).toBeInTheDocument()
    expect(screen.getByText('WhatsApp')).toBeInTheDocument()
    expect(screen.getByText('Monitoramento')).toBeInTheDocument()
    expect(screen.getByText('Qualidade')).toBeInTheDocument()
  })

  it('renderiza itens de Operacoes', async () => {
    const { Sidebar } = await import('@/components/dashboard/sidebar')
    render(<Sidebar />)

    expect(screen.getByText('Conversas')).toBeInTheDocument()
    expect(screen.getByText('Campanhas')).toBeInTheDocument()
    expect(screen.getByText('Vagas')).toBeInTheDocument()
    expect(screen.getByText('Instrucoes')).toBeInTheDocument()
  })

  it('renderiza itens de Cadastros', async () => {
    const { Sidebar } = await import('@/components/dashboard/sidebar')
    render(<Sidebar />)

    expect(screen.getByText('Medicos')).toBeInTheDocument()
    expect(screen.getByText('Hospitais')).toBeInTheDocument()
  })

  it('renderiza itens de WhatsApp', async () => {
    const { Sidebar } = await import('@/components/dashboard/sidebar')
    render(<Sidebar />)

    // Chips e uma entrada unica; Grupos agora e uma tab dentro de /chips
    expect(screen.getByText('Chips')).toBeInTheDocument()

    // Verificar que Chips aponta para /chips
    const chipsLink = screen.getByText('Chips').closest('a')
    expect(chipsLink).toHaveAttribute('href', '/chips')
  })

  it('renderiza itens de Monitoramento', async () => {
    const { Sidebar } = await import('@/components/dashboard/sidebar')
    render(<Sidebar />)

    expect(screen.getByText('Monitor')).toBeInTheDocument()
    expect(screen.getByText('Health')).toBeInTheDocument()
    expect(screen.getByText('Integridade')).toBeInTheDocument()
    expect(screen.getByText('Metricas')).toBeInTheDocument()
  })

  it('renderiza itens de Qualidade', async () => {
    const { Sidebar } = await import('@/components/dashboard/sidebar')
    render(<Sidebar />)

    expect(screen.getByText('Avaliacoes')).toBeInTheDocument()
    expect(screen.getByText('Auditoria')).toBeInTheDocument()
  })

  it('renderiza itens do footer separadamente', async () => {
    const { Sidebar } = await import('@/components/dashboard/sidebar')
    render(<Sidebar />)

    // Instrucoes foi movido para Operacoes
    expect(screen.getByText('Sistema')).toBeInTheDocument()
    expect(screen.getByText('Ajuda')).toBeInTheDocument()
  })

  it('renderiza logo Jull.ia no header', async () => {
    const { Sidebar } = await import('@/components/dashboard/sidebar')
    render(<Sidebar />)

    expect(screen.getByText('J')).toBeInTheDocument()
    expect(screen.getByText('Jull.ia')).toBeInTheDocument()
  })

  it('renderiza botao Sair no footer', async () => {
    const { Sidebar } = await import('@/components/dashboard/sidebar')
    render(<Sidebar />)

    expect(screen.getByText('Sair')).toBeInTheDocument()
  })

  it('Dashboard aparece no topo sem label de grupo', async () => {
    const { Sidebar } = await import('@/components/dashboard/sidebar')
    render(<Sidebar />)

    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    // Dashboard deve ter link para /dashboard
    const dashboardLink = screen.getByText('Dashboard').closest('a')
    expect(dashboardLink).toHaveAttribute('href', '/dashboard')
  })
})
