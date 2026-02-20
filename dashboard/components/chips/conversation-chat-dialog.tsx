/**
 * Conversation Chat Dialog - Sprint 64
 *
 * Modal com visualização de chat de uma conversa.
 * Usado na timeline de interações do chip.
 */

'use client'

import { useCallback, useEffect, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { MessageBubble, type Message } from '@/app/(dashboard)/conversas/components/message-bubble'
import { Phone, ExternalLink } from 'lucide-react'
import Link from 'next/link'

interface ConversationData {
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

interface ConversationChatDialogProps {
  conversationId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ConversationChatDialog({
  conversationId,
  open,
  onOpenChange,
}: ConversationChatDialogProps) {
  const [data, setData] = useState<ConversationData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchConversation = useCallback(async (id: string) => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`/api/conversas/${id}`)
      if (!response.ok) {
        setError('Conversa não encontrada')
        return
      }
      const result = await response.json()
      setData(result)
    } catch {
      setError('Erro ao carregar conversa')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (open && conversationId) {
      fetchConversation(conversationId)
    }
    if (!open) {
      setData(null)
      setError(null)
    }
  }, [open, conversationId, fetchConversation])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex h-[80vh] max-w-2xl flex-col gap-0 p-0">
        {/* Header */}
        <DialogHeader className="flex-shrink-0 border-b px-4 py-3">
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <DialogTitle className="truncate text-base">
                {loading ? (
                  <Skeleton className="h-5 w-32" />
                ) : data ? (
                  data.cliente.nome
                ) : (
                  'Conversa'
                )}
              </DialogTitle>
              {data && (
                <p className="flex items-center gap-1 text-sm text-muted-foreground">
                  <Phone className="h-3 w-3" />
                  {data.cliente.telefone}
                </p>
              )}
            </div>
            {data && (
              <Button variant="ghost" size="sm" asChild className="flex-shrink-0">
                <Link href={`/conversas/${data.id}`}>
                  <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                  Abrir
                </Link>
              </Button>
            )}
          </div>
        </DialogHeader>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {loading && <ChatSkeleton />}

          {error && (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              {error}
            </div>
          )}

          {data &&
            !loading &&
            (data.messages.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                Nenhuma mensagem nesta conversa
              </div>
            ) : (
              <ChatMessages messages={data.messages} />
            ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}

function ChatMessages({ messages }: { messages: Message[] }) {
  // Group messages by date
  const groups: { date: string; messages: Message[] }[] = []
  let currentDate = ''

  for (const msg of messages) {
    const msgDate = new Date(msg.created_at).toLocaleDateString('pt-BR')
    if (msgDate !== currentDate) {
      currentDate = msgDate
      groups.push({ date: msgDate, messages: [] })
    }
    groups[groups.length - 1]?.messages.push(msg)
  }

  return (
    <div className="space-y-4 p-4">
      {groups.map((group) => (
        <div key={group.date}>
          <div className="mb-4 flex justify-center">
            <span className="rounded-full bg-muted px-3 py-1 text-xs">{group.date}</span>
          </div>
          <div className="space-y-2">
            {group.messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function ChatSkeleton() {
  return (
    <div className="space-y-3 p-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className={i % 2 === 0 ? 'mr-auto max-w-[70%]' : 'ml-auto max-w-[70%]'}>
          <Skeleton className="h-14 w-full rounded-lg" />
        </div>
      ))}
    </div>
  )
}
