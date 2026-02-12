/**
 * Chip Errors Dialog - Sprint 56
 *
 * Dialog para exibir detalhes dos erros de um chip.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { AlertTriangle, Clock, Phone, XCircle, Trash2, Loader2 } from 'lucide-react'
import { chipsApi, ChipError } from '@/lib/api/chips'
import { cn } from '@/lib/utils'

interface ChipErrorsDialogProps {
  chipId: string
  chipName: string
  errorCount: number
  open: boolean
  onOpenChange: (open: boolean) => void
  onErrorsCleared?: () => void
}

export function ChipErrorsDialog({
  chipId,
  chipName,
  errorCount,
  open,
  onOpenChange,
  onErrorsCleared,
}: ChipErrorsDialogProps) {
  const [errors, setErrors] = useState<ChipError[]>([])
  const [summary, setSummary] = useState<{ message: string; count: number }[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isClearing, setIsClearing] = useState(false)
  const [fetchError, setFetchError] = useState<string | null>(null)

  const fetchErrors = useCallback(() => {
    setIsLoading(true)
    setFetchError(null)

    chipsApi
      .getChipErrors(chipId, { limit: 50 })
      .then((data) => {
        setErrors(data.errors)
        setSummary(data.summary)
      })
      .catch((err) => {
        console.error('Error fetching chip errors:', err)
        setFetchError('Nao foi possivel carregar os erros')
      })
      .finally(() => {
        setIsLoading(false)
      })
  }, [chipId])

  useEffect(() => {
    if (open && chipId) {
      fetchErrors()
    }
  }, [open, chipId, fetchErrors])

  const handleClearErrors = async () => {
    setIsClearing(true)
    try {
      await chipsApi.clearChipErrors(chipId)
      setErrors([])
      setSummary([])
      onErrorsCleared?.()
      onOpenChange(false)
    } catch (err) {
      console.error('Error clearing chip errors:', err)
    } finally {
      setIsClearing(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[80vh] overflow-hidden sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-status-error-foreground" />
            Erros do Chip {chipName}
          </DialogTitle>
          <DialogDescription>
            {errorCount} erro{errorCount !== 1 ? 's' : ''} nas ultimas 24 horas
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-[50vh] overflow-y-auto">
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : fetchError ? (
            <div className="py-8 text-center text-muted-foreground">
              <XCircle className="mx-auto mb-2 h-8 w-8" />
              {fetchError}
            </div>
          ) : errors.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              Nenhum erro encontrado nas ultimas 24 horas
            </div>
          ) : (
            <div className="space-y-4">
              {/* Resumo */}
              {summary.length > 0 && (
                <div className="rounded-lg border border-border bg-muted/50 p-3">
                  <h4 className="mb-2 text-sm font-medium text-foreground">Resumo</h4>
                  <div className="space-y-1">
                    {summary.map((s, i) => (
                      <div key={i} className="flex items-center justify-between text-sm">
                        <span className="truncate text-muted-foreground" title={s.message}>
                          {s.message}
                        </span>
                        <Badge variant="secondary" className="ml-2 shrink-0">
                          {s.count}x
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Lista de erros */}
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-foreground">Detalhes</h4>
                {errors.map((error) => (
                  <ErrorItem key={error.id} error={error} />
                ))}
              </div>
            </div>
          )}
        </div>

        {errors.length > 0 && (
          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              onClick={handleClearErrors}
              disabled={isClearing}
              className="text-status-error-foreground hover:bg-status-error/10"
            >
              {isClearing ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Limpar erros
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}

function ErrorItem({ error }: { error: ChipError }) {
  const time = new Date(error.createdAt).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <div className="rounded-lg border border-border p-3">
      <div className="mb-1 flex items-center justify-between">
        <Badge
          variant="outline"
          className={cn(
            'text-xs',
            error.errorCode
              ? 'border-status-error-border text-status-error-foreground'
              : 'border-status-warning-border text-status-warning-foreground'
          )}
        >
          {error.tipo.replace(/_/g, ' ')}
        </Badge>
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          {time}
        </span>
      </div>

      <p className="text-sm text-foreground">{error.errorMessage}</p>

      {error.destinatario && (
        <div className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
          <Phone className="h-3 w-3" />
          {error.destinatario}
        </div>
      )}
    </div>
  )
}
