'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  RefreshCw,
  Settings,
  Upload,
  Loader2,
  XCircle,
  CheckCircle2,
  Users,
  Link as LinkIcon,
  Clock,
  Play,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { CapacityBar } from './capacity-bar'
import { LinksTable } from './links-table'
import { ProcessingQueue } from './processing-queue'
import { ImportLinksModal } from './import-links-modal'
import { GroupEntryConfigModal } from './group-entry-config-modal'

interface GroupEntryDashboard {
  links: {
    total: number
    pending: number
    validated: number
    scheduled: number
    processed: number
  }
  queue: {
    queued: number
    processing: number
  }
  processedToday: {
    success: number
    failed: number
  }
  capacity: {
    used: number
    total: number
  }
}

export function GroupEntryPageContent() {
  const [data, setData] = useState<GroupEntryDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [isImportOpen, setIsImportOpen] = useState(false)
  const [isConfigOpen, setIsConfigOpen] = useState(false)
  const [processingAction, setProcessingAction] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      setError(null)

      const [dashboardRes, capacityRes] = await Promise.all([
        fetch('/api/group-entry/dashboard').catch(() => null),
        fetch('/api/group-entry/capacity').catch(() => null),
      ])

      let dashboardData = null
      if (dashboardRes?.ok) {
        dashboardData = await dashboardRes.json()
      }

      let capacityData = null
      if (capacityRes?.ok) {
        capacityData = await capacityRes.json()
      }

      setData({
        links: {
          total: dashboardData?.links?.total || 0,
          pending: dashboardData?.links?.pending || 0,
          validated: dashboardData?.links?.validated || 0,
          scheduled: dashboardData?.links?.scheduled || 0,
          processed: dashboardData?.links?.processed || 0,
        },
        queue: {
          queued: dashboardData?.queue?.queued || 0,
          processing: dashboardData?.queue?.processing || 0,
        },
        processedToday: {
          success: dashboardData?.processed_today?.success || 0,
          failed: dashboardData?.processed_today?.failed || 0,
        },
        capacity: {
          used: capacityData?.used || 0,
          total: capacityData?.total || 100,
        },
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro desconhecido')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleValidatePending = async () => {
    setProcessingAction('validate')
    try {
      await fetch('/api/group-entry/validate/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'pending' }),
      })
      await fetchData()
    } catch {
      // Ignore errors
    } finally {
      setProcessingAction(null)
    }
  }

  const handleScheduleValidated = async () => {
    setProcessingAction('schedule')
    try {
      await fetch('/api/group-entry/schedule/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'validated' }),
      })
      await fetchData()
    } catch {
      // Ignore errors
    } finally {
      setProcessingAction(null)
    }
  }

  const handleProcessQueue = async () => {
    setProcessingAction('process')
    try {
      await fetch('/api/group-entry/process', { method: 'POST' })
      await fetchData()
    } catch {
      // Ignore errors
    } finally {
      setProcessingAction(null)
    }
  }

  if (loading && !data) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-gray-400" />
          <p className="mt-2 text-sm text-gray-500">Carregando dados...</p>
        </div>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="text-center">
          <XCircle className="mx-auto h-8 w-8 text-red-400" />
          <p className="mt-2 text-sm text-red-600">{error}</p>
          <Button onClick={fetchData} variant="outline" className="mt-4">
            Tentar novamente
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Entrada em Grupos</h1>
          <p className="text-gray-500">Gestao de links e entrada em grupos WhatsApp</p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => setIsImportOpen(true)} variant="outline" size="sm">
            <Upload className="mr-2 h-4 w-4" />
            Importar
          </Button>
          <Button onClick={() => setIsConfigOpen(true)} variant="outline" size="sm">
            <Settings className="h-4 w-4" />
          </Button>
          <Button onClick={fetchData} variant="outline" size="sm" disabled={loading}>
            <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
          </Button>
        </div>
      </div>

      {/* Capacity Bar */}
      <Card>
        <CardContent className="pt-6">
          <CapacityBar used={data?.capacity.used || 0} total={data?.capacity.total || 100} />
        </CardContent>
      </Card>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <div>
              <p className="text-sm text-gray-500">Links</p>
              <p className="text-2xl font-bold">{data?.links.total || 0}</p>
              <p className="text-xs text-gray-400">{data?.links.pending || 0} pendentes</p>
            </div>
            <LinkIcon className="h-8 w-8 text-blue-400" />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <div>
              <p className="text-sm text-gray-500">Fila</p>
              <p className="text-2xl font-bold">{data?.queue.queued || 0}</p>
              <p className="text-xs text-gray-400">{data?.queue.processing || 0} processando</p>
            </div>
            <Clock className="h-8 w-8 text-yellow-400" />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center justify-between p-4">
            <div>
              <p className="text-sm text-gray-500">Processados Hoje</p>
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold text-green-600">
                  {data?.processedToday.success || 0}
                </span>
                <span className="text-gray-400">/</span>
                <span className="text-xl font-bold text-red-600">
                  {data?.processedToday.failed || 0}
                </span>
              </div>
            </div>
            <Users className="h-8 w-8 text-green-400" />
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Acoes Rapidas</CardTitle>
          <CardDescription>Execute operacoes em lote</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={handleValidatePending}
              variant="outline"
              size="sm"
              disabled={processingAction !== null || (data?.links.pending || 0) === 0}
            >
              {processingAction === 'validate' ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle2 className="mr-2 h-4 w-4" />
              )}
              Validar Pendentes ({data?.links.pending || 0})
            </Button>
            <Button
              onClick={handleScheduleValidated}
              variant="outline"
              size="sm"
              disabled={processingAction !== null || (data?.links.validated || 0) === 0}
            >
              {processingAction === 'schedule' ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Clock className="mr-2 h-4 w-4" />
              )}
              Agendar Validados ({data?.links.validated || 0})
            </Button>
            <Button
              onClick={handleProcessQueue}
              variant="outline"
              size="sm"
              disabled={processingAction !== null || (data?.queue.queued || 0) === 0}
            >
              {processingAction === 'process' ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              Processar Fila ({data?.queue.queued || 0})
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Links</TabsTrigger>
          <TabsTrigger value="queue">Fila</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <LinksTable onUpdate={fetchData} />
        </TabsContent>

        <TabsContent value="queue">
          <ProcessingQueue onUpdate={fetchData} />
        </TabsContent>
      </Tabs>

      {/* Modals */}
      {isImportOpen && (
        <ImportLinksModal
          onClose={() => setIsImportOpen(false)}
          onImport={() => {
            setIsImportOpen(false)
            fetchData()
          }}
        />
      )}

      {isConfigOpen && (
        <GroupEntryConfigModal
          onClose={() => setIsConfigOpen(false)}
          onSave={() => {
            setIsConfigOpen(false)
            fetchData()
          }}
        />
      )}
    </div>
  )
}
