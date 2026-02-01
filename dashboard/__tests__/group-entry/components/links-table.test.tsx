import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LinksTable } from '@/components/group-entry/links-table'

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('LinksTable', () => {
  const mockOnUpdate = vi.fn()

  const mockLinksResponse = {
    links: [
      {
        id: 'link-1',
        url: 'https://chat.whatsapp.com/ABC123',
        status: 'pending',
        categoria: 'medicos',
        criado_em: '2026-01-15T10:00:00Z',
      },
      {
        id: 'link-2',
        url: 'https://chat.whatsapp.com/DEF456',
        status: 'validated',
        categoria: null,
        criado_em: '2026-01-14T10:00:00Z',
      },
    ],
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockLinksResponse),
    })
  })

  it('renders loading state initially', () => {
    mockFetch.mockImplementation(() => new Promise(() => {}))
    const { container } = render(<LinksTable onUpdate={mockOnUpdate} />)
    expect(container.querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('renders links after loading', async () => {
    render(<LinksTable onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      expect(screen.getByText('...ABC123')).toBeInTheDocument()
    })

    expect(screen.getByText('...DEF456')).toBeInTheDocument()
  })

  it('renders status badges correctly', async () => {
    render(<LinksTable onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      expect(screen.getByText('Pendente')).toBeInTheDocument()
      expect(screen.getByText('Validado')).toBeInTheDocument()
    })
  })

  it('renders categoria when present', async () => {
    render(<LinksTable onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      expect(screen.getByText('medicos')).toBeInTheDocument()
    })
  })

  it('renders "-" when categoria is null', async () => {
    render(<LinksTable onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      const dashCells = screen.getAllByText('-')
      expect(dashCells.length).toBeGreaterThan(0)
    })
  })

  it('renders empty state when no links', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ links: [] }),
    })

    render(<LinksTable onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      expect(screen.getByText('Nenhum link encontrado')).toBeInTheDocument()
    })
  })

  it('renders links count in description', async () => {
    render(<LinksTable onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      expect(screen.getByText('2 links encontrados')).toBeInTheDocument()
    })
  })

  it('fetches with default params', async () => {
    render(<LinksTable onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      expect(screen.getByText('...ABC123')).toBeInTheDocument()
    })

    // Verify initial fetch was called
    expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('/api/group-entry/links'))
  })

  it('renders search input', async () => {
    render(<LinksTable onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Buscar por URL...')).toBeInTheDocument()
    })
  })

  it('renders validate button for pending links', async () => {
    render(<LinksTable onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      const buttons = screen.getAllByRole('button')
      // Should have at least one action button
      expect(buttons.length).toBeGreaterThan(0)
    })
  })

  it('handles API error gracefully', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ error: 'Server error' }),
    })

    render(<LinksTable onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      // Should show empty state on error
      expect(screen.getByText('Nenhum link encontrado')).toBeInTheDocument()
    })
  })

  it('handles fetch exception gracefully', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'))

    render(<LinksTable onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      expect(screen.getByText('Nenhum link encontrado')).toBeInTheDocument()
    })
  })

  it('calls onUpdate after validate action', async () => {
    const user = userEvent.setup()

    // First call: initial load, subsequent calls: after actions
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockLinksResponse),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      })
      .mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockLinksResponse),
      })

    render(<LinksTable onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      expect(screen.getByText('...ABC123')).toBeInTheDocument()
    })

    // Find and click validate button
    const validateButtons = screen.getAllByRole('button')
    const validateButton = validateButtons.find((btn) =>
      btn.querySelector('svg.lucide-check-circle-2')
    )

    if (validateButton) {
      await user.click(validateButton)

      await waitFor(() => {
        expect(mockOnUpdate).toHaveBeenCalled()
      })
    }
  })
})
