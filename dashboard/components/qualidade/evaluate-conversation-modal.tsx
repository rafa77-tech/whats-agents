'use client'

import { useState } from 'react'
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
import {
  useConversationDetail,
  formatTimeBR,
  formatShortId,
  isRatingsComplete,
  DEFAULT_RATINGS,
  MAX_RATING_STARS,
  EVALUATION_CRITERIA,
} from '@/lib/qualidade'
import type {
  EvaluateConversationModalProps,
  ConversationRatings,
  RatingInputProps,
} from '@/lib/qualidade'

function RatingInput({ label, value, onChange }: RatingInputProps) {
  return (
    <div>
      <Label className="text-sm">{label}</Label>
      <div className="mt-1 flex gap-1">
        {Array.from({ length: MAX_RATING_STARS }, (_, i) => i + 1).map((n) => (
          <button key={n} type="button" onClick={() => onChange(n)} className="focus:outline-none">
            <Star
              className={cn(
                'h-5 w-5 transition-colors',
                n <= value ? 'fill-status-warning-solid text-status-warning-solid' : 'text-gray-300'
              )}
            />
          </button>
        ))}
      </div>
    </div>
  )
}

export function EvaluateConversationModal({
  conversationId,
  onClose,
}: EvaluateConversationModalProps) {
  const { conversation, loading, saveEvaluation, saving } = useConversationDetail(conversationId)
  const [ratings, setRatings] = useState<ConversationRatings>(DEFAULT_RATINGS)
  const [observacoes, setObservacoes] = useState('')

  const handleSave = async () => {
    try {
      await saveEvaluation(ratings, observacoes)
      onClose()
    } catch {
      // Error handled by hook
    }
  }

  const updateRating = (key: keyof ConversationRatings, value: number) => {
    setRatings((prev) => ({ ...prev, [key]: value }))
  }

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
          <DialogTitle>Avaliar Conversa {formatShortId(conversationId)}</DialogTitle>
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
                      ? 'ml-4 bg-status-info text-status-info-foreground'
                      : 'mr-4 bg-white text-gray-900'
                  )}
                >
                  <p className="mb-1 text-xs font-medium text-gray-500">
                    {msg.remetente === 'julia' ? 'Julia' : conversation.medicoNome}
                  </p>
                  <p className="whitespace-pre-wrap">{msg.conteudo}</p>
                  <p className="mt-1 text-xs text-gray-400">{formatTimeBR(msg.criadaEm)}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Rating Form */}
          <div className="space-y-4 overflow-y-auto">
            {EVALUATION_CRITERIA.map((criteria) => (
              <RatingInput
                key={criteria.key}
                label={criteria.label}
                value={ratings[criteria.key]}
                onChange={(v) => updateRating(criteria.key, v)}
              />
            ))}

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
            <Button onClick={handleSave} disabled={saving || !isRatingsComplete(ratings)}>
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
