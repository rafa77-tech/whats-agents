'use client'

import { useState } from 'react'
import { Power, Pause, Play, AlertTriangle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useAuth } from '@/hooks/use-auth'
import { JuliaPauseDialog } from './julia-pause-dialog'
import { ConfirmationDialog } from './confirmation-dialog'

interface JuliaStatus {
  is_active: boolean
  mode: string
  paused_until?: string
  pause_reason?: string
}

interface Props {
  status: JuliaStatus
  onToggle: (active: boolean, reason?: string) => Promise<void>
  onPause: (duration: number, reason: string) => Promise<void>
}

export function JuliaToggle({ status, onToggle, onPause }: Props) {
  const [showPauseDialog, setShowPauseDialog] = useState(false)
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [loading, setLoading] = useState(false)

  const { user } = useAuth()
  const canControl = user?.role && ['operator', 'manager', 'admin'].includes(user.role)

  const handleToggleClick = async (newState: boolean) => {
    if (!newState) {
      setShowConfirmDialog(true)
    } else {
      setLoading(true)
      try {
        await onToggle(true)
      } finally {
        setLoading(false)
      }
    }
  }

  const confirmOff = async () => {
    setLoading(true)
    try {
      await onToggle(false, 'Desligada via dashboard')
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadge = () => {
    if (status.is_active) {
      return <Badge className="bg-green-500">Ativa</Badge>
    }
    if (status.mode === 'paused' && status.paused_until) {
      return <Badge variant="secondary">Pausada</Badge>
    }
    return <Badge variant="destructive">Desativada</Badge>
  }

  const getPauseInfo = () => {
    if (!status.paused_until) return null

    const pausedUntil = new Date(status.paused_until)
    const now = new Date()
    const diffMs = pausedUntil.getTime() - now.getTime()

    if (diffMs <= 0) return null

    const diffMins = Math.ceil(diffMs / 60000)
    return `Volta em ${diffMins} min`
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div
                className={`rounded-full p-2 ${status.is_active ? 'bg-green-100' : 'bg-red-100'}`}
              >
                <Power
                  className={`h-5 w-5 ${status.is_active ? 'text-green-600' : 'text-red-600'}`}
                />
              </div>
              <div>
                <CardTitle className="text-lg">Julia</CardTitle>
                <CardDescription>Controle do agente</CardDescription>
              </div>
            </div>
            {getStatusBadge()}
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Toggle principal */}
          <div className="flex items-center justify-between rounded-lg bg-muted p-4">
            <div>
              <p className="font-medium">Status do Agente</p>
              <p className="text-sm text-muted-foreground">
                {status.is_active
                  ? 'Julia esta respondendo automaticamente'
                  : 'Julia nao esta respondendo'}
              </p>
            </div>
            <Switch
              checked={status.is_active}
              onCheckedChange={handleToggleClick}
              disabled={!canControl || loading}
            />
          </div>

          {/* Info de pausa */}
          {status.pause_reason && (
            <div className="flex items-center gap-2 rounded-lg bg-yellow-50 p-3 text-sm">
              <AlertTriangle className="h-4 w-4 text-yellow-600" />
              <div>
                <p className="font-medium">Motivo: {status.pause_reason}</p>
                {getPauseInfo() && <p className="text-muted-foreground">{getPauseInfo()}</p>}
              </div>
            </div>
          )}

          {/* Acoes */}
          <div className="flex gap-2">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => setShowPauseDialog(true)}
              disabled={!canControl || !status.is_active || loading}
            >
              <Pause className="mr-2 h-4 w-4" />
              Pausar
            </Button>

            {!status.is_active && (
              <Button
                className="flex-1"
                onClick={() => handleToggleClick(true)}
                disabled={!canControl || loading}
              >
                <Play className="mr-2 h-4 w-4" />
                Reativar
              </Button>
            )}
          </div>

          {!canControl && (
            <p className="text-center text-xs text-muted-foreground">
              Voce precisa de permissao de Operador para controlar a Julia
            </p>
          )}
        </CardContent>
      </Card>

      <JuliaPauseDialog
        open={showPauseDialog}
        onOpenChange={setShowPauseDialog}
        onPause={onPause}
      />

      <ConfirmationDialog
        open={showConfirmDialog}
        onOpenChange={setShowConfirmDialog}
        title="Desativar Julia?"
        description="A Julia vai parar de responder todas as mensagens. Medicos esperando resposta podem ficar sem atendimento."
        confirmText="Sim, desativar"
        variant="destructive"
        onConfirm={confirmOff}
      />
    </>
  )
}
