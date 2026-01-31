/**
 * Job Detail Modal - Sprint 42
 *
 * Modal com historico de execucoes de um job.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { CheckCircle, XCircle, Clock, Loader2, ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { getCronDescription } from '@/lib/utils/cron-calculator'
import { getJobExecutions } from '@/lib/api/monitor'
import { JOBS_BY_NAME } from '@/lib/monitor/jobs-config'
import type { JobExecution, JobStatus, JobDetailModalProps } from '@/types/monitor'

const STATUS_CONFIG: Record<
  JobStatus,
  {
    icon: typeof CheckCircle
    color: string
    bgColor: string
    label: string
  }
> = {
  running: { icon: Loader2, color: 'text-blue-600', bgColor: 'bg-blue-100', label: 'Executando' },
  success: {
    icon: CheckCircle,
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    label: 'Sucesso',
  },
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

  const fetchExecutions = useCallback(
    async (pageNum: number) => {
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
    },
    [jobName]
  )

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
            <span>{jobDef?.displayName || jobName}</span>
            {jobDef?.isCritical && (
              <Badge variant="destructive" className="text-xs">
                Critico
              </Badge>
            )}
          </DialogTitle>
          {jobDef && (
            <div className="space-y-2">
              <p className="text-sm text-gray-500">{getCronDescription(jobDef.schedule)}</p>
              {jobDef.helpText && (
                <div className="rounded-md bg-blue-50 p-3 text-sm text-blue-800">
                  {jobDef.helpText}
                </div>
              )}
            </div>
          )}
        </DialogHeader>

        <div className="space-y-4">
          {/* Header com total */}
          <div className="flex items-center justify-between text-sm text-gray-500">
            <span>{total} execucoes encontradas</span>
            <span>Pagina {page}</span>
          </div>

          {/* Lista de execucoes */}
          <ScrollArea className="h-[400px]">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
              </div>
            ) : executions.length === 0 ? (
              <div className="py-8 text-center text-gray-500">Nenhuma execucao encontrada.</div>
            ) : (
              <div className="space-y-2">
                {executions.map((exec) => {
                  const config = STATUS_CONFIG[exec.status]
                  const StatusIcon = config.icon

                  return (
                    <div key={exec.id} className="rounded-lg border p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Badge className={cn(config.bgColor, config.color)}>
                            <StatusIcon
                              className={cn(
                                'mr-1 h-3 w-3',
                                exec.status === 'running' && 'animate-spin'
                              )}
                            />
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
                        {exec.itemsProcessed !== null && <span>Itens: {exec.itemsProcessed}</span>}
                        {exec.responseCode !== null && <span>HTTP: {exec.responseCode}</span>}
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

          {/* Paginacao */}
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
              Proxima
              <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
