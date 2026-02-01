/**
 * Chips Bulk Actions - Sprint 36
 *
 * Barra de ações em lote para chips selecionados.
 */

'use client'

import { useState } from 'react'
import { Pause, Play, TrendingUp, X, Loader2 } from 'lucide-react'
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
import { cn } from '@/lib/utils'
import { chipsApi } from '@/lib/api/chips'

type BulkAction = 'pause' | 'resume' | 'promote'

interface ChipsBulkActionsProps {
  selectedIds: string[]
  onClearSelection: () => void
  onActionComplete: () => void
}

const actionConfig = {
  pause: {
    label: 'Pausar',
    icon: Pause,
    description: 'Pausar os chips selecionados? Eles deixarão de enviar mensagens.',
    confirmLabel: 'Pausar Chips',
    variant: 'outline' as const,
  },
  resume: {
    label: 'Retomar',
    icon: Play,
    description: 'Retomar os chips selecionados? Eles voltarão a enviar mensagens.',
    confirmLabel: 'Retomar Chips',
    variant: 'outline' as const,
  },
  promote: {
    label: 'Promover',
    icon: TrendingUp,
    description: 'Promover os chips selecionados para a próxima fase de warmup?',
    confirmLabel: 'Promover Chips',
    variant: 'default' as const,
  },
}

export function ChipsBulkActions({
  selectedIds,
  onClearSelection,
  onActionComplete,
}: ChipsBulkActionsProps) {
  const [isProcessing, setIsProcessing] = useState(false)
  const [confirmAction, setConfirmAction] = useState<BulkAction | null>(null)
  const [results, setResults] = useState<{
    success: number
    failed: number
  } | null>(null)

  const handleAction = async (action: BulkAction) => {
    setIsProcessing(true)
    setResults(null)

    let success = 0
    let failed = 0

    const actionFn = {
      pause: chipsApi.pauseChip,
      resume: chipsApi.resumeChip,
      promote: chipsApi.promoteChip,
    }[action]

    // Processa em paralelo com limite de concorrência
    const batchSize = 5
    for (let i = 0; i < selectedIds.length; i += batchSize) {
      const batch = selectedIds.slice(i, i + batchSize)
      const results = await Promise.allSettled(batch.map((id) => actionFn(id)))

      results.forEach((result) => {
        if (result.status === 'fulfilled' && result.value.success) {
          success++
        } else {
          failed++
        }
      })
    }

    setResults({ success, failed })
    setIsProcessing(false)
    setConfirmAction(null)

    // Atualiza a lista após 1.5s para mostrar o resultado
    setTimeout(() => {
      onActionComplete()
      onClearSelection()
      setResults(null)
    }, 1500)
  }

  if (selectedIds.length === 0) {
    return null
  }

  const config = confirmAction ? actionConfig[confirmAction] : null

  return (
    <>
      <div
        className={cn(
          'fixed bottom-6 left-1/2 z-50 -translate-x-1/2',
          'rounded-lg border border-border bg-card shadow-lg',
          'flex items-center gap-3 px-4 py-3',
          'transition-all duration-200'
        )}
      >
        {/* Selection count */}
        <div className="flex items-center gap-2 border-r border-border pr-3">
          <span className="text-sm font-medium text-foreground">
            {selectedIds.length} chip{selectedIds.length > 1 ? 's' : ''} selecionado
            {selectedIds.length > 1 ? 's' : ''}
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={onClearSelection}
            aria-label="Limpar seleção"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Results feedback */}
        {results && (
          <div className="flex items-center gap-2 border-r border-border pr-3">
            {results.success > 0 && (
              <span className="text-sm text-status-success-foreground">{results.success} sucesso</span>
            )}
            {results.failed > 0 && (
              <span className="text-sm text-status-error-foreground">
                {results.failed} falha{results.failed > 1 ? 's' : ''}
              </span>
            )}
          </div>
        )}

        {/* Action buttons */}
        {!results && (
          <div className="flex items-center gap-2">
            {(Object.keys(actionConfig) as BulkAction[]).map((action) => {
              const { label, icon: Icon, variant } = actionConfig[action]
              return (
                <Button
                  key={action}
                  variant={variant}
                  size="sm"
                  onClick={() => setConfirmAction(action)}
                  disabled={isProcessing}
                >
                  {isProcessing ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Icon className="mr-2 h-4 w-4" />
                  )}
                  {label}
                </Button>
              )
            })}
          </div>
        )}
      </div>

      {/* Confirmation dialog */}
      <AlertDialog open={!!confirmAction} onOpenChange={() => setConfirmAction(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmar Ação</AlertDialogTitle>
            <AlertDialogDescription>
              {config?.description}
              <br />
              <span className="mt-2 block font-medium">
                Esta ação será aplicada a {selectedIds.length} chip
                {selectedIds.length > 1 ? 's' : ''}.
              </span>
            </AlertDialogDescription>
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
