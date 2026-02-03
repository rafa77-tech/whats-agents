'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChipStatusCounters } from './chip-status-counters'
import { ChipTrustDistribution } from './chip-trust-distribution'
import { ChipPoolMetricsComponent } from './chip-pool-metrics'
import { type ChipPoolOverviewData } from '@/types/dashboard'
import { Smartphone } from 'lucide-react'

interface ChipPoolOverviewProps {
  data: ChipPoolOverviewData
}

export function ChipPoolOverview({ data }: ChipPoolOverviewProps) {
  const { statusCounts, trustDistribution, metrics } = data

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Smartphone className="h-4 w-4" />
          Pool de Chips
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Linha 1: Status + Trust */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <ChipStatusCounters counts={statusCounts} />
          <ChipTrustDistribution distribution={trustDistribution} />
        </div>

        {/* Linha 2: Metricas */}
        <div className="border-t pt-4">
          <ChipPoolMetricsComponent metrics={metrics} />
        </div>
      </CardContent>
    </Card>
  )
}
