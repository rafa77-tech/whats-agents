/**
 * Testes para AuditItem
 */

import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AuditItem } from '@/app/(dashboard)/auditoria/components/audit-item'

describe('AuditItem', () => {
  const mockLog = {
    id: 'log1',
    action: 'julia_toggle',
    actor_email: 'admin@example.com',
    actor_role: 'admin',
    details: { enabled: true, reason: 'Test toggle' },
    created_at: '2024-01-15T14:30:00Z',
  }

  it('deve renderizar action label', () => {
    render(<AuditItem log={mockLog} />)

    expect(screen.getByText('Toggle Julia')).toBeInTheDocument()
  })

  it('deve renderizar email do ator', () => {
    render(<AuditItem log={mockLog} />)

    expect(screen.getByText('admin@example.com')).toBeInTheDocument()
  })

  it('deve renderizar role do ator', () => {
    render(<AuditItem log={mockLog} />)

    expect(screen.getByText('admin')).toBeInTheDocument()
  })

  it('deve renderizar data formatada', () => {
    render(<AuditItem log={mockLog} />)

    // Formato: dd/MM HH:mm
    const dateElement = screen.getByText(/\d{2}\/\d{2} \d{2}:\d{2}/)
    expect(dateElement).toBeInTheDocument()
  })

  it('deve expandir detalhes ao clicar', () => {
    render(<AuditItem log={mockLog} />)

    // Inicialmente, detalhes nao devem estar visiveis
    expect(screen.queryByText('Detalhes')).not.toBeInTheDocument()

    // Clicar no item
    const button = screen.getByRole('button')
    fireEvent.click(button)

    // Agora detalhes devem estar visiveis
    expect(screen.getByText('Detalhes')).toBeInTheDocument()
    expect(screen.getByText(/enabled/)).toBeInTheDocument()
    expect(screen.getByText(/reason/)).toBeInTheDocument()
  })

  it('deve colapsar detalhes ao clicar novamente', () => {
    render(<AuditItem log={mockLog} />)

    const button = screen.getByRole('button')

    // Expandir
    fireEvent.click(button)
    expect(screen.getByText('Detalhes')).toBeInTheDocument()

    // Colapsar
    fireEvent.click(button)
    expect(screen.queryByText('Detalhes')).not.toBeInTheDocument()
  })

  it('deve mostrar icone correto para action conhecida', () => {
    render(<AuditItem log={mockLog} />)

    // Power icon para julia_toggle
    const svg = document.querySelector('svg.lucide-power')
    expect(svg).toBeInTheDocument()
  })

  it('deve mostrar icone padrao para action desconhecida', () => {
    const unknownLog = { ...mockLog, action: 'unknown_action' }
    render(<AuditItem log={unknownLog} />)

    // Settings icon como fallback
    const svg = document.querySelector('svg.lucide-settings')
    expect(svg).toBeInTheDocument()
  })

  it('deve mostrar action original quando label nao existe', () => {
    const unknownLog = { ...mockLog, action: 'custom_action' }
    render(<AuditItem log={unknownLog} />)

    expect(screen.getByText('custom_action')).toBeInTheDocument()
  })

  it('deve formatar detalhes como JSON', () => {
    render(<AuditItem log={mockLog} />)

    const button = screen.getByRole('button')
    fireEvent.click(button)

    // Verifica que JSON esta formatado (pre tag com whitespace)
    const preElement = document.querySelector('pre')
    expect(preElement).toBeInTheDocument()
    expect(preElement?.textContent).toContain('"enabled"')
  })
})
