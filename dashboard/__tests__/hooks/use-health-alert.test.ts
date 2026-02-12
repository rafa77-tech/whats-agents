/**
 * Testes para hooks/use-health-alert
 */

import { renderHook } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { useHealthAlert, type HealthStatus } from '@/hooks/use-health-alert'

describe('useHealthAlert', () => {
  it('deve pular callbacks no primeiro render', () => {
    const onStatusChange = vi.fn()
    const onCritical = vi.fn()
    const onRecovery = vi.fn()

    renderHook(() => useHealthAlert('critical', { onStatusChange, onCritical, onRecovery }))

    expect(onStatusChange).not.toHaveBeenCalled()
    expect(onCritical).not.toHaveBeenCalled()
    expect(onRecovery).not.toHaveBeenCalled()
  })

  it('deve retornar early quando currentStatus é null', () => {
    const onStatusChange = vi.fn()

    const { rerender } = renderHook(
      ({ status }: { status: HealthStatus | null }) => useHealthAlert(status, { onStatusChange }),
      { initialProps: { status: 'healthy' as HealthStatus | null } }
    )

    rerender({ status: null })

    expect(onStatusChange).not.toHaveBeenCalled()
  })

  it('deve chamar onStatusChange quando status muda', () => {
    const onStatusChange = vi.fn()

    const { rerender } = renderHook(
      ({ status }: { status: HealthStatus | null }) => useHealthAlert(status, { onStatusChange }),
      { initialProps: { status: 'healthy' as HealthStatus | null } }
    )

    rerender({ status: 'degraded' })

    expect(onStatusChange).toHaveBeenCalledWith('healthy', 'degraded')
  })

  it('deve chamar onCritical quando transiciona para critical', () => {
    const onCritical = vi.fn()

    const { rerender } = renderHook(
      ({ status }: { status: HealthStatus | null }) => useHealthAlert(status, { onCritical }),
      { initialProps: { status: 'healthy' as HealthStatus | null } }
    )

    rerender({ status: 'critical' })

    expect(onCritical).toHaveBeenCalledTimes(1)
  })

  it('deve chamar onRecovery quando sai de critical', () => {
    const onRecovery = vi.fn()

    const { rerender } = renderHook(
      ({ status }: { status: HealthStatus | null }) => useHealthAlert(status, { onRecovery }),
      { initialProps: { status: 'critical' as HealthStatus | null } }
    )

    rerender({ status: 'healthy' })

    expect(onRecovery).toHaveBeenCalledTimes(1)
  })

  it('nao deve chamar onCritical/onRecovery para transicoes nao-criticas', () => {
    const onCritical = vi.fn()
    const onRecovery = vi.fn()

    const { rerender } = renderHook(
      ({ status }: { status: HealthStatus | null }) =>
        useHealthAlert(status, { onCritical, onRecovery }),
      { initialProps: { status: 'healthy' as HealthStatus | null } }
    )

    rerender({ status: 'degraded' })

    expect(onCritical).not.toHaveBeenCalled()
    expect(onRecovery).not.toHaveBeenCalled()
  })

  it('deve retornar isCritical=true quando status é critical', () => {
    const { result } = renderHook(() => useHealthAlert('critical'))

    expect(result.current.isCritical).toBe(true)
  })

  it('deve retornar isCritical=false quando status nao é critical', () => {
    const { result } = renderHook(() => useHealthAlert('healthy'))

    expect(result.current.isCritical).toBe(false)
  })

  it('deve retornar wasCritical=true apos sair de critical', () => {
    const { result, rerender } = renderHook(
      ({ status }: { status: HealthStatus | null }) => useHealthAlert(status),
      { initialProps: { status: 'critical' as HealthStatus | null } }
    )

    rerender({ status: 'healthy' })

    expect(result.current.wasCritical).toBe(true)
  })

  it('deve retornar isTransition=true quando status muda', () => {
    const { result, rerender } = renderHook(
      ({ status }: { status: HealthStatus | null }) => useHealthAlert(status),
      { initialProps: { status: 'healthy' as HealthStatus | null } }
    )

    rerender({ status: 'degraded' })

    expect(result.current.isTransition).toBe(true)
  })

  it('deve retornar isTransition=false quando status nao muda', () => {
    const { result, rerender } = renderHook(
      ({ status }: { status: HealthStatus | null }) => useHealthAlert(status),
      { initialProps: { status: 'healthy' as HealthStatus | null } }
    )

    rerender({ status: 'healthy' })

    expect(result.current.isTransition).toBe(false)
  })

  it('deve funcionar sem opcoes (defaults)', () => {
    const { result } = renderHook(() => useHealthAlert('healthy'))

    expect(result.current.isCritical).toBe(false)
    expect(result.current.wasCritical).toBe(false)
  })

  it('nao deve chamar callbacks quando prev é null e status muda', () => {
    const onStatusChange = vi.fn()

    const { rerender } = renderHook(
      ({ status }: { status: HealthStatus | null }) => useHealthAlert(status, { onStatusChange }),
      { initialProps: { status: null as HealthStatus | null } }
    )

    // On first render, prev is null. After rerender, prev is still null (set from first render).
    // But isFirstRender is now false, so the check `prev !== null && prev !== currentStatus` applies.
    // prev is null, so the condition is false -> no callback
    rerender({ status: 'healthy' })

    expect(onStatusChange).not.toHaveBeenCalled()
  })
})
