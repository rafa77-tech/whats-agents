'use client'

import { MetricCard } from './metric-card'
import { type MetricData } from '@/types/dashboard'

interface MetricsSectionProps {
  metrics: MetricData[]
}

export function MetricsSection({ metrics }: MetricsSectionProps) {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
      {metrics.map((metric, index) => (
        <MetricCard key={index} data={metric} />
      ))}
    </div>
  )
}
