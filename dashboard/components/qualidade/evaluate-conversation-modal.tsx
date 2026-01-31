'use client'

import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Loader2, Star, ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Message {
  id: string
  remetente: 'julia' | 'medico'
  conteudo: string
  criadaEm: string
}

interface ConversationDetail {
  id: string
  medicoNome: string
  mensagens: Message[]
}

interface EvaluateConversationModalProps {
  conversationId: string
  onClose: () => void
}

interface Ratings {
  naturalidade: number
  persona: number
  objetivo: number
  satisfacao: number
}

export function EvaluateConversationModal({
  conversationId,
  onClose,
}: EvaluateConversationModalProps) {
  const [conversation, setConversation] = useState<ConversationDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [ratings, setRatings] = useState<Ratings>({
    naturalidade: 0,
    persona: 0,
    objetivo: 0,
    satisfacao: 0,
  })
  const [observacoes, setObservacoes] = useState('')

  useEffect(() => {
    const fetchConversation = async () => {
      try {
        const res = await fetch(`/api/admin/conversas/${conversationId}`)
        if (res.ok) {
          const data = await res.json()
          setConversation({
            id: data.id,
            medicoNome: data.medico_nome || 'Desconhecido',
            mensagens:
              data.interacoes?.map((m: Record<string, unknown>) => ({
                id: m.id,
                remetente: m.remetente,
                conteudo: m.conteudo,
                criadaEm: m.criada_em,
              })) || [],
          })
        }
      } catch {
        // Ignore errors
      } finally {
        setLoading(false)
      }
    }

    fetchConversation()
  }, [conversationId])

  const handleSave = async () => {
    setSaving(true)
    try {
      await fetch('/api/admin/avaliacoes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversa_id: conversationId,
          naturalidade: ratings.naturalidade,
          persona: ratings.persona,
          objetivo: ratings.objetivo,
          satisfacao: ratings.satisfacao,
          observacoes,
        }),
      })
      onClose()
    } catch {
      // Ignore errors
    } finally {
      setSaving(false)
    }
  }

  const RatingInput = ({
    label,
    value,
    onChange,
  }: {
    label: string
    value: number
    onChange: (v: number) => void
  }) => (
    <div>
      <Label className="text-sm">{label}</Label>
      <div className="mt-1 flex gap-1">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => onChange(n)}
            className="focus:outline-none"
          >
            <Star
              className={cn(
                'h-5 w-5 transition-colors',
                n <= value ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'
              )}
            />
          </button>
        ))}
      </div>
    </div>
  )

  if (loading) {
    return (
      <Dialog open onOpenChange={onClose}>
        <DialogContent className="max-w-3xl">
          <div className="flex justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-h-[80vh] max-w-3xl overflow-hidden">
        <DialogHeader>
          <DialogTitle>Avaliar Conversa #{conversationId.slice(0, 8)}</DialogTitle>
          <DialogDescription>
            Conversa com {conversation?.medicoNome} - {conversation?.mensagens.length} mensagens
          </DialogDescription>
        </DialogHeader>

        <div className="grid max-h-[50vh] grid-cols-2 gap-4 overflow-hidden">
          {/* Messages */}
          <div className="overflow-y-auto rounded-lg border bg-gray-50 p-4">
            <div className="space-y-3">
              {conversation?.mensagens.map((msg) => (
                <div
                  key={msg.id}
                  className={cn(
                    'rounded-lg p-3 text-sm',
                    msg.remetente === 'julia'
                      ? 'ml-4 bg-blue-100 text-blue-900'
                      : 'mr-4 bg-white text-gray-900'
                  )}
                >
                  <p className="mb-1 text-xs font-medium text-gray-500">
                    {msg.remetente === 'julia' ? 'Julia' : conversation.medicoNome}
                  </p>
                  <p className="whitespace-pre-wrap">{msg.conteudo}</p>
                  <p className="mt-1 text-xs text-gray-400">
                    {new Date(msg.criadaEm).toLocaleTimeString('pt-BR', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Rating Form */}
          <div className="space-y-4 overflow-y-auto">
            <RatingInput
              label="Naturalidade"
              value={ratings.naturalidade}
              onChange={(v) => setRatings((r) => ({ ...r, naturalidade: v }))}
            />
            <RatingInput
              label="Persona"
              value={ratings.persona}
              onChange={(v) => setRatings((r) => ({ ...r, persona: v }))}
            />
            <RatingInput
              label="Objetivo"
              value={ratings.objetivo}
              onChange={(v) => setRatings((r) => ({ ...r, objetivo: v }))}
            />
            <RatingInput
              label="Satisfacao"
              value={ratings.satisfacao}
              onChange={(v) => setRatings((r) => ({ ...r, satisfacao: v }))}
            />

            <div>
              <Label htmlFor="observacoes">Observacoes</Label>
              <Textarea
                id="observacoes"
                value={observacoes}
                onChange={(e) => setObservacoes(e.target.value)}
                placeholder="Comentarios sobre a conversa..."
                rows={3}
              />
            </div>
          </div>
        </div>

        <DialogFooter className="flex items-center justify-between">
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled>
              <ChevronLeft className="h-4 w-4" />
              Anterior
            </Button>
            <Button variant="outline" size="sm" disabled>
              Proxima
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose}>
              Cancelar
            </Button>
            <Button
              onClick={handleSave}
              disabled={
                saving ||
                ratings.naturalidade === 0 ||
                ratings.persona === 0 ||
                ratings.objetivo === 0 ||
                ratings.satisfacao === 0
              }
            >
              {saving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Salvando...
                </>
              ) : (
                'Salvar Avaliacao'
              )}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
