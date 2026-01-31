'use client'

import { useState, useEffect, useCallback } from 'react'
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

interface QueueItem {
  id: string
  linkUrl: string
  chipName: string
  scheduledAt: string
  status: 'queued' | 'processing'
}

interface ProcessingQueueProps {
  onUpdate: () => void
}

export function ProcessingQueue({ onUpdate }: ProcessingQueueProps) {
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const fetchQueue = useCallback(async () => {
    try {
      const res = await fetch('/api/group-entry/queue')
      if (res.ok) {
        const data = await res.json()
        setQueue(
          data.queue?.map((q: Record<string, unknown>) => ({
            id: q.id,
            linkUrl: q.link_url,
            chipName: q.chip_name,
            scheduledAt: q.scheduled_at,
            status: q.status,
          })) || []
        )
      }
    } catch {
      // Ignore errors
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchQueue()
  }, [fetchQueue])

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(fetchQueue, 30000)
    return () => clearInterval(interval)
  }, [fetchQueue])

  const handleCancel = async (id: string) => {
    setActionLoading(id)
    try {
      await fetch(`/api/group-entry/queue/${id}`, { method: 'DELETE' })
      await fetchQueue()
      onUpdate()
    } catch {
      // Ignore errors
    } finally {
      setActionLoading(null)
    }
  }

  const handleProcess = async (id: string) => {
    setActionLoading(id)
    try {
      await fetch(`/api/group-entry/process/${id}`, { method: 'POST' })
      await fetchQueue()
      onUpdate()
    } catch {
      // Ignore errors
    } finally {
      setActionLoading(null)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'queued':
        return <Badge className="bg-yellow-100 text-yellow-800">Na Fila</Badge>
      case 'processing':
        return <Badge className="bg-blue-100 text-blue-800">Processando</Badge>
      default:
        return <Badge>{status}</Badge>
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">Fila de Processamento</CardTitle>
            <CardDescription>{queue.length} itens na fila</CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={fetchQueue}>
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
                    <code className="text-xs">
                      {item.linkUrl.replace('https://chat.whatsapp.com/', '...')}
                    </code>
                  </TableCell>
                  <TableCell className="text-sm">{item.chipName}</TableCell>
                  <TableCell className="text-sm text-gray-500">
                    {new Date(item.scheduledAt).toLocaleTimeString('pt-BR', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </TableCell>
                  <TableCell>{getStatusBadge(item.status)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      {item.status === 'queued' && (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleProcess(item.id)}
                            disabled={actionLoading === item.id}
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
                          >
                            {actionLoading === item.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <X className="h-4 w-4 text-red-500" />
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
