/**
 * Shift Metadata Card Component
 *
 * Displays shift metadata: ID, created_at, updated_at, grupo_origem.
 * Grupo de origem is clickable to show the original WhatsApp message.
 */

'use client'

import { useState } from 'react'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { ExternalLink } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { MensagemOriginalModal } from '@/components/mensagem-original-modal'
import type { MensagemOriginal } from '@/lib/vagas'

interface ShiftMetadataCardProps {
  id: string
  createdAt: string | null
  updatedAt: string | null
  grupoOrigem?: string | null
  mensagemOriginal?: MensagemOriginal | null
}

function formatDate(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (isNaN(date.getTime())) return '—'
  return format(date, "dd/MM/yyyy 'as' HH:mm", { locale: ptBR })
}

export function ShiftMetadataCard({
  id,
  createdAt,
  updatedAt,
  grupoOrigem,
  mensagemOriginal,
}: ShiftMetadataCardProps) {
  const [showMsgModal, setShowMsgModal] = useState(false)

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Metadados</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <p className="text-sm text-muted-foreground">ID</p>
            <p className="truncate font-mono text-sm" title={id}>
              {id}
            </p>
          </div>
          {grupoOrigem && (
            <div>
              <p className="text-sm text-muted-foreground">Grupo de Origem</p>
              {mensagemOriginal ? (
                <button
                  type="button"
                  onClick={() => setShowMsgModal(true)}
                  className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
                >
                  {grupoOrigem}
                  <ExternalLink className="h-3 w-3" />
                </button>
              ) : (
                <p className="text-sm font-medium">{grupoOrigem}</p>
              )}
            </div>
          )}
          <div>
            <p className="text-sm text-muted-foreground">Criado em</p>
            <p className="text-sm">{formatDate(createdAt)}</p>
          </div>
          {updatedAt && (
            <div>
              <p className="text-sm text-muted-foreground">Atualizado em</p>
              <p className="text-sm">{formatDate(updatedAt)}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {grupoOrigem && mensagemOriginal && (
        <MensagemOriginalModal
          open={showMsgModal}
          onOpenChange={setShowMsgModal}
          grupoNome={grupoOrigem}
          mensagem={mensagemOriginal}
        />
      )}
    </>
  )
}
