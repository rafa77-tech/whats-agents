/**
 * Dashboard Principal - Sprint 33
 *
 * Layout base com grid responsivo para o dashboard de performance Julia.
 * Busca dados reais das APIs do Supabase.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { DashboardHeader } from '@/components/dashboard/dashboard-header'
import { MetricsSection } from '@/components/dashboard/metrics-section'
import { QualityMetricsSection } from '@/components/dashboard/quality-metrics-section'
import { OperationalStatus } from '@/components/dashboard/operational-status'
import { ChipPoolOverview } from '@/components/dashboard/chip-pool-overview'
import { ChipListTable } from '@/components/dashboard/chip-list-table'
import { ConversionFunnel } from '@/components/dashboard/conversion-funnel'
import { FunnelDrilldownModal } from '@/components/dashboard/funnel-drilldown-modal'
import { TrendsSection } from '@/components/dashboard/trends-section'
import { AlertsList } from '@/components/dashboard/alerts-list'
import { ActivityFeed } from '@/components/dashboard/activity-feed'
import {
  type DashboardPeriod,
  type MetricData,
  type QualityMetricData,
  type OperationalStatusData,
  type ChipPoolOverviewData,
  type ChipDetail,
  type FunnelDataVisual,
  type TrendsData,
  type AlertsData,
  type ActivityFeedData,
} from '@/types/dashboard'

// Default empty states
const defaultOperationalStatus: OperationalStatusData = {
  rateLimitHour: { current: 0, max: 20, label: 'Rate Limit Hora' },
  rateLimitDay: { current: 0, max: 100, label: 'Rate Limit Dia' },
  queueSize: 0,
  llmUsage: { haiku: 80, sonnet: 20 },
  instances: [],
}

const defaultFunnel: FunnelDataVisual = {
  stages: [
    { id: 'enviadas', label: 'Enviadas', count: 0, previousCount: 0, percentage: 100 },
    { id: 'entregues', label: 'Entregues', count: 0, previousCount: 0, percentage: 0 },
    { id: 'respostas', label: 'Respostas', count: 0, previousCount: 0, percentage: 0 },
    { id: 'interesse', label: 'Interesse', count: 0, previousCount: 0, percentage: 0 },
    { id: 'fechadas', label: 'Fechadas', count: 0, previousCount: 0, percentage: 0 },
  ],
  period: '7 dias',
}

const defaultTrends: TrendsData = {
  metrics: [],
  period: '7d',
}

const defaultAlerts: AlertsData = {
  alerts: [],
  totalCritical: 0,
  totalWarning: 0,
}

const defaultActivity: ActivityFeedData = {
  events: [],
  hasMore: false,
}

export default function DashboardPage() {
  const [selectedPeriod, setSelectedPeriod] = useState<DashboardPeriod>('7d')
  const [funnelModalOpen, setFunnelModalOpen] = useState(false)
  const [selectedFunnelStage, setSelectedFunnelStage] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Data states
  const [metricsData, setMetricsData] = useState<MetricData[]>([])
  const [qualityData, setQualityData] = useState<QualityMetricData[]>([])
  const [operationalData, setOperationalData] =
    useState<OperationalStatusData>(defaultOperationalStatus)
  const [chipPoolData, setChipPoolData] = useState<ChipPoolOverviewData | null>(null)
  const [chipsList, setChipsList] = useState<ChipDetail[]>([])
  const [funnelData, setFunnelData] = useState<FunnelDataVisual>(defaultFunnel)
  const [trendsData, setTrendsData] = useState<TrendsData>(defaultTrends)
  const [alertsData, setAlertsData] = useState<AlertsData>(defaultAlerts)
  const [activityData, setActivityData] = useState<ActivityFeedData>(defaultActivity)

  // Header data
  const [juliaStatus, setJuliaStatus] = useState<'online' | 'offline' | 'degraded'>('offline')
  const [lastHeartbeat, setLastHeartbeat] = useState<Date>(new Date())

  // Fetch functions
  const fetchChipPool = useCallback(async () => {
    try {
      const response = await fetch(`/api/dashboard/chips?period=${selectedPeriod}`)
      if (response.ok) {
        const data = await response.json()
        setChipPoolData(data)
      }
    } catch (error) {
      console.error('Error fetching chip pool:', error)
    }
  }, [selectedPeriod])

  const fetchChipsList = useCallback(async () => {
    try {
      const response = await fetch(`/api/dashboard/chips/list?limit=10&sortBy=trust&order=desc`)
      if (response.ok) {
        const data = await response.json()
        setChipsList(data.chips || [])
      }
    } catch (error) {
      console.error('Error fetching chips list:', error)
    }
  }, [])

  const fetchMetrics = useCallback(async () => {
    try {
      const response = await fetch(`/api/dashboard/metrics?period=${selectedPeriod}`)
      if (response.ok) {
        const data = await response.json()
        if (data.metrics) setMetricsData(data.metrics)
      }
    } catch (error) {
      console.error('Error fetching metrics:', error)
    }
  }, [selectedPeriod])

  const fetchQuality = useCallback(async () => {
    try {
      const response = await fetch(`/api/dashboard/quality?period=${selectedPeriod}`)
      if (response.ok) {
        const data = await response.json()
        if (data.metrics) setQualityData(data.metrics)
      }
    } catch (error) {
      console.error('Error fetching quality:', error)
    }
  }, [selectedPeriod])

  const fetchOperational = useCallback(async () => {
    try {
      const response = await fetch(`/api/dashboard/operational`)
      if (response.ok) {
        const data = await response.json()
        if (data && data.rateLimitHour) setOperationalData(data)
      }
    } catch (error) {
      console.error('Error fetching operational:', error)
    }
  }, [])

  const fetchFunnel = useCallback(async () => {
    try {
      const response = await fetch(`/api/dashboard/funnel?period=${selectedPeriod}`)
      if (response.ok) {
        const data = await response.json()
        if (data && data.stages) setFunnelData(data)
      }
    } catch (error) {
      console.error('Error fetching funnel:', error)
    }
  }, [selectedPeriod])

  const fetchTrends = useCallback(async () => {
    try {
      const response = await fetch(`/api/dashboard/trends?period=${selectedPeriod}`)
      if (response.ok) {
        const data = await response.json()
        if (data && data.metrics) setTrendsData(data)
      }
    } catch (error) {
      console.error('Error fetching trends:', error)
    }
  }, [selectedPeriod])

  const fetchAlerts = useCallback(async () => {
    try {
      const response = await fetch(`/api/dashboard/alerts`)
      if (response.ok) {
        const data = await response.json()
        if (data) setAlertsData(data)
      }
    } catch (error) {
      console.error('Error fetching alerts:', error)
    }
  }, [])

  const fetchActivity = useCallback(async () => {
    try {
      const response = await fetch(`/api/dashboard/activity`)
      if (response.ok) {
        const data = await response.json()
        if (data) setActivityData(data)
      }
    } catch (error) {
      console.error('Error fetching activity:', error)
    }
  }, [])

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(`/api/dashboard/status`)
      if (response.ok) {
        const data = await response.json()
        if (data) {
          setJuliaStatus(data.status || 'offline')
          if (data.lastHeartbeat) setLastHeartbeat(new Date(data.lastHeartbeat))
        }
      }
    } catch (error) {
      console.error('Error fetching status:', error)
    }
  }, [])

  useEffect(() => {
    const fetchAllData = async () => {
      setIsLoading(true)
      await Promise.all([
        fetchStatus(),
        fetchChipPool(),
        fetchChipsList(),
        fetchMetrics(),
        fetchQuality(),
        fetchOperational(),
        fetchFunnel(),
        fetchTrends(),
        fetchAlerts(),
        fetchActivity(),
      ])
      setIsLoading(false)
    }

    void fetchAllData()
  }, [
    selectedPeriod,
    fetchStatus,
    fetchChipPool,
    fetchChipsList,
    fetchMetrics,
    fetchQuality,
    fetchOperational,
    fetchFunnel,
    fetchTrends,
    fetchAlerts,
    fetchActivity,
  ])

  const handlePeriodChange = (period: DashboardPeriod) => {
    setSelectedPeriod(period)
  }

  const handleExport = async (format: 'csv' | 'pdf') => {
    try {
      const response = await fetch(
        `/api/dashboard/export?format=${format}&period=${selectedPeriod}`
      )
      if (!response.ok) return

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url

      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = `dashboard-julia-${selectedPeriod}.${format}`
      if (contentDisposition) {
        const match = /filename="?([^"]+)"?/.exec(contentDisposition)
        if (match?.[1]) filename = match[1]
      }

      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Export error:', error)
    }
  }

  const handleFunnelStageClick = (stageId: string) => {
    setSelectedFunnelStage(stageId)
    setFunnelModalOpen(true)
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Carregando dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-[1600px] space-y-6 p-6">
        <section aria-label="Header do Dashboard">
          <DashboardHeader
            juliaStatus={juliaStatus}
            lastHeartbeat={lastHeartbeat}
            uptime30d={99.8}
            selectedPeriod={selectedPeriod}
            onPeriodChange={handlePeriodChange}
            onExport={handleExport}
          />
        </section>

        {metricsData.length > 0 && (
          <section aria-label="Metricas Principais">
            <MetricsSection metrics={metricsData} />
          </section>
        )}

        {qualityData.length > 0 && (
          <section aria-label="Qualidade Persona">
            <QualityMetricsSection metrics={qualityData} />
          </section>
        )}

        <section aria-label="Status Operacional">
          <OperationalStatus data={operationalData} />
        </section>

        <section aria-label="Pool de Chips" className="space-y-6">
          {chipPoolData ? (
            <ChipPoolOverview data={chipPoolData} />
          ) : (
            <div className="rounded-lg border border-gray-200 bg-white p-6">
              <p className="text-center text-gray-500">Carregando pool de chips...</p>
            </div>
          )}
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            {chipsList.length > 0 ? (
              <ChipListTable chips={chipsList} />
            ) : (
              <p className="text-center text-gray-500">Nenhum chip encontrado</p>
            )}
          </div>
        </section>

        <section aria-label="Funil de Conversao">
          <ConversionFunnel data={funnelData} onStageClick={handleFunnelStageClick} />
        </section>

        <section
          aria-label="Tendencias e Alertas"
          className="grid grid-cols-1 gap-6 lg:grid-cols-2"
        >
          {trendsData.metrics.length > 0 ? (
            <TrendsSection data={trendsData} />
          ) : (
            <div className="rounded-lg border border-gray-200 bg-white p-6">
              <p className="text-center text-gray-500">Sem dados de tendencias</p>
            </div>
          )}
          <AlertsList initialData={alertsData} />
        </section>

        <section aria-label="Feed de Atividades">
          <ActivityFeed initialData={activityData} />
        </section>
      </div>

      <FunnelDrilldownModal
        open={funnelModalOpen}
        onOpenChange={setFunnelModalOpen}
        stage={selectedFunnelStage}
        period={selectedPeriod}
      />
    </div>
  )
}
