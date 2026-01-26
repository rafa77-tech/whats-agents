'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface DataPoint {
  hour: string
  avg_time_seconds: number
  count: number
}

interface Props {
  data?: DataPoint[] | undefined
}

export function ResponseTimeChart({ data = [] }: Props) {
  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Tempo Medio de Resposta por Hora</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-[300px] items-center justify-center text-muted-foreground">
            Sem dados para o periodo
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Tempo Medio de Resposta por Hora</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="hour"
                className="text-xs"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
                interval={2}
              />
              <YAxis
                className="text-xs"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
                label={{
                  value: 'segundos',
                  angle: -90,
                  position: 'insideLeft',
                  style: { fill: 'hsl(var(--muted-foreground))' },
                }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                }}
                formatter={(value) => [`${value}s`, 'Tempo medio']}
              />
              <Bar dataKey="avg_time_seconds" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
