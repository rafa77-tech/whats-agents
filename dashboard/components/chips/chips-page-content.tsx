/**
 * Chips Page Content - Sprint 36
 *
 * Conteúdo principal da página de chips.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import type { Route } from 'next'
import { RefreshCw, AlertTriangle, Settings, Cpu, Activity, MessageSquare } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PoolMetricCard } from './pool-metric-card'
import { StatusCounterCard } from './status-counter-card'
import { TrustDistributionChart } from './trust-distribution-chart'
import { PoolHealthIndicators } from './pool-health-indicators'
import { ChipsTable } from './chips-table'
import { ChipsPagination } from './chips-pagination'
import { ChipsFilters } from './chips-filters'
import { ChipsBulkActions } from './chips-bulk-actions'
import { ChipsPageSkeleton } from './chips-page-skeleton'
import { chipsApi } from '@/lib/api/chips'
import { PoolStatus, ChipListItem, ChipsListParams, TrustLevelExtended } from '@/types/chips'
import { ChipStatus } from '@/types/dashboard'

const displayStatusOrder: ChipStatus[] = [
  'active',
  'ready',
  'warming',
  'degraded',
  'paused',
  'banned',
]

export function ChipsPageContent() {
  const router = useRouter()

  // Pool status state
  const [poolStatus, setPoolStatus] = useState<PoolStatus | null>(null)
  const [isLoadingPool, setIsLoadingPool] = useState(true)

  // Chips list state
  const [chips, setChips] = useState<ChipListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [_isLoadingChips, setIsLoadingChips] = useState(true)
  const [filters, setFilters] = useState<Partial<ChipsListParams>>({
    sortBy: 'trust',
    order: 'desc',
  })

  // Fetch pool status
  const fetchPoolStatus = useCallback(async () => {
    try {
      const data = await chipsApi.getPoolStatus()
      setPoolStatus(data)
    } catch (error) {
      console.error('Error fetching pool status:', error)
    } finally {
      setIsLoadingPool(false)
    }
  }, [])

  // Fetch chips list
  const fetchChips = useCallback(async () => {
    setIsLoadingChips(true)
    try {
      const response = await chipsApi.listChips({
        page,
        pageSize,
        ...filters,
      })
      setChips(response.chips)
      setTotal(response.total)
    } catch (error) {
      console.error('Error fetching chips:', error)
    } finally {
      setIsLoadingChips(false)
    }
  }, [page, pageSize, filters])

  // Initial load
  useEffect(() => {
    fetchPoolStatus()
  }, [fetchPoolStatus])

  useEffect(() => {
    fetchChips()
  }, [fetchChips])

  // Handlers
  const handleRefresh = () => {
    setIsLoadingPool(true)
    fetchPoolStatus()
    fetchChips()
  }

  const handlePageChange = (newPage: number) => {
    setPage(newPage)
    setSelectedIds([])
  }

  const handlePageSizeChange = (newPageSize: number) => {
    setPageSize(newPageSize)
    setPage(1)
    setSelectedIds([])
  }

  const handleFiltersChange = (newFilters: Partial<ChipsListParams>) => {
    setFilters(newFilters)
    setPage(1)
    setSelectedIds([])
  }

  const handleRowClick = (chip: ChipListItem) => {
    router.push(`/chips/${chip.id}` as Route)
  }

  // Loading state
  if (isLoadingPool && !poolStatus) {
    return <ChipsPageSkeleton />
  }

  // Calculate metrics
  const utilizationPercent =
    poolStatus && poolStatus.totalDailyCapacity > 0
      ? (poolStatus.totalMessagesToday / poolStatus.totalDailyCapacity) * 100
      : 0

  const getUtilizationStatus = () => {
    if (utilizationPercent >= 90) return 'danger'
    if (utilizationPercent >= 70) return 'warning'
    return 'success'
  }

  const getTrustStatus = () => {
    if (!poolStatus) return 'neutral'
    if (poolStatus.avgTrustScore >= 70) return 'success'
    if (poolStatus.avgTrustScore >= 50) return 'warning'
    return 'danger'
  }

  const getAlertsStatus = () => {
    if (!poolStatus) return 'neutral'
    if (poolStatus.criticalAlerts > 0) return 'danger'
    if (poolStatus.activeAlerts > 0) return 'warning'
    return 'success'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <nav className="mb-1 text-sm text-gray-500">
            <Link href={'/dashboard' as Route} className="hover:text-gray-700">
              Dashboard
            </Link>
            <span className="mx-2">/</span>
            <span className="text-gray-900">Chips</span>
          </nav>
          <h1 className="text-2xl font-bold text-gray-900">Pool de Chips</h1>
          <p className="mt-1 text-sm text-gray-600">Gerencie os chips WhatsApp do sistema Julia</p>
        </div>

        <div className="flex items-center gap-3">
          {poolStatus && poolStatus.criticalAlerts > 0 && (
            <Link href={'/chips/alertas' as Route}>
              <Button variant="destructive" size="sm">
                <AlertTriangle className="mr-2 h-4 w-4" />
                {poolStatus.criticalAlerts} Alertas
              </Button>
            </Link>
          )}

          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isLoadingPool}>
            <RefreshCw className={`mr-2 h-4 w-4 ${isLoadingPool ? 'animate-spin' : ''}`} />
            Atualizar
          </Button>

          <Link href={'/chips/configuracoes' as Route}>
            <Button variant="outline" size="sm">
              <Settings className="mr-2 h-4 w-4" />
              Config
            </Button>
          </Link>
        </div>
      </div>

      {/* Metrics Cards */}
      {poolStatus && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          <PoolMetricCard
            title="Total de Chips"
            value={poolStatus.total}
            subtitle={`${poolStatus.byStatus.active || 0} ativos`}
            icon={<Cpu className="h-6 w-6" />}
            status="neutral"
          />

          <PoolMetricCard
            title="Trust Score Medio"
            value={poolStatus.avgTrustScore.toFixed(1)}
            subtitle="Score de confianca do pool"
            icon={<Activity className="h-6 w-6" />}
            status={getTrustStatus()}
          />

          <PoolMetricCard
            title="Mensagens Hoje"
            value={poolStatus.totalMessagesToday.toLocaleString()}
            subtitle={`de ${poolStatus.totalDailyCapacity.toLocaleString()} (${utilizationPercent.toFixed(1)}%)`}
            icon={<MessageSquare className="h-6 w-6" />}
            status={getUtilizationStatus()}
          />

          <PoolMetricCard
            title="Alertas Ativos"
            value={poolStatus.activeAlerts}
            subtitle={
              poolStatus.criticalAlerts > 0
                ? `${poolStatus.criticalAlerts} criticos`
                : 'Nenhum critico'
            }
            icon={<AlertTriangle className="h-6 w-6" />}
            status={getAlertsStatus()}
          />
        </div>
      )}

      {/* Status Counters */}
      {poolStatus && (
        <div>
          <h3 className="mb-3 text-sm font-medium text-gray-500">Distribuicao por Status</h3>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
            {displayStatusOrder.map((status) => {
              const count = poolStatus.byStatus[status] || 0
              const percentage = poolStatus.total > 0 ? (count / poolStatus.total) * 100 : 0

              return (
                <StatusCounterCard
                  key={status}
                  status={status}
                  count={count}
                  percentage={percentage}
                />
              )
            })}
          </div>
        </div>
      )}

      {/* Trust Distribution and Health Indicators */}
      {poolStatus && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <TrustDistributionChart
            distribution={poolStatus.byTrustLevel as Record<TrustLevelExtended, number>}
            total={poolStatus.total}
          />
          <PoolHealthIndicators />
        </div>
      )}

      {/* Chips Table Section */}
      <div className="rounded-lg border border-gray-200 bg-white">
        <div className="border-b border-gray-200 p-4">
          <h3 className="text-lg font-semibold text-gray-900">Chips do Pool</h3>
          <p className="mt-1 text-sm text-gray-500">{total} chips encontrados</p>
        </div>

        <div className="border-b border-gray-200 p-4">
          <ChipsFilters filters={filters} onFiltersChange={handleFiltersChange} />
        </div>

        <ChipsTable
          chips={chips}
          selectedIds={selectedIds}
          onSelectionChange={setSelectedIds}
          onRowClick={handleRowClick}
        />

        <ChipsPagination
          page={page}
          pageSize={pageSize}
          total={total}
          onPageChange={handlePageChange}
          onPageSizeChange={handlePageSizeChange}
        />
      </div>

      {/* Bulk Actions Bar */}
      <ChipsBulkActions
        selectedIds={selectedIds}
        onClearSelection={() => setSelectedIds([])}
        onActionComplete={() => {
          fetchChips()
          fetchPoolStatus()
        }}
      />
    </div>
  )
}
