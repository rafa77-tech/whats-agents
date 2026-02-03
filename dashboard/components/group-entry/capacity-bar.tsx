'use client'

import { cn } from '@/lib/utils'
import { calculateCapacityPercentage, getCapacityColor, isCapacityWarning } from '@/lib/group-entry'

interface CapacityBarProps {
  used: number
  total: number
}

export function CapacityBar({ used, total }: CapacityBarProps) {
  const percentage = calculateCapacityPercentage(used, total)
  const colorClass = getCapacityColor(percentage)
  const showWarning = isCapacityWarning(percentage)

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-medium text-foreground">
          Capacidade: {used}/{total} grupos
        </span>
        <span className="text-sm text-muted-foreground">{percentage}%</span>
      </div>
      <div className="h-4 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={cn('h-full transition-all duration-500', colorClass)}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showWarning && (
        <p className="mt-1 text-xs text-status-warning-foreground">
          Capacidade quase no limite. Considere adicionar mais chips.
        </p>
      )}
    </div>
  )
}
