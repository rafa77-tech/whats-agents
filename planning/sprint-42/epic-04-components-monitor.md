# Epic 04: Components Monitor

## Objetivo

Criar os 6 componentes React para a página Monitor.

## Contexto

Componentes a criar:
1. `monitor-page-content.tsx` - Client component principal
2. `system-health-card.tsx` - Card de saúde do sistema
3. `jobs-stats-cards.tsx` - Cards de estatísticas
4. `jobs-table.tsx` - Tabela de jobs
5. `job-detail-modal.tsx` - Modal de histórico
6. `jobs-filters.tsx` - Filtros

### Estrutura de Arquivos

```
dashboard/components/monitor/
├── index.ts
├── monitor-page-content.tsx
├── system-health-card.tsx
├── jobs-stats-cards.tsx
├── jobs-table.tsx
├── job-detail-modal.tsx
└── jobs-filters.tsx
```

---

## Story 4.1: Criar System Health Card

### Objetivo
Componente que exibe status geral de saúde do sistema.

### Tarefas

1. **Criar componente:**

**Arquivo:** `dashboard/components/monitor/system-health-card.tsx`

```typescript
/**
 * System Health Card - Sprint 42
 *
 * Exibe status geral de saúde do sistema com score e breakdown.
 */

'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Activity, CheckCircle, AlertTriangle, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SystemHealthData, SystemHealthStatus } from '@/types/monitor'

interface SystemHealthCardProps {
  data: SystemHealthData | null
  isLoading?: boolean
}

const STATUS_CONFIG: Record<SystemHealthStatus, {
  label: string
  color: string
  bgColor: string
  icon: typeof CheckCircle
}> = {
  healthy: {
    label: 'Saudável',
    color: 'text-green-700',
    bgColor: 'bg-green-100',
    icon: CheckCircle,
  },
  degraded: {
    label: 'Degradado',
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-100',
    icon: AlertTriangle,
  },
  critical: {
    label: 'Crítico',
    color: 'text-red-700',
    bgColor: 'bg-red-100',
    icon: XCircle,
  },
}

export function SystemHealthCard({ data, isLoading }: SystemHealthCardProps) {
  if (isLoading || !data) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-8 w-32 rounded bg-gray-200" />
            <div className="h-4 w-full rounded bg-gray-200" />
          </div>
        </CardContent>
      </Card>
    )
  }

  const config = STATUS_CONFIG[data.status]
  const StatusIcon = config.icon

  return (
    <Card className={cn('border-l-4', {
      'border-l-green-500': data.status === 'healthy',
      'border-l-yellow-500': data.status === 'degraded',
      'border-l-red-500': data.status === 'critical',
    })}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Activity className="h-5 w-5" />
            Saúde do Sistema
          </CardTitle>
          <Badge className={cn(config.bgColor, config.color)}>
            <StatusIcon className="mr-1 h-3 w-3" />
            {config.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Score principal */}
          <div className="flex items-end gap-2">
            <span className={cn('text-4xl font-bold', config.color)}>
              {data.score}
            </span>
            <span className="mb-1 text-gray-500">/ 100</span>
          </div>

          {/* Progress bar */}
          <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
            <div
              className={cn('h-full transition-all', {
                'bg-green-500': data.score >= 80,
                'bg-yellow-500': data.score >= 50 && data.score < 80,
                'bg-red-500': data.score < 50,
              })}
              style={{ width: `${data.score}%` }}
            />
          </div>

          {/* Breakdown */}
          <div className="grid grid-cols-2 gap-4 pt-2 md:grid-cols-4">
            {Object.entries(data.checks).map(([key, check]) => (
              <div key={key} className="rounded-lg bg-gray-50 p-3">
                <div className="mb-1 text-xs capitalize text-gray-500">
                  {key}
                </div>
                <div className="flex items-center gap-1">
                  <span className="font-semibold">{check.score}</span>
                  <span className="text-xs text-gray-400">/ {check.max}</span>
                </div>
                <div className="mt-1 truncate text-xs text-gray-400">
                  {check.details}
                </div>
              </div>
            ))}
          </div>

          {/* Last updated */}
          <div className="text-xs text-gray-400">
            Atualizado: {new Date(data.lastUpdated).toLocaleString('pt-BR')}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
```

### DoD

- [ ] Componente `SystemHealthCard` criado
- [ ] Exibe status (healthy/degraded/critical) com ícone e cor
- [ ] Exibe score 0-100 com progress bar
- [ ] Exibe breakdown por subsistema
- [ ] Loading state implementado
- [ ] Responsivo (grid 2x2 mobile, 4x1 desktop)

