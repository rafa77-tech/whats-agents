/**
 * Chip Actions Panel - Sprint 36
 *
 * Painel de ações disponíveis para o chip.
 */

'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
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
import { chipsApi } from '@/lib/api/chips'
import { ChipFullDetail } from '@/types/chips'
import { Pause, Play, TrendingUp, AlertTriangle, Loader2 } from 'lucide-react'

interface ChipActionsPanelProps {
  chip: ChipFullDetail
  onActionComplete: () => void
}

type ActionType = 'pause' | 'resume' | 'promote'

interface ActionConfig {
  label: string
  description: string
  confirmLabel: string
  icon: typeof Pause
  variant: 'default' | 'outline' | 'destructive'
  condition: (chip: ChipFullDetail) => boolean
}

const actionsConfig: Record<ActionType, ActionConfig> = {
  pause: {
    label: 'Pausar Chip',
    description:
      'Ao pausar o chip, ele deixará de enviar e receber mensagens até ser retomado manualmente.',
    confirmLabel: 'Pausar',
    icon: Pause,
    variant: 'outline',
    condition: (chip) => chip.status !== 'paused' && chip.status !== 'banned',
  },
  resume: {
    label: 'Retomar Chip',
    description: 'Ao retomar o chip, ele voltará a enviar e receber mensagens normalmente.',
    confirmLabel: 'Retomar',
    icon: Play,
    variant: 'default',
    condition: (chip) => chip.status === 'paused',
  },
  promote: {
    label: 'Promover Fase',
    description:
      'Promover o chip para a próxima fase de warmup. Isso aumentará os limites de mensagens.',
    confirmLabel: 'Promover',
    icon: TrendingUp,
    variant: 'default',
    condition: (chip) =>
      chip.status === 'warming' && chip.warmupPhase !== 'operacao' && chip.trustScore >= 70,
  },
}

export function ChipActionsPanel({ chip, onActionComplete }: ChipActionsPanelProps) {
  const [confirmAction, setConfirmAction] = useState<ActionType | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleAction = async (action: ActionType) => {
    setIsProcessing(true)
    setError(null)

    try {
      const actionFn = {
        pause: chipsApi.pauseChip,
        resume: chipsApi.resumeChip,
        promote: chipsApi.promoteChip,
      }[action]

      const result = await actionFn(chip.id)

      if (result.success) {
        onActionComplete()
      } else {
        setError(result.message || 'Ação falhou')
      }
    } catch (err) {
      console.error('Action failed:', err)
      setError('Erro ao executar ação')
    } finally {
      setIsProcessing(false)
      setConfirmAction(null)
    }
  }

  const availableActions = (Object.keys(actionsConfig) as ActionType[]).filter((action) =>
    actionsConfig[action].condition(chip)
  )

  const config = confirmAction ? actionsConfig[confirmAction] : null

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Ações</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {error && (
            <div className="mb-2 rounded-md border border-red-200 bg-red-50 p-3">
              <div className="flex items-center gap-2 text-red-600">
                <AlertTriangle className="h-4 w-4" />
                <span className="text-sm">{error}</span>
              </div>
            </div>
          )}

          {availableActions.length === 0 ? (
            <p className="py-2 text-sm text-gray-500">
              Nenhuma ação disponível para este chip no momento.
            </p>
          ) : (
            availableActions.map((action) => {
              const actionConfig = actionsConfig[action]
              const Icon = actionConfig.icon

              return (
                <Button
                  key={action}
                  variant={actionConfig.variant}
                  className="w-full justify-start"
                  onClick={() => setConfirmAction(action)}
                  disabled={isProcessing}
                >
                  <Icon className="mr-2 h-4 w-4" />
                  {actionConfig.label}
                </Button>
              )
            })
          )}

          {/* Status info */}
          {chip.status === 'banned' && (
            <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3">
              <div className="flex items-start gap-2 text-red-600">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <div>
                  <span className="text-sm font-medium">Chip Banido</span>
                  <p className="mt-1 text-xs text-red-500">
                    Este chip foi banido pelo WhatsApp e não pode ser recuperado.
                  </p>
                </div>
              </div>
            </div>
          )}

          {chip.status === 'warming' && chip.warmupPhase && (
            <div className="mt-4 rounded-md border border-blue-200 bg-blue-50 p-3">
              <span className="text-sm text-blue-700">Em aquecimento - Dia {chip.warmingDay}</span>
              {chip.trustScore < 70 && (
                <p className="mt-1 text-xs text-blue-600">
                  Trust score precisa ser ≥ 70 para promoção
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Confirmation dialog */}
      <AlertDialog open={!!confirmAction} onOpenChange={() => setConfirmAction(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{config?.label}</AlertDialogTitle>
            <AlertDialogDescription>{config?.description}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isProcessing}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => confirmAction && handleAction(confirmAction)}
              disabled={isProcessing}
            >
              {isProcessing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processando...
                </>
              ) : (
                config?.confirmLabel
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
