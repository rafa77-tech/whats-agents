'use client'

import { XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ErrorStateProps {
  message?: string
  onRetry?: () => void
}

export function ErrorState({
  message = 'Nao foi possivel carregar os dados',
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="flex min-h-[200px] items-center justify-center">
      <div className="text-center">
        <XCircle className="mx-auto h-8 w-8 text-red-400" />
        <p className="mt-2 text-sm text-red-600">{message}</p>
        {onRetry && (
          <Button onClick={onRetry} variant="outline" size="sm" className="mt-4">
            Tentar novamente
          </Button>
        )}
      </div>
    </div>
  )
}
