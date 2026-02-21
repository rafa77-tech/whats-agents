'use client'

import { Component, Suspense, lazy, useCallback } from 'react'
import type { ErrorInfo, ReactNode } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import type { Route } from 'next'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent } from '@/components/ui/card'

const TemplatesTab = lazy(() => import('./tabs/templates-tab'))
const QualityTab = lazy(() => import('./tabs/quality-tab'))
const AnalyticsTab = lazy(() => import('./tabs/analytics-tab'))
const FlowsTab = lazy(() => import('./tabs/flows-tab'))

const TAB_IDS = ['templates', 'quality', 'analytics', 'flows'] as const
type TabId = (typeof TAB_IDS)[number]

function isValidTab(tab: string | null): tab is TabId {
  return tab !== null && TAB_IDS.includes(tab as TabId)
}

interface TabErrorBoundaryProps {
  children: ReactNode
}

interface TabErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

class TabErrorBoundary extends Component<TabErrorBoundaryProps, TabErrorBoundaryState> {
  constructor(props: TabErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): TabErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('[MetaTab] Render error:', error, errorInfo)
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-sm text-muted-foreground">
              Erro ao carregar esta aba. Tente recarregar a página.
            </p>
          </CardContent>
        </Card>
      )
    }
    return this.props.children
  }
}

function TabSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-64 rounded-xl" />
    </div>
  )
}

export function MetaUnifiedPage() {
  const searchParams = useSearchParams()
  const router = useRouter()

  const tabParam = searchParams.get('tab')
  const tab: TabId = isValidTab(tabParam) ? tabParam : 'templates'

  const handleTabChange = useCallback(
    (newTab: string) => {
      router.push(`/meta?tab=${newTab}` as Route, { scroll: false })
    },
    [router]
  )

  return (
    <div className="min-h-screen bg-secondary">
      <div className="mx-auto max-w-[1600px] p-6">
        <Tabs value={tab} onValueChange={handleTabChange}>
          <TabsList className="grid w-full max-w-lg grid-cols-4">
            <TabsTrigger value="templates">Templates</TabsTrigger>
            <TabsTrigger value="quality">Qualidade</TabsTrigger>
            <TabsTrigger value="analytics">Custos</TabsTrigger>
            <TabsTrigger value="flows">Flows</TabsTrigger>
          </TabsList>

          <TabsContent value="templates" className="mt-6 space-y-6">
            <TabErrorBoundary>
              <Suspense fallback={<TabSkeleton />}>
                <TemplatesTab />
              </Suspense>
            </TabErrorBoundary>
          </TabsContent>

          <TabsContent value="quality" className="mt-6 space-y-6">
            <TabErrorBoundary>
              <Suspense fallback={<TabSkeleton />}>
                <QualityTab />
              </Suspense>
            </TabErrorBoundary>
          </TabsContent>

          <TabsContent value="analytics" className="mt-6 space-y-6">
            <TabErrorBoundary>
              <Suspense fallback={<TabSkeleton />}>
                <AnalyticsTab />
              </Suspense>
            </TabErrorBoundary>
          </TabsContent>

          <TabsContent value="flows" className="mt-6 space-y-6">
            <TabErrorBoundary>
              <Suspense fallback={<TabSkeleton />}>
                <FlowsTab />
              </Suspense>
            </TabErrorBoundary>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
