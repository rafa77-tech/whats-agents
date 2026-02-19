'use client'

import { useState } from 'react'
import { FileText, X, MessageSquare, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { ConversationSummary as SummaryType } from '@/types/conversas'

interface Props {
  summary: SummaryType
}

export function ConversationSummary({ summary }: Props) {
  const [dismissed, setDismissed] = useState(false)

  if (dismissed) return null

  return (
    <div className="border-b bg-muted/20 px-4 py-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
            <FileText className="h-3.5 w-3.5" />
            Resumo
          </div>
          <p className="text-sm leading-relaxed text-foreground">{summary.text}</p>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <MessageSquare className="h-3 w-3" />
              {summary.total_msg_medico} medico / {summary.total_msg_julia} Julia
            </span>
            {summary.duracao_dias > 0 && (
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {summary.duracao_dias} dia{summary.duracao_dias > 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 flex-shrink-0"
          onClick={() => setDismissed(true)}
        >
          <X className="h-3 w-3" />
        </Button>
      </div>
    </div>
  )
}
