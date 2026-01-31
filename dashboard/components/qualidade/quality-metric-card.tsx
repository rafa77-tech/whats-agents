'use client'

import { Card, CardContent } from '@/components/ui/card'
import { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface QualityMetricCardProps {
  title: string
  value: number
  suffix?: string
  icon: LucideIcon
  color: 'green' | 'yellow' | 'blue' | 'red'
}

const colorClasses = {
  green: {
    bg: 'bg-green-50',
    text: 'text-green-600',
    icon: 'text-green-400',
  },
  yellow: {
    bg: 'bg-yellow-50',
    text: 'text-yellow-600',
    icon: 'text-yellow-400',
  },
  blue: {
    bg: 'bg-blue-50',
    text: 'text-blue-600',
    icon: 'text-blue-400',
  },
  red: {
    bg: 'bg-red-50',
    text: 'text-red-600',
    icon: 'text-red-400',
  },
}

export function QualityMetricCard({
  title,
  value,
  suffix,
  icon: Icon,
  color,
}: QualityMetricCardProps) {
  const colors = colorClasses[color]

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
