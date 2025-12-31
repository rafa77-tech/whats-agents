# E07: Sistema de Notificações

**Épico:** Web Push + Toast + Realtime
**Estimativa:** 8h
**Prioridade:** P1 (Importante)
**Dependências:** E01, E02, E04

---

## Objetivo

Implementar sistema completo de notificações:
- Web Push API para notificações do browser
- Toast notifications in-app
- Supabase Realtime para atualizações live
- Centro de notificações (histórico)

---

## Tipos de Notificações

| Tipo | Prioridade | Push | Toast | Descrição |
|------|------------|------|-------|-----------|
| `handoff_request` | Alta | Sim | Sim | Médico pede humano |
| `rate_limit_warning` | Alta | Sim | Sim | 80%+ do limite |
| `circuit_open` | Crítica | Sim | Sim | Integração falhou |
| `new_conversion` | Média | Sim | Sim | Médico confirmou plantão |
| `campaign_complete` | Baixa | Não | Sim | Campanha finalizada |
| `system_alert` | Crítica | Sim | Sim | Alerta de sistema |

---

## Estrutura de Arquivos

```
components/
├── notifications/
│   ├── notification-provider.tsx
│   ├── notification-center.tsx
│   ├── notification-bell.tsx
│   ├── notification-item.tsx
│   ├── push-permission.tsx
│   └── toast-notification.tsx
lib/
├── notifications/
│   ├── push.ts
│   ├── realtime.ts
│   └── types.ts
hooks/
└── use-notifications.ts
public/
└── sw.js                    # Service Worker
```

---

## Stories

### S07.1: Service Worker para Push

**Arquivo:** `public/sw.js`

```javascript
// Service Worker para Web Push Notifications

self.addEventListener('push', function(event) {
  if (!event.data) return;

  const data = event.data.json();

  const options = {
    body: data.body,
    icon: '/icon-192.png',
    badge: '/badge-72.png',
    tag: data.tag || 'default',
    data: data.data || {},
    actions: data.actions || [],
    requireInteraction: data.priority === 'high',
    vibrate: data.priority === 'high' ? [200, 100, 200] : undefined,
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();

  const data = event.notification.data;
  let url = '/';

  // Redirecionar baseado no tipo
  if (data.type === 'handoff_request') {
    url = `/conversas/${data.conversation_id}`;
  } else if (data.type === 'rate_limit_warning') {
    url = '/sistema';
  } else if (data.type === 'new_conversion') {
    url = `/medicos/${data.doctor_id}`;
  }

  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(function(clientList) {
      // Se já tem uma janela aberta, focar nela
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.focus();
          client.navigate(url);
          return;
        }
      }
      // Senão, abrir nova janela
      if (clients.openWindow) {
        return clients.openWindow(url);
      }
    })
  );
});
```

**Arquivo:** `lib/notifications/push.ts`

```typescript
const VAPID_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY!

export async function registerPushNotifications(): Promise<PushSubscription | null> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    console.log('Push notifications not supported')
    return null
  }

  try {
    // Registrar service worker
    const registration = await navigator.serviceWorker.register('/sw.js')
    console.log('Service Worker registered')

    // Verificar permissão
    const permission = await Notification.requestPermission()
    if (permission !== 'granted') {
      console.log('Notification permission denied')
      return null
    }

    // Obter ou criar subscription
    let subscription = await registration.pushManager.getSubscription()

    if (!subscription) {
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
      })
    }

    return subscription

  } catch (error) {
    console.error('Failed to register push:', error)
    return null
  }
}

export async function unregisterPushNotifications(): Promise<boolean> {
  try {
    const registration = await navigator.serviceWorker.ready
    const subscription = await registration.pushManager.getSubscription()

    if (subscription) {
      await subscription.unsubscribe()
      return true
    }

    return false
  } catch (error) {
    console.error('Failed to unregister push:', error)
    return false
  }
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - base64String.length % 4) % 4)
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/')

  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}
```

**DoD:**
- [ ] Service Worker registrado
- [ ] Push subscription funcionando
- [ ] Click abre URL correta

---

### S07.2: Notification Types e Context

**Arquivo:** `lib/notifications/types.ts`

