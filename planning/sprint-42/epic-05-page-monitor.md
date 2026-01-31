# Epic 05: Page Monitor

## Objetivo

Criar a página principal `/monitor` que compõe todos os componentes.

## Contexto

A página precisa:
- Buscar dados das APIs
- Gerenciar estado de filtros
- Implementar auto-refresh
- Compor todos os componentes criados no Epic 04

---

## Story 5.1: Criar Página Monitor

### Objetivo
Implementar a página `/monitor` com todos os componentes integrados.

### Tarefas

1. **Criar estrutura de diretórios:**
```bash
mkdir -p dashboard/app/(dashboard)/monitor
```

2. **Implementar page.tsx:**

**Arquivo:** `dashboard/app/(dashboard)/monitor/page.tsx`

```typescript
/**
 * Monitor Page - Sprint 42
 *
 * Página de monitoramento de jobs e saúde do sistema.
 */

import { Suspense } from 'react'
import { Metadata } from 'next'
import { MonitorPageContent } from '@/components/monitor/monitor-page-content'

export const metadata: Metadata = {
  title: 'Monitor | Julia Dashboard',
  description: 'Monitoramento de jobs e saúde do sistema',
}

function MonitorSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-8 w-48 rounded bg-gray-200" />
      <div className="h-32 rounded bg-gray-200" />
      <div className="grid grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 rounded bg-gray-200" />
        ))}
      </div>
      <div className="h-12 rounded bg-gray-200" />
      <div className="h-96 rounded bg-gray-200" />
    </div>
  )
}

export default function MonitorPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-[1600px] p-6">
        <Suspense fallback={<MonitorSkeleton />}>
          <MonitorPageContent />
        </Suspense>
      </div>
    </div>
  )
}
```

### DoD

- [ ] Arquivo `page.tsx` criado
- [ ] Metadata configurada
- [ ] Skeleton de loading implementado
- [ ] Suspense wrapper funcionando

---

## Story 5.2: Criar MonitorPageContent

### Objetivo
Implementar o client component principal que gerencia estado e fetch de dados.

### Tarefas

**Arquivo:** `dashboard/components/monitor/monitor-page-content.tsx`