---

## Story 4.2: Criar Jobs Stats Cards

### Objetivo
Grid de 4 cards com estatísticas principais.

### Tarefas

**Arquivo:** `dashboard/components/monitor/jobs-stats-cards.tsx`

```typescript
/**
 * Jobs Stats Cards - Sprint 42
 *
 * Grid de 4 cards com estatísticas de jobs.
 */

'use client'

import { Card, CardContent } from '@/components/ui/card'
import {
  Server,
  CheckCircle,
  XCircle,
  AlertTriangle,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface JobsStatsCardsProps {
  stats: {
    totalJobs: number
    successRate24h: number
    failedJobs24h: number
    runningJobs: number
    staleJobs: number
  } | null
  isLoading?: boolean
}

export function JobsStatsCards({ stats, isLoading }: JobsStatsCardsProps) {
  if (isLoading || !stats) {
    return (
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <div className="animate-pulse space-y-2">
                <div className="h-4 w-16 rounded bg-gray-200" />
                <div className="h-8 w-12 rounded bg-gray-200" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const cards = [
    {
      label: 'Total Jobs',
      value: stats.totalJobs,
      icon: Server,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      label: 'Taxa de Sucesso',
      value: `${stats.successRate24h}%`,
      icon: CheckCircle,
      color: stats.successRate24h >= 95 ? 'text-green-600' : stats.successRate24h >= 80 ? 'text-yellow-600' : 'text-red-600',
      bgColor: stats.successRate24h >= 95 ? 'bg-green-50' : stats.successRate24h >= 80 ? 'bg-yellow-50' : 'bg-red-50',
    },
    {
      label: 'Jobs com Erro',
      value: stats.failedJobs24h,
      icon: XCircle,
      color: stats.failedJobs24h === 0 ? 'text-green-600' : stats.failedJobs24h <= 3 ? 'text-yellow-600' : 'text-red-600',
      bgColor: stats.failedJobs24h === 0 ? 'bg-green-50' : stats.failedJobs24h <= 3 ? 'bg-yellow-50' : 'bg-red-50',
    },
    {
      label: 'Jobs Atrasados',
      value: stats.staleJobs,
      icon: AlertTriangle,
      color: stats.staleJobs === 0 ? 'text-green-600' : stats.staleJobs <= 2 ? 'text-yellow-600' : 'text-red-600',
      bgColor: stats.staleJobs === 0 ? 'bg-green-50' : stats.staleJobs <= 2 ? 'bg-yellow-50' : 'bg-red-50',
    },
  ]

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.label}>
          <CardContent className={cn('p-4', card.bgColor)}>
            <div className="flex items-center gap-3">
              <card.icon className={cn('h-8 w-8', card.color)} />
              <div>
                <div className="text-sm text-gray-600">{card.label}</div>
                <div className={cn('text-2xl font-bold', card.color)}>
                  {card.value}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
```

### DoD

- [ ] Componente `JobsStatsCards` criado
- [ ] 4 cards: Total Jobs, Taxa de Sucesso, Jobs com Erro, Jobs Atrasados
- [ ] Cores dinâmicas baseadas em thresholds
- [ ] Loading state com skeleton
- [ ] Grid responsivo 2x2 mobile, 4x1 desktop

---

## Story 4.3: Criar Jobs Filters

### Objetivo
Componente de filtros para a tabela de jobs.

### Tarefas

**Arquivo:** `dashboard/components/monitor/jobs-filters.tsx`

