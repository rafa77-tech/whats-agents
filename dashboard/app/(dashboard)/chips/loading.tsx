import { Loader2 } from 'lucide-react'

/**
 * Loading state para o módulo de Chips (Suspense fallback).
 *
 * Sprint 44 T05.5: Adicionar loading.tsx para Suspense.
 */
export default function ChipsLoading() {
  return (
    <div className="flex min-h-[400px] items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-revoluna-400" />
        <p className="text-sm text-muted-foreground">Carregando chips...</p>
      </div>
    </div>
  )
}
