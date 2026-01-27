'use client'

import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { useRouter } from 'next/navigation'
import type { Route } from 'next'
import {
  UserPlus,
  AlertTriangle,
  XCircle,
  CheckCircle,
  Send,
  AlertOctagon,
  Circle,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type {
  Notification,
  NotificationType,
  NotificationPriority,
} from '@/lib/notifications/types'

const ICONS: Record<NotificationType, LucideIcon> = {
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
  onMarkAsRead?: (id: string) => void
}

export function NotificationItem({ notification, compact = false, onClose, onMarkAsRead }: Props) {
  const router = useRouter()

  const Icon = ICONS[notification.type]

  const handleClick = () => {
    // Mark as read
    if (!notification.read && onMarkAsRead) {
      onMarkAsRead(notification.id)
    }

    // Navigate based on type
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
    } else if (notification.type === 'system_alert') {
      url = '/sistema'
    }

    router.push(url as Route)
    onClose?.()
  }

  const timeAgo = formatDistanceToNow(new Date(notification.created_at), {
    addSuffix: true,
    locale: ptBR,
  })

  if (compact) {
    return (
      <button
        onClick={handleClick}
        className={cn(
          'w-full p-3 text-left transition-colors hover:bg-muted',
          !notification.read && 'bg-blue-50/50 dark:bg-blue-900/10'
        )}
      >
        <div className="flex gap-3">
          <div className={cn('mt-0.5', PRIORITY_COLORS[notification.priority])}>
            <Icon className="h-4 w-4" />
          </div>
          <div className="min-w-0 flex-1">
            <p className={cn('text-sm', !notification.read && 'font-medium')}>
              {notification.title}
            </p>
            <p className="truncate text-xs text-muted-foreground">{notification.body}</p>
            <p className="mt-1 text-xs text-muted-foreground">{timeAgo}</p>
          </div>
          {!notification.read && <Circle className="mt-1.5 h-2 w-2 fill-blue-500 text-blue-500" />}
        </div>
      </button>
    )
  }

  return (
    <button
      onClick={handleClick}
      className={cn(
        'w-full rounded-lg p-4 text-left transition-colors',
        PRIORITY_BG[notification.priority],
        !notification.read && 'ring-1 ring-blue-200 dark:ring-blue-800'
      )}
    >
      <div className="flex gap-4">
        <div
          className={cn(
            'rounded-full p-2',
            PRIORITY_BG[notification.priority],
            PRIORITY_COLORS[notification.priority]
          )}
        >
          <Icon className="h-5 w-5" />
        </div>
        <div className="flex-1">
          <div className="flex items-start justify-between gap-2">
            <p className={cn('font-medium', !notification.read && 'font-semibold')}>
              {notification.title}
            </p>
            {!notification.read && (
              <Circle className="mt-1.5 h-2 w-2 flex-shrink-0 fill-blue-500 text-blue-500" />
            )}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">{notification.body}</p>
          <p className="mt-2 text-xs text-muted-foreground">{timeAgo}</p>
        </div>
      </div>
    </button>
  )
}
