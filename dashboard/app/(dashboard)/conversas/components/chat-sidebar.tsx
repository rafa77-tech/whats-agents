'use client'

import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { Bot, UserCheck } from 'lucide-react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'
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
    if (waitMs > 60 * 60 * 1000) return 'border-l-4 border-l-status-warning-solid'
  }
  return 'border-l-4 border-l-transparent'
}

export function ChatSidebar({ conversations, selectedId, onSelect, hasMore, onLoadMore }: Props) {
  return (
    <div className="divide-y">
      {conversations.map((conversation) => {
        const isSelected = conversation.id === selectedId
        const isHandoff = conversation.controlled_by === 'human'
        const urgencyBorder = getUrgencyBorder(conversation)

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
              'flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-muted/50',
              urgencyBorder,
              isSelected && 'bg-muted'
            )}
          >
            {/* Avatar */}
            <Avatar className="h-10 w-10 flex-shrink-0">
              <AvatarFallback
                className={cn(
                  'text-xs font-medium',
                  isHandoff
                    ? 'bg-state-handoff text-state-handoff-foreground'
                    : 'bg-state-ai text-state-ai-foreground'
                )}
              >
                {initials}
              </AvatarFallback>
            </Avatar>

            {/* Content — 2 lines only */}
            <div className="min-w-0 flex-1">
              {/* Line 1: Name + specialty + time */}
              <div className="flex items-center justify-between">
                <div className="flex min-w-0 items-center gap-1.5">
                  <span className="truncate text-sm font-medium">
                    {conversation.cliente_nome}
                  </span>
                  {conversation.especialidade && (
                    <span className="hidden truncate text-xs text-muted-foreground sm:inline">
                      · {conversation.especialidade}
                    </span>
                  )}
                </div>
                <span className="flex-shrink-0 text-xs text-muted-foreground">{timeAgo}</span>
              </div>

              {/* Line 2: Last message + badges */}
              <div className="mt-0.5 flex items-center justify-between gap-2">
                <span className="min-w-0 truncate text-xs text-muted-foreground">
                  {conversation.last_message || ''}
                </span>
                <div className="flex flex-shrink-0 items-center gap-1">
                  {isHandoff ? (
                    <UserCheck className="h-3.5 w-3.5 text-state-handoff-foreground" />
                  ) : (
                    <Bot className="h-3.5 w-3.5 text-state-ai-muted" />
                  )}
                  {conversation.unread_count > 0 && (
                    <span className="flex h-5 min-w-[20px] items-center justify-center rounded-full bg-state-ai-button px-1.5 text-xs font-medium text-white">
                      {conversation.unread_count}
                    </span>
                  )}
                </div>
              </div>
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
