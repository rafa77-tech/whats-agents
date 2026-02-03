'use client'

import { useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { AlertTriangle } from 'lucide-react'

/**
 * Error Boundary para o módulo de Chips.
 *
 * Sprint 44 T05.1: Error Boundary específico para chips.
 */
export default function ChipsError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error('Chips module error:', error)
  }, [error])

  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center gap-4">
      <AlertTriangle className="h-12 w-12 text-destructive" />
      <h2 className="text-xl font-semibold">Erro no módulo de Chips</h2>
      <p className="max-w-md text-center text-muted-foreground">
        Ocorreu um erro ao carregar os dados de chips. Tente novamente ou volte para o dashboard.
      </p>
      <div className="flex gap-2">
        <Button onClick={() => reset()}>Tentar novamente</Button>
        <Button variant="outline" onClick={() => (window.location.href = '/chips')}>
          Voltar para Chips
        </Button>
      </div>
      {process.env.NODE_ENV === 'development' && (
        <pre className="mt-4 max-w-lg overflow-auto rounded bg-muted p-4 text-xs">
          {error.message}
        </pre>
      )}
    </div>
  )
}
