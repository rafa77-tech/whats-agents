'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import {
  Send,
  Loader2,
  MessageCircle,
  Lightbulb,
  Check,
  X,
  Bot,
  UserCog,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { ChannelMessage, InstructionPreview } from '@/types/conversas'

interface Props {
  conversationId: string
}

type ChannelMode = 'question' | 'instruction'

const QUICK_BUTTONS = [
  { label: 'Explica a ultima msg', prompt: 'Explica a ultima mensagem do medico e o que voce acha que ele quis dizer' },
  { label: 'Qual sua leitura?', prompt: 'Qual sua leitura geral sobre essa conversa? O medico parece interessado?' },
  { label: 'O que faria agora?', prompt: 'O que voce faria agora nessa conversa? Qual seria seu proximo passo?' },
]

export function SupervisorChannel({ conversationId }: Props) {
  const [messages, setMessages] = useState<ChannelMessage[]>([])
  const [input, setInput] = useState('')
  const [mode, setMode] = useState<ChannelMode>('question')
  const [sending, setSending] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [pendingPreview, setPendingPreview] = useState<InstructionPreview | null>(null)
  const [processingAction, setProcessingAction] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  // Load channel history
  useEffect(() => {
    const loadHistory = async (): Promise<void> => {
      try {
        const response = await fetch(`/api/conversas/${conversationId}/channel`)
        if (response.ok) {
          const data = await response.json()
          setMessages((data.messages || []) as ChannelMessage[])
        }
      } catch (err) {
        console.error('Failed to load channel history:', err)
      } finally {
        setLoaded(true)
      }
    }

    void loadHistory()
  }, [conversationId])

  // Scroll on new messages
  useEffect(() => {
    if (messages.length > 0) {
      scrollToBottom()
    }
  }, [messages.length, scrollToBottom])

  const handleSend = async (): Promise<void> => {
    const content = input.trim()
    if (!content || sending) return

    setSending(true)
    setInput('')

    try {
      const response = await fetch(`/api/conversas/${conversationId}/channel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, type: mode }),
      })

      if (!response.ok) {
        setSending(false)
        return
      }

      const result = await response.json()

      if (mode === 'instruction') {
        // Instruction mode: show preview
        const preview = result as {
          id: string
          instruction: string
          preview_message: string
          status: string
        }
        setPendingPreview({
          id: preview.id,
          instruction: preview.instruction,
          preview_message: preview.preview_message,
          status: 'pending',
        })

        // Add supervisor message to chat
        setMessages((prev) => [
          ...prev,
          {
            id: `temp-${Date.now()}`,
            conversation_id: conversationId,
            role: 'supervisor',
            content: `[Instrucao] ${content}`,
            metadata: { type: 'instruction' },
            created_at: new Date().toISOString(),
          },
        ])
      } else {
        // Question mode: add both messages
        const questionResult = result as {
          supervisor_message: string
          julia_response: string
          message_id?: string
        }
        setMessages((prev) => [
          ...prev,
          {
            id: `temp-q-${Date.now()}`,
            conversation_id: conversationId,
            role: 'supervisor',
            content: questionResult.supervisor_message,
            metadata: { type: 'question' },
            created_at: new Date().toISOString(),
          },
          {
            id: questionResult.message_id || `temp-a-${Date.now()}`,
            conversation_id: conversationId,
            role: 'julia',
            content: questionResult.julia_response,
            metadata: { type: 'response' },
            created_at: new Date().toISOString(),
          },
        ])
      }
    } catch (err) {
      console.error('Failed to send channel message:', err)
    } finally {
      setSending(false)
    }
  }

  const handlePreviewAction = async (action: 'confirm' | 'reject'): Promise<void> => {
    if (!pendingPreview) return
    setProcessingAction(true)

    try {
      const response = await fetch(
        `/api/conversas/${conversationId}/channel/${pendingPreview.id}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action }),
        }
      )

      if (response.ok) {
        const statusText = action === 'confirm' ? 'Mensagem enviada ao medico' : 'Instrucao rejeitada'
        setMessages((prev) => [
          ...prev,
          {
            id: `system-${Date.now()}`,
            conversation_id: conversationId,
            role: 'julia',
            content: statusText,
            metadata: { type: `instruction_${action}ed` },
            created_at: new Date().toISOString(),
          },
        ])
        setPendingPreview(null)
      }
    } catch (err) {
      console.error(`Failed to ${action} instruction:`, err)
    } finally {
      setProcessingAction(false)
    }
  }

  const handleQuickButton = (prompt: string): void => {
    setInput(prompt)
    setMode('question')
  }

  if (!loaded) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      {/* Messages */}
      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
            <Bot className="h-8 w-8 text-muted-foreground/50" />
            <p className="text-xs text-muted-foreground">
              Converse com Julia sobre esta conversa.
            </p>
            <p className="text-[10px] text-muted-foreground/70">
              Faca perguntas ou envie instrucoes.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={cn(
                  'flex',
                  msg.role === 'supervisor' ? 'justify-end' : 'justify-start'
                )}
              >
                <div
                  className={cn(
                    'max-w-[85%] rounded-lg px-2.5 py-1.5 text-xs',
                    msg.role === 'supervisor'
                      ? 'rounded-tr-none bg-primary text-primary-foreground'
                      : 'rounded-tl-none bg-muted'
                  )}
                >
                  {/* Role indicator */}
                  <div className="mb-0.5 flex items-center gap-1 text-[10px] opacity-70">
                    {msg.role === 'supervisor' ? (
                      <>
                        <UserCog className="h-2.5 w-2.5" />
                        Supervisor
                      </>
                    ) : (
                      <>
                        <Bot className="h-2.5 w-2.5" />
                        Julia
                      </>
                    )}
                  </div>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  <span className="mt-0.5 block text-[9px] opacity-50">
                    {msg.created_at
                      ? formatDistanceToNow(new Date(msg.created_at), {
                          addSuffix: true,
                          locale: ptBR,
                        })
                      : ''}
                  </span>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Preview Banner */}
      {pendingPreview && (
        <div className="border-t bg-amber-50 p-3 dark:bg-amber-950/20">
          <div className="mb-1 text-[10px] font-medium uppercase text-amber-700 dark:text-amber-400">
            Preview da mensagem
          </div>
          <p className="rounded bg-white p-2 text-xs dark:bg-background">
            {pendingPreview.preview_message}
          </p>
          <div className="mt-2 flex gap-2">
            <Button
              size="sm"
              className="h-7 gap-1 text-xs"
              onClick={() => void handlePreviewAction('confirm')}
              disabled={processingAction}
            >
              {processingAction ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Check className="h-3 w-3" />
              )}
              Enviar ao medico
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 gap-1 text-xs"
              onClick={() => void handlePreviewAction('reject')}
              disabled={processingAction}
            >
              <X className="h-3 w-3" />
              Rejeitar
            </Button>
          </div>
        </div>
      )}

      {/* Quick buttons */}
      {messages.length === 0 && (
        <div className="border-t px-3 py-2">
          <div className="flex flex-wrap gap-1">
            {QUICK_BUTTONS.map((btn) => (
              <button
                key={btn.label}
                onClick={() => handleQuickButton(btn.prompt)}
                className="rounded-full bg-muted px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:bg-muted/80"
              >
                {btn.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t p-2">
        {/* Mode toggle */}
        <div className="mb-1.5 flex gap-1">
          <button
            onClick={() => setMode('question')}
            className={cn(
              'flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] transition-colors',
              mode === 'question'
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground'
            )}
          >
            <MessageCircle className="h-2.5 w-2.5" />
            Pergunta
          </button>
          <button
            onClick={() => setMode('instruction')}
            className={cn(
              'flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] transition-colors',
              mode === 'instruction'
                ? 'bg-amber-600 text-white'
                : 'bg-muted text-muted-foreground'
            )}
          >
            <Lightbulb className="h-2.5 w-2.5" />
            Instrucao
          </button>
        </div>

        {/* Input field */}
        <div className="flex gap-1">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                void handleSend()
              }
            }}
            placeholder={
              mode === 'instruction'
                ? 'Ex: Oferece a vaga do Sao Luiz...'
                : 'Pergunte a Julia sobre esta conversa...'
            }
            className="flex-1 rounded border bg-background px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
            disabled={sending || !!pendingPreview}
          />
          <Button
            size="icon"
            className="h-7 w-7 flex-shrink-0"
            onClick={() => void handleSend()}
            disabled={sending || !input.trim() || !!pendingPreview}
          >
            {sending ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Send className="h-3 w-3" />
            )}
          </Button>
        </div>

        {mode === 'instruction' && (
          <p className="mt-1 text-[9px] text-amber-600">
            Instrucoes geram um preview para confirmacao antes do envio.
          </p>
        )}
      </div>
    </div>
  )
}
