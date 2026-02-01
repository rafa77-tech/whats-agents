'use client'

import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { METRIC_CARD_COLORS } from '@/lib/qualidade'
import type { QualityMetricCardProps } from '@/lib/qualidade'

export function QualityMetricCard({
  title,
  value,
  suffix,
  icon: Icon,
  color,
}: QualityMetricCardProps) {
  const colors = METRIC_CARD_COLORS[color]

  return (
    <Card>
      <CardContent className={cn('flex items-center justify-between p-4', colors.bg)}>
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className={cn('text-2xl font-bold', colors.text)}>
            {value}
            {suffix && <span className="text-lg font-normal text-gray-500">{suffix}</span>}
          </p>
        </div>
        <Icon className={cn('h-8 w-8', colors.icon)} />
      </CardContent>
    </Card>
  )
}
