'use client'

import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { Bot, UserCheck, CheckCheck, Smartphone } from 'lucide-react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { cn, formatPhone } from '@/lib/utils'
import { getSentimentColor } from '@/lib/conversas/constants'
import type { ConversationListItem } from '@/types/conversas'

interface Props {
  conversations: ConversationListItem[]
  selectedId: string | null
  onSelect: (id: string) => void
  hasMore?: boolean
  onLoadMore?: () => void
}

function getUrgencyBorder(conv: ConversationListItem): string {
  if (conv.controlled_by === 'human' || conv.has_handoff) return 'border-l-4 border-l-destructive'
  if (conv.last_message_direction === 'entrada' && conv.last_message_at) {
    const waitMs = Date.now() - new Date(conv.last_message_at).getTime()
    if (waitMs > 60 * 60 * 1000) return 'border-l-4 border-l-amber-400'
  }
  return 'border-l-4 border-l-transparent'
}

function getWaitTime(conv: ConversationListItem): string | null {
  if (conv.last_message_direction !== 'entrada' || !conv.last_message_at) return null
  const waitMs = Date.now() - new Date(conv.last_message_at).getTime()
  if (waitMs < 10 * 60 * 1000) return null // < 10 min, no display
  const minutes = Math.floor(waitMs / 60000)
  if (minutes < 60) return `${minutes}min`
  const hours = Math.floor(minutes / 60)
  return `${hours}h`
}

export function ChatSidebar({ conversations, selectedId, onSelect, hasMore, onLoadMore }: Props) {
  return (
    <div className="divide-y">
      {conversations.map((conversation) => {
        const isSelected = conversation.id === selectedId
        const isHandoff = conversation.controlled_by === 'human'
        const urgencyBorder = getUrgencyBorder(conversation)
        const waitTime = getWaitTime(conversation)

        const timeAgo = conversation.last_message_at
          ? formatDistanceToNow(new Date(conversation.last_message_at), {
              addSuffix: false,
              locale: ptBR,
            })
          : null

        const initials = conversation.cliente_nome
          .split(' ')
          .slice(0, 2)
          .map((n) => n[0])
          .join('')
          .toUpperCase()

        return (
          <button
            key={conversation.id}
            onClick={() => onSelect(conversation.id)}
            className={cn(
              'flex w-full items-center gap-3 px-3 py-3 text-left transition-colors hover:bg-muted/50',
              urgencyBorder,
              isSelected && 'bg-muted'
            )}
          >
            {/* Avatar with sentiment dot */}
            <div className="relative flex-shrink-0">
              <Avatar className="h-12 w-12">
                <AvatarFallback
                  className={cn(
                    'text-sm font-medium',
                    isHandoff
                      ? 'bg-state-handoff text-state-handoff-foreground'
                      : 'bg-state-ai text-state-ai-foreground'
                  )}
                >
                  {initials}
                </AvatarFallback>
              </Avatar>
              {/* Sentiment indicator dot */}
              {conversation.sentimento_score != null && (
                <span
                  className={cn(
                    'absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-background',
                    getSentimentColor(conversation.sentimento_score)
                  )}
                />
              )}
            </div>

            {/* Content */}
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate font-medium">{conversation.cliente_nome}</span>
                <div className="flex flex-shrink-0 items-center gap-1">
                  {waitTime && (
                    <span className="text-[10px] font-medium text-amber-600">{waitTime}</span>
                  )}
                  <span className="text-xs text-muted-foreground">{timeAgo}</span>
                </div>
              </div>

              {/* Especialidade + Stage */}
              {(conversation.especialidade || conversation.stage_jornada) && (
                <div className="mt-0.5 flex items-center gap-1.5">
                  {conversation.especialidade && (
                    <span className="truncate text-[10px] text-muted-foreground">
                      {conversation.especialidade}
                    </span>
                  )}
                  {conversation.stage_jornada && (
                    <span className="rounded bg-muted px-1 py-0.5 text-[9px] font-medium">
                      {conversation.stage_jornada}
                    </span>
                  )}
                </div>
              )}

              <div className="mt-0.5 flex items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-1">
                  {conversation.last_message && (
                    <>
                      <CheckCheck className="h-3.5 w-3.5 flex-shrink-0 text-state-unread" />
                      <span className="truncate text-sm text-muted-foreground">
                        {conversation.last_message}
                      </span>
                    </>
                  )}
                </div>

                {/* Badges */}
                <div className="flex flex-shrink-0 items-center gap-1">
                  {isHandoff ? (
                    <span className="flex items-center gap-0.5 rounded bg-state-handoff px-1.5 py-0.5 text-[10px] font-medium text-state-handoff-foreground">
                      <UserCheck className="h-3 w-3" />
                    </span>
                  ) : (
                    <span className="flex items-center gap-0.5 rounded bg-state-ai px-1.5 py-0.5 text-[10px] font-medium text-state-ai-foreground">
                      <Bot className="h-3 w-3" />
                    </span>
                  )}

                  {conversation.unread_count > 0 && (
                    <span className="flex h-5 min-w-[20px] items-center justify-center rounded-full bg-state-ai-button px-1.5 text-xs font-medium text-white">
                      {conversation.unread_count}
                    </span>
                  )}
                </div>
              </div>

              {/* Chip info */}
              {conversation.chip && (
                <div className="mt-1 flex items-center gap-1 text-[10px] text-muted-foreground">
                  <Smartphone className="h-3 w-3" />
                  <span className="truncate">
                    {conversation.chip.instance_name} • {formatPhone(conversation.chip.telefone)}
                  </span>
                </div>
              )}
            </div>
          </button>
        )
      })}

      {/* Load More */}
      {hasMore && onLoadMore && (
        <button
          onClick={onLoadMore}
          className="w-full py-3 text-center text-sm text-primary hover:bg-muted/50"
        >
          Carregar mais conversas
        </button>
      )}
    </div>
  )
}
