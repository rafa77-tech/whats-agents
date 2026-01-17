/**
 * Alert Item Component - Sprint 33 E13
 *
 * Individual alert item with severity-based styling.
 */

'use client'

import { type DashboardAlert } from '@/types/dashboard'
import { Button } from '@/components/ui/button'
import { AlertCircle, AlertTriangle, Info, ExternalLink } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'

interface AlertItemProps {
  alert: DashboardAlert
}

const severityConfig = {
  critical: {
    icon: AlertCircle,
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    iconColor: 'text-red-500',
    textColor: 'text-red-800',
  },
  warning: {
    icon: AlertTriangle,
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    iconColor: 'text-yellow-500',
    textColor: 'text-yellow-800',
  },
  info: {
    icon: Info,
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    iconColor: 'text-blue-500',
    textColor: 'text-blue-800',
  },
}

export function AlertItem({ alert }: AlertItemProps) {
  const { severity, title, message, createdAt, actionLabel, actionUrl } = alert
  const config = severityConfig[severity]
  const Icon = config.icon

  return (
    <div className={`rounded-lg border p-3 ${config.bgColor} ${config.borderColor} `}>
      <div className="flex items-start gap-3">
        <Icon className={`mt-0.5 h-5 w-5 ${config.iconColor}`} />

        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <h4 className={`text-sm font-medium ${config.textColor}`}>{title}</h4>
            <span className="whitespace-nowrap text-xs text-gray-500">
              {formatDistanceToNow(new Date(createdAt), {
                addSuffix: true,
                locale: ptBR,
              })}
            </span>
          </div>

          <p className="mt-0.5 text-sm text-gray-600">{message}</p>

          {actionUrl && (
            <Button variant="ghost" size="sm" className="mt-2 h-7 px-2 text-xs" asChild>
              <a href={actionUrl} target="_blank" rel="noopener noreferrer">
                {actionLabel || 'Ver detalhes'}
                <ExternalLink className="ml-1 h-3 w-3" />
              </a>
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
