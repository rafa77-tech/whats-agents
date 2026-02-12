/**
 * Testes para hooks/use-tab-alert
 */

import { renderHook } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useTabAlert, useFaviconAlert } from '@/hooks/use-tab-alert'

describe('useTabAlert', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    document.title = 'Julia Dashboard'
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('deve iniciar blink quando enabled=true', () => {
    renderHook(() =>
      useTabAlert({
        enabled: true,
        originalTitle: 'Julia Dashboard',
        alertTitle: '🔴 ALERTA',
        blinkInterval: 1000,
      })
    )

    // Avanca timer para ativar o primeiro blink
    vi.advanceTimersByTime(1000)
    expect(document.title).toBe('🔴 ALERTA')

    // Avanca para o segundo blink (volta ao original)
    vi.advanceTimersByTime(1000)
    expect(document.title).toBe('Julia Dashboard')
  })

  it('deve restaurar titulo quando enabled=false', () => {
    const { rerender } = renderHook(
      ({ enabled }: { enabled: boolean }) =>
        useTabAlert({
          enabled,
          originalTitle: 'Julia Dashboard',
          alertTitle: '🔴 ALERTA',
        }),
      { initialProps: { enabled: true } }
    )

    vi.advanceTimersByTime(1000)
    expect(document.title).toBe('🔴 ALERTA')

    rerender({ enabled: false })

    expect(document.title).toBe('Julia Dashboard')
  })

  it('deve limpar interval ao desabilitar', () => {
    const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval')

    const { rerender } = renderHook(
      ({ enabled }: { enabled: boolean }) =>
        useTabAlert({
          enabled,
          originalTitle: 'Julia Dashboard',
          alertTitle: '🔴 ALERTA',
        }),
      { initialProps: { enabled: true } }
    )

    rerender({ enabled: false })

    expect(clearIntervalSpy).toHaveBeenCalled()
    clearIntervalSpy.mockRestore()
  })

  it('deve restaurar titulo no cleanup (unmount)', () => {
    const { unmount } = renderHook(() =>
      useTabAlert({
        enabled: true,
        originalTitle: 'Original Title',
        alertTitle: '🔴 ALERTA',
      })
    )

    vi.advanceTimersByTime(1000)
    expect(document.title).toBe('🔴 ALERTA')

    unmount()

    expect(document.title).toBe('Original Title')
  })

  it('deve usar valores default quando nao fornecidos', () => {
    renderHook(() => useTabAlert({ enabled: true }))

    vi.advanceTimersByTime(1000)
    // Default alertTitle
    expect(document.title).toBe('🔴 ALERTA - Julia Dashboard')
  })

  it('nao deve iniciar blink quando enabled=false desde o inicio', () => {
    renderHook(() =>
      useTabAlert({
        enabled: false,
        originalTitle: 'Julia Dashboard',
      })
    )

    vi.advanceTimersByTime(5000)
    expect(document.title).toBe('Julia Dashboard')
  })
})

describe('useFaviconAlert', () => {
  it('deve buscar link do favicon quando hasProblem=true', () => {
    const mockLink = document.createElement('link')
    mockLink.rel = 'icon'
    document.head.appendChild(mockLink)

    const querySelectorSpy = vi.spyOn(document, 'querySelector')

    renderHook(() => useFaviconAlert(true))

    expect(querySelectorSpy).toHaveBeenCalledWith("link[rel*='icon']")

    querySelectorSpy.mockRestore()
    document.head.removeChild(mockLink)
  })

  it('deve executar sem erro quando hasProblem=false', () => {
    expect(() => {
      renderHook(() => useFaviconAlert(false))
    }).not.toThrow()
  })

  it('deve executar sem erro quando link nao existe', () => {
    expect(() => {
      renderHook(() => useFaviconAlert(true))
    }).not.toThrow()
  })
})
