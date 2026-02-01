'use client'

import { useCallback, useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, Phone, User, MoreVertical } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { MessageList } from '../components/message-list'
import { ConversationActions } from '../components/conversation-actions'
import type { Message } from '../components/message-bubble'

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

function ConversationDetailSkeleton() {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b p-4">
        <Skeleton className="h-10 w-48" />
      </div>
      <div className="flex-1 space-y-4 p-4">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    </div>
  )
}

export default function ConversationDetailPage() {
  const params = useParams()
  const router = useRouter()

  const conversationId = params.id as string

  const [loading, setLoading] = useState(true)
  const [conversation, setConversation] = useState<ConversationDetail | null>(null)

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

  useEffect(() => {
    fetchConversation()
    // Refresh every 10 seconds
    const interval = setInterval(fetchConversation, 10000)
    return () => clearInterval(interval)
  }, [fetchConversation])

  if (loading) {
    return <ConversationDetailSkeleton />
  }

  if (!conversation) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-muted-foreground">Conversa nao encontrada</p>
      </div>
    )
  }

  const cliente = conversation.cliente || { id: '', nome: 'Desconhecido', telefone: '' }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="sticky top-0 z-10 border-b bg-background p-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => router.back()} className="md:hidden">
            <ArrowLeft className="h-5 w-5" />
          </Button>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h1 className="truncate font-semibold">{cliente.nome}</h1>
              {conversation.controlled_by === 'human' && (
                <span className="rounded bg-yellow-100 px-2 py-0.5 text-xs text-yellow-800">
                  Handoff
                </span>
              )}
            </div>
            <p className="flex items-center gap-1 text-sm text-muted-foreground">
              <Phone className="h-3 w-3" />
              {cliente.telefone}
            </p>
          </div>

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
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto">
        <MessageList messages={conversation.messages || []} />
      </div>

      {/* Actions */}
      <ConversationActions
        conversationId={conversationId}
        controlledBy={conversation.controlled_by}
        onRefresh={fetchConversation}
      />
    </div>
  )
}
