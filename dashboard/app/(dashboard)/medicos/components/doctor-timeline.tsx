'use client'

import { useCallback, useEffect, useState } from 'react'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { MessageCircle, Send, UserCheck, type LucideIcon } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { getEventColor } from '@/lib/medicos'
import type { TimelineEvent } from '@/lib/medicos'

const EVENT_ICONS: Record<string, LucideIcon> = {
  message_sent: Send,
  message_received: MessageCircle,
  handoff: UserCheck,
}

interface Props {
  doctorId: string
}

export function DoctorTimeline({ doctorId }: Props) {
  const [loading, setLoading] = useState(true)
  const [events, setEvents] = useState<TimelineEvent[]>([])

  const fetchTimeline = useCallback(async () => {
    try {
      const response = await fetch(`/api/medicos/${doctorId}/timeline`)

      if (response.ok) {
        const result = await response.json()
        setEvents(result.events || [])
      }
    } catch (err) {
      console.error('Failed to fetch timeline:', err)
    } finally {
      setLoading(false)
    }
  }, [doctorId])

  useEffect(() => {
    fetchTimeline()
  }, [fetchTimeline])

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    )
  }

  if (events.length === 0) {
    return (
      <div className="py-8 text-center text-muted-foreground">Nenhuma interacao registrada</div>
    )
  }

  return (
    <div className="relative">
      {/* Linha vertical */}
      <div className="absolute bottom-0 left-4 top-0 w-0.5 bg-border" />

      <div className="space-y-6">
        {events.map((event) => {
          const Icon = EVENT_ICONS[event.type] || MessageCircle
          const colorClass = getEventColor(event.type)

          return (
            <div key={event.id} className="relative pl-10">
              {/* Icone */}
              <div
                className={cn(
                  'absolute left-0 flex h-8 w-8 items-center justify-center rounded-full',
                  colorClass
                )}
              >
                <Icon className="h-4 w-4" />
              </div>

              {/* Conteudo */}
              <div className="rounded-lg bg-muted p-4">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-medium">{event.title}</p>
                  <span className="whitespace-nowrap text-xs text-muted-foreground">
                    {format(new Date(event.created_at), "dd/MM 'as' HH:mm", {
                      locale: ptBR,
                    })}
                  </span>
                </div>
                {event.description && (
                  <p className="mt-1 text-sm text-muted-foreground">{event.description}</p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
