import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DoctorStats } from '@/app/(dashboard)/medicos/components/doctor-stats'

describe('DoctorStats', () => {
  const mockDoctor = {
    id: 'doctor-123',
    nome: 'João Silva',
    stage_jornada: 'novo',
    pressure_score_atual: 75,
    contexto_consolidado: 'Médico interessado em plantões noturnos',
    conversations_count: 5,
    last_interaction_at: '2026-01-15T12:00:00Z',
    created_at: '2025-12-01T12:00:00Z',
  }

  it('renders conversations count', () => {
    render(<DoctorStats doctor={mockDoctor} />)
    expect(screen.getByText('Conversas')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
  })

  it('renders pressure score', () => {
    render(<DoctorStats doctor={mockDoctor} />)
    expect(screen.getByText('Pressure Score')).toBeInTheDocument()
    expect(screen.getByText('75')).toBeInTheDocument()
  })

  it('renders N/A when pressure score is not available', () => {
    const { pressure_score_atual: _, ...restDoctor } = mockDoctor
    render(<DoctorStats doctor={restDoctor} />)
    expect(screen.getByText('N/A')).toBeInTheDocument()
  })

  it('renders registration date', () => {
    render(<DoctorStats doctor={mockDoctor} />)
    expect(screen.getByText('Cadastro')).toBeInTheDocument()
    // Should show formatted date like "01/12/2025"
    expect(screen.getByText('01/12/2025')).toBeInTheDocument()
  })

  it('renders last interaction date', () => {
    render(<DoctorStats doctor={mockDoctor} />)
    expect(screen.getByText('Ultima Interacao')).toBeInTheDocument()
    expect(screen.getByText('15/01/2026')).toBeInTheDocument()
  })

  it('shows Nunca when no last interaction', () => {
    const { last_interaction_at: _, ...restDoctor } = mockDoctor
    render(<DoctorStats doctor={restDoctor} />)
    expect(screen.getByText('Nunca')).toBeInTheDocument()
  })

  it('renders consolidated context when available', () => {
    render(<DoctorStats doctor={mockDoctor} />)
    expect(screen.getByText('Contexto Consolidado')).toBeInTheDocument()
    expect(screen.getByText('Médico interessado em plantões noturnos')).toBeInTheDocument()
  })

  it('does not render context section when not available', () => {
    const { contexto_consolidado: _, ...restDoctor } = mockDoctor
    render(<DoctorStats doctor={restDoctor} />)
    expect(screen.queryByText('Contexto Consolidado')).not.toBeInTheDocument()
  })

  it('renders stat descriptions', () => {
    render(<DoctorStats doctor={mockDoctor} />)
    expect(screen.getByText('Total de conversas')).toBeInTheDocument()
    expect(screen.getByText('Indice de saturacao')).toBeInTheDocument()
    expect(screen.getByText('Data de cadastro')).toBeInTheDocument()
    expect(screen.getByText('Ultimo contato')).toBeInTheDocument()
  })
})
