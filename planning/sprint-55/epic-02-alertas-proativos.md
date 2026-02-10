# ÉPICO 02: Alertas Proativos no Dashboard

## Contexto

O dashboard de monitoramento (`/health` e `/monitor`) já existe e é robusto, com:
- Health score 0-100
- Status de serviços
- Painel de alertas
- Auto-refresh configurável

**Problema:** O usuário precisa estar olhando a tela para ver problemas. Não há notificação proativa quando algo fica crítico.

Este épico adiciona **alertas visuais, sonoros e browser notifications** para que problemas críticos não passem despercebidos.

## Escopo

- **Incluído**:
  - Alerta sonoro quando status vira crítico
  - Favicon badge quando há problemas
  - Título da aba piscando com alerta
  - Browser notifications (com permissão)

- **Excluído**:
  - Push notifications via service worker (PWA completo)
  - Integração com Slack (foi removida intencionalmente na Sprint 47)

---

## Tarefa T02.1: Hook de Detecção de Mudança de Status

### Objetivo

Criar hook React que detecta quando o status de saúde muda e dispara callbacks.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Criar | `dashboard/hooks/use-health-alert.ts` |

### Implementação

```typescript
// dashboard/hooks/use-health-alert.ts
'use client'

import { useEffect, useRef, useCallback } from 'react'

type HealthStatus = 'healthy' | 'degraded' | 'critical'

interface UseHealthAlertOptions {
  onStatusChange?: (from: HealthStatus | null, to: HealthStatus) => void
  onCritical?: () => void
  onRecovery?: () => void
}

export function useHealthAlert(
  currentStatus: HealthStatus | null,
  options: UseHealthAlertOptions = {}
) {
  const previousStatus = useRef<HealthStatus | null>(null)
  const { onStatusChange, onCritical, onRecovery } = options

  useEffect(() => {
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
    isTransition: previousStatus.current !== null && previousStatus.current !== currentStatus,
  }
}
```

### Testes Obrigatórios

**Unitários:**
- [ ] Chama `onStatusChange` quando status muda
- [ ] Chama `onCritical` quando transição para critical
- [ ] Chama `onRecovery` quando sai de critical
- [ ] Não chama callbacks no primeiro render (sem status anterior)
- [ ] Não chama callbacks quando status não muda

**Arquivo de teste:** `dashboard/__tests__/hooks/use-health-alert.test.ts`

```typescript
import { renderHook } from '@testing-library/react'
import { useHealthAlert } from '@/hooks/use-health-alert'

describe('useHealthAlert', () => {
  it('should call onCritical when status becomes critical', () => {
    const onCritical = jest.fn()
    const { rerender } = renderHook(
      ({ status }) => useHealthAlert(status, { onCritical }),
      { initialProps: { status: 'healthy' as const } }
    )

    rerender({ status: 'critical' as const })
    expect(onCritical).toHaveBeenCalledTimes(1)
  })

  it('should call onRecovery when status leaves critical', () => {
    const onRecovery = jest.fn()
    const { rerender } = renderHook(
      ({ status }) => useHealthAlert(status, { onRecovery }),
      { initialProps: { status: 'critical' as const } }
    )

    rerender({ status: 'healthy' as const })
    expect(onRecovery).toHaveBeenCalledTimes(1)
  })

  it('should not call callbacks on initial render', () => {
    const onStatusChange = jest.fn()
    renderHook(() => useHealthAlert('critical', { onStatusChange }))
    expect(onStatusChange).not.toHaveBeenCalled()
  })
})
```

### Definition of Done

- [ ] Hook implementado
- [ ] Testes unitários passando
- [ ] Exportado em `dashboard/hooks/index.ts`

### Estimativa

1 hora

---

## Tarefa T02.2: Alerta Sonoro

### Objetivo

Tocar som de alerta quando status fica crítico.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Criar | `dashboard/lib/alert-sound.ts` |
| Criar | `dashboard/public/sounds/alert-critical.mp3` |