```typescript
/**
 * Jobs Filters - Sprint 42
 *
 * Filtros para a lista de jobs.
 */

'use client'

import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Search } from 'lucide-react'
import type { MonitorFilters, JobStatusFilter, TimeRangeFilter, JobCategory } from '@/types/monitor'

interface JobsFiltersProps {
  filters: MonitorFilters
  onFiltersChange: (filters: MonitorFilters) => void
}

const STATUS_OPTIONS: { value: JobStatusFilter; label: string }[] = [
  { value: 'all', label: 'Todos os Status' },
  { value: 'running', label: 'Executando' },
  { value: 'success', label: 'Sucesso' },
  { value: 'error', label: 'Erro' },
  { value: 'timeout', label: 'Timeout' },
  { value: 'stale', label: 'Atrasados' },
]

const TIME_OPTIONS: { value: TimeRangeFilter; label: string }[] = [
  { value: '1h', label: 'Última hora' },
  { value: '6h', label: 'Últimas 6h' },
  { value: '24h', label: 'Últimas 24h' },
]

const CATEGORY_OPTIONS: { value: JobCategory | 'all'; label: string }[] = [
  { value: 'all', label: 'Todas Categorias' },
  { value: 'critical', label: 'Críticos' },
  { value: 'frequent', label: 'Frequentes' },
  { value: 'hourly', label: 'Horários' },
  { value: 'daily', label: 'Diários' },
  { value: 'weekly', label: 'Semanais' },
]

export function JobsFilters({ filters, onFiltersChange }: JobsFiltersProps) {
  const updateFilter = <K extends keyof MonitorFilters>(
    key: K,
    value: MonitorFilters[K]
  ) => {
    onFiltersChange({ ...filters, [key]: value })
  }

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
      {/* Search */}
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <Input
          placeholder="Buscar por nome..."
          value={filters.search}
          onChange={(e) => updateFilter('search', e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Status filter */}
      <Select
        value={filters.status}
        onValueChange={(v) => updateFilter('status', v as JobStatusFilter)}
      >
        <SelectTrigger className="w-full sm:w-[160px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {STATUS_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Category filter */}
      <Select
        value={filters.category}
        onValueChange={(v) => updateFilter('category', v as JobCategory | 'all')}
      >
        <SelectTrigger className="w-full sm:w-[160px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {CATEGORY_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Time range buttons */}
      <div className="flex gap-1 rounded-lg bg-gray-100 p-1">
        {TIME_OPTIONS.map((opt) => (
          <Button
            key={opt.value}
            variant={filters.timeRange === opt.value ? 'default' : 'ghost'}
            size="sm"
            onClick={() => updateFilter('timeRange', opt.value)}
            className="px-3"
          >
            {opt.label}
          </Button>
        ))}
      </div>
    </div>
  )
}
```

### DoD

- [ ] Componente `JobsFilters` criado
- [ ] Input de busca por nome
- [ ] Select de status (all, running, success, error, timeout, stale)
- [ ] Select de categoria (all, critical, frequent, hourly, daily, weekly)
- [ ] Button group de período (1h, 6h, 24h)
- [ ] Callbacks funcionando
- [ ] Responsivo

---

## Story 4.4: Criar Jobs Table

### Objetivo
Tabela de jobs com status, última execução, duração, etc.

### Tarefas

**Arquivo:** `dashboard/components/monitor/jobs-table.tsx`

```typescript
/**
 * Jobs Table - Sprint 42
 *
 * Tabela de jobs com status e métricas.
 */

'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Loader2,
  ChevronRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { JobSummary, JobStatus, JobCategory } from '@/types/monitor'

interface JobsTableProps {
  jobs: JobSummary[] | null
  isLoading?: boolean
  onJobClick: (jobName: string) => void
}

const STATUS_CONFIG: Record<JobStatus, {
  icon: typeof CheckCircle
  color: string
  bgColor: string
  label: string
}> = {
  running: {
    icon: Loader2,
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
    label: 'Executando',
  },
  success: {
    icon: CheckCircle,
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    label: 'Sucesso',
  },
  error: {
    icon: XCircle,
    color: 'text-red-600',
    bgColor: 'bg-red-100',
    label: 'Erro',
  },
  timeout: {
    icon: Clock,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-100',
    label: 'Timeout',
  },
}

const CATEGORY_COLORS: Record<JobCategory, string> = {
  critical: 'bg-red-100 text-red-700',
  frequent: 'bg-blue-100 text-blue-700',
  hourly: 'bg-purple-100 text-purple-700',
  daily: 'bg-green-100 text-green-700',
  weekly: 'bg-gray-100 text-gray-700',
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}m`
}

function formatTimeAgo(dateStr: string | null): string {
  if (!dateStr) return 'Nunca'
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000)
  if (seconds < 60) return `${seconds}s atrás`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m atrás`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h atrás`
  return `${Math.floor(seconds / 86400)}d atrás`
}

