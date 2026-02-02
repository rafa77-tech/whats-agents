'use client'

import { useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Loader2, XCircle, RefreshCw, Play, X } from 'lucide-react'
import { toast } from '@/hooks/use-toast'
import {
  useProcessingQueue,
  useQueueActions,
  getQueueStatusBadgeColor,
  getQueueStatusLabel,
  formatLinkUrl,
  formatTime,
} from '@/lib/group-entry'

interface ProcessingQueueProps {
  onUpdate: () => void
}

export function ProcessingQueue({ onUpdate }: ProcessingQueueProps) {
  const { queue, loading, error, refresh } = useProcessingQueue(true)

  const handleSuccess = () => {
    refresh()
    onUpdate()
  }

  const {
    actionLoading,
    error: actionError,
    processItem,
    cancelItem,
  } = useQueueActions(handleSuccess)

  // Show toast on errors
  useEffect(() => {
    if (error) {
      toast({
        title: 'Erro',
        description: error,
        variant: 'destructive',
      })
    }
  }, [error])

  useEffect(() => {
    if (actionError) {
      toast({
        title: 'Erro na acao',
        description: actionError,
        variant: 'destructive',
      })
    }
  }, [actionError])

  const handleProcess = async (id: string) => {
    const success = await processItem(id)
    if (success) {
      toast({
        title: 'Sucesso',
        description: 'Item processado com sucesso',
      })
    }
  }

  const handleCancel = async (id: string) => {
    const success = await cancelItem(id)
    if (success) {
      toast({
        title: 'Sucesso',
        description: 'Item cancelado com sucesso',
      })
    }
  }

  const renderStatusBadge = (status: string) => {
    const colorClass = getQueueStatusBadgeColor(status)
    const label = getQueueStatusLabel(status)
    return <Badge className={colorClass}>{label}</Badge>
  }

  const canTakeAction = (status: string) => status === 'queued'

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">Fila de Processamento</CardTitle>
            <CardDescription>{queue.length} itens na fila</CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={refresh}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        ) : queue.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>#</TableHead>
                <TableHead>Link</TableHead>
                <TableHead>Chip</TableHead>
                <TableHead>Agendado</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Acoes</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {queue.map((item, index) => (
                <TableRow key={item.id}>
                  <TableCell className="font-medium">{index + 1}</TableCell>
                  <TableCell>
                    <code className="text-xs">{formatLinkUrl(item.link_url)}</code>
                  </TableCell>
                  <TableCell className="text-sm">{item.chip_name}</TableCell>
                  <TableCell className="text-sm text-gray-500">
                    {formatTime(item.scheduled_at)}
                  </TableCell>
                  <TableCell>{renderStatusBadge(item.status)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      {canTakeAction(item.status) && (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleProcess(item.id)}
                            disabled={actionLoading === item.id}
                            title="Processar agora"
                          >
                            {actionLoading === item.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Play className="h-4 w-4" />
                            )}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleCancel(item.id)}
                            disabled={actionLoading === item.id}
                            title="Cancelar"
                          >
                            {actionLoading === item.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <X className="h-4 w-4 text-status-error-foreground" />
                            )}
                          </Button>
                        </>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <div className="py-8 text-center text-gray-500">
            <XCircle className="mx-auto h-8 w-8 text-gray-300" />
            <p className="mt-2">Nenhum item na fila</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