```typescript
export type NotificationType =
  | 'handoff_request'
  | 'rate_limit_warning'
  | 'circuit_open'
  | 'new_conversion'
  | 'campaign_complete'
  | 'system_alert'

export type NotificationPriority = 'low' | 'medium' | 'high' | 'critical'

export interface Notification {
  id: string
  type: NotificationType
  title: string
  body: string
  priority: NotificationPriority
  read: boolean
  data?: Record<string, any>
  created_at: string
}

export interface NotificationConfig {
  push_enabled: boolean
  toast_enabled: boolean
  types: Record<NotificationType, {
    push: boolean
    toast: boolean
    sound: boolean
  }>
}

export const DEFAULT_CONFIG: NotificationConfig = {
  push_enabled: true,
  toast_enabled: true,
  types: {
    handoff_request: { push: true, toast: true, sound: true },
    rate_limit_warning: { push: true, toast: true, sound: false },
    circuit_open: { push: true, toast: true, sound: true },
    new_conversion: { push: true, toast: true, sound: false },
    campaign_complete: { push: false, toast: true, sound: false },
    system_alert: { push: true, toast: true, sound: true },
  }
}

export const NOTIFICATION_ICONS: Record<NotificationType, string> = {
  handoff_request: 'UserPlus',
  rate_limit_warning: 'AlertTriangle',
  circuit_open: 'XCircle',
  new_conversion: 'CheckCircle',
  campaign_complete: 'Send',
  system_alert: 'AlertOctagon',
}

export const NOTIFICATION_COLORS: Record<NotificationPriority, string> = {
  low: 'text-gray-500',
  medium: 'text-blue-500',
  high: 'text-yellow-500',
  critical: 'text-red-500',
}
```

**Arquivo:** `components/notifications/notification-provider.tsx`

```typescript
'use client'

import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { createClient } from '@/lib/supabase/client'
import { api } from '@/lib/api/client'
import { useToast } from '@/components/ui/use-toast'
import { registerPushNotifications } from '@/lib/notifications/push'
import type { Notification, NotificationConfig, DEFAULT_CONFIG } from '@/lib/notifications/types'

interface NotificationContextType {
  notifications: Notification[]
  unreadCount: number
  config: NotificationConfig
  isLoading: boolean
  markAsRead: (id: string) => void
  markAllAsRead: () => void
  updateConfig: (config: Partial<NotificationConfig>) => void
  requestPushPermission: () => Promise<boolean>
}

const NotificationContext = createContext<NotificationContextType | null>(null)

export function NotificationProvider({ children }: { children: ReactNode }) {
  const [pushSubscription, setPushSubscription] = useState<PushSubscription | null>(null)

  const queryClient = useQueryClient()
  const { toast } = useToast()
  const supabase = createClient()

  // Buscar notificações
  const { data: notifications = [], isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: async () => {
      const result = await api.get<{ notifications: Notification[] }>(
        '/dashboard/notifications?limit=50'
      )
      return result.notifications
    },
    refetchInterval: 60000 // Refresh a cada minuto
  })

  // Buscar configurações
  const { data: config = DEFAULT_CONFIG } = useQuery({
    queryKey: ['notification-config'],
    queryFn: async () => {
      const result = await api.get<{ config: NotificationConfig }>(
        '/dashboard/notifications/config'
      )
      return result.config
    }
  })

  // Marcar como lida
  const markAsReadMutation = useMutation({
    mutationFn: (id: string) => api.post(`/dashboard/notifications/${id}/read`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    }
  })

  // Marcar todas como lidas
  const markAllAsReadMutation = useMutation({
    mutationFn: () => api.post('/dashboard/notifications/read-all'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    }
  })

  // Atualizar config
  const updateConfigMutation = useMutation({
    mutationFn: (newConfig: Partial<NotificationConfig>) =>
      api.put('/dashboard/notifications/config', newConfig),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notification-config'] })
    }
  })

  // Supabase Realtime
  useEffect(() => {
    const channel = supabase
      .channel('dashboard-notifications')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'dashboard_notifications'
        },
        (payload) => {
          const notification = payload.new as Notification

          // Invalidar query para atualizar lista
          queryClient.invalidateQueries({ queryKey: ['notifications'] })

          // Mostrar toast se configurado
          if (config.toast_enabled && config.types[notification.type]?.toast) {
            toast({
              title: notification.title,
              description: notification.body,
              variant: notification.priority === 'critical' ? 'destructive' : 'default'
            })
          }

          // Som se configurado
          if (config.types[notification.type]?.sound) {
            playNotificationSound()
          }
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [config, queryClient, supabase, toast])

  // Request push permission
  const requestPushPermission = async (): Promise<boolean> => {
    const subscription = await registerPushNotifications()
    if (subscription) {
      setPushSubscription(subscription)
      // Salvar no backend
      await api.post('/dashboard/notifications/push-subscription', {
        subscription: subscription.toJSON()
      })
      return true
    }
    return false
  }

  const unreadCount = notifications.filter(n => !n.read).length

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        unreadCount,
        config,
        isLoading,
        markAsRead: (id) => markAsReadMutation.mutate(id),
        markAllAsRead: () => markAllAsReadMutation.mutate(),
        updateConfig: (newConfig) => updateConfigMutation.mutate(newConfig),
        requestPushPermission,
      }}
    >
      {children}
    </NotificationContext.Provider>
  )
}

export function useNotifications() {
  const context = useContext(NotificationContext)
  if (!context) {
    throw new Error('useNotifications must be used within NotificationProvider')
  }
  return context
}

function playNotificationSound() {
  try {
    const audio = new Audio('/sounds/notification.mp3')
    audio.volume = 0.5
    audio.play()
  } catch (e) {
    // Silently fail if audio not available
  }
}
```