export function JobsTable({ jobs, isLoading, onJobClick }: JobsTableProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Jobs do Sistema</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-12 rounded bg-gray-200" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">
          Jobs do Sistema
          {jobs && (
            <span className="ml-2 text-sm font-normal text-gray-500">
              ({jobs.length} jobs)
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Job</TableHead>
              <TableHead>Categoria</TableHead>
              <TableHead>Última Execução</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Duração Média</TableHead>
              <TableHead className="text-right">Execuções 24h</TableHead>
              <TableHead></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {jobs?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="py-8 text-center text-gray-500">
                  Nenhum job encontrado com os filtros aplicados.
                </TableCell>
              </TableRow>
            ) : (
              jobs?.map((job) => {
                const statusConfig = job.lastStatus ? STATUS_CONFIG[job.lastStatus] : null
                const StatusIcon = statusConfig?.icon || Clock

                return (
                  <TableRow
                    key={job.name}
                    className="cursor-pointer hover:bg-gray-50"
                    onClick={() => onJobClick(job.name)}
                  >
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {job.isCritical && (
                          <AlertTriangle className="h-4 w-4 text-red-500" title="Job crítico" />
                        )}
                        {job.isStale && (
                          <AlertTriangle className="h-4 w-4 text-yellow-500" title="Job atrasado" />
                        )}
                        <div>
                          <div className="font-medium">{job.name}</div>
                          <div className="text-xs text-gray-500">{job.description}</div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={cn('text-xs', CATEGORY_COLORS[job.category])}>
                        {job.category}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">{formatTimeAgo(job.lastRun)}</div>
                      <div className="text-xs text-gray-400">{job.schedule}</div>
                    </TableCell>
                    <TableCell>
                      {statusConfig ? (
                        <Badge className={cn(statusConfig.bgColor, statusConfig.color)}>
                          <StatusIcon className={cn('mr-1 h-3 w-3', job.lastStatus === 'running' && 'animate-spin')} />
                          {statusConfig.label}
                        </Badge>
                      ) : (
                        <Badge variant="outline">N/A</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {job.avgDurationMs > 0 ? formatDuration(job.avgDurationMs) : '-'}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <span className="text-green-600">{job.success24h}</span>
                        <span className="text-gray-400">/</span>
                        <span className={job.errors24h > 0 ? 'text-red-600' : 'text-gray-400'}>
                          {job.errors24h}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <ChevronRight className="h-4 w-4 text-gray-400" />
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
```

### DoD

- [ ] Componente `JobsTable` criado
- [ ] Colunas: Job, Categoria, Última Execução, Status, Duração, Execuções 24h
- [ ] Status com ícones e cores (running, success, error, timeout)
- [ ] Indicador de job crítico (ícone warning vermelho)
- [ ] Indicador de job atrasado/stale (ícone warning amarelo)
- [ ] Formatação de duração (ms, s, m)
- [ ] Formatação de tempo (Xm atrás, Xh atrás)
- [ ] Click handler para abrir detalhes
- [ ] Loading state
- [ ] Empty state

---

## Story 4.5: Criar Job Detail Modal

### Objetivo
Modal que exibe histórico de execuções de um job específico.

### Tarefas

**Arquivo:** `dashboard/components/monitor/job-detail-modal.tsx`

```typescript
/**
 * Job Detail Modal - Sprint 42
 *
 * Modal com histórico de execuções de um job.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { getJobExecutions } from '@/lib/api/monitor'
import { JOBS_BY_NAME } from '@/lib/monitor/jobs-config'
import type { JobExecution, JobStatus, JobDetailModalProps } from '@/types/monitor'

const STATUS_CONFIG: Record<JobStatus, {
  icon: typeof CheckCircle
  color: string
  bgColor: string
  label: string
}> = {
  running: { icon: Loader2, color: 'text-blue-600', bgColor: 'bg-blue-100', label: 'Executando' },
  success: { icon: CheckCircle, color: 'text-green-600', bgColor: 'bg-green-100', label: 'Sucesso' },
  error: { icon: XCircle, color: 'text-red-600', bgColor: 'bg-red-100', label: 'Erro' },
  timeout: { icon: Clock, color: 'text-yellow-600', bgColor: 'bg-yellow-100', label: 'Timeout' },
}

export function JobDetailModal({ open, onOpenChange, jobName }: JobDetailModalProps) {
  const [executions, setExecutions] = useState<JobExecution[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [total, setTotal] = useState(0)

  const jobDef = jobName ? JOBS_BY_NAME[jobName] : null

  const fetchExecutions = useCallback(async (pageNum: number) => {
    if (!jobName) return
    setIsLoading(true)
    try {
      const data = await getJobExecutions(jobName, { page: pageNum, pageSize: 20 })
      setExecutions(data.executions)
      setHasMore(data.hasMore)
      setTotal(data.total)
      setPage(pageNum)
    } catch (error) {
      console.error('Error fetching job executions:', error)
    } finally {
      setIsLoading(false)
    }
  }, [jobName])

  useEffect(() => {
    if (open && jobName) {
      fetchExecutions(1)
    }
  }, [open, jobName, fetchExecutions])

  const handlePrevPage = () => {
    if (page > 1) fetchExecutions(page - 1)
  }

  const handleNextPage = () => {
    if (hasMore) fetchExecutions(page + 1)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[80vh] max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span>{jobName}</span>
            {jobDef?.isCritical && (
              <Badge variant="destructive" className="text-xs">Crítico</Badge>
            )}
          </DialogTitle>
          {jobDef && (
            <p className="text-sm text-gray-500">
              {jobDef.description} • Schedule: {jobDef.schedule}
            </p>
          )}
        </DialogHeader>

        <div className="space-y-4">
          {/* Header com total */}
          <div className="flex items-center justify-between text-sm text-gray-500">
            <span>{total} execuções encontradas</span>
            <span>Página {page}</span>
          </div>

          {/* Lista de execuções */}
          <ScrollArea className="h-[400px]">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
              </div>
            ) : executions.length === 0 ? (
              <div className="py-8 text-center text-gray-500">
                Nenhuma execução encontrada.
              </div>
            ) : (
              <div className="space-y-2">
                {executions.map((exec) => {
                  const config = STATUS_CONFIG[exec.status]
                  const StatusIcon = config.icon

                  return (
                    <div
                      key={exec.id}
                      className="rounded-lg border p-3"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Badge className={cn(config.bgColor, config.color)}>
                            <StatusIcon className={cn('mr-1 h-3 w-3', exec.status === 'running' && 'animate-spin')} />
                            {config.label}
                          </Badge>
                          <span className="text-sm text-gray-500">
                            {new Date(exec.startedAt).toLocaleString('pt-BR')}
                          </span>
                        </div>
                        <div className="text-sm text-gray-500">
                          {exec.durationMs ? `${exec.durationMs}ms` : '-'}
                        </div>
                      </div>

                      {/* Detalhes adicionais */}
                      <div className="mt-2 flex gap-4 text-xs text-gray-400">
                        {exec.itemsProcessed !== null && (
                          <span>Itens: {exec.itemsProcessed}</span>
                        )}
                        {exec.responseCode !== null && (
                          <span>HTTP: {exec.responseCode}</span>
                        )}
                      </div>

                      {/* Erro */}
                      {exec.error && (
                        <div className="mt-2 rounded bg-red-50 p-2 text-xs text-red-600">
                          {exec.error}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </ScrollArea>

          {/* Paginação */}
          <div className="flex items-center justify-between">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePrevPage}
              disabled={page === 1 || isLoading}
            >
              <ChevronLeft className="mr-1 h-4 w-4" />
              Anterior
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleNextPage}
              disabled={!hasMore || isLoading}
            >
              Próxima
              <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
```

### DoD

- [ ] Componente `JobDetailModal` criado
- [ ] Exibe nome do job e descrição
- [ ] Exibe indicador de job crítico
- [ ] Lista execuções com: status, data/hora, duração
- [ ] Exibe itens processados e response code quando disponível
- [ ] Exibe mensagem de erro quando aplicável
- [ ] Paginação (anterior/próxima)
- [ ] Loading state
- [ ] Empty state

---

## Story 4.6: Criar Index de Exports

### Objetivo
Criar arquivo index.ts para exportar todos os componentes.

### Tarefas

**Arquivo:** `dashboard/components/monitor/index.ts`

```typescript
/**
 * Monitor Components - Sprint 42
 */

export { SystemHealthCard } from './system-health-card'
export { JobsStatsCards } from './jobs-stats-cards'
export { JobsFilters } from './jobs-filters'
export { JobsTable } from './jobs-table'
export { JobDetailModal } from './job-detail-modal'
```

### DoD

- [ ] Arquivo `index.ts` criado
- [ ] Todos os 5 componentes exportados
- [ ] Imports funcionando

---

## Checklist do Épico

- [ ] **S42.E04.1** - `SystemHealthCard` implementado
- [ ] **S42.E04.2** - `JobsStatsCards` implementado
- [ ] **S42.E04.3** - `JobsFilters` implementado
- [ ] **S42.E04.4** - `JobsTable` implementado
- [ ] **S42.E04.5** - `JobDetailModal` implementado
- [ ] **S42.E04.6** - `index.ts` criado
- [ ] Todos os componentes tipados
- [ ] Loading states implementados
- [ ] Componentes responsivos
- [ ] Build passa sem erros
