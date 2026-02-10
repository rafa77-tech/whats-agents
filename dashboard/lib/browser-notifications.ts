/**
 * Browser Notifications para Alertas Críticos
 *
 * Sprint 55 E02 T02.4
 *
 * Envia notificações do browser quando status fica crítico.
 * Funciona mesmo com aba em background.
 */

'use client'

/**
 * Verifica se browser suporta notifications.
 */
export function isNotificationSupported(): boolean {
  return 'Notification' in window
}

/**
 * Verifica se permissão já foi concedida.
 */
export function isNotificationGranted(): boolean {
  return isNotificationSupported() && Notification.permission === 'granted'
}

/**
 * Pede permissão para enviar notificações.
 *
 * Deve ser chamado em resposta a ação do usuário (click).
 *
 * @returns true se permissão concedida
 */
export async function requestNotificationPermission(): Promise<boolean> {
  if (!isNotificationSupported()) {
    console.warn('Browser does not support notifications')
    return false
  }

  if (Notification.permission === 'granted') {
    return true
  }

  if (Notification.permission !== 'denied') {
    const permission = await Notification.requestPermission()
    return permission === 'granted'
  }

  return false
}

/**
 * Envia notificação de alerta crítico.
 *
 * @param message Mensagem a exibir
 */
export function sendCriticalNotification(message: string): void {
  if (!isNotificationGranted()) {
    return
  }

  try {
    const notification = new Notification('🔴 Julia - Alerta Crítico', {
      body: message,
      icon: '/favicon.ico',
      tag: 'julia-critical-alert', // Evita duplicatas
      requireInteraction: true, // Não fecha automaticamente
    })

    notification.onclick = () => {
      window.focus()
      notification.close()
    }
  } catch (e) {
    console.warn('Could not send notification:', e)
  }
}

/**
 * Envia notificação de recuperação.
 */
export function sendRecoveryNotification(): void {
  if (!isNotificationGranted()) {
    return
  }

  try {
    const notification = new Notification('✅ Julia - Sistema Recuperado', {
      body: 'O sistema voltou ao estado saudável.',
      icon: '/favicon.ico',
      tag: 'julia-recovery-alert',
    })

    // Auto-close após 5 segundos
    setTimeout(() => notification.close(), 5000)
  } catch (e) {
    console.warn('Could not send notification:', e)
  }
}

/**
 * Envia notificação de degradação (warning).
 */
export function sendDegradedNotification(message: string): void {
  if (!isNotificationGranted()) {
    return
  }

  try {
    const notification = new Notification('⚠️ Julia - Sistema Degradado', {
      body: message,
      icon: '/favicon.ico',
      tag: 'julia-degraded-alert',
    })

    // Auto-close após 10 segundos
    setTimeout(() => notification.close(), 10000)
  } catch (e) {
    console.warn('Could not send notification:', e)
  }
}
