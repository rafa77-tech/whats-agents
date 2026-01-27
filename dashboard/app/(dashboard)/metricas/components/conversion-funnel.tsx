'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface FunnelStage {
  name: string
  count: number
  percentage: number
  color: string
}

interface Props {
  data?: FunnelStage[] | undefined
}

const DEFAULT_DATA: FunnelStage[] = [
  { name: 'Prospeccao', count: 0, percentage: 100, color: 'bg-gray-400' },
  { name: 'Engajados', count: 0, percentage: 0, color: 'bg-blue-400' },
  { name: 'Negociando', count: 0, percentage: 0, color: 'bg-yellow-400' },
  { name: 'Convertidos', count: 0, percentage: 0, color: 'bg-green-400' },
]

export function ConversionFunnel({ data = DEFAULT_DATA }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Funil de Conversao</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {data.map((stage, index) => (
          <div key={stage.name} className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="font-medium">{stage.name}</span>
              <span className="text-muted-foreground">
                {stage.count} ({stage.percentage.toFixed(1)}%)
              </span>
            </div>
            <div className="relative h-3 w-full overflow-hidden rounded-full bg-secondary">
              <div
                className={`h-full rounded-full ${stage.color}`}
                style={{ width: `${stage.percentage}%` }}
              />
            </div>
            {index < data.length - 1 && (
              <div className="flex justify-center">
                <div className="h-4 w-0.5 bg-border" />
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
