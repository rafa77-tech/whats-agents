/**
 * Jobs Table - Sprint 42
 *
 * Tabela de jobs com status, metricas, ordenacao e acoes.
 */

'use client'

import { useState, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
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
  Play,
  Pause,
  Trash2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { executeJobAction, type JobActionType } from '@/lib/api/monitor'
import type { JobSummary, JobStatus, JobCategory } from '@/types/monitor'

interface JobsTableProps {
  jobs: JobSummary[] | null
  isLoading?: boolean
  onJobClick: (jobName: string) => void
  onJobAction?: () => void // callback para refresh apos acao
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
    color: 'text-status-info-foreground',
    bgColor: 'bg-status-info',
    label: 'Executando',
    priority: 1,
  },
  error: {
    icon: XCircle,
    color: 'text-status-error-foreground',
    bgColor: 'bg-status-error',
    label: 'Erro',
    priority: 2,
  },
  timeout: {
    icon: Clock,
    color: 'text-status-warning-foreground',
    bgColor: 'bg-status-warning',
    label: 'Timeout',
    priority: 3,
  },
  success: {
    icon: CheckCircle,
    color: 'text-status-success-foreground',
    bgColor: 'bg-status-success',
    label: 'Sucesso',
    priority: 4,
  },
}

const CATEGORY_COLORS: Record<JobCategory, string> = {
  critical: 'bg-status-error text-status-error-foreground',
  frequent: 'bg-status-info text-status-info-foreground',
  hourly: 'bg-accent/20 text-accent',
  daily: 'bg-status-success text-status-success-foreground',
  weekly: 'bg-status-neutral text-status-neutral-foreground',
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
      className={cn('cursor-pointer select-none hover:bg-muted/50', className)}
      onClick={() => onSort(column)}
    >
      <div className="flex items-center gap-1">
        {children}
        <Icon className={cn('h-4 w-4', isActive ? 'text-foreground' : 'text-muted-foreground')} />
      </div>
    </TableHead>
  )
}

// Tipos para dialogos de confirmacao
type DialogType = 'run' | 'pause' | 'delete' | null

interface DialogState {
  type: DialogType
  job: JobSummary | null
}

