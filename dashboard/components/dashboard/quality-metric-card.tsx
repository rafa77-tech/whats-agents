'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Check, AlertTriangle, AlertCircle, TrendingUp, TrendingDown, Info } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import {
  type QualityMetricData,
  type QualityUnit,
  type QualityThreshold,
  type ThresholdOperator,
} from '@/types/dashboard'

interface QualityMetricCardProps {
  data: QualityMetricData
}

function formatValue(value: number, unit: QualityUnit): string {
  if (unit === 'percent') {
    return `${value.toFixed(1)}%`
  }
  return `${value.toFixed(0)}s`
}

function getQualityStatus(
  value: number,
  threshold: QualityThreshold,
  operator: ThresholdOperator
): 'good' | 'warning' | 'critical' {
  const isGood = operator === 'lt' ? value < threshold.good : value > threshold.good
  const isWarning = operator === 'lt' ? value < threshold.warning : value > threshold.warning

  if (isGood) return 'good'
  if (isWarning) return 'warning'
  return 'critical'
}

function StatusBadge({ status }: { status: 'good' | 'warning' | 'critical' }) {
  const config = {
    good: {
      className: 'bg-status-success text-status-success-foreground border-status-success-border',
      icon: Check,
      label: 'Otimo',
    },
    warning: {
      className: 'bg-status-warning text-status-warning-foreground border-status-warning-border',
      icon: AlertTriangle,
      label: 'Atencao',
    },
    critical: {
      className: 'bg-status-error text-status-error-foreground border-status-error-border',
      icon: AlertCircle,
      label: 'Critico',
    },
  }

  const { className, icon: Icon, label } = config[status]

  return (
    <Badge className={className}>
      <Icon className="mr-1 h-3 w-3" />
      {label}
    </Badge>
  )
}

export function QualityMetricCard({ data }: QualityMetricCardProps) {
  const { label, value, unit, threshold, operator, previousValue, tooltip } = data
  const status = getQualityStatus(value, threshold, operator)

  // Para comparativo, inversao de logica para "menos e melhor"
  const diff = previousValue !== 0 ? ((value - previousValue) / previousValue) * 100 : 0

  // Se operator e "lt", queda e positiva (melhor)
  const isImprovement = operator === 'lt' ? diff < 0 : diff > 0

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
          {tooltip && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Info className="h-4 w-4 text-muted-foreground/70" />
                </TooltipTrigger>
                <TooltipContent>
                  <p className="max-w-xs">{tooltip}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-end justify-between">
          <div>
            <div className="text-3xl font-bold">{formatValue(value, unit)}</div>
            <div className="mt-1 text-sm text-muted-foreground">
              Meta: {operator === 'lt' ? '<' : '>'} {formatValue(threshold.good, unit)}
            </div>
          </div>
          <StatusBadge status={status} />
        </div>

        <div className="mt-4 flex items-center justify-between border-t pt-4">
          <span className="text-sm text-muted-foreground">
            vs sem. ant: {formatValue(previousValue, unit)}
          </span>
          {Math.abs(diff) >= 1 && (
            <span
              className={`flex items-center text-sm ${
                isImprovement ? 'text-status-success-foreground' : 'text-status-error-foreground'
              }`}
            >
              {isImprovement ? (
                <TrendingDown className="mr-1 h-3 w-3" />
              ) : (
                <TrendingUp className="mr-1 h-3 w-3" />
              )}
              {diff > 0 ? '+' : ''}
              {diff.toFixed(0)}%
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
