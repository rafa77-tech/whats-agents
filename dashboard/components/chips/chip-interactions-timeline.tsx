/**
 * Chip Interactions Timeline - Sprint 36
 *
 * Timeline de interações recentes do chip.
 * Sprint 64: Clique na interação abre modal de chat.
 * Sprint 64: Agrupa interações por número de telefone.
 */

'use client'

import { useMemo, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { chipsApi } from '@/lib/api/chips'
import { ChipInteraction, ChipInteractionsResponse } from '@/types/chips'
import { ConversationChatDialog } from './conversation-chat-dialog'
import {
  MessageSquare,
  Users,
  UserPlus,
  Image,
  AlertCircle,
  Heart,
  ChevronDown,
  ChevronRight,
  Loader2,
  Phone,
  Clock,
  CheckCircle2,
  XCircle,
} from 'lucide-react'

interface ChipInteractionsTimelineProps {
  chipId: string
  initialData: ChipInteractionsResponse
}

interface InteractionGroup {
  phone: string | null
  interactions: ChipInteraction[]
  conversationId: string | undefined
  lastTimestamp: string
  hasErrors: boolean
}

const interactionTypeConfig: Record<
  string,
  { icon: typeof MessageSquare; color: string; bgColor: string; label: string }
> = {
  conversa_individual: {
    icon: MessageSquare,
    color: 'text-status-info-solid',
    bgColor: 'bg-status-info/10',
    label: 'Conversa',
  },
  mensagem_grupo: {
    icon: Users,
    color: 'text-status-info-foreground',
    bgColor: 'bg-status-info/10',
    label: 'Mensagem em Grupo',
  },
  entrada_grupo: {
    icon: UserPlus,
    color: 'text-status-success-solid',
    bgColor: 'bg-status-success/10',
    label: 'Entrada em Grupo',
  },
  midia_enviada: {
    icon: Image,
    color: 'text-status-warning-solid',
    bgColor: 'bg-status-warning/10',
    label: 'Mídia Enviada',
  },
  erro: {
    icon: AlertCircle,
    color: 'text-status-error-solid',
    bgColor: 'bg-status-error/10',
    label: 'Erro',
  },
  warmup_par: {
    icon: Heart,
    color: 'text-status-info-foreground',
    bgColor: 'bg-status-info/10',
    label: 'Warmup Par',
  },
}

const defaultInteractionConfig = {
  icon: MessageSquare,
  color: 'text-muted-foreground',
  bgColor: 'bg-muted/50',
  label: 'Interação',
}

function groupInteractionsByPhone(interactions: ChipInteraction[]): InteractionGroup[] {
  const phoneMap = new Map<string, InteractionGroup>()
  const result: InteractionGroup[] = []

  for (const interaction of interactions) {
    const phone = interaction.destinatario || interaction.remetente

    if (!phone) {
      // No phone — keep as individual entry
      result.push({
        phone: null,
        interactions: [interaction],
        conversationId: interaction.conversationId,
        lastTimestamp: interaction.timestamp,
        hasErrors: !interaction.success,
      })
      continue
    }

    const existing = phoneMap.get(phone)
    if (existing) {
      existing.interactions.push(interaction)
      // Keep the most recent conversationId
      if (interaction.conversationId && !existing.conversationId) {
        existing.conversationId = interaction.conversationId
      }
      if (!interaction.success) {
        existing.hasErrors = true
      }
    } else {
      const group: InteractionGroup = {
        phone,
        interactions: [interaction],
        conversationId: interaction.conversationId,
        lastTimestamp: interaction.timestamp,
        hasErrors: !interaction.success,
      }
      phoneMap.set(phone, group)
      result.push(group)
    }
  }

  return result
}

export function ChipInteractionsTimeline({ chipId, initialData }: ChipInteractionsTimelineProps) {
  const [interactions, setInteractions] = useState<ChipInteraction[]>(initialData.interactions)
  const [hasMore, setHasMore] = useState(initialData.hasMore)
  const [isLoading, setIsLoading] = useState(false)
  const [chatConversationId, setChatConversationId] = useState<string | null>(null)

  const groups = useMemo(() => groupInteractionsByPhone(interactions), [interactions])

  const handleLoadMore = async () => {
    setIsLoading(true)
    try {
      const response = await chipsApi.getChipInteractions(chipId, {
        offset: interactions.length,
        limit: 20,
      })
      setInteractions([...interactions, ...response.interactions])
      setHasMore(response.hasMore)
    } catch (error) {
      console.error('Error loading more interactions:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between text-base">
            <span>Interações Recentes</span>
            <span className="text-sm font-normal text-muted-foreground">
              {initialData.total} total
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {interactions.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              Nenhuma interação registrada
            </div>
          ) : (
            <div className="space-y-1">
              {groups.map((group, index) => (
                <GroupItem
                  key={group.phone || group.interactions[0]?.id}
                  group={group}
                  isLast={index === groups.length - 1}
                  onOpenChat={setChatConversationId}
                />
              ))}

              {hasMore && (
                <div className="flex justify-center pt-4">
                  <Button variant="outline" size="sm" onClick={handleLoadMore} disabled={isLoading}>
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Carregando...
                      </>
                    ) : (
                      <>
                        <ChevronDown className="mr-2 h-4 w-4" />
                        Carregar mais
                      </>
                    )}
                  </Button>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <ConversationChatDialog
        conversationId={chatConversationId}
        open={chatConversationId !== null}
        onOpenChange={(open) => {
          if (!open) setChatConversationId(null)
        }}
      />
    </>
  )
}

function GroupItem({
  group,
  isLast,
  onOpenChat,
}: {
  group: InteractionGroup
  isLast: boolean
  onOpenChat: (conversationId: string) => void
}) {
  const first = group.interactions[0]

  // Single interaction — render individually (no grouping needed)
  if (group.interactions.length === 1 && first) {
    return <InteractionItem interaction={first} isLast={isLast} onOpenChat={onOpenChat} />
  }

  // Multiple interactions grouped by phone
  return <PhoneGroupItem group={group} isLast={isLast} onOpenChat={onOpenChat} />
}

function PhoneGroupItem({
  group,
  isLast,
  onOpenChat,
}: {
  group: InteractionGroup
  isLast: boolean
  onOpenChat: (conversationId: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const hasConversation = !!group.conversationId
  const count = group.interactions.length
  const typeCounts = new Map<string, number>()

  for (const i of group.interactions) {
    const config = interactionTypeConfig[i.type] || defaultInteractionConfig
    typeCounts.set(config.label, (typeCounts.get(config.label) || 0) + 1)
  }

  const summaryParts = Array.from(typeCounts.entries()).map(([label, c]) =>
    c > 1 ? `${c} ${label.toLowerCase()}` : label.toLowerCase()
  )

  const handleHeaderClick = () => {
    if (hasConversation && group.conversationId) {
      onOpenChat(group.conversationId)
    } else {
      setExpanded(!expanded)
    }
  }

  return (
    <div className="flex gap-3">
      {/* Timeline line and dot */}
      <div className="flex flex-col items-center">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-status-info/10">
          <Phone className="h-4 w-4 text-status-info-solid" />
        </div>
        {!isLast && <div className="my-1 w-0.5 flex-1 bg-muted" />}
      </div>

      {/* Content */}
      <div className={cn('flex-1 pb-4', isLast && 'pb-0')}>
        <div
          className="-mx-1 cursor-pointer rounded-md px-1 transition-colors hover:bg-muted/50"
          onClick={handleHeaderClick}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                {hasConversation ? (
                  <MessageSquare className="h-3.5 w-3.5 text-primary" />
                ) : (
                  <ChevronRight
                    className={cn(
                      'h-3.5 w-3.5 text-muted-foreground transition-transform',
                      expanded && 'rotate-90'
                    )}
                  />
                )}
                <span className="text-sm font-medium text-foreground">
                  {formatPhone(group.phone!)}
                </span>
                <Badge variant="secondary" className="text-xs">
                  {count} interações
                </Badge>
                {group.hasErrors && (
                  <Badge variant="destructive" className="text-xs">
                    Erros
                  </Badge>
                )}
              </div>
              <p className="ml-6 mt-0.5 text-sm text-muted-foreground">
                {summaryParts.join(', ')}
                {hasConversation && <span className="ml-1 text-xs text-primary">Ver conversa</span>}
              </p>
            </div>
            <span className="whitespace-nowrap text-xs text-muted-foreground">
              {formatTimestamp(group.lastTimestamp)}
            </span>
          </div>
        </div>

        {/* Expanded: show individual interactions */}
        {expanded && !hasConversation && (
          <div className="ml-6 mt-2 space-y-2 rounded-md border bg-muted/30 p-3">
            {group.interactions.map((interaction) => (
              <ExpandedInteractionRow key={interaction.id} interaction={interaction} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function ExpandedInteractionRow({ interaction }: { interaction: ChipInteraction }) {
  const config = interactionTypeConfig[interaction.type] || defaultInteractionConfig
  const Icon = config.icon

  return (
    <div className="flex items-start gap-2 text-sm">
      <Icon className={cn('mt-0.5 h-3.5 w-3.5 shrink-0', config.color)} />
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="font-medium">{config.label}</span>
          {!interaction.success && (
            <Badge variant="destructive" className="text-xs">
              Falhou
            </Badge>
          )}
        </div>
        <p className="text-muted-foreground">{interaction.description}</p>
        {interaction.erroMensagem && (
          <p className="text-xs text-status-error-solid">{interaction.erroMensagem}</p>
        )}
      </div>
      <span className="whitespace-nowrap text-xs text-muted-foreground">
        {formatTimestamp(interaction.timestamp)}
      </span>
    </div>
  )
}

function hasExpandableDetails(interaction: ChipInteraction): boolean {
  return !!(
    interaction.erroMensagem ||
    interaction.midiaTipo ||
    interaction.obteveResposta != null ||
    interaction.tempoRespostaSegundos != null ||
    (interaction.metadata && Object.keys(interaction.metadata).length > 0)
  )
}

function formatPhone(phone: string): string {
  if (phone.length === 13 && phone.startsWith('55')) {
    const ddd = phone.slice(2, 4)
    const num = phone.slice(4)
    return `(${ddd}) ${num.slice(0, 5)}-${num.slice(5)}`
  }
  return phone
}

function InteractionItem({
  interaction,
  isLast,
  onOpenChat,
}: {
  interaction: ChipInteraction
  isLast: boolean
  onOpenChat: (conversationId: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const config = interactionTypeConfig[interaction.type] || defaultInteractionConfig
  const Icon = config.icon

  const hasConversation = !!interaction.conversationId
  const hasDetails = hasExpandableDetails(interaction)
  const isClickable = hasConversation || hasDetails
  const phone = interaction.destinatario || interaction.remetente

  const handleClick = () => {
    if (hasConversation && interaction.conversationId) {
      onOpenChat(interaction.conversationId)
    } else if (hasDetails) {
      setExpanded(!expanded)
    }
  }

  return (
    <div className="flex gap-3">
      {/* Timeline line and dot */}
      <div className="flex flex-col items-center">
        <div
          className={cn(
            'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
            config.bgColor
          )}
        >
          <Icon className={cn('h-4 w-4', config.color)} />
        </div>
        {!isLast && <div className="my-1 w-0.5 flex-1 bg-muted" />}
      </div>

      {/* Content */}
      <div className={cn('flex-1 pb-4', isLast && 'pb-0')}>
        <div
          className={cn(
            'flex items-start justify-between gap-2',
            isClickable &&
              '-mx-1 cursor-pointer rounded-md px-1 transition-colors hover:bg-muted/50'
          )}
          onClick={isClickable ? handleClick : undefined}
        >
          <div className="flex-1">
            <div className="flex items-center gap-2">
              {hasConversation ? (
                <MessageSquare className="h-3.5 w-3.5 text-primary" />
              ) : hasDetails ? (
                <ChevronRight
                  className={cn(
                    'h-3.5 w-3.5 text-muted-foreground transition-transform',
                    expanded && 'rotate-90'
                  )}
                />
              ) : null}
              <span className="text-sm font-medium text-foreground">{config.label}</span>
              {!interaction.success && (
                <Badge variant="destructive" className="text-xs">
                  Falhou
                </Badge>
              )}
              {phone && <span className="text-xs text-muted-foreground">{formatPhone(phone)}</span>}
            </div>
            <p className={cn('mt-0.5 text-sm text-muted-foreground', isClickable && 'ml-6')}>
              {interaction.description}
              {hasConversation && <span className="ml-1 text-xs text-primary">Ver conversa</span>}
            </p>
          </div>
          <span className="whitespace-nowrap text-xs text-muted-foreground">
            {formatTimestamp(interaction.timestamp)}
          </span>
        </div>

        {/* Expanded details (only for non-conversation interactions) */}
        {expanded && !hasConversation && (
          <div className="ml-6 mt-2 space-y-1.5 rounded-md border bg-muted/30 p-3 text-sm">
            <InteractionDetails interaction={interaction} />
          </div>
        )}
      </div>
    </div>
  )
}

function InteractionDetails({ interaction }: { interaction: ChipInteraction }) {
  return (
    <>
      {interaction.destinatario && (
        <DetailRow
          icon={Phone}
          label="Destinatário"
          value={formatPhone(interaction.destinatario)}
        />
      )}
      {interaction.remetente && (
        <DetailRow icon={Phone} label="Remetente" value={formatPhone(interaction.remetente)} />
      )}

      {interaction.erroMensagem && (
        <DetailRow
          icon={XCircle}
          label="Erro"
          value={interaction.erroMensagem}
          className="text-status-error-solid"
        />
      )}

      {interaction.midiaTipo && (
        <DetailRow icon={Image} label="Tipo de mídia" value={interaction.midiaTipo} />
      )}

      {interaction.obteveResposta != null && (
        <DetailRow
          icon={interaction.obteveResposta ? CheckCircle2 : XCircle}
          label="Obteve resposta"
          value={interaction.obteveResposta ? 'Sim' : 'Não'}
          className={interaction.obteveResposta ? 'text-status-success-solid' : ''}
        />
      )}

      {interaction.tempoRespostaSegundos != null && (
        <DetailRow
          icon={Clock}
          label="Tempo de resposta"
          value={formatDuration(interaction.tempoRespostaSegundos)}
        />
      )}

      {interaction.metadata && Object.keys(interaction.metadata).length > 0 && (
        <MetadataDetails metadata={interaction.metadata} />
      )}

      <DetailRow
        icon={Clock}
        label="Data/hora"
        value={new Date(interaction.timestamp).toLocaleString('pt-BR')}
      />
    </>
  )
}

function DetailRow({
  icon: IconComponent,
  label,
  value,
  className,
}: {
  icon: typeof Phone
  label: string
  value: string
  className?: string
}) {
  return (
    <div className="flex items-start gap-2">
      <IconComponent className={cn('mt-0.5 h-3.5 w-3.5 text-muted-foreground', className)} />
      <span className="text-muted-foreground">{label}:</span>
      <span className={cn('font-medium text-foreground', className)}>{value}</span>
    </div>
  )
}

function MetadataDetails({ metadata }: { metadata: Record<string, unknown> }) {
  const displayKeys = Object.entries(metadata).filter(
    ([, v]) => v !== null && v !== undefined && v !== ''
  )

  if (displayKeys.length === 0) return null

  const labelMap: Record<string, string> = {
    tipo_warmup: 'Tipo warmup',
    simulada: 'Simulada',
    sucesso: 'Sucesso',
    error: 'Erro',
    grupo_nome: 'Grupo',
    grupo_id: 'ID do grupo',
  }

  return (
    <>
      {displayKeys.map(([key, value]) => (
        <div key={key} className="flex items-start gap-2">
          <span className="text-muted-foreground">{labelMap[key] || key}:</span>
          <span className="font-medium text-foreground">
            {typeof value === 'boolean' ? (value ? 'Sim' : 'Não') : String(value)}
          </span>
        </div>
      ))}
    </>
  )
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return secs > 0 ? `${mins}min ${secs}s` : `${mins}min`
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffMins < 60) {
    return `${diffMins}m atrás`
  } else if (diffHours < 24) {
    return `${diffHours}h atrás`
  } else if (diffDays < 7) {
    return `${diffDays}d atrás`
  } else {
    return date.toLocaleDateString('pt-BR')
  }
}
