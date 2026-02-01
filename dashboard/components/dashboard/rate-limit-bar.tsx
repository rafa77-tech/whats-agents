'use client'

import { type RateLimitData } from '@/types/dashboard'

interface RateLimitBarProps {
  data: RateLimitData
}

function getProgressColor(percentage: number): string {
  if (percentage < 50) return 'bg-status-success-solid'
  if (percentage < 80) return 'bg-status-warning-solid'
  return 'bg-status-error-solid'
}

export function RateLimitBar({ data }: RateLimitBarProps) {
  const { current, max, label } = data
  const percentage = (current / max) * 100

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">
          {current}/{max}
        </span>
      </div>
      <div className="h-2 rounded-full bg-muted">
        <div
          className={`h-full rounded-full transition-all ${getProgressColor(percentage)}`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
    </div>
  )
}
