'use client'

import { cn } from '@/lib/utils'

interface HealthGaugeProps {
  score: number
  status: 'healthy' | 'degraded' | 'critical'
}

export function HealthGauge({ score, status }: HealthGaugeProps) {
  // Calculate the stroke dashoffset for the progress arc
  const circumference = 2 * Math.PI * 45 // radius = 45
  const strokeDashoffset = circumference - (score / 100) * circumference

  const getColor = () => {
    if (status === 'healthy') return { stroke: '#22c55e', bg: '#dcfce7' }
    if (status === 'degraded') return { stroke: '#eab308', bg: '#fef9c3' }
    return { stroke: '#ef4444', bg: '#fee2e2' }
  }

  const colors = getColor()

  return (
    <div className="relative h-40 w-40">
      <svg className="h-full w-full -rotate-90 transform" viewBox="0 0 100 100">
        {/* Background circle */}
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke="#e5e7eb"
          strokeWidth="8"
          strokeLinecap="round"
        />
        {/* Progress arc */}
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke={colors.stroke}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className="transition-all duration-500 ease-out"
        />
      </svg>
      {/* Score display */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-center">
          <span
            className={cn(
              'text-4xl font-bold',
              status === 'healthy' && 'text-green-600',
              status === 'degraded' && 'text-yellow-600',
              status === 'critical' && 'text-red-600'
            )}
          >
            {score}
          </span>
          <span className="text-sm text-gray-400">/100</span>
        </div>
      </div>
    </div>
  )
}
