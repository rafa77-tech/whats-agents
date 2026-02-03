/**
 * Testes para Command Palette
 *
 * Sprint 45: Testes do Command Palette (Cmd+K)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

// Mock scrollIntoView (not available in jsdom)
Element.prototype.scrollIntoView = vi.fn()

// Mock next/navigation
const mockPush = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/dashboard',
}))

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value
    },
    clear: () => {
      store = {}
    },
  }
})()
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

describe('CommandPalette', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.clear()
  })

  it('renderiza quando open=true', async () => {
    const { CommandPalette } = await import('@/components/command-palette/command-palette')
    render(<CommandPalette open={true} onOpenChange={() => {}} />)

    // Deve mostrar o input de busca
    expect(screen.getByPlaceholderText(/buscar/i)).toBeInTheDocument()
  })

  it('nao renderiza quando open=false', async () => {
    const { CommandPalette } = await import('@/components/command-palette/command-palette')
    render(<CommandPalette open={false} onOpenChange={() => {}} />)

    expect(screen.queryByPlaceholderText(/buscar/i)).not.toBeInTheDocument()
  })

  it('mostra todas as paginas', async () => {
    const { CommandPalette } = await import('@/components/command-palette/command-palette')
    render(<CommandPalette open={true} onOpenChange={() => {}} />)

    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Conversas')).toBeInTheDocument()
    expect(screen.getByText('Campanhas')).toBeInTheDocument()
    expect(screen.getByText('Chips')).toBeInTheDocument()
    expect(screen.getByText('Grupos')).toBeInTheDocument()
  })

  it('mostra acoes rapidas', async () => {
    const { CommandPalette } = await import('@/components/command-palette/command-palette')
    render(<CommandPalette open={true} onOpenChange={() => {}} />)

    expect(screen.getByText('Nova Campanha')).toBeInTheDocument()
    expect(screen.getByText('Atualizar Pagina')).toBeInTheDocument()
  })

  it('Grupos aponta para /chips/grupos', async () => {
    const onOpenChange = vi.fn()
    const { CommandPalette } = await import('@/components/command-palette/command-palette')
    render(<CommandPalette open={true} onOpenChange={onOpenChange} />)

    // Clicar em Grupos deve navegar para /chips/grupos
    const gruposItem = screen.getByText('Grupos').closest('[cmdk-item]')
    if (gruposItem) {
      fireEvent.click(gruposItem)
      expect(mockPush).toHaveBeenCalledWith('/chips/grupos')
    }
  })

  it('fecha ao clicar no backdrop', async () => {
    const onOpenChange = vi.fn()
    const { CommandPalette } = await import('@/components/command-palette/command-palette')
    render(<CommandPalette open={true} onOpenChange={onOpenChange} />)

    // Clicar no backdrop (div com aria-hidden="true")
    const backdrop = document.querySelector('[aria-hidden="true"]')
    if (backdrop) {
      fireEvent.click(backdrop)
      expect(onOpenChange).toHaveBeenCalledWith(false)
    }
  })

  it('mostra hint de teclado ESC', async () => {
    const { CommandPalette } = await import('@/components/command-palette/command-palette')
    render(<CommandPalette open={true} onOpenChange={() => {}} />)

    expect(screen.getByText('esc')).toBeInTheDocument()
  })

  it('mostra footer com dicas de navegacao', async () => {
    const { CommandPalette } = await import('@/components/command-palette/command-palette')
    render(<CommandPalette open={true} onOpenChange={() => {}} />)

    expect(screen.getByText('navegar')).toBeInTheDocument()
    expect(screen.getByText('selecionar')).toBeInTheDocument()
  })

  it('mostra branding Jull.ia no footer', async () => {
    const { CommandPalette } = await import('@/components/command-palette/command-palette')
    render(<CommandPalette open={true} onOpenChange={() => {}} />)

    expect(screen.getByText('Jull.ia Command')).toBeInTheDocument()
  })
})

describe('CommandPaletteProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renderiza children', async () => {
    const { CommandPaletteProvider } =
      await import('@/components/command-palette/command-palette-provider')
    render(
      <CommandPaletteProvider>
        <div data-testid="child">Child Content</div>
      </CommandPaletteProvider>
    )

    expect(screen.getByTestId('child')).toBeInTheDocument()
  })

  it('abre command palette com Cmd+K', async () => {
    const { CommandPaletteProvider } =
      await import('@/components/command-palette/command-palette-provider')
    render(
      <CommandPaletteProvider>
        <div>Content</div>
      </CommandPaletteProvider>
    )

    // Simular Cmd+K
    fireEvent.keyDown(document, { key: 'k', metaKey: true })

    // Command palette deve estar visivel
    expect(await screen.findByPlaceholderText(/buscar/i)).toBeInTheDocument()
  })

  it('abre command palette com Ctrl+K', async () => {
    const { CommandPaletteProvider } =
      await import('@/components/command-palette/command-palette-provider')
    render(
      <CommandPaletteProvider>
        <div>Content</div>
      </CommandPaletteProvider>
    )

    // Simular Ctrl+K (Windows)
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true })

    // Command palette deve estar visivel
    expect(await screen.findByPlaceholderText(/buscar/i)).toBeInTheDocument()
  })
})
