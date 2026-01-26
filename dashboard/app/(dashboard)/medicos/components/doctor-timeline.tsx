'use client'

import { useCallback, useEffect, useState } from 'react'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { MessageCircle, Send, UserCheck, type LucideIcon } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/hooks/use-auth'
import { cn } from '@/lib/utils'

interface TimelineEvent {
  id: string
  type: string
  title: string
  description?: string
  created_at: string
  metadata?: Record<string, unknown>
}

const EVENT_ICONS: Record<string, LucideIcon> = {
  message_sent: Send,
  message_received: MessageCircle,
  handoff: UserCheck,
}

const EVENT_COLORS: Record<string, string> = {
  message_sent: 'bg-blue-100 text-blue-600',
  message_received: 'bg-green-100 text-green-600',
  handoff: 'bg-orange-100 text-orange-600',
}

interface Props {
  doctorId: string
}

export function DoctorTimeline({ doctorId }: Props) {
  const { session } = useAuth()
  const [loading, setLoading] = useState(true)
  const [events, setEvents] = useState<TimelineEvent[]>([])

  const fetchTimeline = useCallback(async () => {
    if (!session?.access_token) return

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/dashboard/doctors/${doctorId}/timeline`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      })

      if (response.ok) {
        const result = await response.json()
        setEvents(result.events || [])
      }
    } catch (err) {
      console.error('Failed to fetch timeline:', err)
    } finally {
      setLoading(false)
    }
  }, [session?.access_token, doctorId])

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
          const colorClass = EVENT_COLORS[event.type] || 'bg-gray-100 text-gray-600'

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