**DoD:**
- [ ] Context com todas notificações
- [ ] Contador de não lidas
- [ ] Supabase Realtime listener
- [ ] Som para notificações importantes

---

### S07.3: Notification Bell (Header)

**Arquivo:** `components/notifications/notification-bell.tsx`

```typescript
'use client'

import { useState } from 'react'
import { Bell } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { useNotifications } from './notification-provider'
import { NotificationItem } from './notification-item'

export function NotificationBell() {
  const [open, setOpen] = useState(false)
  const { notifications, unreadCount, markAllAsRead, isLoading } = useNotifications()

  const recentNotifications = notifications.slice(0, 10)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-red-500 text-white text-xs flex items-center justify-center">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent className="w-80 p-0" align="end">
        <div className="flex items-center justify-between p-4">
          <h4 className="font-semibold">Notificações</h4>
          {unreadCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => markAllAsRead()}
            >
              Marcar todas como lidas
            </Button>
          )}
        </div>

        <Separator />

        <ScrollArea className="h-[300px]">
          {recentNotifications.length === 0 ? (
            <div className="p-4 text-center text-muted-foreground">
              Nenhuma notificação
            </div>
          ) : (
            <div className="divide-y">
              {recentNotifications.map((notification) => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                  compact
                  onClose={() => setOpen(false)}
                />
              ))}
            </div>
          )}
        </ScrollArea>

        <Separator />

        <div className="p-2">
          <Button
            variant="ghost"
            className="w-full"
            onClick={() => {
              setOpen(false)
              // Navigate to full notification center
              window.location.href = '/notificacoes'
            }}
          >
            Ver todas as notificações
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}
```

**DoD:**
- [ ] Bell icon com badge de contagem
- [ ] Popover com últimas 10 notificações
- [ ] Marcar todas como lidas
- [ ] Link para centro completo

---

### S07.4: Notification Item Component

**Arquivo:** `components/notifications/notification-item.tsx`

