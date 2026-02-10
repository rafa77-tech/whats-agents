/**
 * Hook de Alerta na Aba do Browser
 *
 * Sprint 55 E02 T02.3
 *
 * Faz o título da aba piscar quando há alerta crítico.
 */

'use client'

import { useEffect, useRef } from 'react'

interface UseTabAlertOptions {
  /** Se o alerta está ativo */
  enabled: boolean
  /** Título original da página */
  originalTitle?: string
  /** Título de alerta (com emoji) */
  alertTitle?: string
  /** Intervalo de blink em ms */
  blinkInterval?: number
}

/**
 * Hook que faz o título da aba piscar quando enabled=true.
 *
 * @example
 * ```tsx
 * useTabAlert({
 *   enabled: status === 'critical',
 *   originalTitle: 'Health Center | Julia',
 *   alertTitle: '🔴 CRÍTICO - Julia',
 * })
 * ```
 */
export function useTabAlert({
  enabled,
  originalTitle = 'Julia Dashboard',
  alertTitle = '🔴 ALERTA - Julia Dashboard',
  blinkInterval = 1000,
}: UseTabAlertOptions): void {
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const isAlertTitle = useRef(false)

  useEffect(() => {
    if (enabled) {
      // Iniciar blink
      intervalRef.current = setInterval(() => {
        document.title = isAlertTitle.current ? originalTitle : alertTitle
        isAlertTitle.current = !isAlertTitle.current
      }, blinkInterval)
    } else {
      // Parar blink e restaurar título
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      document.title = originalTitle
      isAlertTitle.current = false
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
      document.title = originalTitle
    }
  }, [enabled, originalTitle, alertTitle, blinkInterval])
}

/**
 * Hook para atualizar o favicon com badge de alerta.
 *
 * Nota: Implementação simplificada - apenas muda o emoji no título.
 * Para favicon dinâmico, seria necessário canvas.
 */
export function useFaviconAlert(hasProblem: boolean): void {
  useEffect(() => {
    // Poderia ser expandido para mudar o favicon dinamicamente
    // Por enquanto, o título piscante já dá feedback visual suficiente
    const link = document.querySelector("link[rel*='icon']") as HTMLLinkElement | null
    if (link && hasProblem) {
      // Futuro: link.href = '/favicon-alert.ico'
    }
  }, [hasProblem])
}
