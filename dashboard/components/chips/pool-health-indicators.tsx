/**
 * Pool Health Indicators - Sprint 36
 *
 * Mostra indicadores de saúde do pool e alertas de problemas.
 */

'use client'

import { useState, useEffect } from 'react'
import {
  AlertTriangle,
  CheckCircle,
  Info,
  XCircle,
  TrendingDown,
  AlertCircle,
  Battery,
  Clock,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { chipsApi } from '@/lib/api/chips'
import { PoolHealthStatus, PoolHealthIssue } from '@/types/chips'

const healthStatusConfig: Record<
  string,
  {
    color: string
    icon: typeof CheckCircle
    iconColor: string
    label: string
    labelColor: string
  }
> = {
  healthy: {
    color: 'bg-status-success/10 border-status-success-border',
    icon: CheckCircle,
    iconColor: 'text-status-success-solid',
    label: 'Saudável',
    labelColor: 'bg-status-success text-status-success-foreground',
  },
  attention: {
    color: 'bg-status-info/10 border-status-info-border',
    icon: Info,
    iconColor: 'text-status-info-solid',
    label: 'Atenção',
    labelColor: 'bg-status-info text-status-info-foreground',
  },
  warning: {
    color: 'bg-status-warning/10 border-status-warning-border',
    icon: AlertCircle,
    iconColor: 'text-status-warning-solid',
    label: 'Alerta',
    labelColor: 'bg-status-warning text-status-warning-foreground',
  },
  critical: {
    color: 'bg-status-error/10 border-status-error-border',
    icon: XCircle,
    iconColor: 'text-status-error-solid',
    label: 'Crítico',
    labelColor: 'bg-status-error text-status-error-foreground',
  },
}

const defaultHealthConfig = {
  color: 'bg-muted/50 border-muted',
  icon: Info,
  iconColor: 'text-muted-foreground',
  label: 'Desconhecido',
  labelColor: 'bg-status-neutral text-status-neutral-foreground',
}

const issueTypeConfig: Record<
  string,
  { icon: typeof TrendingDown; color: string; bgColor: string }
> = {
  trust_dropping: {
    icon: TrendingDown,
    color: 'text-status-warning-foreground',
    bgColor: 'bg-status-warning/10',
  },
  high_errors: {
    icon: XCircle,
    color: 'text-status-error-solid',
    bgColor: 'bg-status-error/10',
  },
  low_capacity: {
    icon: Battery,
    color: 'text-status-warning-solid',
    bgColor: 'bg-status-warning/10',
  },
  stale_chips: {
    icon: Clock,
    color: 'text-muted-foreground',
    bgColor: 'bg-muted/50',
  },
  ban_risk: {
    icon: AlertTriangle,
    color: 'text-status-error-foreground',
    bgColor: 'bg-status-error/10',
  },
}

const defaultIssueTypeConfig = {
  icon: AlertCircle,
  color: 'text-muted-foreground',
  bgColor: 'bg-muted/50',
}

const severityBadgeConfig: Record<string, string> = {
  info: 'bg-status-info text-status-info-foreground',
  warning: 'bg-status-warning text-status-warning-foreground',
  critical: 'bg-status-error text-status-error-foreground',
}

const defaultSeverityBadge = 'bg-status-neutral text-status-neutral-foreground'

interface PoolHealthIndicatorsProps {
  className?: string
}

export function PoolHealthIndicators({ className }: PoolHealthIndicatorsProps) {
  const [health, setHealth] = useState<PoolHealthStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await chipsApi.getPoolHealth()
        setHealth(data)
        setError(null)
      } catch (err) {
        console.error('Error fetching pool health:', err)
        setError('Não foi possível carregar indicadores de saúde')
      } finally {
        setIsLoading(false)
      }
    }

    fetchHealth()
    const interval = setInterval(fetchHealth, 60000) // Atualiza a cada minuto
    return () => clearInterval(interval)
  }, [])

  if (isLoading) {
    return (
      <Card className={cn('animate-pulse', className)}>
        <CardHeader>
          <div className="h-6 w-48 rounded bg-muted" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="h-16 rounded bg-muted" />
            <div className="h-16 rounded bg-muted" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error || !health) {
    return (
      <Card className={cn('border-border', className)}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <AlertTriangle className="h-5 w-5 text-muted-foreground" />
            Saúde do Pool
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{error || 'Dados indisponíveis'}</p>
        </CardContent>
      </Card>
    )
  }

  const config = healthStatusConfig[health.status] || defaultHealthConfig
  const StatusIcon = config.icon

  return (
    <Card className={cn('border', config.color, className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <StatusIcon className={cn('h-5 w-5', config.iconColor)} />
            Saúde do Pool
          </CardTitle>
          <Badge className={config.labelColor}>{config.label}</Badge>
        </div>
        <div className="mt-2 flex items-center gap-4">
          <div className="text-2xl font-bold">{health.score}/100</div>
          <div className="text-sm text-muted-foreground">
            Atualizado em {new Date(health.lastUpdated).toLocaleTimeString('pt-BR')}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {health.issues.length === 0 ? (
          <div className="flex items-center gap-2 text-status-success-foreground">
            <CheckCircle className="h-4 w-4" />
            <span className="text-sm">Nenhum problema identificado</span>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm font-medium text-muted-foreground">
              {health.issues.length} problema{health.issues.length > 1 ? 's' : ''} identificado
              {health.issues.length > 1 ? 's' : ''}
            </p>
            <div className="space-y-2">
              {health.issues.map((issue) => (
                <HealthIssueCard key={issue.id} issue={issue} />
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

interface HealthIssueCardProps {
  issue: PoolHealthIssue
}

function HealthIssueCard({ issue }: HealthIssueCardProps) {
  const typeConfig = issueTypeConfig[issue.type] || defaultIssueTypeConfig
  const IssueIcon = typeConfig.icon

  return (
    <div className={cn('rounded-lg border p-3', typeConfig.bgColor, 'border-border')}>
      <div className="flex items-start gap-3">
        <div className={cn('rounded-md p-1.5', 'bg-background')}>
          <IssueIcon className={cn('h-4 w-4', typeConfig.color)} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-foreground">{issue.message}</span>
            <Badge
              className={cn(
                'shrink-0',
                severityBadgeConfig[issue.severity] || defaultSeverityBadge
              )}
            >
              {issue.severity === 'critical'
                ? 'Crítico'
                : issue.severity === 'warning'
                  ? 'Alerta'
                  : 'Info'}
            </Badge>
          </div>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span>
              {issue.affectedChips} chip{issue.affectedChips > 1 ? 's' : ''} afetado
              {issue.affectedChips > 1 ? 's' : ''}
            </span>
          </div>
          {issue.recommendation && (
            <p className="mt-2 rounded bg-background/50 p-2 text-xs text-muted-foreground">
              <strong>Recomendação:</strong> {issue.recommendation}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