```typescript
'use client'

import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { useRouter } from 'next/navigation'
import {
  UserPlus,
  AlertTriangle,
  XCircle,
  CheckCircle,
  Send,
  AlertOctagon,
  Circle
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useNotifications } from './notification-provider'
import type { Notification, NotificationType, NotificationPriority } from '@/lib/notifications/types'

const ICONS: Record<NotificationType, React.ComponentType<{ className?: string }>> = {
  handoff_request: UserPlus,
  rate_limit_warning: AlertTriangle,
  circuit_open: XCircle,
  new_conversion: CheckCircle,
  campaign_complete: Send,
  system_alert: AlertOctagon,
}

const PRIORITY_COLORS: Record<NotificationPriority, string> = {
  low: 'text-gray-400',
  medium: 'text-blue-500',
  high: 'text-yellow-500',
  critical: 'text-red-500',
}

const PRIORITY_BG: Record<NotificationPriority, string> = {
  low: 'bg-gray-100 dark:bg-gray-800',
  medium: 'bg-blue-50 dark:bg-blue-900/20',
  high: 'bg-yellow-50 dark:bg-yellow-900/20',
  critical: 'bg-red-50 dark:bg-red-900/20',
}

interface Props {
  notification: Notification
  compact?: boolean
  onClose?: () => void
}

export function NotificationItem({ notification, compact = false, onClose }: Props) {
  const router = useRouter()
  const { markAsRead } = useNotifications()

  const Icon = ICONS[notification.type]

  const handleClick = () => {
    // Marcar como lida
    if (!notification.read) {
      markAsRead(notification.id)
    }

    // Navegar baseado no tipo
    let url = '/'
    if (notification.type === 'handoff_request' && notification.data?.conversation_id) {
      url = `/conversas/${notification.data.conversation_id}`
    } else if (notification.type === 'rate_limit_warning') {
      url = '/sistema'
    } else if (notification.type === 'circuit_open') {
      url = '/sistema'
    } else if (notification.type === 'new_conversion' && notification.data?.doctor_id) {
      url = `/medicos/${notification.data.doctor_id}`
    } else if (notification.type === 'campaign_complete' && notification.data?.campaign_id) {
      url = `/campanhas/${notification.data.campaign_id}`
    }

    router.push(url)
    onClose?.()
  }

  const timeAgo = formatDistanceToNow(new Date(notification.created_at), {
    addSuffix: true,
    locale: ptBR
  })

  if (compact) {
    return (
      <button
        onClick={handleClick}
        className={cn(
          'w-full p-3 text-left hover:bg-muted transition-colors',
          !notification.read && 'bg-blue-50/50 dark:bg-blue-900/10'
        )}
      >
        <div className="flex gap-3">
          <div className={cn('mt-0.5', PRIORITY_COLORS[notification.priority])}>
            <Icon className="h-4 w-4" />
          </div>
          <div className="flex-1 min-w-0">
            <p className={cn('text-sm', !notification.read && 'font-medium')}>
              {notification.title}
            </p>
            <p className="text-xs text-muted-foreground truncate">
              {notification.body}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {timeAgo}
            </p>
          </div>
          {!notification.read && (
            <Circle className="h-2 w-2 fill-blue-500 text-blue-500 mt-1.5" />
          )}
        </div>
      </button>
    )
  }

  return (
    <button
      onClick={handleClick}
      className={cn(
        'w-full p-4 text-left rounded-lg transition-colors',
        PRIORITY_BG[notification.priority],
        !notification.read && 'ring-1 ring-blue-200 dark:ring-blue-800'
      )}
    >
      <div className="flex gap-4">
        <div className={cn(
          'p-2 rounded-full',
          PRIORITY_BG[notification.priority],
          PRIORITY_COLORS[notification.priority]
        )}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="flex-1">
          <div className="flex items-start justify-between gap-2">
            <p className={cn('font-medium', !notification.read && 'font-semibold')}>
              {notification.title}
            </p>
            {!notification.read && (
              <Circle className="h-2 w-2 fill-blue-500 text-blue-500 flex-shrink-0 mt-1.5" />
            )}
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            {notification.body}
          </p>
          <p className="text-xs text-muted-foreground mt-2">
            {timeAgo}
          </p>
        </div>
      </div>
    </button>
  )
}
```

**DoD:**
- [ ] Ícone por tipo
- [ ] Cores por prioridade
- [ ] Indicador de não lida
- [ ] Tempo relativo
- [ ] Click navega corretamente

---

### S07.5: Push Permission Component

**Arquivo:** `components/notifications/push-permission.tsx`

```typescript
'use client'

import { useState, useEffect } from 'react'
import { Bell, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useNotifications } from './notification-provider'

export function PushPermissionBanner() {
  const [show, setShow] = useState(false)
  const [loading, setLoading] = useState(false)
  const { config, requestPushPermission, updateConfig } = useNotifications()

  useEffect(() => {
    // Mostrar banner se push não está ativo e nunca foi negado
    const checkPermission = async () => {
      if (!('Notification' in window)) return

      const permission = Notification.permission
      const dismissed = localStorage.getItem('push-permission-dismissed')

      if (permission === 'default' && !dismissed && !config.push_enabled) {
        setShow(true)
      }
    }

    checkPermission()
  }, [config.push_enabled])

  const handleEnable = async () => {
    setLoading(true)
    const success = await requestPushPermission()
    setLoading(false)

    if (success) {
      updateConfig({ push_enabled: true })
      setShow(false)
    }
  }

  const handleDismiss = () => {
    localStorage.setItem('push-permission-dismissed', 'true')
    setShow(false)
  }

  if (!show) return null

  return (
    <Card className="fixed bottom-4 right-4 z-50 w-80 shadow-lg md:bottom-6 md:right-6">
      <CardContent className="p-4">
        <div className="flex gap-3">
          <div className="p-2 rounded-full bg-blue-100 dark:bg-blue-900/30">
            <Bell className="h-5 w-5 text-blue-600" />
          </div>
          <div className="flex-1">
            <p className="font-medium">Ativar notificações?</p>
            <p className="text-sm text-muted-foreground mt-1">
              Receba alertas importantes mesmo quando não estiver no dashboard.
            </p>
            <div className="flex gap-2 mt-3">
              <Button
                size="sm"
                onClick={handleEnable}
                disabled={loading}
              >
                {loading ? 'Ativando...' : 'Ativar'}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleDismiss}
              >
                Agora não
              </Button>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={handleDismiss}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
```

