import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DoctorCard } from '@/app/(dashboard)/medicos/components/doctor-card'
import type { Doctor } from '@/app/(dashboard)/medicos/components/doctor-card'

// Get the mocked router
const mockPush = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
  }),
}))

describe('DoctorCard', () => {
  const mockDoctor: Doctor = {
    id: 'doctor-123',
    nome: 'João Silva',
    telefone: '11999998888',
    especialidade: 'Cardiologia',
    cidade: 'São Paulo',
    stage_jornada: 'novo',
    opt_out: false,
    created_at: '2026-01-01T00:00:00Z',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders doctor name', () => {
    render(<DoctorCard doctor={mockDoctor} />)
    expect(screen.getByText('João Silva')).toBeInTheDocument()
  })

  it('renders doctor initials in avatar', () => {
    render(<DoctorCard doctor={mockDoctor} />)
    expect(screen.getByText('JS')).toBeInTheDocument()
  })

  it('renders phone number', () => {
    render(<DoctorCard doctor={mockDoctor} />)
    expect(screen.getByText('11999998888')).toBeInTheDocument()
  })

  it('renders specialty when provided', () => {
    render(<DoctorCard doctor={mockDoctor} />)
    expect(screen.getByText('Cardiologia')).toBeInTheDocument()
  })

  it('renders city when provided', () => {
    render(<DoctorCard doctor={mockDoctor} />)
    expect(screen.getByText('São Paulo')).toBeInTheDocument()
  })

  it('renders journey stage badge', () => {
    render(<DoctorCard doctor={mockDoctor} />)
    expect(screen.getByText('Novo')).toBeInTheDocument()
  })

  it('renders opt-out badge when opt_out is true', () => {
    const optOutDoctor = { ...mockDoctor, opt_out: true }
    render(<DoctorCard doctor={optOutDoctor} />)
    expect(screen.getByText('Opt-out')).toBeInTheDocument()
  })

  it('does not render opt-out badge when opt_out is false', () => {
    render(<DoctorCard doctor={mockDoctor} />)
    expect(screen.queryByText('Opt-out')).not.toBeInTheDocument()
  })

  it('renders different stage labels', () => {
    const stageMapping = [
      { stage: 'respondeu', label: 'Respondeu' },
      { stage: 'negociando', label: 'Negociando' },
      { stage: 'convertido', label: 'Convertido' },
      { stage: 'perdido', label: 'Perdido' },
    ]

    stageMapping.forEach(({ stage, label }) => {
      const doctor = { ...mockDoctor, stage_jornada: stage }
      const { unmount } = render(<DoctorCard doctor={doctor} />)
      expect(screen.getByText(label)).toBeInTheDocument()
      unmount()
    })
  })

  it('handles English stage names', () => {
    const doctor = { ...mockDoctor, stage_jornada: 'engaged' }
    render(<DoctorCard doctor={doctor} />)
    expect(screen.getByText('Engajado')).toBeInTheDocument()
  })

  it('navigates to doctor profile on click', async () => {
    const user = userEvent.setup()
    render(<DoctorCard doctor={mockDoctor} />)

    const card = screen.getByText('João Silva').closest('[class*="cursor-pointer"]')
    if (card) {
      await user.click(card)
      expect(mockPush).toHaveBeenCalledWith('/medicos/doctor-123')
    }
  })

  it('handles doctor without specialty', () => {
    const { especialidade: _, ...restDoctor } = mockDoctor
    render(<DoctorCard doctor={restDoctor} />)
    expect(screen.queryByText('Cardiologia')).not.toBeInTheDocument()
  })

  it('handles doctor without city', () => {
    const { cidade: _, ...restDoctor } = mockDoctor
    render(<DoctorCard doctor={restDoctor} />)
    expect(screen.queryByText('São Paulo')).not.toBeInTheDocument()
  })

  it('handles unknown stage gracefully', () => {
    const doctorUnknownStage = { ...mockDoctor, stage_jornada: 'custom_stage' }
    render(<DoctorCard doctor={doctorUnknownStage} />)
    expect(screen.getByText('custom_stage')).toBeInTheDocument()
  })

  it('handles single-word name', () => {
    const doctorSingleName = { ...mockDoctor, nome: 'João' }
    render(<DoctorCard doctor={doctorSingleName} />)
    expect(screen.getByText('J')).toBeInTheDocument()
  })
})
