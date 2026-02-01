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

const severityConfig: Record<
  string,
  {
    icon: typeof AlertCircle
    bgColor: string
    borderColor: string
    iconColor: string
    textColor: string
  }
> = {
  critical: {
    icon: AlertCircle,
    bgColor: 'bg-status-error/10',
    borderColor: 'border-status-error-border',
    iconColor: 'text-status-error-solid',
    textColor: 'text-status-error-foreground',
  },
  warning: {
    icon: AlertTriangle,
    bgColor: 'bg-status-warning/10',
    borderColor: 'border-status-warning-border',
    iconColor: 'text-status-warning-solid',
    textColor: 'text-status-warning-foreground',
  },
  info: {
    icon: Info,
    bgColor: 'bg-status-info/10',
    borderColor: 'border-status-info-border',
    iconColor: 'text-status-info-solid',
    textColor: 'text-status-info-foreground',
  },
}

const defaultSeverityConfig = {
  icon: Info,
  bgColor: 'bg-muted/50',
  borderColor: 'border-border',
  iconColor: 'text-muted-foreground',
  textColor: 'text-foreground',
}

export function AlertItem({ alert }: AlertItemProps) {
  const { severity, title, message, createdAt, actionLabel, actionUrl } = alert
  const config = severityConfig[severity] || defaultSeverityConfig
  const Icon = config.icon

  return (
    <div className={`rounded-lg border p-3 ${config.bgColor} ${config.borderColor} `}>
      <div className="flex items-start gap-3">
        <Icon className={`mt-0.5 h-5 w-5 ${config.iconColor}`} />

        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <h4 className={`text-sm font-medium ${config.textColor}`}>{title}</h4>
            <span className="whitespace-nowrap text-xs text-muted-foreground">
              {formatDistanceToNow(new Date(createdAt), {
                addSuffix: true,
                locale: ptBR,
              })}
            </span>
          </div>

          <p className="mt-0.5 text-sm text-muted-foreground">{message}</p>

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