### Implementação

```typescript
// dashboard/lib/alert-sound.ts
'use client'

let audioContext: AudioContext | null = null

// Som de alerta usando Web Audio API (não precisa de arquivo externo)
export function playAlertSound() {
  try {
    // Criar contexto se não existir
    if (!audioContext) {
      audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
    }

    const oscillator = audioContext.createOscillator()
    const gainNode = audioContext.createGain()

    oscillator.connect(gainNode)
    gainNode.connect(audioContext.destination)

    // Som de alerta: dois beeps
    oscillator.frequency.value = 800
    oscillator.type = 'sine'

    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime)
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3)

    oscillator.start(audioContext.currentTime)
    oscillator.stop(audioContext.currentTime + 0.3)

    // Segundo beep
    setTimeout(() => {
      if (!audioContext) return
      const osc2 = audioContext.createOscillator()
      const gain2 = audioContext.createGain()
      osc2.connect(gain2)
      gain2.connect(audioContext.destination)
      osc2.frequency.value = 800
      osc2.type = 'sine'
      gain2.gain.setValueAtTime(0.3, audioContext.currentTime)
      gain2.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3)
      osc2.start(audioContext.currentTime)
      osc2.stop(audioContext.currentTime + 0.3)
    }, 400)

  } catch (e) {
    console.warn('Could not play alert sound:', e)
  }
}

// Pedir permissão para som (alguns browsers bloqueiam autoplay)
export function requestSoundPermission(): Promise<boolean> {
  return new Promise((resolve) => {
    try {
      if (!audioContext) {
        audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
      }
      if (audioContext.state === 'suspended') {
        audioContext.resume().then(() => resolve(true)).catch(() => resolve(false))
      } else {
        resolve(true)
      }
    } catch {
      resolve(false)
    }
  })
}
```

### Testes Obrigatórios

**Unitários:**
- [ ] `playAlertSound` não lança exceção se AudioContext não disponível
- [ ] `requestSoundPermission` retorna boolean

**Manual:**
- [ ] Som toca quando status fica crítico
- [ ] Som não toca repetidamente (apenas na transição)

### Definition of Done

- [ ] Função de som implementada
- [ ] Som toca no evento de status crítico
- [ ] Não depende de arquivo externo (usa Web Audio API)
- [ ] Graceful fallback se áudio bloqueado

### Estimativa

30 minutos

---

## Tarefa T02.3: Favicon Badge e Título Piscante

### Objetivo

Mostrar indicador visual na aba do browser quando há problemas.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Criar | `dashboard/hooks/use-tab-alert.ts` |
| Criar | `dashboard/public/favicon-alert.ico` (opcional) |

### Implementação

```typescript
// dashboard/hooks/use-tab-alert.ts
'use client'

import { useEffect, useRef } from 'react'

interface UseTabAlertOptions {
  enabled: boolean
  originalTitle?: string
  alertTitle?: string
  blinkInterval?: number
}

export function useTabAlert({
  enabled,
  originalTitle = 'Julia Dashboard',
  alertTitle = '🔴 ALERTA - Julia Dashboard',
  blinkInterval = 1000,
}: UseTabAlertOptions) {
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
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
```

### Testes Obrigatórios

**Unitários:**
- [ ] Título pisca quando `enabled=true`
- [ ] Título restaura quando `enabled=false`
- [ ] Limpa interval no unmount

### Definition of Done

- [ ] Hook implementado
- [ ] Título da aba pisca quando status crítico
- [ ] Restaura ao normal quando status OK

### Estimativa

30 minutos

---

## Tarefa T02.4: Browser Notifications

### Objetivo

Enviar notificação do browser quando status fica crítico (mesmo com aba em background).

### Arquivos

| Ação | Arquivo |
|------|---------|
| Criar | `dashboard/lib/browser-notifications.ts` |

### Implementação

