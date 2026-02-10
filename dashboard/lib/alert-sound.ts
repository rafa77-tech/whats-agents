/**
 * Alerta Sonoro usando Web Audio API
 *
 * Sprint 55 E02 T02.2
 *
 * Gera som de alerta sem dependência de arquivos externos.
 */

'use client'

let audioContext: AudioContext | null = null

/**
 * Toca som de alerta (dois beeps).
 *
 * Usa Web Audio API para gerar som programaticamente.
 * Graceful fallback se áudio bloqueado pelo browser.
 */
export function playAlertSound(): void {
  try {
    // Criar contexto se não existir
    if (!audioContext) {
      audioContext = new (window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext })
          .webkitAudioContext)()
    }

    // Primeiro beep
    playBeep(audioContext, 0)

    // Segundo beep após 400ms
    setTimeout(() => {
      if (audioContext) {
        playBeep(audioContext, 0)
      }
    }, 400)
  } catch (e) {
    console.warn('Could not play alert sound:', e)
  }
}

/**
 * Toca um beep individual.
 */
function playBeep(ctx: AudioContext, delay: number): void {
  const oscillator = ctx.createOscillator()
  const gainNode = ctx.createGain()

  oscillator.connect(gainNode)
  gainNode.connect(ctx.destination)

  oscillator.frequency.value = 800
  oscillator.type = 'sine'

  const startTime = ctx.currentTime + delay
  gainNode.gain.setValueAtTime(0.3, startTime)
  gainNode.gain.exponentialRampToValueAtTime(0.01, startTime + 0.3)

  oscillator.start(startTime)
  oscillator.stop(startTime + 0.3)
}

/**
 * Toca som de recuperação (tom mais agradável).
 */
export function playRecoverySound(): void {
  try {
    if (!audioContext) {
      audioContext = new (window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext })
          .webkitAudioContext)()
    }

    const oscillator = audioContext.createOscillator()
    const gainNode = audioContext.createGain()

    oscillator.connect(gainNode)
    gainNode.connect(audioContext.destination)

    // Tom mais agradável para recovery
    oscillator.frequency.value = 523.25 // C5
    oscillator.type = 'sine'

    gainNode.gain.setValueAtTime(0.2, audioContext.currentTime)
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5)

    oscillator.start(audioContext.currentTime)
    oscillator.stop(audioContext.currentTime + 0.5)
  } catch (e) {
    console.warn('Could not play recovery sound:', e)
  }
}

/**
 * Pedir permissão para som (alguns browsers bloqueiam autoplay).
 *
 * Deve ser chamado em resposta a uma ação do usuário (click).
 */
export async function requestSoundPermission(): Promise<boolean> {
  try {
    if (!audioContext) {
      audioContext = new (window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext })
          .webkitAudioContext)()
    }

    if (audioContext.state === 'suspended') {
      await audioContext.resume()
    }

    return audioContext.state === 'running'
  } catch {
    return false
  }
}

/**
 * Verifica se som está habilitado.
 */
export function isSoundEnabled(): boolean {
  return audioContext?.state === 'running'
}
