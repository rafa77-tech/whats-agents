/**
 * Jobs Table - Sprint 42
 *
 * Tabela de jobs com status, metricas e ordenacao.
 */

'use client'

import { useState, useMemo } from 'react'
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
  ArrowUp,
  ArrowDown,
  ArrowUpDown,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { JobSummary, JobStatus, JobCategory } from '@/types/monitor'

interface JobsTableProps {
  jobs: JobSummary[] | null
  isLoading?: boolean
  onJobClick: (jobName: string) => void
}

type SortColumn = 'name' | 'category' | 'lastRun' | 'status' | 'duration' | 'executions'
type SortDirection = 'asc' | 'desc'

const STATUS_CONFIG: Record<
  JobStatus,
  {
    icon: typeof CheckCircle
    color: string
    bgColor: string
    label: string
    priority: number
  }
> = {
  running: {
    icon: Loader2,
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
    label: 'Executando',
    priority: 1,
  },
  error: {
    icon: XCircle,
    color: 'text-red-600',
    bgColor: 'bg-red-100',
    label: 'Erro',
    priority: 2,
  },
  timeout: {
    icon: Clock,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-100',
    label: 'Timeout',
    priority: 3,
  },
  success: {
    icon: CheckCircle,
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    label: 'Sucesso',
    priority: 4,
  },
}

const CATEGORY_COLORS: Record<JobCategory, string> = {
  critical: 'bg-red-100 text-red-700',
  frequent: 'bg-blue-100 text-blue-700',
  hourly: 'bg-purple-100 text-purple-700',
  daily: 'bg-green-100 text-green-700',
  weekly: 'bg-gray-100 text-gray-700',
}

const CATEGORY_PRIORITY: Record<JobCategory, number> = {
  critical: 1,
  frequent: 2,
  hourly: 3,
  daily: 4,
  weekly: 5,
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

interface SortableHeaderProps {
  column: SortColumn
  currentSort: SortColumn | null
  direction: SortDirection
  onSort: (column: SortColumn) => void
  children: React.ReactNode
  className?: string
}

function SortableHeader({
  column,
  currentSort,
  direction,
  onSort,
  children,
  className,
}: SortableHeaderProps) {
  const isActive = currentSort === column
  const Icon = isActive ? (direction === 'asc' ? ArrowUp : ArrowDown) : ArrowUpDown

  return (
    <TableHead
      className={cn('cursor-pointer select-none hover:bg-gray-50', className)}
      onClick={() => onSort(column)}
    >
      <div className="flex items-center gap-1">
        {children}
        <Icon className={cn('h-4 w-4', isActive ? 'text-gray-900' : 'text-gray-400')} />
      </div>
    </TableHead>
  )
}

export function JobsTable({ jobs, isLoading, onJobClick }: JobsTableProps) {
  const [sortColumn, setSortColumn] = useState<SortColumn | null>(null)
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      // Toggle direction or reset
      if (sortDirection === 'asc') {
        setSortDirection('desc')
      } else {
        setSortColumn(null)
        setSortDirection('asc')
      }
    } else {
      setSortColumn(column)
      setSortDirection('asc')
    }
  }

  const sortedJobs = useMemo(() => {
    if (!jobs || !sortColumn) return jobs

    return [...jobs].sort((a, b) => {
      let comparison = 0

      switch (sortColumn) {
        case 'name':
          comparison = a.displayName.localeCompare(b.displayName)
          break
        case 'category':
          comparison = CATEGORY_PRIORITY[a.category] - CATEGORY_PRIORITY[b.category]
          break
        case 'lastRun':
          if (!a.lastRun && !b.lastRun) comparison = 0
          else if (!a.lastRun) comparison = 1
          else if (!b.lastRun) comparison = -1
          else comparison = new Date(b.lastRun).getTime() - new Date(a.lastRun).getTime()
          break
        case 'status':
          const priorityA = a.lastStatus ? STATUS_CONFIG[a.lastStatus].priority : 99
          const priorityB = b.lastStatus ? STATUS_CONFIG[b.lastStatus].priority : 99
          comparison = priorityA - priorityB
          break
        case 'duration':
          comparison = a.avgDurationMs - b.avgDurationMs
          break
        case 'executions':
          comparison = a.runs24h - b.runs24h
          break
      }

      return sortDirection === 'asc' ? comparison : -comparison
    })
  }, [jobs, sortColumn, sortDirection])

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
            <span className="ml-2 text-sm font-normal text-gray-500">({jobs.length} jobs)</span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <SortableHeader
                column="name"
                currentSort={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
              >
                Job
              </SortableHeader>
              <SortableHeader
                column="category"
                currentSort={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
              >
                Categoria
              </SortableHeader>
              <SortableHeader
                column="lastRun"
                currentSort={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
              >
                Última Execução
              </SortableHeader>
              <SortableHeader
                column="status"
                currentSort={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
              >
                Status
              </SortableHeader>
              <SortableHeader
                column="duration"
                currentSort={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
              >
                Duração Média
              </SortableHeader>
              <SortableHeader
                column="executions"
                currentSort={sortColumn}
                direction={sortDirection}
                onSort={handleSort}
                className="text-right"
              >
                Execuções 24h
              </SortableHeader>
              <TableHead></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedJobs?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="py-8 text-center text-gray-500">
                  Nenhum job encontrado com os filtros aplicados.
                </TableCell>
              </TableRow>
            ) : (
              sortedJobs?.map((job) => {
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
                          <span title="Job crítico">
                            <AlertTriangle className="h-4 w-4 text-red-500" />
                          </span>
                        )}
                        {job.isStale && (
                          <span title="Job atrasado">
                            <AlertTriangle className="h-4 w-4 text-yellow-500" />
                          </span>
                        )}
                        <div>
                          <div className="font-medium">{job.displayName}</div>
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
                      <div className="text-xs text-gray-400">{job.scheduleDescription}</div>
                    </TableCell>
                    <TableCell>
                      {statusConfig ? (
                        <Badge className={cn(statusConfig.bgColor, statusConfig.color)}>
                          <StatusIcon
                            className={cn(
                              'mr-1 h-3 w-3',
                              job.lastStatus === 'running' && 'animate-spin'
                            )}
                          />
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