```typescript
// dashboard/lib/browser-notifications.ts
'use client'

export async function requestNotificationPermission(): Promise<boolean> {
  if (!('Notification' in window)) {
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

export function sendCriticalNotification(message: string) {
  if (Notification.permission !== 'granted') {
    return
  }

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
}

export function sendRecoveryNotification() {
  if (Notification.permission !== 'granted') {
    return
  }

  new Notification('✅ Julia - Sistema Recuperado', {
    body: 'O sistema voltou ao estado saudável.',
    icon: '/favicon.ico',
    tag: 'julia-recovery-alert',
  })
}
```

### Testes Obrigatórios

**Unitários:**
- [ ] `requestNotificationPermission` retorna false se API não disponível
- [ ] `sendCriticalNotification` não lança erro se permissão negada

**Manual:**
- [ ] Notificação aparece quando status fica crítico
- [ ] Clicar na notificação foca a aba
- [ ] Notificação de recovery aparece quando recupera

### Definition of Done

- [ ] Funções de notificação implementadas
- [ ] Integrado com hook de detecção de mudança
- [ ] Pede permissão na primeira vez

### Estimativa

30 minutos

---

## Tarefa T02.5: Integração no Health Center

### Objetivo

Integrar todos os alertas no componente `HealthPageContent`.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Modificar | `dashboard/components/health/health-page-content.tsx` |

### Implementação

```typescript
// Adicionar imports no início
import { useHealthAlert } from '@/hooks/use-health-alert'
import { useTabAlert } from '@/hooks/use-tab-alert'
import { playAlertSound, requestSoundPermission } from '@/lib/alert-sound'
import {
  requestNotificationPermission,
  sendCriticalNotification,
  sendRecoveryNotification
} from '@/lib/browser-notifications'

// Dentro do componente HealthPageContent:

export function HealthPageContent() {
  // ... estado existente ...
  const [notificationsEnabled, setNotificationsEnabled] = useState(false)

  // Pedir permissões no mount
  useEffect(() => {
    requestSoundPermission()
    requestNotificationPermission().then(setNotificationsEnabled)
  }, [])

  // Hook de detecção de mudança
  useHealthAlert(data?.status ?? null, {
    onCritical: () => {
      playAlertSound()
      if (notificationsEnabled) {
        sendCriticalNotification('Sistema em estado crítico. Verifique o Health Center.')
      }
    },
    onRecovery: () => {
      if (notificationsEnabled) {
        sendRecoveryNotification()
      }
    },
  })

  // Hook de título piscante
  useTabAlert({
    enabled: data?.status === 'critical',
    originalTitle: 'Health Center | Julia Dashboard',
    alertTitle: '🔴 CRÍTICO - Julia Dashboard',
  })

  // ... resto do componente ...
}
```

### Testes Obrigatórios

**E2E:**
- [ ] Página carrega sem erros
- [ ] Auto-refresh continua funcionando
- [ ] Som toca quando mock de API retorna status critical

**Arquivo:** `dashboard/e2e/health-alerts.e2e.ts`

### Definition of Done

- [ ] Hooks integrados no componente
- [ ] Alerta sonoro funciona na transição para critical
- [ ] Título pisca quando critical
- [ ] Notificação aparece (se permissão concedida)
- [ ] Testes E2E passando

### Estimativa

1.5 horas

---

## Resumo do Épico

| Tarefa | Estimativa | Risco |
|--------|------------|-------|
| T02.1: Hook de detecção | 1h | Baixo |
| T02.2: Alerta sonoro | 30min | Baixo |
| T02.3: Tab alert | 30min | Baixo |
| T02.4: Browser notifications | 30min | Médio (permissões) |
| T02.5: Integração | 1.5h | Médio |
| **Total** | **4h** | |

## Ordem de Execução

1. T02.1 - Hook de detecção (base para os outros)
2. T02.2, T02.3, T02.4 - Podem ser paralelos
3. T02.5 - Integração final

## Paralelizável

- T02.2, T02.3, T02.4 podem ser feitos simultaneamente após T02.1
