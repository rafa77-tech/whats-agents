'use client'

import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { type LucideIcon } from 'lucide-react'
import { getKpiStatusColors } from '@/lib/integridade'
import type { KpiStatus } from '@/lib/integridade'

interface KpiCardProps {
  title: string
  value: number | string
  suffix?: string
  icon: LucideIcon
  status: KpiStatus
  trend?: number
}

export function KpiCard({ title, value, suffix, icon: Icon, status, trend }: KpiCardProps) {
  const colors = getKpiStatusColors(status)

  return (
    <Card className={cn('border-2', colors.border)}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500">{title}</p>
            <div className="mt-1 flex items-baseline gap-1">
              <span className={cn('text-3xl font-bold', colors.text)}>{value}</span>
              {suffix && <span className="text-sm text-gray-400">{suffix}</span>}
            </div>
            {trend !== undefined && (
              <p
                className={cn(
                  'mt-1 text-xs',
                  trend >= 0 ? 'text-status-success-foreground' : 'text-status-error-foreground'
                )}
              >
                {trend >= 0 ? '+' : ''}
                {trend}% vs ontem
              </p>
            )}
          </div>
          <div className={cn('rounded-lg p-3', colors.bg)}>
            <Icon className={cn('h-6 w-6', colors.icon)} />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
