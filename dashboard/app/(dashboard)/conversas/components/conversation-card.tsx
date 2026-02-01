'use client'

import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { useRouter } from 'next/navigation'
import { MessageCircle, Bot, UserCheck } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'

export interface Conversation {
  id: string
  cliente_nome: string
  cliente_telefone: string
  status: string
  controlled_by: string
  last_message?: string
  last_message_at?: string
  unread_count: number
}

interface Props {
  conversation: Conversation
}

export function ConversationCard({ conversation }: Props) {
  const router = useRouter()

  const getStatusBadge = () => {
    if (conversation.controlled_by === 'human') {
      return (
        <Badge variant="secondary" className="bg-state-handoff text-state-handoff-foreground">
          <UserCheck className="mr-1 h-3 w-3" />
          Handoff
        </Badge>
      )
    }
    if (conversation.status === 'active') {
      return (
        <Badge className="bg-state-ai text-state-ai-foreground">
          <Bot className="mr-1 h-3 w-3" />
          Julia
        </Badge>
      )
    }
    return <Badge variant="outline">{conversation.status}</Badge>
  }

  const timeAgo = conversation.last_message_at
    ? formatDistanceToNow(new Date(conversation.last_message_at), {
        addSuffix: true,
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
    <Card
      className={cn(
        'cursor-pointer transition-colors hover:bg-muted/50',
        conversation.unread_count > 0 && 'border-l-4 border-l-state-unread-border'
      )}
      onClick={() => router.push(`/conversas/${conversation.id}`)}
    >
      <CardContent className="p-4">
        <div className="flex gap-3">
          <Avatar className="h-12 w-12">
            <AvatarFallback className="bg-primary/10 text-primary">{initials}</AvatarFallback>
          </Avatar>

          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="truncate font-medium">{conversation.cliente_nome}</p>
                <p className="text-sm text-muted-foreground">{conversation.cliente_telefone}</p>
              </div>
              <div className="flex flex-col items-end gap-1">
                {getStatusBadge()}
                {timeAgo && <span className="text-xs text-muted-foreground">{timeAgo}</span>}
              </div>
            </div>

            {conversation.last_message && (
              <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">
                {conversation.last_message}
              </p>
            )}

            {conversation.unread_count > 0 && (
              <div className="mt-2 flex items-center gap-1">
                <MessageCircle className="h-3 w-3 text-state-unread" />
                <span className="text-xs font-medium text-state-unread">
                  {conversation.unread_count} nao lida
                  {conversation.unread_count > 1 && 's'}
                </span>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
