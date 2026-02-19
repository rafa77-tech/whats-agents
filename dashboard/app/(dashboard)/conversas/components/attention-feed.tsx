'use client'

import { AlertTriangle, Clock, Frown, Hand, Eye } from 'lucide-react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { ConversationListItem } from '@/types/conversas'

interface Props {
  conversations: ConversationListItem[]
  selectedId: string | null
  onSelect: (id: string) => void
  onAssume?: (id: string) => void
}

function getAttentionIcon(conv: ConversationListItem) {
  if (conv.controlled_by === 'human' || conv.has_handoff) {
    return <AlertTriangle className="h-3.5 w-3.5 text-destructive" />
  }
  if (conv.sentimento_score != null && conv.sentimento_score <= -2) {
    return <Frown className="h-3.5 w-3.5 text-destructive" />
  }
  return <Clock className="h-3.5 w-3.5 text-status-warning-solid" />
}

function getUrgencyLevel(conv: ConversationListItem): 'critical' | 'warning' {
  if (conv.controlled_by === 'human' || conv.has_handoff) return 'critical'
  if (conv.sentimento_score != null && conv.sentimento_score <= -2) return 'critical'
  return 'warning'
}

export function AttentionFeed({ conversations, selectedId, onSelect, onAssume }: Props) {
  if (conversations.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-4 text-center">
        <div className="rounded-full bg-success-light p-3">
          <AlertTriangle className="h-6 w-6 text-success-dark" />
        </div>
        <p className="text-sm font-medium text-muted-foreground">Tudo sob controle</p>
        <p className="text-xs text-muted-foreground/70">
          Nenhuma conversa precisa de atencao no momento.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-2 p-2">
      {conversations.map((conv) => {
        const urgency = getUrgencyLevel(conv)
        const isSelected = conv.id === selectedId
        const initials = conv.cliente_nome
          .split(' ')
          .slice(0, 2)
          .map((n) => n[0])
          .join('')
          .toUpperCase()

        return (
          <div
            key={conv.id}
            role="button"
            tabIndex={0}
            onClick={() => onSelect(conv.id)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') onSelect(conv.id)
            }}
            className={cn(
              'w-full cursor-pointer rounded-lg border p-3 text-left transition-colors',
              urgency === 'critical'
                ? 'border-destructive/30 bg-destructive/5 hover:bg-destructive/10'
                : 'border-status-warning/30 bg-status-warning/5 hover:bg-status-warning/10',
              isSelected && 'ring-2 ring-primary/50'
            )}
          >
            {/* Header: avatar + name + icon */}
            <div className="flex items-center gap-2.5">
              <Avatar className="h-8 w-8 flex-shrink-0">
                <AvatarFallback
                  className={cn(
                    'text-xs font-medium',
                    conv.controlled_by === 'human'
                      ? 'bg-state-handoff text-state-handoff-foreground'
                      : 'bg-state-ai text-state-ai-foreground'
                  )}
                >
                  {initials}
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  {getAttentionIcon(conv)}
                  <span className="truncate text-sm font-medium">{conv.cliente_nome}</span>
                  {conv.especialidade && (
                    <span className="hidden truncate text-xs text-muted-foreground sm:inline">
                      · {conv.especialidade}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Reason — the most important information */}
            {conv.attention_reason && (
              <p className="mt-1.5 text-xs font-medium text-muted-foreground">
                {conv.attention_reason}
              </p>
            )}

            {/* Context: last message */}
            {conv.last_message && (
              <p className="mt-1 line-clamp-2 text-xs italic text-muted-foreground/80">
                &ldquo;{conv.last_message}&rdquo;
              </p>
            )}

            {/* Actions */}
            <div className="mt-2 flex gap-2" onClick={(e) => e.stopPropagation()}>
              {conv.controlled_by === 'ai' && onAssume && (
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 gap-1 text-xs"
                  onClick={(e) => {
                    e.stopPropagation()
                    onAssume(conv.id)
                  }}
                >
                  <Hand className="h-3 w-3" />
                  Assumir
                </Button>
              )}
              <Button
                size="sm"
                variant="ghost"
                className="h-7 gap-1 text-xs"
                onClick={(e) => {
                  e.stopPropagation()
                  onSelect(conv.id)
                }}
              >
                <Eye className="h-3 w-3" />
                Ver conversa
              </Button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
