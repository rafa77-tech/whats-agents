/**
 * Chip Interactions Timeline - Sprint 36
 *
 * Timeline de interações recentes do chip.
 */

'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { chipsApi } from '@/lib/api/chips'
import { ChipInteraction, ChipInteractionsResponse, InteractionType } from '@/types/chips'
import {
  MessageSquare,
  Users,
  UserPlus,
  Image,
  AlertCircle,
  Heart,
  ChevronDown,
  Loader2,
} from 'lucide-react'

interface ChipInteractionsTimelineProps {
  chipId: string
  initialData: ChipInteractionsResponse
}

const interactionTypeConfig: Record<
  InteractionType,
  { icon: typeof MessageSquare; color: string; bgColor: string; label: string }
> = {
  conversa_individual: {
    icon: MessageSquare,
    color: 'text-blue-500',
    bgColor: 'bg-blue-50',
    label: 'Conversa',
  },
  mensagem_grupo: {
    icon: Users,
    color: 'text-purple-500',
    bgColor: 'bg-purple-50',
    label: 'Mensagem em Grupo',
  },
  entrada_grupo: {
    icon: UserPlus,
    color: 'text-green-500',
    bgColor: 'bg-green-50',
    label: 'Entrada em Grupo',
  },
  midia_enviada: {
    icon: Image,
    color: 'text-orange-500',
    bgColor: 'bg-orange-50',
    label: 'Mídia Enviada',
  },
  erro: {
    icon: AlertCircle,
    color: 'text-red-500',
    bgColor: 'bg-red-50',
    label: 'Erro',
  },
  warmup_par: {
    icon: Heart,
    color: 'text-pink-500',
    bgColor: 'bg-pink-50',
    label: 'Warmup Par',
  },
}

export function ChipInteractionsTimeline({ chipId, initialData }: ChipInteractionsTimelineProps) {
  const [interactions, setInteractions] = useState<ChipInteraction[]>(initialData.interactions)
  const [hasMore, setHasMore] = useState(initialData.hasMore)
  const [isLoading, setIsLoading] = useState(false)

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
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-base">
          <span>Interações Recentes</span>
          <span className="text-sm font-normal text-gray-500">{initialData.total} total</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {interactions.length === 0 ? (
          <div className="py-8 text-center text-gray-500">Nenhuma interação registrada</div>
        ) : (
          <div className="space-y-1">
            {interactions.map((interaction, index) => (
              <InteractionItem
                key={interaction.id}
                interaction={interaction}
                isLast={index === interactions.length - 1}
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
  )
}

function InteractionItem({
  interaction,
  isLast,
}: {
  interaction: ChipInteraction
  isLast: boolean
}) {
  const config = interactionTypeConfig[interaction.type]
  const Icon = config.icon

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
        {!isLast && <div className="my-1 w-0.5 flex-1 bg-gray-200" />}
      </div>

      {/* Content */}
      <div className={cn('flex-1 pb-4', isLast && 'pb-0')}>
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-900">{config.label}</span>
              {!interaction.success && (
                <Badge variant="destructive" className="text-xs">
                  Falhou
                </Badge>
              )}
            </div>
            <p className="mt-0.5 text-sm text-gray-600">{interaction.description}</p>
          </div>
          <span className="whitespace-nowrap text-xs text-gray-500">
            {formatTimestamp(interaction.timestamp)}
          </span>
        </div>
      </div>
    </div>
  )
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
