'use client'

import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { Bot, UserCheck, CheckCheck, Smartphone } from 'lucide-react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'

export interface ChipInfo {
  id: string
  telefone: string
  instance_name: string
  status: string
  trust_level: string
}

export interface ConversationItem {
  id: string
  cliente_nome: string
  cliente_telefone: string
  status: string
  controlled_by: string
  last_message?: string
  last_message_at?: string
  unread_count: number
  chip?: ChipInfo | null
}

interface Props {
  conversations: ConversationItem[]
  selectedId: string | null
  onSelect: (id: string) => void
  hasMore?: boolean
  onLoadMore?: () => void
}

function formatPhone(phone: string): string {
  // Format as (11) 9xxxx-xxxx
  const cleaned = phone.replace(/\D/g, '').slice(-11)
  if (cleaned.length === 11) {
    return `(${cleaned.slice(0, 2)}) ${cleaned.slice(2, 7)}-${cleaned.slice(7)}`
  }
  return phone.slice(-11)
}

export function ChatSidebar({ conversations, selectedId, onSelect, hasMore, onLoadMore }: Props) {
  return (
    <div className="divide-y">
      {conversations.map((conversation) => {
        const isSelected = conversation.id === selectedId
        const isHandoff = conversation.controlled_by === 'human'

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
              isSelected && 'bg-muted'
            )}
          >
            {/* Avatar */}
            <Avatar className="h-12 w-12 flex-shrink-0">
              <AvatarFallback
                className={cn(
                  'text-sm font-medium',
                  isHandoff ? 'bg-yellow-100 text-yellow-700' : 'bg-emerald-100 text-emerald-700'
                )}
              >
                {initials}
              </AvatarFallback>
            </Avatar>

            {/* Content */}
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate font-medium">{conversation.cliente_nome}</span>
                <span className="flex-shrink-0 text-xs text-muted-foreground">{timeAgo}</span>
              </div>

              <div className="mt-0.5 flex items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-1">
                  {conversation.last_message && (
                    <>
                      <CheckCheck className="h-3.5 w-3.5 flex-shrink-0 text-blue-500" />
                      <span className="truncate text-sm text-muted-foreground">
                        {conversation.last_message}
                      </span>
                    </>
                  )}
                </div>

                {/* Badges */}
                <div className="flex flex-shrink-0 items-center gap-1">
                  {isHandoff ? (
                    <span className="flex items-center gap-0.5 rounded bg-yellow-100 px-1.5 py-0.5 text-[10px] font-medium text-yellow-700">
                      <UserCheck className="h-3 w-3" />
                    </span>
                  ) : (
                    <span className="flex items-center gap-0.5 rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700">
                      <Bot className="h-3 w-3" />
                    </span>
                  )}

                  {conversation.unread_count > 0 && (
                    <span className="flex h-5 min-w-[20px] items-center justify-center rounded-full bg-emerald-500 px-1.5 text-xs font-medium text-white">
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
