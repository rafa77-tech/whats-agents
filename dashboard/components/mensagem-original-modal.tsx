/**
 * Modal para exibir a mensagem original do grupo WhatsApp que originou uma vaga.
 * Usado tanto na pagina de detalhes da vaga quanto no modal de vagas-hoje.
 */

'use client'

import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { MessageSquare, User, Clock } from 'lucide-react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'

interface MensagemOriginalModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  grupoNome: string
  mensagem: {
    texto: string
    sender_nome: string
    created_at: string
  }
}

function formatTimestamp(value: string): string {
  try {
    return format(new Date(value), "dd/MM/yyyy 'as' HH:mm", { locale: ptBR })
  } catch {
    return '-'
  }
}

export function MensagemOriginalModal({
  open,
  onOpenChange,
  grupoNome,
  mensagem,
}: MensagemOriginalModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Mensagem Original
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <User className="h-3.5 w-3.5" />
              {mensagem.sender_nome}
            </span>
            <span className="inline-flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              {formatTimestamp(mensagem.created_at)}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">Grupo: {grupoNome}</p>
          <ScrollArea className="max-h-[400px]">
            <div className="whitespace-pre-wrap rounded-md bg-muted/50 p-4 text-sm leading-relaxed">
              {mensagem.texto}
            </div>
          </ScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  )
}
