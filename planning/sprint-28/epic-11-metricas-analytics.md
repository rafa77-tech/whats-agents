# E11: Métricas e Analytics

**Épico:** Dashboard Analítico + KPIs + Gráficos
**Estimativa:** 8h
**Prioridade:** P1 (Core)
**Dependências:** E01, E02, E04

---

## Objetivo

Implementar visualização de métricas e analytics:
- KPIs principais
- Gráficos de tendência
- Funil de conversão
- Métricas de campanha
- Exportação de relatórios

---

## Estrutura de Arquivos

```
app/(dashboard)/metricas/
├── page.tsx                   # Dashboard analítico
├── components/
│   ├── kpi-cards.tsx
│   ├── conversion-funnel.tsx
│   ├── trend-chart.tsx
│   ├── campaign-stats.tsx
│   ├── response-time-chart.tsx
│   ├── date-range-picker.tsx
│   └── metric-card.tsx
```

---

## Stories

### S11.1: Página de Métricas

**Arquivo:** `app/(dashboard)/metricas/page.tsx`

```typescript
'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Download, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api/client'
import { KPICards } from './components/kpi-cards'
import { ConversionFunnel } from './components/conversion-funnel'
import { TrendChart } from './components/trend-chart'
import { ResponseTimeChart } from './components/response-time-chart'
import { DateRangePicker } from './components/date-range-picker'

type DateRange = {
  from: Date
  to: Date
}

export default function MetricasPage() {
  const [dateRange, setDateRange] = useState<DateRange>({
    from: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // 30 dias
    to: new Date()
  })

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['metrics', dateRange],
    queryFn: () => api.get('/dashboard/metrics', {
      params: {
        from: dateRange.from.toISOString(),
        to: dateRange.to.toISOString()
      }
    })
  })

  const handleExport = async () => {
    const response = await api.get('/dashboard/metrics/export', {
      params: {
        from: dateRange.from.toISOString(),
        to: dateRange.to.toISOString()
      }
    })
    // Download CSV
  }

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  return (
    <div className="p-4 md:p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Métricas</h1>
          <p className="text-muted-foreground">
            Análise de performance da Julia
          </p>
        </div>
        <div className="flex gap-2">
          <DateRangePicker
            value={dateRange}
            onChange={setDateRange}
          />
          <Button variant="outline" size="icon" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button variant="outline" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            <span className="hidden md:inline">Exportar</span>
          </Button>
        </div>
      </div>

      {/* KPIs */}
      <KPICards data={data?.kpis} />

      {/* Charts Grid */}
      <div className="grid gap-6 md:grid-cols-2">
        <ConversionFunnel data={data?.funnel} />
        <TrendChart data={data?.trends} />
      </div>

      {/* Response Time */}
      <ResponseTimeChart data={data?.response_times} />
    </div>
  )
}
```

---

### S11.2: KPI Cards

**Arquivo:** `app/(dashboard)/metricas/components/kpi-cards.tsx`

```typescript
'use client'

import {
  MessageCircle,
  Users,
  TrendingUp,
  Clock,
  ArrowUp,
  ArrowDown
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface KPI {
  label: string
  value: number | string
  change: number
  changeLabel: string
  icon: 'messages' | 'users' | 'conversion' | 'time'
}

interface Props {
  data?: {
    total_messages: KPI
    active_doctors: KPI
    conversion_rate: KPI
    avg_response_time: KPI
  }
}

const ICONS = {
  messages: MessageCircle,
  users: Users,
  conversion: TrendingUp,
  time: Clock
}

export function KPICards({ data }: Props) {
  if (!data) return null

  const kpis = [
    { ...data.total_messages, icon: 'messages' as const },
    { ...data.active_doctors, icon: 'users' as const },
    { ...data.conversion_rate, icon: 'conversion' as const },
    { ...data.avg_response_time, icon: 'time' as const }
  ]

  return (
    <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
      {kpis.map((kpi, index) => {
        const Icon = ICONS[kpi.icon]
        const isPositive = kpi.change >= 0
        const ChangeIcon = isPositive ? ArrowUp : ArrowDown

        return (
          <Card key={index}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {kpi.label}
              </CardTitle>
              <Icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{kpi.value}</div>
              <div className={cn(
                'flex items-center text-xs mt-1',
                isPositive ? 'text-green-600' : 'text-red-600'
              )}>
                <ChangeIcon className="h-3 w-3 mr-1" />
                <span>{Math.abs(kpi.change)}%</span>
                <span className="text-muted-foreground ml-1">
                  {kpi.changeLabel}
                </span>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
```

