'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import {
  Phone,
  MoreVertical,
  User,
  Bot,
  UserCheck,
  CheckCheck,
  Hand,
  RotateCcw,
  Loader2,
} from 'lucide-react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { MessageInput } from './message-input'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'

interface Message {
  id: string
  tipo: 'entrada' | 'saida'
  conteudo: string
  created_at: string
}

interface ConversationDetail {
  id: string
  status: string
  controlled_by: string
  cliente: {
    id: string
    nome: string
    telefone: string
  }
  messages: Message[]
}

interface Props {
  conversationId: string
  onControlChange?: () => void
}

export function ChatPanel({ conversationId, onControlChange }: Props) {
  const router = useRouter()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [loading, setLoading] = useState(true)
  const [changingControl, setChangingControl] = useState(false)
  const [conversation, setConversation] = useState<ConversationDetail | null>(null)

  // Scroll to bottom instantly (no animation)
  const scrollToBottom = useCallback((instant = true) => {
    if (instant) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'instant' })
    } else {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [])

  const fetchConversation = useCallback(async () => {
    try {
      const response = await fetch(`/api/conversas/${conversationId}`)

      if (response.ok) {
        const result = await response.json()
        setConversation(result)
      }
    } catch (err) {
      console.error('Failed to fetch conversation:', err)
    } finally {
      setLoading(false)
    }
  }, [conversationId])

  const handleControlChange = async (newControl: 'ai' | 'human') => {
    setChangingControl(true)
    try {
      const response = await fetch(`/api/conversas/${conversationId}/control`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ controlled_by: newControl }),
      })

      if (response.ok) {
        await fetchConversation()
        onControlChange?.()
      }
    } catch (err) {
      console.error('Failed to change control:', err)
    } finally {
      setChangingControl(false)
    }
  }

  const handleSendMessage = async (message: string, attachment?: { type: string; file: File }) => {
    try {
      // For now, only text is supported
      // TODO: Implement media sending via Evolution API
      if (attachment) {
        console.log('Attachment:', attachment.type, attachment.file.name)
        // Future: upload to storage, send via Evolution API
      }

      const response = await fetch(`/api/conversas/${conversationId}/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      })

      if (response.ok) {
        await fetchConversation()
        setTimeout(() => scrollToBottom(false), 100)
      }
    } catch (err) {
      console.error('Failed to send message:', err)
    }
  }

  useEffect(() => {
    setLoading(true)
    fetchConversation()

    // Refresh every 10 seconds
    const interval = setInterval(fetchConversation, 10000)
    return () => clearInterval(interval)
  }, [fetchConversation])

  // Scroll to bottom instantly when conversation loads
  useEffect(() => {
    if (conversation?.messages.length) {
      // Use requestAnimationFrame to ensure DOM is rendered
      requestAnimationFrame(() => scrollToBottom(true))
    }
  }, [conversation?.messages.length, scrollToBottom])

  if (loading) {
    return (
      <div className="flex h-full flex-1 flex-col">
        <div className="flex items-center gap-3 border-b bg-muted/30 p-3">
          <Skeleton className="h-10 w-10 rounded-full" />
          <div className="space-y-1">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-24" />
          </div>
        </div>
        <div className="flex-1 space-y-4 p-4">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className={cn('h-12 w-2/3', i % 2 === 0 ? 'ml-auto' : '')} />
          ))}
        </div>
      </div>
    )
  }

  if (!conversation) {
    return (
      <div className="flex h-full flex-1 items-center justify-center text-muted-foreground">
        Conversa nao encontrada
      </div>
    )
  }

  const cliente = conversation.cliente
  const isHandoff = conversation.controlled_by === 'human'

  const initials = cliente.nome
    .split(' ')
    .slice(0, 2)
    .map((n) => n[0])
    .join('')
    .toUpperCase()

  // Group messages by date
  const groupedMessages: { date: string; messages: Message[] }[] = []
  let currentDate = ''

  conversation.messages.forEach((msg) => {
    const msgDate = format(new Date(msg.created_at), "d 'de' MMMM", { locale: ptBR })
    if (msgDate !== currentDate) {
      currentDate = msgDate
      groupedMessages.push({ date: msgDate, messages: [] })
    }
    const lastGroup = groupedMessages[groupedMessages.length - 1]
    if (lastGroup) {
      lastGroup.messages.push(msg)
    }
  })

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b bg-muted/30 px-4 py-2">
        <div className="flex items-center gap-3">
          <Avatar className="h-10 w-10">
            <AvatarFallback
              className={cn(
                'text-sm font-medium',
                isHandoff ? 'bg-yellow-100 text-yellow-700' : 'bg-emerald-100 text-emerald-700'
              )}
            >
              {initials}
            </AvatarFallback>
          </Avatar>

          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium">{cliente.nome}</span>
              {isHandoff && (
                <span className="flex items-center gap-1 rounded bg-yellow-100 px-1.5 py-0.5 text-xs font-medium text-yellow-700">
                  <UserCheck className="h-3 w-3" />
                  Handoff
                </span>
              )}
            </div>
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <Phone className="h-3 w-3" />
              {cliente.telefone}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Control Button */}
          {isHandoff ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleControlChange('ai')}
              disabled={changingControl}
              className="gap-2 border-emerald-200 text-emerald-700 hover:bg-emerald-50 hover:text-emerald-800"
            >
              {changingControl ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RotateCcw className="h-4 w-4" />
              )}
              <span className="hidden sm:inline">Devolver para Julia</span>
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleControlChange('human')}
              disabled={changingControl}
              className="gap-2 border-yellow-200 text-yellow-700 hover:bg-yellow-50 hover:text-yellow-800"
            >
              {changingControl ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Hand className="h-4 w-4" />
              )}
              <span className="hidden sm:inline">Assumir conversa</span>
            </Button>
          )}

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <MoreVertical className="h-5 w-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => router.push(`/medicos/${cliente.id}`)}>
                <User className="mr-2 h-4 w-4" />
                Ver perfil do medico
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              {isHandoff ? (
                <DropdownMenuItem
                  onClick={() => handleControlChange('ai')}
                  disabled={changingControl}
                >
                  <RotateCcw className="mr-2 h-4 w-4" />
                  Devolver para Julia
                </DropdownMenuItem>
              ) : (
                <DropdownMenuItem
                  onClick={() => handleControlChange('human')}
                  disabled={changingControl}
                >
                  <Hand className="mr-2 h-4 w-4" />
                  Assumir conversa
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Messages */}
      <div
        className="min-h-0 flex-1 overflow-y-auto p-4"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%239C92AC' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
        }}
      >
        {conversation.messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            Nenhuma mensagem ainda
          </div>
        ) : (
          <div className="space-y-4">
            {groupedMessages.map((group) => (
              <div key={group.date}>
                {/* Date separator */}
                <div className="mb-4 flex justify-center">
                  <span className="rounded-lg bg-muted px-3 py-1 text-xs text-muted-foreground shadow-sm">
                    {group.date}
                  </span>
                </div>

                {/* Messages */}
                <div className="space-y-1">
                  {group.messages.map((message) => {
                    const isOutgoing = message.tipo === 'saida'
                    const time = format(new Date(message.created_at), 'HH:mm')

                    return (
                      <div
                        key={message.id}
                        className={cn('flex', isOutgoing ? 'justify-end' : 'justify-start')}
                      >
                        <div
                          className={cn(
                            'relative max-w-[70%] rounded-lg px-3 py-2 shadow-sm',
                            isOutgoing
                              ? 'rounded-tr-none bg-emerald-100 text-emerald-900 dark:bg-emerald-900 dark:text-emerald-100'
                              : 'rounded-tl-none bg-white dark:bg-slate-800'
                          )}
                        >
                          {/* Sender indicator for outgoing */}
                          {isOutgoing && (
                            <div className="mb-1 flex items-center gap-1 text-xs font-medium text-emerald-700 dark:text-emerald-300">
                              <Bot className="h-3 w-3" />
                              Julia
                            </div>
                          )}

                          <p className="whitespace-pre-wrap break-words text-sm">
                            {message.conteudo}
                          </p>

                          <div
                            className={cn(
                              'mt-1 flex items-center gap-1',
                              isOutgoing ? 'justify-end' : 'justify-start'
                            )}
                          >
                            <span className="text-[10px] text-muted-foreground">{time}</span>
                            {isOutgoing && <CheckCheck className="h-3 w-3 text-blue-500" />}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
            {/* Scroll anchor */}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Footer - Message Input or Status */}
      {isHandoff ? (
        <div className="border-t bg-background p-3">
          <MessageInput
            onSend={handleSendMessage}
            placeholder="Digite sua mensagem... (Enter para enviar)"
          />
          <p className="mt-2 text-center text-xs text-muted-foreground">
            Voce esta no controle desta conversa.{' '}
            <button
              onClick={() => handleControlChange('ai')}
              disabled={changingControl}
              className="text-emerald-600 hover:underline"
            >
              Devolver para Julia
            </button>
          </p>
        </div>
      ) : (
        <div className="border-t bg-emerald-50 px-4 py-3 dark:bg-emerald-950/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm">
              <Bot className="h-5 w-5 text-emerald-600" />
              <div>
                <span className="font-medium text-emerald-800 dark:text-emerald-200">
                  Julia esta respondendo
                </span>
                <p className="text-xs text-emerald-600 dark:text-emerald-400">
                  Respostas automaticas ativas
                </p>
              </div>
            </div>
            <Button
              size="sm"
              onClick={() => handleControlChange('human')}
              disabled={changingControl}
              className="gap-2 bg-yellow-500 text-white hover:bg-yellow-600"
            >
              {changingControl ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Hand className="h-4 w-4" />
              )}
              Assumir
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
