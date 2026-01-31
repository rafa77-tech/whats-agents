'use client'

import { cn } from '@/lib/utils'

interface CapacityBarProps {
  used: number
  total: number
}

export function CapacityBar({ used, total }: CapacityBarProps) {
  const percentage = total > 0 ? Math.round((used / total) * 100) : 0

  const getColor = () => {
    if (percentage >= 90) return 'bg-red-500'
    if (percentage >= 70) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">
          Capacidade: {used}/{total} grupos
        </span>
        <span className="text-sm text-gray-500">{percentage}%</span>
      </div>
      <div className="h-4 w-full overflow-hidden rounded-full bg-gray-200">
        <div
          className={cn('h-full transition-all duration-500', getColor())}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {percentage >= 80 && (
        <p className="mt-1 text-xs text-yellow-600">
          Capacidade quase no limite. Considere adicionar mais chips.
        </p>
      )}
    </div>
  )
}
