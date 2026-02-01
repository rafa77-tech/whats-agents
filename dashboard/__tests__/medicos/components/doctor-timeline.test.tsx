import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { DoctorTimeline } from '@/app/(dashboard)/medicos/components/doctor-timeline'

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('DoctorTimeline', () => {
  const mockEvents = [
    {
      id: 'event-1',
      type: 'message_sent',
      title: 'Mensagem enviada',
      description: 'Olá, tudo bem?',
      created_at: '2026-01-15T14:30:00Z',
    },
    {
      id: 'event-2',
      type: 'message_received',
      title: 'Resposta recebida',
      description: 'Tudo ótimo!',
      created_at: '2026-01-15T14:35:00Z',
    },
    {
      id: 'event-3',
      type: 'handoff',
      title: 'Transferido para humano',
      created_at: '2026-01-15T14:40:00Z',
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ events: mockEvents }),
    })
  })

  it('shows loading skeleton initially', () => {
    render(<DoctorTimeline doctorId="doctor-123" />)
    // Skeleton components should be present
    const container = document.querySelector('.space-y-4')
    expect(container).toBeInTheDocument()
  })

  it('fetches timeline from API', async () => {
    render(<DoctorTimeline doctorId="doctor-123" />)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/medicos/doctor-123/timeline')
    })
  })

  it('renders events after loading', async () => {
    render(<DoctorTimeline doctorId="doctor-123" />)

    await waitFor(() => {
      expect(screen.getByText('Mensagem enviada')).toBeInTheDocument()
      expect(screen.getByText('Resposta recebida')).toBeInTheDocument()
      expect(screen.getByText('Transferido para humano')).toBeInTheDocument()
    })
  })

  it('renders event descriptions', async () => {
    render(<DoctorTimeline doctorId="doctor-123" />)

    await waitFor(() => {
      expect(screen.getByText('Olá, tudo bem?')).toBeInTheDocument()
      expect(screen.getByText('Tudo ótimo!')).toBeInTheDocument()
    })
  })

  it('shows empty state when no events', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ events: [] }),
    })

    render(<DoctorTimeline doctorId="doctor-123" />)

    await waitFor(() => {
      expect(screen.getByText('Nenhuma interacao registrada')).toBeInTheDocument()
    })
  })

  it('handles API error gracefully', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
    })

    render(<DoctorTimeline doctorId="doctor-123" />)

    await waitFor(() => {
      expect(screen.getByText('Nenhuma interacao registrada')).toBeInTheDocument()
    })
  })

  it('renders formatted dates', async () => {
    render(<DoctorTimeline doctorId="doctor-123" />)

    await waitFor(() => {
      // Should show formatted dates like "15/01 as HH:mm"
      const dateElements = screen.getAllByText(/15\/01/)
      expect(dateElements.length).toBeGreaterThanOrEqual(3)
    })
  })
})
