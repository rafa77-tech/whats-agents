/**
 * Testes para AuditFilters
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AuditFilters } from '@/app/(dashboard)/auditoria/components/audit-filters'

describe('AuditFilters', () => {
  const defaultFilters = {
    action: undefined,
    actor_email: undefined,
    from_date: undefined,
    to_date: undefined,
  }

  it('deve renderizar todos os campos de filtro', () => {
    const onApply = vi.fn()
    const onClear = vi.fn()

    render(<AuditFilters filters={defaultFilters} onApply={onApply} onClear={onClear} />)

    expect(screen.getByText('Tipo de Acao')).toBeInTheDocument()
    expect(screen.getByText('Email do Usuario')).toBeInTheDocument()
    expect(screen.getByText('Data Inicio')).toBeInTheDocument()
    expect(screen.getByText('Data Fim')).toBeInTheDocument()
  })

  it('deve ter botao de aplicar', () => {
    const onApply = vi.fn()
    const onClear = vi.fn()

    render(<AuditFilters filters={defaultFilters} onApply={onApply} onClear={onClear} />)

    expect(screen.getByRole('button', { name: /aplicar/i })).toBeInTheDocument()
  })

  it('deve ter botao de limpar', () => {
    const onApply = vi.fn()
    const onClear = vi.fn()

    render(<AuditFilters filters={defaultFilters} onApply={onApply} onClear={onClear} />)

    expect(screen.getByRole('button', { name: /limpar/i })).toBeInTheDocument()
  })

  it('deve chamar onClear ao clicar em limpar', () => {
    const onApply = vi.fn()
    const onClear = vi.fn()

    render(<AuditFilters filters={defaultFilters} onApply={onApply} onClear={onClear} />)

    fireEvent.click(screen.getByRole('button', { name: /limpar/i }))

    expect(onClear).toHaveBeenCalled()
  })

  it('deve chamar onApply ao clicar em aplicar', () => {
    const onApply = vi.fn()
    const onClear = vi.fn()

    render(<AuditFilters filters={defaultFilters} onApply={onApply} onClear={onClear} />)

    fireEvent.click(screen.getByRole('button', { name: /aplicar/i }))

    expect(onApply).toHaveBeenCalled()
  })

  it('deve mostrar filtros existentes', () => {
    const onApply = vi.fn()
    const onClear = vi.fn()
    const filters = {
      actor_email: 'admin@test.com',
      from_date: '2024-01-01',
      to_date: '2024-01-31',
    }

    render(<AuditFilters filters={filters} onApply={onApply} onClear={onClear} />)

    const emailInput = screen.getByPlaceholderText(/usuario@email.com/i) as HTMLInputElement
    expect(emailInput.value).toBe('admin@test.com')
  })

  it('deve permitir digitar email', () => {
    const onApply = vi.fn()
    const onClear = vi.fn()

    render(<AuditFilters filters={defaultFilters} onApply={onApply} onClear={onClear} />)

    const emailInput = screen.getByPlaceholderText(/usuario@email.com/i)
    fireEvent.change(emailInput, { target: { value: 'new@test.com' } })

    fireEvent.click(screen.getByRole('button', { name: /aplicar/i }))

    expect(onApply).toHaveBeenCalledWith(expect.objectContaining({ actor_email: 'new@test.com' }))
  })

  it('deve permitir selecionar data de inicio', () => {
    const onApply = vi.fn()
    const onClear = vi.fn()

    render(<AuditFilters filters={defaultFilters} onApply={onApply} onClear={onClear} />)

    // Inputs do tipo date nao sao textbox no testing-library
    // Vamos buscar por selector direto
    const startDateInput = document.querySelector('input[type="date"]') as HTMLInputElement
    if (startDateInput) {
      fireEvent.change(startDateInput, { target: { value: '2024-01-01' } })
    }

    fireEvent.click(screen.getByRole('button', { name: /aplicar/i }))

    expect(onApply).toHaveBeenCalled()
  })

  it('deve ter opcoes de tipo de acao', () => {
    const onApply = vi.fn()
    const onClear = vi.fn()

    render(<AuditFilters filters={defaultFilters} onApply={onApply} onClear={onClear} />)

    // Verifica que tem o select de tipo de acao
    // O componente usa shadcn Select que renderiza como trigger
    const selectTrigger = screen.getByRole('combobox')
    expect(selectTrigger).toBeInTheDocument()
  })
})
