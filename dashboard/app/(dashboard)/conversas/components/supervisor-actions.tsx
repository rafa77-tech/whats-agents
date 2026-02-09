'use client'

import { useState } from 'react'
import { Pause, Play, Hand, RotateCcw, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

interface Props {
  conversationId: string
  controlledBy: 'ai' | 'human'
  isPaused: boolean
  onControlChange: (newControl: 'ai' | 'human') => void
  onPauseChange: (paused: boolean) => void
}

export function SupervisorActions({
  conversationId,
  controlledBy,
  isPaused,
  onControlChange,
  onPauseChange,
}: Props) {
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const handlePauseToggle = async (): Promise<void> => {
    setActionLoading('pause')
    try {
      const response = await fetch(`/api/conversas/${conversationId}/pause`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: isPaused ? 'resume' : 'pause',
          motivo: 'Pausado pelo supervisor',
        }),
      })

      if (response.ok) {
        onPauseChange(!isPaused)
      }
    } catch (err) {
      console.error('Failed to toggle pause:', err)
    } finally {
      setActionLoading(null)
    }
  }

  const isHandoff = controlledBy === 'human'

  return (
    <TooltipProvider>
      <div className="flex items-center gap-1">
        {/* Pause/Resume Julia */}
        {!isHandoff && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className={cn('h-8 w-8', isPaused && 'text-status-warning-foreground')}
                onClick={handlePauseToggle}
                disabled={actionLoading === 'pause'}
              >
                {actionLoading === 'pause' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : isPaused ? (
                  <Play className="h-4 w-4" />
                ) : (
                  <Pause className="h-4 w-4" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent>{isPaused ? 'Retomar Julia' : 'Pausar Julia'}</TooltipContent>
          </Tooltip>
        )}

        {/* Handoff toggle */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className={cn(
                'h-8 w-8',
                isHandoff ? 'text-state-ai-foreground' : 'text-state-handoff-foreground'
              )}
              onClick={() => onControlChange(isHandoff ? 'ai' : 'human')}
            >
              {isHandoff ? <RotateCcw className="h-4 w-4" /> : <Hand className="h-4 w-4" />}
            </Button>
          </TooltipTrigger>
          <TooltipContent>{isHandoff ? 'Devolver para Julia' : 'Assumir conversa'}</TooltipContent>
        </Tooltip>
      </div>
    </TooltipProvider>
  )
}
