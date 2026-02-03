/**
 * Chips Tab Header - Sprint 45
 *
 * Header unificado para a pagina de chips com tabs.
 * Inclui titulo, botao de refresh, e botao de nova instancia.
 */

'use client'

import { useState } from 'react'
import Link from 'next/link'
import type { Route } from 'next'
import { RefreshCw, Plus, AlertTriangle, Smartphone } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { CreateInstanceDialog } from './create-instance-dialog'

interface ChipsTabHeaderProps {
  alertCount: number
  onRefresh: () => void
}

export function ChipsTabHeader({ alertCount, onRefresh }: ChipsTabHeaderProps) {
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const handleRefresh = async () => {
    setIsRefreshing(true)
    onRefresh()
    // Add a small delay to show the spinning animation
    setTimeout(() => setIsRefreshing(false), 500)
  }

  return (
    <>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-jullia-gradient flex h-10 w-10 items-center justify-center rounded-xl shadow-sm">
            <Smartphone className="h-5 w-5 text-white" />
          </div>
          <div>
            <nav className="mb-0.5 text-sm text-muted-foreground">
              <Link href={'/dashboard' as Route} className="hover:text-foreground">
                Dashboard
              </Link>
              <span className="mx-2">/</span>
              <span className="text-foreground">Chips</span>
            </nav>
            <h1 className="text-xl font-bold text-foreground sm:text-2xl">Pool de Chips</h1>
          </div>
          {alertCount > 0 && (
            <Badge variant="destructive" className="ml-2 hidden sm:flex">
              <AlertTriangle className="mr-1 h-3 w-3" />
              {alertCount} alertas
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isRefreshing}>
            <RefreshCw className={`mr-2 h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Atualizar</span>
          </Button>

          <Button size="sm" onClick={() => setShowCreateDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            <span className="hidden sm:inline">Nova Instancia</span>
            <span className="sm:hidden">Novo</span>
          </Button>
        </div>
      </div>

      <CreateInstanceDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onSuccess={onRefresh}
      />
    </>
  )
}
