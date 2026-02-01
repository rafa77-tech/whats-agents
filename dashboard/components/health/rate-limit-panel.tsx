'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface RateLimitPanelProps {
  rateLimit:
    | {
        hourly: { used: number; limit: number }
        daily: { used: number; limit: number }
      }
    | undefined
}

export function RateLimitPanel({ rateLimit }: RateLimitPanelProps) {
  // Safe access with fallbacks
  const hourly = rateLimit?.hourly ?? { used: 0, limit: 20 }
  const daily = rateLimit?.daily ?? { used: 0, limit: 100 }

  const hourlyPercentage = hourly.limit > 0 ? Math.round((hourly.used / hourly.limit) * 100) : 0
  const dailyPercentage = daily.limit > 0 ? Math.round((daily.used / daily.limit) * 100) : 0

  const getProgressColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-red-500'
    if (percentage >= 70) return 'bg-yellow-500'
    return 'bg-green-500'
  }

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
            <span className="text-sm font-medium text-gray-700">Por Hora</span>
            <span className="text-sm text-gray-500">
              {hourly.used}/{hourly.limit} ({hourlyPercentage}%)
            </span>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-gray-200">
            <div
              className={cn(
                'h-full transition-all duration-500',
                getProgressColor(hourlyPercentage)
              )}
              style={{ width: `${hourlyPercentage}%` }}
            />
          </div>
          {hourlyPercentage >= 80 && (
            <p className="mt-1 text-xs text-yellow-600">
              Proximo do limite horario ({100 - hourlyPercentage}% restante)
            </p>
          )}
        </div>

        {/* Daily */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">Por Dia</span>
            <span className="text-sm text-gray-500">
              {daily.used}/{daily.limit} ({dailyPercentage}%)
            </span>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-gray-200">
            <div
              className={cn(
                'h-full transition-all duration-500',
                getProgressColor(dailyPercentage)
              )}
              style={{ width: `${dailyPercentage}%` }}
            />
          </div>
          {dailyPercentage >= 80 && (
            <p className="mt-1 text-xs text-yellow-600">
              Proximo do limite diario ({100 - dailyPercentage}% restante)
            </p>
          )}
        </div>

        <p className="text-xs text-gray-400">
          Limites configurados para evitar ban do WhatsApp. Mensagens excedentes sao enfileiradas.
        </p>
      </CardContent>
    </Card>
  )
}