**DoD:**
- [ ] Banner aparece se nunca pediu permissão
- [ ] Dismiss persiste no localStorage
- [ ] Request permission funciona
- [ ] Posição fixa no canto

---

### S07.6: Backend - Endpoints de Notificações

**Arquivo:** `app/api/routes/dashboard/notifications.py`

```python
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.api.routes.dashboard import CurrentUser
from app.services.supabase import supabase
from app.core.auth import DashboardUser

router = APIRouter(prefix="/notifications", tags=["dashboard-notifications"])

class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    body: str
    priority: str
    read: bool
    data: Optional[dict]
    created_at: str

class NotificationConfigUpdate(BaseModel):
    push_enabled: Optional[bool] = None
    toast_enabled: Optional[bool] = None
    types: Optional[dict] = None

class PushSubscription(BaseModel):
    subscription: dict

@router.get("")
async def list_notifications(
    user: CurrentUser,
    limit: int = Query(50, le=100),
    unread_only: bool = False
):
    """Lista notificações do usuário."""

    query = supabase.table("dashboard_notifications").select("*").eq(
        "user_id", user.id
    ).order("created_at", desc=True).limit(limit)

    if unread_only:
        query = query.eq("read", False)

    result = query.execute()

    return {"notifications": result.data}

@router.post("/{notification_id}/read")
async def mark_as_read(notification_id: str, user: CurrentUser):
    """Marca notificação como lida."""

    result = supabase.table("dashboard_notifications").update({
        "read": True,
        "read_at": datetime.now().isoformat()
    }).eq("id", notification_id).eq("user_id", user.id).execute()

    return {"success": True}

@router.post("/read-all")
async def mark_all_as_read(user: CurrentUser):
    """Marca todas notificações como lidas."""

    result = supabase.table("dashboard_notifications").update({
        "read": True,
        "read_at": datetime.now().isoformat()
    }).eq("user_id", user.id).eq("read", False).execute()

    return {"success": True, "count": len(result.data)}

@router.get("/config")
async def get_notification_config(user: CurrentUser):
    """Retorna configurações de notificação do usuário."""

    result = supabase.table("dashboard_notification_config").select("*").eq(
        "user_id", user.id
    ).single().execute()

    if not result.data:
        # Retornar defaults
        return {
            "config": {
                "push_enabled": False,
                "toast_enabled": True,
                "types": {}
            }
        }

    return {"config": result.data}

@router.put("/config")
async def update_notification_config(
    config: NotificationConfigUpdate,
    user: CurrentUser
):
    """Atualiza configurações de notificação."""

    data = {k: v for k, v in config.model_dump().items() if v is not None}
    data["user_id"] = user.id
    data["updated_at"] = datetime.now().isoformat()

    result = supabase.table("dashboard_notification_config").upsert(
        data,
        on_conflict="user_id"
    ).execute()

    return {"success": True}

@router.post("/push-subscription")
async def save_push_subscription(
    data: PushSubscription,
    user: CurrentUser
):
    """Salva subscription de push do usuário."""

    result = supabase.table("dashboard_push_subscriptions").upsert({
        "user_id": user.id,
        "subscription": data.subscription,
        "updated_at": datetime.now().isoformat()
    }, on_conflict="user_id").execute()

    return {"success": True}
```

**Arquivo:** `app/services/dashboard_notifications.py`

