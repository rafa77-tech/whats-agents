'use client'

import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Loader2, AlertTriangle, CheckCircle2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  getAnomalySeverityColors,
  getAnomalySeverityLabel,
  formatResolutionNotes,
  truncateAnomalyId,
  formatDateTimeBR,
} from '@/lib/integridade'
import type { Anomaly, AnomalyResolutionType } from '@/lib/integridade'

interface AnomalyDetailModalProps {
  anomaly: Anomaly
  onClose: () => void
  onResolve: (id: string, notas: string) => Promise<void>
}

export function AnomalyDetailModal({ anomaly, onClose, onResolve }: AnomalyDetailModalProps) {
  const [notas, setNotas] = useState('')
  const [resolving, setResolving] = useState(false)

  const handleResolve = async (tipo: AnomalyResolutionType) => {
    setResolving(true)
    try {
      const notasCompletas = formatResolutionNotes(tipo, notas)
      await onResolve(anomaly.id, notasCompletas)
    } finally {
      setResolving(false)
    }
  }

  const severityColors = getAnomalySeverityColors(anomaly.severidade)

  return (
    <Dialog open onOpenChange={() => onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className={cn('h-5 w-5', severityColors.icon)} />
            Anomalia #{truncateAnomalyId(anomaly.id)}
          </DialogTitle>
          <DialogDescription>Detalhes e resolucao da anomalia</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Info Grid */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Tipo</p>
              <p className="font-medium">{anomaly.tipo}</p>
            </div>
            <div>
              <p className="text-gray-500">Severidade</p>
              <Badge className={severityColors.badge}>
                {getAnomalySeverityLabel(anomaly.severidade)}
              </Badge>
            </div>
            <div>
              <p className="text-gray-500">Entidade</p>
              <p className="font-medium">{anomaly.entidade}</p>
            </div>
            <div>
              <p className="text-gray-500">ID</p>
              <code className="text-xs">{anomaly.entidadeId}</code>
            </div>
            <div className="col-span-2">
              <p className="text-gray-500">Detectada</p>
              <p className="font-medium">{formatDateTimeBR(anomaly.criadaEm)}</p>
            </div>
          </div>

          {/* Message */}
          <div>
            <p className="mb-1 text-sm text-gray-500">Detalhes</p>
            <div className="rounded-lg bg-gray-50 p-3 text-sm">
              {anomaly.mensagem || 'Sem detalhes adicionais'}
            </div>
          </div>

          {/* Status */}
          {anomaly.resolvida ? (
            <div className="flex items-center gap-2 rounded-lg bg-status-success p-3 text-status-success-foreground">
              <CheckCircle2 className="h-5 w-5" />
              <span>Esta anomalia ja foi resolvida</span>
            </div>
          ) : (
            <>
              {/* Resolution Notes */}
              <div>
                <p className="mb-1 text-sm text-gray-500">Notas de Resolucao</p>
                <Textarea
                  placeholder="Descreva a causa e a resolucao..."
                  value={notas}
                  onChange={(e) => setNotas(e.target.value)}
                  rows={3}
                />
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Fechar
          </Button>
          {!anomaly.resolvida && (
            <>
              <Button
                variant="outline"
                onClick={() => handleResolve('falso_positivo')}
                disabled={resolving}
              >
                {resolving ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Falso Positivo'}
              </Button>
              <Button onClick={() => handleResolve('corrigido')} disabled={resolving}>
                {resolving ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Marcar Corrigido'}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