```typescript
/**
 * Monitor Page Content - Sprint 42
 *
 * Client component principal da página de monitor.
 * Gerencia estado, fetch de dados e auto-refresh.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { RefreshCw, Activity } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { getMonitorOverview, getMonitorJobs } from '@/lib/api/monitor'
import {
  SystemHealthCard,
  JobsStatsCards,
  JobsFilters,
  JobsTable,
  JobDetailModal,
} from '@/components/monitor'
import type {
  MonitorOverviewResponse,
  MonitorJobsResponse,
  MonitorFilters,
} from '@/types/monitor'

const AUTO_REFRESH_INTERVAL = 30000 // 30 segundos

export function MonitorPageContent() {
  // Estado de dados
  const [overview, setOverview] = useState<MonitorOverviewResponse | null>(null)
  const [jobsData, setJobsData] = useState<MonitorJobsResponse | null>(null)

  // Estado de UI
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

  // Estado de filtros
  const [filters, setFilters] = useState<MonitorFilters>({
    status: 'all',
    timeRange: '24h',
    search: '',
    category: 'all',
  })

  // Estado do modal
  const [selectedJob, setSelectedJob] = useState<string | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  // Fetch overview
  const fetchOverview = useCallback(async () => {
    try {
      const data = await getMonitorOverview()
      setOverview(data)
    } catch (error) {
      console.error('Error fetching overview:', error)
    }
  }, [])

  // Fetch jobs
  const fetchJobs = useCallback(async () => {
    try {
      const data = await getMonitorJobs({
        status: filters.status,
        timeRange: filters.timeRange,
        search: filters.search,
        category: filters.category,
      })
      setJobsData(data)
    } catch (error) {
      console.error('Error fetching jobs:', error)
    }
  }, [filters])

  // Fetch all data
  const fetchAll = useCallback(async () => {
    await Promise.all([fetchOverview(), fetchJobs()])
    setLastUpdate(new Date())
  }, [fetchOverview, fetchJobs])

  // Initial load
  useEffect(() => {
    const load = async () => {
      setIsLoading(true)
      await fetchAll()
      setIsLoading(false)
    }
    void load()
  }, [fetchAll])

  // Refetch jobs when filters change
  useEffect(() => {
    if (!isLoading) {
      void fetchJobs()
    }
  }, [filters, fetchJobs, isLoading])

  // Auto-refresh
  useEffect(() => {
    const interval = setInterval(() => {
      void fetchAll()
    }, AUTO_REFRESH_INTERVAL)
    return () => clearInterval(interval)
  }, [fetchAll])

  // Manual refresh
  const handleRefresh = async () => {
    setIsRefreshing(true)
    await fetchAll()
    setIsRefreshing(false)
  }

  // Open job detail modal
  const handleJobClick = (jobName: string) => {
    setSelectedJob(jobName)
    setIsModalOpen(true)
  }

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-8 w-48 rounded bg-gray-200" />
        <div className="h-32 rounded bg-gray-200" />
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 rounded bg-gray-200" />
          ))}
        </div>
        <div className="h-12 rounded bg-gray-200" />
        <div className="h-96 rounded bg-gray-200" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
            <Activity className="h-6 w-6" />
            Monitor do Sistema
          </h1>
          <p className="mt-1 text-sm text-gray-600">
            Monitoramento em tempo real dos jobs e saúde do sistema
          </p>
        </div>

        <div className="flex items-center gap-3">
          {lastUpdate && (
            <span className="text-xs text-gray-500">
              Atualizado: {lastUpdate.toLocaleTimeString('pt-BR')}
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={cn('mr-2 h-4 w-4', isRefreshing && 'animate-spin')} />
            Atualizar
          </Button>
        </div>
      </div>

      {/* System Health */}
      <section aria-label="Saúde do Sistema">
        <SystemHealthCard data={overview?.systemHealth ?? null} />
      </section>

      {/* Stats Cards */}
      <section aria-label="Estatísticas">
        <JobsStatsCards stats={overview?.jobsStats ?? null} />
      </section>

      {/* Alerts Banner (if any critical) */}
      {overview?.alerts.criticalStale.length ? (
        <section aria-label="Alertas">
          <div className="rounded-lg border border-red-200 bg-red-50 p-4">
            <div className="flex items-center gap-2 font-medium text-red-800">
              <Activity className="h-5 w-5" />
              {overview.alerts.criticalStale.length} job(s) crítico(s) atrasado(s)
            </div>
            <div className="mt-2 text-sm text-red-700">
              {overview.alerts.criticalStale.join(', ')}
            </div>
          </div>
        </section>
      ) : null}

      {/* Filters */}
      <section aria-label="Filtros">
        <JobsFilters filters={filters} onFiltersChange={setFilters} />
      </section>

      {/* Jobs Table */}
      <section aria-label="Lista de Jobs">
        <JobsTable
          jobs={jobsData?.jobs ?? null}
          onJobClick={handleJobClick}
        />
      </section>

      {/* Job Detail Modal */}
      <JobDetailModal
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        jobName={selectedJob}
      />
    </div>
  )
}
```

3. **Atualizar index.ts:**

**Arquivo:** `dashboard/components/monitor/index.ts`

```typescript
/**
 * Monitor Components - Sprint 42
 */

export { MonitorPageContent } from './monitor-page-content'
export { SystemHealthCard } from './system-health-card'
export { JobsStatsCards } from './jobs-stats-cards'
export { JobsFilters } from './jobs-filters'
export { JobsTable } from './jobs-table'
export { JobDetailModal } from './job-detail-modal'
```

### DoD

- [ ] `MonitorPageContent` implementado
- [ ] Fetch de overview e jobs funcionando
- [ ] Auto-refresh a cada 30 segundos
- [ ] Manual refresh com botão
- [ ] Filtros atualizando a lista
- [ ] Clique no job abre modal
- [ ] Banner de alertas críticos
- [ ] Loading state inicial
- [ ] Timestamp de última atualização
- [ ] Exports atualizados no index.ts

---

## Checklist do Épico

- [ ] **S42.E05.1** - `page.tsx` criada com metadata
- [ ] **S42.E05.2** - `MonitorPageContent` implementado
- [ ] Fetch de dados funcionando
- [ ] Auto-refresh a cada 30s
- [ ] Filtros funcionando
- [ ] Modal de detalhes funcionando
- [ ] Alertas críticos exibidos
- [ ] Página acessível via `/monitor`
- [ ] Build passa sem erros

---

## Validação

```bash
cd dashboard

# Build
npm run build

# Dev server
npm run dev

# Acessar http://localhost:3000/monitor
# Verificar:
# - Página carrega
# - Dados aparecem
# - Filtros funcionam
# - Clique no job abre modal
# - Refresh manual funciona
# - Auto-refresh atualiza dados
```
