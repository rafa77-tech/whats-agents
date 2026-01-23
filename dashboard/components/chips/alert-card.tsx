/**
 * Alert Card - Sprint 36
 *
 * Card individual de alerta.
 */

'use client'

import { useState } from 'react'
import Link from 'next/link'
import type { Route } from 'next'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { cn } from '@/lib/utils'
import { chipsApi } from '@/lib/api/chips'
import { ChipAlert, ChipAlertSeverity, ChipAlertType } from '@/types/chips'
import {
  AlertTriangle,
  TrendingDown,
  Ban,
  AlertCircle,
  Activity,
  MessageSquare,
  Wifi,
  Clock,
  Target,
  Shield,
  CheckCircle,
  Loader2,
  Phone,
  ExternalLink,
} from 'lucide-react'

interface AlertCardProps {
  alert: ChipAlert
  onResolved: () => void
}

const severityConfig: Record<
  ChipAlertSeverity,
  { color: string; bgColor: string; borderColor: string }
> = {
  critico: {
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
  },
  alerta: {
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
  },
  atencao: {
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
  },
  info: {
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
  },
}

const typeConfig: Record<ChipAlertType, { icon: typeof AlertTriangle; label: string }> = {
  TRUST_CAINDO: { icon: TrendingDown, label: 'Trust Caindo' },
  TAXA_BLOCK_ALTA: { icon: Ban, label: 'Taxa de Block Alta' },
  ERROS_FREQUENTES: { icon: AlertCircle, label: 'Erros Frequentes' },
  DELIVERY_BAIXO: { icon: Activity, label: 'Delivery Baixo' },
  RESPOSTA_BAIXA: { icon: MessageSquare, label: 'Resposta Baixa' },
  DESCONEXAO: { icon: Wifi, label: 'Desconexão' },
  LIMITE_PROXIMO: { icon: Clock, label: 'Limite Próximo' },
  FASE_ESTAGNADA: { icon: Target, label: 'Fase Estagnada' },
  QUALIDADE_META: { icon: Shield, label: 'Qualidade Meta' },
  COMPORTAMENTO_ANOMALO: { icon: AlertTriangle, label: 'Comportamento Anômalo' },
}

const severityLabels: Record<ChipAlertSeverity, string> = {
  critico: 'Crítico',
  alerta: 'Alerta',
  atencao: 'Atenção',
  info: 'Info',
}

export function AlertCard({ alert, onResolved }: AlertCardProps) {
  const [isResolving, setIsResolving] = useState(false)
  const [showResolveDialog, setShowResolveDialog] = useState(false)
  const [notes, setNotes] = useState('')

  const handleResolve = async () => {
    setIsResolving(true)
    try {
      await chipsApi.resolveAlert(alert.id, notes)
      setShowResolveDialog(false)
      onResolved()
    } catch (error) {
      console.error('Error resolving alert:', error)
    } finally {
      setIsResolving(false)
    }
  }

  const severity = severityConfig[alert.severity]
  const type = typeConfig[alert.type]
  const Icon = type.icon

  return (
    <Card className={cn('border', alert.resolvedAt ? 'bg-gray-50' : severity.borderColor)}>
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          {/* Icon */}
          <div
            className={cn(
              'shrink-0 rounded-full p-2',
              alert.resolvedAt ? 'bg-gray-100' : severity.bgColor
            )}
          >
            {alert.resolvedAt ? (
              <CheckCircle className="h-5 w-5 text-gray-500" />
            ) : (
              <Icon className={cn('h-5 w-5', severity.color)} />
            )}
          </div>

          {/* Content */}
          <div className="min-w-0 flex-1">
            <div className="mb-1 flex items-start justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="font-medium text-gray-900">{alert.title}</h3>
                <Badge
                  className={cn(
                    alert.resolvedAt
                      ? 'bg-gray-100 text-gray-600'
                      : cn(severity.bgColor, severity.color)
                  )}
                >
                  {severityLabels[alert.severity]}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  {type.label}
                </Badge>
              </div>
              <span className="whitespace-nowrap text-xs text-gray-500">
                {formatTimestamp(alert.createdAt)}
              </span>
            </div>

            <p className="mb-2 text-sm text-gray-600">{alert.message}</p>

            {alert.recommendation && !alert.resolvedAt && (
              <p className="mb-2 rounded bg-gray-50 p-2 text-sm text-gray-500">
                <strong>Recomendação:</strong> {alert.recommendation}
              </p>
            )}

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4 text-xs text-gray-500">
                <Link
                  href={`/chips/${alert.chipId}` as Route}
                  className="flex items-center gap-1 hover:text-gray-700"
                >
                  <Phone className="h-3 w-3" />
                  {alert.chipTelefone}
                  <ExternalLink className="h-3 w-3" />
                </Link>
              </div>

              {!alert.resolvedAt && (
                <Dialog open={showResolveDialog} onOpenChange={setShowResolveDialog}>
                  <DialogTrigger asChild>
                    <Button variant="outline" size="sm">
                      <CheckCircle className="mr-1 h-4 w-4" />
                      Resolver
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Resolver Alerta</DialogTitle>
                      <DialogDescription>
                        Adicione notas sobre a resolução deste alerta.
                      </DialogDescription>
                    </DialogHeader>
                    <div className="py-4">
                      <Textarea
                        placeholder="Descreva como o alerta foi resolvido..."
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        rows={4}
                      />
                    </div>
                    <DialogFooter>
                      <Button
                        variant="outline"
                        onClick={() => setShowResolveDialog(false)}
                        disabled={isResolving}
                      >
                        Cancelar
                      </Button>
                      <Button onClick={handleResolve} disabled={isResolving}>
                        {isResolving ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Resolvendo...
                          </>
                        ) : (
                          'Marcar como Resolvido'
                        )}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              )}

              {alert.resolvedAt && (
                <div className="text-xs text-gray-500">
                  Resolvido em {new Date(alert.resolvedAt).toLocaleString('pt-BR')}
                  {alert.resolvedBy && ` por ${alert.resolvedBy}`}
                </div>
              )}
            </div>

            {alert.resolvedAt && alert.resolutionNotes && (
              <p className="mt-2 rounded bg-green-50 p-2 text-sm text-gray-500">
                <strong>Resolução:</strong> {alert.resolutionNotes}
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffMins < 60) {
    return `${diffMins}m atrás`
  } else if (diffHours < 24) {
    return `${diffHours}h atrás`
  } else if (diffDays < 7) {
    return `${diffDays}d atrás`
  } else {
    return date.toLocaleDateString('pt-BR')
  }
}
