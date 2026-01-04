'use client'

import { format } from 'date-fns'
import { Check, CheckCheck, Bot, User } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface Message {
  id: string
  tipo: 'entrada' | 'saida'
  conteudo: string
  created_at: string
  metadata?: {
    model?: string
    delivered?: boolean
    read?: boolean
  }
}

interface Props {
  message: Message
}

export function MessageBubble({ message }: Props) {
  const isOutgoing = message.tipo === 'saida'
  const time = format(new Date(message.created_at), 'HH:mm')

  return (
    <div
      className={cn(
        'flex max-w-[85%] gap-2 md:max-w-[70%]',
        isOutgoing ? 'ml-auto flex-row-reverse' : 'mr-auto'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full',
          isOutgoing ? 'bg-primary/10' : 'bg-muted'
        )}
      >
        {isOutgoing ? (
          <Bot className="h-4 w-4 text-primary" />
        ) : (
          <User className="h-4 w-4 text-muted-foreground" />
        )}
      </div>

      {/* Bubble */}
      <div
        className={cn(
          'rounded-lg px-4 py-2',
          isOutgoing
            ? 'rounded-tr-none bg-primary text-primary-foreground'
            : 'rounded-tl-none bg-muted'
        )}
      >
        <p className="whitespace-pre-wrap break-words">{message.conteudo}</p>
        <div
          className={cn(
            'mt-1 flex items-center gap-1',
            isOutgoing ? 'justify-end' : 'justify-start'
          )}
        >
          <span
            className={cn(
              'text-xs',
              isOutgoing ? 'text-primary-foreground/70' : 'text-muted-foreground'
            )}
          >
            {time}
          </span>
          {isOutgoing &&
            (message.metadata?.read ? (
              <CheckCheck className="h-3 w-3 text-blue-400" />
            ) : message.metadata?.delivered ? (
              <CheckCheck className="h-3 w-3" />
            ) : (
              <Check className="h-3 w-3" />
            ))}
        </div>
      </div>
    </div>
  )
}
