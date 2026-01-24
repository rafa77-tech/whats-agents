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
    color: 'bg-green-50 border-green-200',
    icon: CheckCircle,
    iconColor: 'text-green-500',
    label: 'Saudável',
    labelColor: 'bg-green-100 text-green-800',
  },
  attention: {
    color: 'bg-blue-50 border-blue-200',
    icon: Info,
    iconColor: 'text-blue-500',
    label: 'Atenção',
    labelColor: 'bg-blue-100 text-blue-800',
  },
  warning: {
    color: 'bg-yellow-50 border-yellow-200',
    icon: AlertCircle,
    iconColor: 'text-yellow-500',
    label: 'Alerta',
    labelColor: 'bg-yellow-100 text-yellow-800',
  },
  critical: {
    color: 'bg-red-50 border-red-200',
    icon: XCircle,
    iconColor: 'text-red-500',
    label: 'Crítico',
    labelColor: 'bg-red-100 text-red-800',
  },
}

const defaultHealthConfig = {
  color: 'bg-gray-50 border-gray-200',
  icon: Info,
  iconColor: 'text-gray-500',
  label: 'Desconhecido',
  labelColor: 'bg-gray-100 text-gray-800',
}

const issueTypeConfig: Record<
  string,
  { icon: typeof TrendingDown; color: string; bgColor: string }
> = {
  trust_dropping: {
    icon: TrendingDown,
    color: 'text-orange-500',
    bgColor: 'bg-orange-50',
  },
  high_errors: {
    icon: XCircle,
    color: 'text-red-500',
    bgColor: 'bg-red-50',
  },
  low_capacity: {
    icon: Battery,
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-50',
  },
  stale_chips: {
    icon: Clock,
    color: 'text-gray-500',
    bgColor: 'bg-gray-50',
  },
  ban_risk: {
    icon: AlertTriangle,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
  },
}

const defaultIssueTypeConfig = {
  icon: AlertCircle,
  color: 'text-gray-500',
  bgColor: 'bg-gray-50',
}

const severityBadgeConfig: Record<string, string> = {
  info: 'bg-blue-100 text-blue-800',
  warning: 'bg-yellow-100 text-yellow-800',
  critical: 'bg-red-100 text-red-800',
}

const defaultSeverityBadge = 'bg-gray-100 text-gray-800'

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
          <div className="h-6 w-48 rounded bg-gray-200" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="h-16 rounded bg-gray-200" />
            <div className="h-16 rounded bg-gray-200" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error || !health) {
    return (
      <Card className={cn('border-gray-200', className)}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <AlertTriangle className="h-5 w-5 text-gray-400" />
            Saúde do Pool
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">{error || 'Dados indisponíveis'}</p>
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
          <div className="text-sm text-gray-500">
            Atualizado em {new Date(health.lastUpdated).toLocaleTimeString('pt-BR')}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {health.issues.length === 0 ? (
          <div className="flex items-center gap-2 text-green-600">
            <CheckCircle className="h-4 w-4" />
            <span className="text-sm">Nenhum problema identificado</span>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm font-medium text-gray-600">
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
    <div className={cn('rounded-lg border p-3', typeConfig.bgColor, 'border-gray-200')}>
      <div className="flex items-start gap-3">
        <div className={cn('rounded-md p-1.5', 'bg-white')}>
          <IssueIcon className={cn('h-4 w-4', typeConfig.color)} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-gray-900">{issue.message}</span>
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
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span>
              {issue.affectedChips} chip{issue.affectedChips > 1 ? 's' : ''} afetado
              {issue.affectedChips > 1 ? 's' : ''}
            </span>
          </div>
          {issue.recommendation && (
            <p className="mt-2 rounded bg-white/50 p-2 text-xs text-gray-600">
              <strong>Recomendação:</strong> {issue.recommendation}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