export function JobsTable({ jobs, isLoading, onJobClick, onJobAction }: JobsTableProps) {
  const [sortColumn, setSortColumn] = useState<SortColumn | null>(null)
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')

  // Estado dos dialogos
  const [dialogState, setDialogState] = useState<DialogState>({ type: null, job: null })
  const [deleteConfirmText, setDeleteConfirmText] = useState('')
  const [isActionLoading, setIsActionLoading] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

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

  // Abrir dialogo de confirmacao
  const openDialog = (type: DialogType, job: JobSummary) => {
    setDialogState({ type, job })
    setDeleteConfirmText('')
    setActionError(null)
  }

  // Fechar dialogo
  const closeDialog = () => {
    setDialogState({ type: null, job: null })
    setDeleteConfirmText('')
    setActionError(null)
  }

  // Executar acao no job
  const handleAction = async (action: JobActionType) => {
    if (!dialogState.job) return

    setIsActionLoading(true)
    setActionError(null)

    try {
      await executeJobAction(dialogState.job.name, action)
      closeDialog()
      onJobAction?.() // Refresh dados
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Erro ao executar acao')
    } finally {
      setIsActionLoading(false)
    }
  }

  // Verifica se pode confirmar delete
  const canConfirmDelete = dialogState.job && deleteConfirmText === dialogState.job.displayName

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
              <div key={i} className="h-12 rounded bg-muted" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <TooltipProvider>
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">
            Jobs do Sistema
            {jobs && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">({jobs.length} jobs)</span>
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
                >
                  Execuções 24h
                </SortableHeader>
                <TableHead className="w-[100px]">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedJobs?.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                    Nenhum job encontrado com os filtros aplicados.
                  </TableCell>
                </TableRow>
              ) : (
                sortedJobs?.map((job) => {
                  const statusConfig = job.lastStatus ? STATUS_CONFIG[job.lastStatus] : null
                  const StatusIcon = statusConfig?.icon || Clock

                  return (
                    <TableRow key={job.name} className="hover:bg-muted/50">
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {job.isCritical && (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span>
                                  <AlertTriangle className="h-4 w-4 text-status-error-solid" />
                                </span>
                              </TooltipTrigger>
                              <TooltipContent side="top">
                                <p>Job Critico</p>
                              </TooltipContent>
                            </Tooltip>
                          )}
                          {job.isStale && (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span>
                                  <AlertTriangle className="h-4 w-4 text-status-warning-solid" />
                                </span>
                              </TooltipTrigger>
                              <TooltipContent side="top">
                                <p>Job Atrasado</p>
                              </TooltipContent>
                            </Tooltip>
                          )}
                          <div className="cursor-pointer" onClick={() => onJobClick(job.name)}>
                            <div className="font-medium">{job.displayName}</div>
                            <div className="text-xs text-muted-foreground">{job.description}</div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge className={cn('text-xs', CATEGORY_COLORS[job.category])}>
                          {job.category}
                        </Badge>
                      </TableCell>
                      <TableCell suppressHydrationWarning>
                        <div className="text-sm">{formatTimeAgo(job.lastRun)}</div>
                        <div className="text-xs text-muted-foreground">{job.scheduleDescription}</div>
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
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <span className="text-status-success-foreground">{job.success24h}</span>
                          <span className="text-muted-foreground">/</span>
                          <span className={job.errors24h > 0 ? 'text-status-error-foreground' : 'text-muted-foreground'}>
                            {job.errors24h}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          {/* Executar - desabilitado se já está rodando */}
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-7 w-7 p-0"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    openDialog('run', job)
                                  }}
                                  disabled={job.lastStatus === 'running'}
                                >
                                  <Play
                                    className={cn(
                                      'h-3.5 w-3.5',
                                      job.lastStatus === 'running'
                                        ? 'text-muted-foreground/50'
                                        : 'text-status-success-foreground'
                                    )}
                                  />
                                </Button>
                              </span>
                            </TooltipTrigger>
                            <TooltipContent side="top">
                              {job.lastStatus === 'running' ? 'Job em execução' : 'Executar agora'}
                            </TooltipContent>
                          </Tooltip>

                          {/* Pausar - desabilitado se não está rodando */}
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-7 w-7 p-0"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    openDialog('pause', job)
                                  }}
                                  disabled={
                                    job.lastStatus !== 'running' && job.lastStatus !== 'success'
                                  }
                                >
                                  <Pause
                                    className={cn(
                                      'h-3.5 w-3.5',
                                      job.lastStatus !== 'running' && job.lastStatus !== 'success'
                                        ? 'text-muted-foreground/50'
                                        : 'text-status-warning-foreground'
                                    )}
                                  />
                                </Button>
                              </span>
                            </TooltipTrigger>
                            <TooltipContent side="top">Pausar job</TooltipContent>
                          </Tooltip>

                          {/* Remover */}
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-7 w-7 p-0"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    openDialog('delete', job)
                                  }}
                                >
                                  <Trash2 className="h-3.5 w-3.5 text-status-error-solid" />
                                </Button>
                              </span>
                            </TooltipTrigger>
                            <TooltipContent side="top">Remover job</TooltipContent>
                          </Tooltip>

                          {/* Ver detalhes */}
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 w-7 p-0"
                            onClick={() => onJobClick(job.name)}
                          >
                            <ChevronRight className="h-4 w-4 text-muted-foreground" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Dialog de Confirmacao - Executar */}
      <AlertDialog
        open={dialogState.type === 'run'}
        onOpenChange={(open) => !open && closeDialog()}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Executar Job</AlertDialogTitle>
            <AlertDialogDescription>
              Deseja executar o job <strong>{dialogState.job?.displayName}</strong> agora?
              <br />
              <br />
              Esta ação irá iniciar uma execução imediata do job, independente do agendamento
              configurado.
            </AlertDialogDescription>
          </AlertDialogHeader>
          {actionError && (
            <div className="rounded-md bg-status-error p-3 text-sm text-status-error-foreground">{actionError}</div>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isActionLoading}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => handleAction('run')}
              disabled={isActionLoading}
              className="bg-status-success-solid hover:bg-status-success-solid-hover"
            >
              {isActionLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              Executar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Dialog de Confirmacao - Pausar */}
      <AlertDialog
        open={dialogState.type === 'pause'}
        onOpenChange={(open) => !open && closeDialog()}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Pausar Job</AlertDialogTitle>
            <AlertDialogDescription>
              Deseja pausar o job <strong>{dialogState.job?.displayName}</strong>?
              <br />
              <br />O job não será executado automaticamente até ser retomado. Isso pode afetar o
              funcionamento do sistema se for um job crítico.
            </AlertDialogDescription>
          </AlertDialogHeader>
          {actionError && (
            <div className="rounded-md bg-status-error p-3 text-sm text-status-error-foreground">{actionError}</div>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isActionLoading}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => handleAction('pause')}
              disabled={isActionLoading}
              className="bg-status-warning-solid hover:bg-status-warning-solid-hover"
            >
              {isActionLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Pause className="mr-2 h-4 w-4" />
              )}
              Pausar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Dialog de Confirmacao - Remover (com input de confirmacao) */}
      <AlertDialog
        open={dialogState.type === 'delete'}
        onOpenChange={(open) => !open && closeDialog()}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="text-status-error-solid">Remover Job</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div>
                <p>
                  Você está prestes a remover o job <strong>{dialogState.job?.displayName}</strong>.
                </p>
                <p className="mt-2">
                  Esta ação é <strong>irreversível</strong>. O job será removido do scheduler e não
                  será mais executado.
                </p>
                <p className="mt-4">
                  Para confirmar, digite o nome do job:{' '}
                  <code className="rounded bg-muted px-2 py-1 text-sm font-bold">
                    {dialogState.job?.displayName}
                  </code>
                </p>
                <Input
                  className="mt-3"
                  placeholder="Digite o nome do job para confirmar"
                  value={deleteConfirmText}
                  onChange={(e) => setDeleteConfirmText(e.target.value)}
                  disabled={isActionLoading}
                />
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          {actionError && (
            <div className="rounded-md bg-status-error p-3 text-sm text-status-error-foreground">{actionError}</div>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isActionLoading}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => handleAction('delete')}
              disabled={isActionLoading || !canConfirmDelete}
              className="bg-status-error-solid hover:bg-status-error-solid-hover disabled:opacity-50"
            >
              {isActionLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Remover Permanentemente
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </TooltipProvider>
  )
}
