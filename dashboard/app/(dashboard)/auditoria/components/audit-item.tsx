'use client'

import { useState } from 'react'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import {
  Power,
  Flag,
  User,
  Settings,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Megaphone,
  Play,
  Pause,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'

interface AuditLog {
  id: string
  action: string
  actor_email: string
  actor_role: string
  details: Record<string, unknown>
  created_at: string
}

interface Props {
  log: AuditLog
}

type IconComponent = React.ComponentType<{ className?: string }>

const ACTION_ICONS: Record<string, IconComponent> = {
  julia_toggle: Power,
  julia_pause: Power,
  feature_flag_update: Flag,
  rate_limit_update: Settings,
  manual_handoff: User,
  return_to_julia: RefreshCw,
  circuit_reset: RefreshCw,
  create_campaign: Megaphone,
  start_campaign: Play,
  pause_campaign: Pause,
}

const ACTION_LABELS: Record<string, string> = {
  julia_toggle: 'Toggle Julia',
  julia_pause: 'Pausar Julia',
  feature_flag_update: 'Atualizar Feature Flag',
  rate_limit_update: 'Atualizar Rate Limit',
  manual_handoff: 'Handoff Manual',
  return_to_julia: 'Retornar para Julia',
  circuit_reset: 'Reset Circuit Breaker',
  create_campaign: 'Criar Campanha',
  start_campaign: 'Iniciar Campanha',
  pause_campaign: 'Pausar Campanha',
}

export function AuditItem({ log }: Props) {
  const [expanded, setExpanded] = useState(false)

  const Icon = ACTION_ICONS[log.action] ?? Settings
  const actionLabel = ACTION_LABELS[log.action] ?? log.action

  return (
    <div className="border-b last:border-b-0">
      <button
        className="w-full p-4 text-left hover:bg-muted/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-full bg-muted">
            <Icon className="h-4 w-4" />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="font-medium">{actionLabel}</p>
              <Badge variant="outline" className="text-xs">
                {log.actor_role}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground truncate">{log.actor_email}</p>
          </div>

          <div className="text-right shrink-0">
            <p className="text-sm text-muted-foreground">
              {format(new Date(log.created_at), 'dd/MM HH:mm', { locale: ptBR })}
            </p>
          </div>

          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground shrink-0" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4">
          <div className="p-3 bg-muted rounded-lg">
            <p className="text-xs font-medium mb-2">Detalhes</p>
            <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
              {JSON.stringify(log.details, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}
