'use client'

import { useCallback, useEffect, useState } from 'react'
import { Download, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/hooks/use-auth'
import { KPICards } from './components/kpi-cards'
import { ConversionFunnel } from './components/conversion-funnel'
import { TrendChart } from './components/trend-chart'
import { ResponseTimeChart } from './components/response-time-chart'
import { DateRangePicker } from './components/date-range-picker'

interface DateRange {
  from: Date
  to: Date
}

interface MetricsData {
  kpis: {
    total_messages: { label: string; value: string; change: number; changeLabel: string }
    active_doctors: { label: string; value: string; change: number; changeLabel: string }
    conversion_rate: { label: string; value: string; change: number; changeLabel: string }
    avg_response_time: { label: string; value: string; change: number; changeLabel: string }
  }
  funnel: Array<{ name: string; count: number; percentage: number; color: string }>
  trends: Array<{ date: string; messages: number; conversions: number }>
  response_times: Array<{ hour: string; avg_time_seconds: number; count: number }>
}

export default function MetricasPage() {
  const { session } = useAuth()
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [data, setData] = useState<MetricsData | null>(null)
  const [dateRange, setDateRange] = useState<DateRange>({
    from: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
    to: new Date(),
  })

  const fetchMetrics = useCallback(async () => {
    if (!session?.access_token) return

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const fromDate = dateRange.from.toISOString().split('T')[0]
      const toDate = dateRange.to.toISOString().split('T')[0]

      const response = await fetch(`${apiUrl}/dashboard/metrics?from=${fromDate}&to=${toDate}`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      })

      if (response.ok) {
        const result = await response.json()
        setData(result)
      }
    } catch (err) {
      console.error('Failed to fetch metrics:', err)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [session?.access_token, dateRange])

  useEffect(() => {
    fetchMetrics()
  }, [fetchMetrics])

  const handleRefresh = () => {
    setRefreshing(true)
    fetchMetrics()
  }

  const handleExport = async () => {
    if (!session?.access_token) return

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const fromDate = dateRange.from.toISOString().split('T')[0]
      const toDate = dateRange.to.toISOString().split('T')[0]

      const response = await fetch(
        `${apiUrl}/dashboard/metrics/export?from=${fromDate}&to=${toDate}`,
        {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        }
      )

      if (response.ok) {
        const result = await response.json()
        // Download as CSV
        const blob = new Blob([result.content], { type: 'text/csv' })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = result.filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
      }
    } catch (err) {
      console.error('Failed to export metrics:', err)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6 p-4 md:p-6">
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
        <Skeleton className="h-64" />
      </div>
    )
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <h1 className="text-2xl font-bold">Metricas</h1>
          <p className="text-muted-foreground">Analise de performance da Julia</p>
        </div>
        <div className="flex gap-2">
          <DateRangePicker value={dateRange} onChange={setDateRange} />
          <Button variant="outline" size="icon" onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          </Button>
          <Button variant="outline" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
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
