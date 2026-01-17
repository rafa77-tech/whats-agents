'use client'

import { QualityMetricCard } from './quality-metric-card'
import { type QualityMetricData } from '@/types/dashboard'

interface QualityMetricsSectionProps {
  metrics: QualityMetricData[]
}

export function QualityMetricsSection({ metrics }: QualityMetricsSectionProps) {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
      {metrics.map((metric, index) => (
        <QualityMetricCard key={index} data={metric} />
      ))}
    </div>
  )
}
