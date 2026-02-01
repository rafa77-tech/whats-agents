/**
 * Activity Item Component - Sprint 33 E14
 *
 * Individual activity event in the feed timeline.
 */

'use client'

import { type ActivityEvent } from '@/types/dashboard'
import {
  CheckCircle,
  RefreshCw,
  Send,
  MessageSquare,
  Award,
  AlertTriangle,
  type LucideIcon,
} from 'lucide-react'
import { format } from 'date-fns'

interface ActivityItemProps {
  event: ActivityEvent
}

const typeConfig: Record<
  string,
  {
    icon: LucideIcon
    bgColor: string
    iconColor: string
  }
> = {
  fechamento: {
    icon: CheckCircle,
    bgColor: 'bg-status-success',
    iconColor: 'text-status-success-foreground',
  },
  handoff: {
    icon: RefreshCw,
    bgColor: 'bg-status-info',
    iconColor: 'text-status-info-foreground',
  },
  campanha: {
    icon: Send,
    bgColor: 'bg-purple-100',
    iconColor: 'text-purple-600',
  },
  resposta: {
    icon: MessageSquare,
    bgColor: 'bg-status-success',
    iconColor: 'text-status-success-foreground',
  },
  chip: {
    icon: Award,
    bgColor: 'bg-status-warning',
    iconColor: 'text-status-warning-foreground',
  },
  alerta: {
    icon: AlertTriangle,
    bgColor: 'bg-orange-100',
    iconColor: 'text-orange-600',
  },
}

const defaultTypeConfig = {
  icon: MessageSquare,
  bgColor: 'bg-status-neutral',
  iconColor: 'text-muted-foreground',
}

export function ActivityItem({ event }: ActivityItemProps) {
  const { type, message, chipName, timestamp } = event
  const config = typeConfig[type] || defaultTypeConfig
  const Icon = config.icon

  const time = format(new Date(timestamp), 'HH:mm')

  return (
    <div className="flex items-start gap-3 py-2">
      {/* Timestamp */}
      <span className="w-12 pt-0.5 text-xs text-muted-foreground/70">{time}</span>

      {/* Icon */}
      <div className={`rounded-full p-1.5 ${config.bgColor}`}>
        <Icon className={`h-3.5 w-3.5 ${config.iconColor}`} />
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <p className="text-sm text-foreground/80">
          {chipName && <span className="font-medium text-foreground">{chipName} </span>}
          {message}
        </p>
      </div>
    </div>
  )
}
