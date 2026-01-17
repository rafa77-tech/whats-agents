/**
 * Trends Section Component - Sprint 33 E12
 *
 * Card containing multiple sparkline charts for key metrics.
 */

'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { SparklineChart } from './sparkline-chart'
import { type TrendsData } from '@/types/dashboard'
import { TrendingUp } from 'lucide-react'

interface TrendsSectionProps {
  data: TrendsData
}

export function TrendsSection({ data }: TrendsSectionProps) {
  const { metrics, period } = data

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-gray-500">
          <TrendingUp className="h-4 w-4" />
          Tendencias ({period})
        </CardTitle>
      </CardHeader>
      <CardContent className="divide-y">
        {metrics.map((metric) => (
          <SparklineChart key={metric.id} metric={metric} />
        ))}
      </CardContent>
    </Card>
  )
}
