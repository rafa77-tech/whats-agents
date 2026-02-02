'use client'

import { useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { AlertTriangle } from 'lucide-react'

/**
 * Error Boundary para o Dashboard.
 *
 * Sprint 44 T05.1: Adicionar Error Boundaries para capturar erros de runtime.
 */
export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log para serviço de monitoramento
    console.error('Dashboard error:', error)
  }, [error])

  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center gap-4">
      <AlertTriangle className="h-12 w-12 text-destructive" />
      <h2 className="text-xl font-semibold">Algo deu errado</h2>
      <p className="max-w-md text-center text-muted-foreground">
        Ocorreu um erro ao carregar esta página. Tente novamente ou entre em contato com o suporte.
      </p>
      <div className="flex gap-2">
        <Button onClick={() => reset()}>Tentar novamente</Button>
        <Button variant="outline" onClick={() => (window.location.href = '/')}>
          Voltar ao início
        </Button>
      </div>
      {process.env.NODE_ENV === 'development' && (
        <pre className="mt-4 max-w-lg overflow-auto rounded bg-muted p-4 text-xs">{error.message}</pre>
      )}
    </div>
  )
}
