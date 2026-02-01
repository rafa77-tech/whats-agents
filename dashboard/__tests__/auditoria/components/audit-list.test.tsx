/**
 * Testes para AuditList
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AuditList } from '@/app/(dashboard)/auditoria/components/audit-list'

describe('AuditList', () => {
  const mockLogs = [
    {
      id: 'log1',
      action: 'julia_toggle',
      actor_email: 'admin@example.com',
      actor_role: 'admin',
      details: { enabled: true },
      created_at: '2024-01-15T10:00:00Z',
    },
    {
      id: 'log2',
      action: 'manual_handoff',
      actor_email: 'user@example.com',
      actor_role: 'operator',
      details: { conversation_id: 'conv123' },
      created_at: '2024-01-15T11:00:00Z',
    },
  ]

  it('deve renderizar lista de logs', () => {
    const onPageChange = vi.fn()

    render(
      <AuditList logs={mockLogs} total={2} page={1} pages={1} onPageChange={onPageChange} />
    )

    expect(screen.getByText('Toggle Julia')).toBeInTheDocument()
    expect(screen.getByText('Handoff Manual')).toBeInTheDocument()
  })

  it('deve mostrar total de registros', () => {
    const onPageChange = vi.fn()

    render(
      <AuditList logs={mockLogs} total={2} page={1} pages={1} onPageChange={onPageChange} />
    )

    expect(screen.getByText('2 registros')).toBeInTheDocument()
  })

  it('deve mostrar singular para 1 registro', () => {
    const onPageChange = vi.fn()

    render(
      <AuditList
        logs={[mockLogs[0]!]}
        total={1}
        page={1}
        pages={1}
        onPageChange={onPageChange}
      />
    )

    expect(screen.getByText('1 registro')).toBeInTheDocument()
  })

  it('deve mostrar paginacao', () => {
    const onPageChange = vi.fn()

    render(
      <AuditList logs={mockLogs} total={100} page={2} pages={5} onPageChange={onPageChange} />
    )

    expect(screen.getByText('2 / 5')).toBeInTheDocument()
  })

  it('deve chamar onPageChange ao clicar em proxima', () => {
    const onPageChange = vi.fn()

    render(
      <AuditList logs={mockLogs} total={100} page={2} pages={5} onPageChange={onPageChange} />
    )

    const nextButton = screen.getAllByRole('button').find(
      (btn) => btn.querySelector('svg.lucide-chevron-right') !== null
    )

    fireEvent.click(nextButton!)

    expect(onPageChange).toHaveBeenCalledWith(3)
  })

  it('deve chamar onPageChange ao clicar em anterior', () => {
    const onPageChange = vi.fn()

    render(
      <AuditList logs={mockLogs} total={100} page={2} pages={5} onPageChange={onPageChange} />
    )

    const prevButton = screen.getAllByRole('button').find(
      (btn) => btn.querySelector('svg.lucide-chevron-left') !== null
    )

    fireEvent.click(prevButton!)

    expect(onPageChange).toHaveBeenCalledWith(1)
  })

  it('deve desabilitar botao anterior na primeira pagina', () => {
    const onPageChange = vi.fn()

    render(
      <AuditList logs={mockLogs} total={100} page={1} pages={5} onPageChange={onPageChange} />
    )

    const prevButton = screen.getAllByRole('button').find(
      (btn) => btn.querySelector('svg.lucide-chevron-left') !== null
    )

    expect(prevButton).toBeDisabled()
  })

  it('deve desabilitar botao proxima na ultima pagina', () => {
    const onPageChange = vi.fn()

    render(
      <AuditList logs={mockLogs} total={100} page={5} pages={5} onPageChange={onPageChange} />
    )

    const nextButton = screen.getAllByRole('button').find(
      (btn) => btn.querySelector('svg.lucide-chevron-right') !== null
    )

    expect(nextButton).toBeDisabled()
  })

  it('deve mostrar estado vazio quando nao ha logs', () => {
    const onPageChange = vi.fn()

    render(<AuditList logs={[]} total={0} page={1} pages={0} onPageChange={onPageChange} />)

    expect(screen.getByText('Nenhum log encontrado')).toBeInTheDocument()
    expect(screen.getByText(/ajuste os filtros/i)).toBeInTheDocument()
  })
})
