'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import {
  DEFAULT_RATE_LIMIT,
  getProgressColor,
  calculatePercentage,
  shouldShowRateLimitWarning,
} from '@/lib/health'
import type { RateLimitData } from '@/lib/health'

interface RateLimitPanelProps {
  rateLimit: RateLimitData | undefined
}

export function RateLimitPanel({ rateLimit }: RateLimitPanelProps) {
  // Safe access with fallbacks
  const hourly = rateLimit?.hourly ?? DEFAULT_RATE_LIMIT.hourly
  const daily = rateLimit?.daily ?? DEFAULT_RATE_LIMIT.daily

  const hourlyPercentage = calculatePercentage(hourly.used, hourly.limit)
  const dailyPercentage = calculatePercentage(daily.used, daily.limit)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Rate Limiting</CardTitle>
        <CardDescription>Uso de limite de mensagens</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Hourly */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-foreground/80">Por Hora</span>
            <span className="text-sm text-muted-foreground">
              {hourly.used}/{hourly.limit} ({hourlyPercentage}%)
            </span>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
            <div
              className={cn(
                'h-full transition-all duration-500',
                getProgressColor(hourlyPercentage)
              )}
              style={{ width: `${hourlyPercentage}%` }}
            />
          </div>
          {shouldShowRateLimitWarning(hourlyPercentage) && (
            <p className="mt-1 text-xs text-status-warning-foreground">
              Proximo do limite horario ({100 - hourlyPercentage}% restante)
            </p>
          )}
        </div>

        {/* Daily */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-foreground/80">Por Dia</span>
            <span className="text-sm text-muted-foreground">
              {daily.used}/{daily.limit} ({dailyPercentage}%)
            </span>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
            <div
              className={cn(
                'h-full transition-all duration-500',
                getProgressColor(dailyPercentage)
              )}
              style={{ width: `${dailyPercentage}%` }}
            />
          </div>
          {shouldShowRateLimitWarning(dailyPercentage) && (
            <p className="mt-1 text-xs text-status-warning-foreground">
              Proximo do limite diario ({100 - dailyPercentage}% restante)
            </p>
          )}
        </div>

        <p className="text-xs text-muted-foreground/70">
          Limites configurados para evitar ban do WhatsApp. Mensagens excedentes sao enfileiradas.
        </p>
      </CardContent>
    </Card>
  )
}
