/**
 * Chips Unified Page - Sprint 45
 *
 * Pagina unificada do modulo de chips com tabs.
 * Consolida 5 subpaginas em uma unica pagina com navegacao por tabs.
 */

'use client'

import { Suspense, lazy, useState, useEffect, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import type { Route } from 'next'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ChipsTabHeader } from './chips-tab-header'

// Lazy load tab contents
const OverviewTab = lazy(() => import('./tabs/overview-tab'))
const AlertsTab = lazy(() => import('./tabs/alerts-tab'))
const WarmupTab = lazy(() => import('./tabs/warmup-tab'))
const ConfigTab = lazy(() => import('./tabs/config-tab'))

const TAB_IDS = ['visao-geral', 'alertas', 'warmup', 'configuracoes'] as const
type TabId = (typeof TAB_IDS)[number]

function isValidTab(tab: string | null): tab is TabId {
  return tab !== null && TAB_IDS.includes(tab as TabId)
}

// Skeleton components for each tab
function OverviewSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-lg" />
        ))}
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-20 rounded-lg" />
        ))}
      </div>
      <Skeleton className="h-96 rounded-lg" />
    </div>
  )
}

function AlertsSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-lg" />
        ))}
      </div>
      <Skeleton className="h-12 rounded-lg" />
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-20 rounded-lg" />
        ))}
      </div>
    </div>
  )
}

function WarmupSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 rounded-lg" />
        ))}
      </div>
      <Skeleton className="h-32 rounded-lg" />
      <Skeleton className="h-64 rounded-lg" />
    </div>
  )
}

function ConfigSkeleton() {
  return (
    <div className="space-y-6">
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-40 rounded-lg" />
      ))}
    </div>
  )
}

export function ChipsUnifiedPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [criticalAlerts, setCriticalAlerts] = useState(0)
  const [refreshKey, setRefreshKey] = useState(0)

  const tabParam = searchParams.get('tab')
  const tab: TabId = isValidTab(tabParam) ? tabParam : 'visao-geral'

  // Fetch alert count for badge
  const fetchAlertCount = useCallback(async () => {
    try {
      const response = await fetch('/api/dashboard/chips/alerts/count')
      if (response.ok) {
        const data = await response.json()
        setCriticalAlerts(data.critical || 0)
      }
    } catch (error) {
      console.error('Error fetching alert count:', error)
    }
  }, [])

  useEffect(() => {
    fetchAlertCount()
    const interval = setInterval(fetchAlertCount, 30000)
    return () => clearInterval(interval)
  }, [fetchAlertCount])

  const setTab = (value: string) => {
    const url = value === 'visao-geral' ? '/chips' : `/chips?tab=${value}`
    router.push(url as Route, { scroll: false })
  }

  const handleRefresh = () => {
    setRefreshKey((prev) => prev + 1)
    fetchAlertCount()
  }

  return (
    <div className="space-y-6">
      <ChipsTabHeader alertCount={criticalAlerts} onRefresh={handleRefresh} />

      <Tabs value={tab} onValueChange={setTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4 lg:inline-flex lg:w-auto lg:grid-cols-none">
          <TabsTrigger value="visao-geral" className="text-xs sm:text-sm">
            Visao Geral
          </TabsTrigger>
          <TabsTrigger value="alertas" className="text-xs sm:text-sm">
            <span>Alertas</span>
            {criticalAlerts > 0 && (
              <Badge variant="destructive" className="ml-1.5 h-5 min-w-[20px] px-1.5 text-[10px]">
                {criticalAlerts}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="warmup" className="text-xs sm:text-sm">
            Warmup
          </TabsTrigger>
          <TabsTrigger value="configuracoes" className="text-xs sm:text-sm">
            Config
          </TabsTrigger>
        </TabsList>

        <div className="mt-6">
          <TabsContent value="visao-geral" className="mt-0">
            <Suspense fallback={<OverviewSkeleton />}>
              <OverviewTab key={`overview-${refreshKey}`} />
            </Suspense>
          </TabsContent>

          <TabsContent value="alertas" className="mt-0">
            <Suspense fallback={<AlertsSkeleton />}>
              <AlertsTab key={`alerts-${refreshKey}`} />
            </Suspense>
          </TabsContent>

          <TabsContent value="warmup" className="mt-0">
            <Suspense fallback={<WarmupSkeleton />}>
              <WarmupTab key={`warmup-${refreshKey}`} />
            </Suspense>
          </TabsContent>

          <TabsContent value="configuracoes" className="mt-0">
            <Suspense fallback={<ConfigSkeleton />}>
              <ConfigTab key={`config-${refreshKey}`} />
            </Suspense>
          </TabsContent>
        </div>
      </Tabs>
    </div>
  )
}
