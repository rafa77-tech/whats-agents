import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ProcessingQueue } from '@/components/group-entry/processing-queue'

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('ProcessingQueue', () => {
  const mockOnUpdate = vi.fn()

  const mockQueueResponse = {
    queue: [
      {
        id: 'queue-1',
        link_url: 'https://chat.whatsapp.com/ABC123',
        chip_name: 'Chip Julia 01',
        scheduled_at: '2026-01-15T14:30:00Z',
        status: 'queued',
      },
      {
        id: 'queue-2',
        link_url: 'https://chat.whatsapp.com/DEF456',
        chip_name: 'Chip Julia 02',
        scheduled_at: '2026-01-15T15:00:00Z',
        status: 'processing',
      },
    ],
  }

  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockQueueResponse),
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders loading state initially', () => {
    mockFetch.mockImplementation(() => new Promise(() => {}))
    const { container } = render(<ProcessingQueue onUpdate={mockOnUpdate} />)
    expect(container.querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('renders queue items after loading', async () => {
    vi.useRealTimers()
    render(<ProcessingQueue onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      expect(screen.getByText('...ABC123')).toBeInTheDocument()
    })

    expect(screen.getByText('...DEF456')).toBeInTheDocument()
  })

  it('renders chip names', async () => {
    vi.useRealTimers()
    render(<ProcessingQueue onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      expect(screen.getByText('Chip Julia 01')).toBeInTheDocument()
      expect(screen.getByText('Chip Julia 02')).toBeInTheDocument()
    })
  })

  it('renders status badges correctly', async () => {
    vi.useRealTimers()
    render(<ProcessingQueue onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      expect(screen.getByText('Na Fila')).toBeInTheDocument()
      expect(screen.getByText('Processando')).toBeInTheDocument()
    })
  })

  it('renders queue count in description', async () => {
    vi.useRealTimers()
    render(<ProcessingQueue onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      expect(screen.getByText('2 itens na fila')).toBeInTheDocument()
    })
  })

  it('renders empty state when no items', async () => {
    vi.useRealTimers()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ queue: [] }),
    })

    render(<ProcessingQueue onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      expect(screen.getByText('Nenhum item na fila')).toBeInTheDocument()
    })
  })

  it('renders index numbers', async () => {
    vi.useRealTimers()
    render(<ProcessingQueue onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      expect(screen.getByText('1')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
    })
  })

  it('renders refresh button', async () => {
    vi.useRealTimers()
    render(<ProcessingQueue onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      const refreshButton = screen.getByRole('button', { name: '' })
      expect(refreshButton.querySelector('svg.lucide-refresh-cw')).toBeInTheDocument()
    })
  })

  it('calls refresh on button click', async () => {
    vi.useRealTimers()
    const user = userEvent.setup()
    render(<ProcessingQueue onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      expect(screen.getByText('...ABC123')).toBeInTheDocument()
    })

    const refreshButton = screen
      .getAllByRole('button')
      .find((btn) => btn.querySelector('svg.lucide-refresh-cw'))

    if (refreshButton) {
      await user.click(refreshButton)

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(2)
      })
    }
  })

  it('shows action buttons only for queued items', async () => {
    vi.useRealTimers()
    render(<ProcessingQueue onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      expect(screen.getByText('Na Fila')).toBeInTheDocument()
    })

    // Process and Cancel buttons should exist for queued items
    const playButtons = screen
      .getAllByRole('button')
      .filter((btn) => btn.querySelector('svg.lucide-play'))
    const cancelButtons = screen
      .getAllByRole('button')
      .filter((btn) => btn.querySelector('svg.lucide-x'))

    expect(playButtons.length).toBe(1) // Only one queued item
    expect(cancelButtons.length).toBe(1)
  })

  it('handles API error gracefully', async () => {
    vi.useRealTimers()
    mockFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ error: 'Server error' }),
    })

    render(<ProcessingQueue onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      expect(screen.getByText('Nenhum item na fila')).toBeInTheDocument()
    })
  })

  it('sets up auto-refresh interval', async () => {
    const setIntervalSpy = vi.spyOn(global, 'setInterval')

    render(<ProcessingQueue onUpdate={mockOnUpdate} />)

    // Verify setInterval was called with 30 seconds
    expect(setIntervalSpy).toHaveBeenCalledWith(expect.any(Function), 30000)

    setIntervalSpy.mockRestore()
  })

  it('calls onUpdate after process action', async () => {
    vi.useRealTimers()
    const user = userEvent.setup()

    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockQueueResponse),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      })
      .mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockQueueResponse),
      })

    render(<ProcessingQueue onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      expect(screen.getByText('...ABC123')).toBeInTheDocument()
    })

    const processButton = screen
      .getAllByRole('button')
      .find((btn) => btn.querySelector('svg.lucide-play'))

    if (processButton) {
      await user.click(processButton)

      await waitFor(() => {
        expect(mockOnUpdate).toHaveBeenCalled()
      })
    }
  })

  it('calls onUpdate after cancel action', async () => {
    vi.useRealTimers()
    const user = userEvent.setup()

    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockQueueResponse),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      })
      .mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockQueueResponse),
      })

    render(<ProcessingQueue onUpdate={mockOnUpdate} />)

    await waitFor(() => {
      expect(screen.getByText('...ABC123')).toBeInTheDocument()
    })

    const cancelButton = screen
      .getAllByRole('button')
      .find((btn) => btn.querySelector('svg.lucide-x'))

    if (cancelButton) {
      await user.click(cancelButton)

      await waitFor(() => {
        expect(mockOnUpdate).toHaveBeenCalled()
      })
    }
  })
})