---

### S11.3: Funil de Conversão

**Arquivo:** `app/(dashboard)/metricas/components/conversion-funnel.tsx`

```typescript
'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'

interface FunnelStage {
  name: string
  count: number
  percentage: number
  color: string
}

interface Props {
  data?: FunnelStage[]
}

const DEFAULT_DATA: FunnelStage[] = [
  { name: 'Prospecção', count: 0, percentage: 100, color: 'bg-gray-400' },
  { name: 'Engajados', count: 0, percentage: 0, color: 'bg-blue-400' },
  { name: 'Negociando', count: 0, percentage: 0, color: 'bg-yellow-400' },
  { name: 'Convertidos', count: 0, percentage: 0, color: 'bg-green-400' }
]

export function ConversionFunnel({ data = DEFAULT_DATA }: Props) {
  const total = data[0]?.count || 1

  return (
    <Card>
      <CardHeader>
        <CardTitle>Funil de Conversão</CardTitle>
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
            <div className="relative">
              <Progress
                value={stage.percentage}
                className="h-3"
              />
              <div
                className={`absolute inset-0 h-3 rounded-full ${stage.color}`}
                style={{ width: `${stage.percentage}%` }}
              />
            </div>
            {index < data.length - 1 && (
              <div className="flex justify-center">
                <div className="w-0.5 h-4 bg-border" />
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
```

---

### S11.4: Gráfico de Tendência

**Arquivo:** `app/(dashboard)/metricas/components/trend-chart.tsx`

```typescript
'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts'

interface DataPoint {
  date: string
  messages: number
  conversions: number
}

interface Props {
  data?: DataPoint[]
}

export function TrendChart({ data = [] }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Tendência</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="date"
                className="text-xs"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <YAxis
                className="text-xs"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px'
                }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="messages"
                name="Mensagens"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="conversions"
                name="Conversões"
                stroke="hsl(142.1 76.2% 36.3%)"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
```

---

### S11.5: Tempo de Resposta

**Arquivo:** `app/(dashboard)/metricas/components/response-time-chart.tsx`

```typescript
'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts'

interface DataPoint {
  hour: string
  avg_time_seconds: number
  count: number
}

interface Props {
  data?: DataPoint[]
}

export function ResponseTimeChart({ data = [] }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Tempo Médio de Resposta por Hora</CardTitle>
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
              />
              <YAxis
                className="text-xs"
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
                label={{
                  value: 'segundos',
                  angle: -90,
                  position: 'insideLeft',
                  style: { fill: 'hsl(var(--muted-foreground))' }
                }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px'
                }}
                formatter={(value: number) => [`${value}s`, 'Tempo médio']}
              />
              <Bar
                dataKey="avg_time_seconds"
                fill="hsl(var(--primary))"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
```

---

## Backend Endpoints

```python
# app/api/routes/dashboard/metrics.py

@router.get("")
async def get_metrics(
    user: CurrentUser,
    from_date: str = Query(...),
    to_date: str = Query(...)
):
    """Retorna métricas agregadas para o período."""

    # KPIs
    kpis = await calculate_kpis(from_date, to_date)

    # Funil
    funnel = await calculate_funnel()

    # Tendências
    trends = await calculate_trends(from_date, to_date)

    # Tempos de resposta
    response_times = await calculate_response_times(from_date, to_date)

    return {
        "kpis": kpis,
        "funnel": funnel,
        "trends": trends,
        "response_times": response_times
    }

@router.get("/export")
async def export_metrics(
    user: CurrentUser,
    from_date: str = Query(...),
    to_date: str = Query(...)
):
    """Exporta métricas em CSV."""
    # Gera CSV com dados do período
```

---

## Checklist Final

- [ ] KPI cards com comparativo
- [ ] Funil de conversão visual
- [ ] Gráfico de tendência linha
- [ ] Gráfico de tempo de resposta
- [ ] Date range picker
- [ ] Exportação CSV
- [ ] Refresh manual
- [ ] Mobile responsivo
- [ ] Recharts integrado
