/**
 * Hook de Detecção de Mudança de Status de Saúde
 *
 * Sprint 55 E02 T02.1
 *
 * Detecta transições de status e dispara callbacks apropriados.
 */

'use client'

import { useEffect, useRef } from 'react'

export type HealthStatus = 'healthy' | 'degraded' | 'critical'

interface UseHealthAlertOptions {
  /** Chamado quando status muda */
  onStatusChange?: (from: HealthStatus | null, to: HealthStatus) => void
  /** Chamado quando status vira critical */
  onCritical?: () => void
  /** Chamado quando status sai de critical */
  onRecovery?: () => void
}

/**
 * Hook que monitora mudanças no status de saúde.
 *
 * @example
 * ```tsx
 * useHealthAlert(data?.status ?? null, {
 *   onCritical: () => playAlertSound(),
 *   onRecovery: () => sendRecoveryNotification(),
 * })
 * ```
 */
export function useHealthAlert(
  currentStatus: HealthStatus | null,
  options: UseHealthAlertOptions = {}
) {
  const previousStatus = useRef<HealthStatus | null>(null)
  const isFirstRender = useRef(true)
  const { onStatusChange, onCritical, onRecovery } = options

  useEffect(() => {
    // Skip first render (no previous status to compare)
    if (isFirstRender.current) {
      isFirstRender.current = false
      previousStatus.current = currentStatus
      return
    }

    if (currentStatus === null) return

    const prev = previousStatus.current

    // Detectar mudança de status
    if (prev !== null && prev !== currentStatus) {
      onStatusChange?.(prev, currentStatus)

      // Ficou crítico
      if (currentStatus === 'critical' && prev !== 'critical') {
        onCritical?.()
      }

      // Recuperou de crítico
      if (prev === 'critical' && currentStatus !== 'critical') {
        onRecovery?.()
      }
    }

    previousStatus.current = currentStatus
  }, [currentStatus, onStatusChange, onCritical, onRecovery])

  return {
    previousStatus: previousStatus.current,
    isTransition:
      previousStatus.current !== null && previousStatus.current !== currentStatus,
    isCritical: currentStatus === 'critical',
    wasCritical: previousStatus.current === 'critical',
  }
}