```python
from datetime import datetime
from typing import Optional
import json

from app.services.supabase import supabase

async def create_notification(
    type: str,
    title: str,
    body: str,
    priority: str = "medium",
    data: Optional[dict] = None,
    user_ids: Optional[list] = None
):
    """
    Cria notificação para usuários do dashboard.
    Se user_ids for None, notifica todos os usuários.
    """

    if user_ids is None:
        # Buscar todos os usuários ativos
        users = supabase.table("dashboard_users").select("id").eq(
            "is_active", True
        ).execute()
        user_ids = [u["id"] for u in users.data]

    notifications = []
    for user_id in user_ids:
        notifications.append({
            "user_id": user_id,
            "type": type,
            "title": title,
            "body": body,
            "priority": priority,
            "data": data,
            "read": False,
            "created_at": datetime.now().isoformat()
        })

    result = supabase.table("dashboard_notifications").insert(notifications).execute()

    # Enviar push para quem tem subscription
    for user_id in user_ids:
        await send_push_to_user(user_id, {
            "title": title,
            "body": body,
            "priority": priority,
            "data": data or {}
        })

    return result.data

async def send_push_to_user(user_id: str, payload: dict):
    """Envia push notification para um usuário."""
    from pywebpush import webpush, WebPushException
    import os

    # Buscar subscription
    result = supabase.table("dashboard_push_subscriptions").select(
        "subscription"
    ).eq("user_id", user_id).single().execute()

    if not result.data:
        return

    subscription = result.data["subscription"]

    try:
        webpush(
            subscription_info=subscription,
            data=json.dumps(payload),
            vapid_private_key=os.environ["VAPID_PRIVATE_KEY"],
            vapid_claims={
                "sub": "mailto:support@revoluna.com"
            }
        )
    except WebPushException as e:
        if e.response and e.response.status_code == 410:
            # Subscription expirou, remover
            supabase.table("dashboard_push_subscriptions").delete().eq(
                "user_id", user_id
            ).execute()
```

**DoD:**
- [ ] CRUD de notificações
- [ ] Configurações por usuário
- [ ] Push subscriptions salvas
- [ ] Envio de push via pywebpush

---

### S07.7: Migration para Tabelas

```sql
-- Migration: create_dashboard_notifications

-- Tabela de notificações
CREATE TABLE dashboard_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES dashboard_users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium',
    data JSONB,
    read BOOLEAN NOT NULL DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON dashboard_notifications(user_id);
CREATE INDEX idx_notifications_unread ON dashboard_notifications(user_id, read) WHERE read = FALSE;
CREATE INDEX idx_notifications_created ON dashboard_notifications(created_at DESC);

-- Configurações de notificação
CREATE TABLE dashboard_notification_config (
    user_id UUID PRIMARY KEY REFERENCES dashboard_users(id) ON DELETE CASCADE,
    push_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    toast_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    types JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Push subscriptions
CREATE TABLE dashboard_push_subscriptions (
    user_id UUID PRIMARY KEY REFERENCES dashboard_users(id) ON DELETE CASCADE,
    subscription JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS
ALTER TABLE dashboard_notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_notification_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_push_subscriptions ENABLE ROW LEVEL SECURITY;

-- Policy: usuário só vê suas notificações
CREATE POLICY "Users can view own notifications"
    ON dashboard_notifications FOR SELECT
    USING (user_id = auth.uid()::uuid);

CREATE POLICY "Users can update own notifications"
    ON dashboard_notifications FOR UPDATE
    USING (user_id = auth.uid()::uuid);

CREATE POLICY "Users can manage own config"
    ON dashboard_notification_config FOR ALL
    USING (user_id = auth.uid()::uuid);

CREATE POLICY "Users can manage own subscriptions"
    ON dashboard_push_subscriptions FOR ALL
    USING (user_id = auth.uid()::uuid);

-- Enable Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE dashboard_notifications;
```

**DoD:**
- [ ] Tabelas criadas
- [ ] RLS configurado
- [ ] Realtime habilitado

---

## Checklist Final

- [ ] Service Worker para push
- [ ] Push registration funcionando
- [ ] NotificationProvider com realtime
- [ ] Bell com contagem no header
- [ ] NotificationItem com navegação
- [ ] Push permission banner
- [ ] Backend endpoints
- [ ] Serviço de criação de notificações
- [ ] Migration aplicada
- [ ] Som para notificações importantes
- [ ] Mobile responsivo
