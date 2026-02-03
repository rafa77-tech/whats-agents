'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
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
import { useToast } from '@/hooks/use-toast'
import { RotateCcw, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { getCircuitStateColors, CIRCUIT_STATE_LEGEND } from '@/lib/health'
import type { Circuit, CircuitState } from '@/lib/health'

interface CircuitBreakersPanelProps {
  circuits: Circuit[]
  onReset: () => void
}

export function CircuitBreakersPanel({ circuits, onReset }: CircuitBreakersPanelProps) {
  const { toast } = useToast()
  const [resetDialog, setResetDialog] = useState<string | null>(null)
  const [resetting, setResetting] = useState(false)

  const handleReset = async (circuitName: string) => {
    setResetting(true)
    try {
      const res = await fetch(`/api/guardrails/circuits/${circuitName}/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          motivo: 'Reset manual via Health Center',
          usuario: 'dashboard',
        }),
      })

      if (!res.ok) throw new Error('Falha ao resetar circuit breaker')

      toast({
        title: 'Circuit Breaker Resetado',
        description: `${circuitName} foi resetado com sucesso.`,
      })

      onReset()
    } catch {
      toast({
        variant: 'destructive',
        title: 'Erro',
        description: 'Nao foi possivel resetar o circuit breaker.',
      })
    } finally {
      setResetting(false)
      setResetDialog(null)
    }
  }

  const getStateBadge = (state: CircuitState) => {
    const colors = getCircuitStateColors(state)
    return <Badge className={colors.badge}>{state}</Badge>
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Circuit Breakers</CardTitle>
          <CardDescription>Status e controle dos circuit breakers</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {circuits.map((circuit) => {
              const colors = getCircuitStateColors(circuit.state)
              return (
                <div
                  key={circuit.name}
                  className={cn(
                    'flex items-center justify-between rounded-lg border p-3',
                    colors.border,
                    colors.bg
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div className={cn('h-3 w-3 rounded-full', colors.indicator)} />
                    <div>
                      <p className="font-medium capitalize">{circuit.name}</p>
                      <p className="text-xs text-muted-foreground">
                        Falhas: {circuit.failures}/{circuit.threshold}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {getStateBadge(circuit.state)}
                    {circuit.state !== 'CLOSED' && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setResetDialog(circuit.name)}
                      >
                        <RotateCcw className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
          <p className="mt-4 text-xs text-muted-foreground/70">{CIRCUIT_STATE_LEGEND}</p>
        </CardContent>
      </Card>

      <AlertDialog open={resetDialog !== null} onOpenChange={() => setResetDialog(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Resetar Circuit Breaker?</AlertDialogTitle>
            <AlertDialogDescription>
              Isso vai zerar o contador de falhas e mudar o estado para CLOSED. O circuit breaker{' '}
              <strong>{resetDialog}</strong> voltara a aceitar requisicoes.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => resetDialog && handleReset(resetDialog)}
              disabled={resetting}
            >
              {resetting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Resetar'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
