'use client'

import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { type LucideIcon } from 'lucide-react'

interface KpiCardProps {
  title: string
  value: number | string
  suffix?: string
  icon: LucideIcon
  status: 'good' | 'warn' | 'bad'
  trend?: number
}

export function KpiCard({ title, value, suffix, icon: Icon, status, trend }: KpiCardProps) {
  return (
    <Card
      className={cn(
        'border-2',
        status === 'good' && 'border-green-200',
        status === 'warn' && 'border-yellow-200',
        status === 'bad' && 'border-red-200'
      )}
    >
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500">{title}</p>
            <div className="mt-1 flex items-baseline gap-1">
              <span
                className={cn(
                  'text-3xl font-bold',
                  status === 'good' && 'text-green-600',
                  status === 'warn' && 'text-yellow-600',
                  status === 'bad' && 'text-red-600'
                )}
              >
                {value}
              </span>
              {suffix && <span className="text-sm text-gray-400">{suffix}</span>}
            </div>
            {trend !== undefined && (
              <p className={cn('mt-1 text-xs', trend >= 0 ? 'text-green-600' : 'text-red-600')}>
                {trend >= 0 ? '+' : ''}
                {trend}% vs ontem
              </p>
            )}
          </div>
          <div
            className={cn(
              'rounded-lg p-3',
              status === 'good' && 'bg-green-100',
              status === 'warn' && 'bg-yellow-100',
              status === 'bad' && 'bg-red-100'
            )}
          >
            <Icon
              className={cn(
                'h-6 w-6',
                status === 'good' && 'text-green-600',
                status === 'warn' && 'text-yellow-600',
                status === 'bad' && 'text-red-600'
              )}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
