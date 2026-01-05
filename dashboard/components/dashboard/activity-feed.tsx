'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { formatRelativeTime } from '@/lib/utils'
import { MessageSquare, CheckCircle, AlertTriangle, UserPlus, Send, Megaphone } from 'lucide-react'

// Mock activity data generator - called only on client
function generateMockActivities() {
  return [
    {
      id: '1',
      tipo: 'resposta',
      descricao: 'Dr. Carlos Silva respondeu mensagem',
      created_at: new Date(Date.now() - 2 * 60000).toISOString(),
    },
    {
      id: '2',
      tipo: 'plantao_confirmado',
      descricao: 'Dra. Ana confirmou plantao dia 15/01',
      created_at: new Date(Date.now() - 15 * 60000).toISOString(),
    },
    {
      id: '3',
      tipo: 'handoff',
      descricao: 'Dr. Pedro solicitou atendimento humano',
      created_at: new Date(Date.now() - 30 * 60000).toISOString(),
    },
    {
      id: '4',
      tipo: 'mensagem',
      descricao: 'Julia enviou oferta para Dr. Marcos',
      created_at: new Date(Date.now() - 45 * 60000).toISOString(),
    },
    {
      id: '5',
      tipo: 'novo_medico',
      descricao: 'Novo medico cadastrado: Dr. Felipe Santos',
      created_at: new Date(Date.now() - 60 * 60000).toISOString(),
    },
    {
      id: '6',
      tipo: 'campanha',
      descricao: "Campanha 'Cardiologia SP' iniciada",
      created_at: new Date(Date.now() - 2 * 60 * 60000).toISOString(),
    },
  ]
}

interface ActivityItem {
  id: string
  tipo: string
  descricao: string
  created_at: string
}

const ACTIVITY_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  mensagem: Send,
  plantao_confirmado: CheckCircle,
  handoff: AlertTriangle,
  novo_medico: UserPlus,
  campanha: Megaphone,
  resposta: MessageSquare,
}

const ACTIVITY_COLORS: Record<string, string> = {
  mensagem: 'text-blue-500 bg-blue-50',
  plantao_confirmado: 'text-green-500 bg-green-50',
  handoff: 'text-red-500 bg-red-50',
  novo_medico: 'text-purple-500 bg-purple-50',
  campanha: 'text-amber-500 bg-amber-50',
  resposta: 'text-emerald-500 bg-emerald-50',
}

export function ActivityFeed() {
  // Use state to avoid hydration mismatch with Date.now()
  const [activities, setActivities] = useState<ActivityItem[]>([])
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    // TODO: Replace with real API call
    setActivities(generateMockActivities())
    setMounted(true)
  }, [])

  // Show skeleton while not mounted to avoid hydration mismatch
  if (!mounted) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Atividade Recente</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[200px] animate-pulse space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="h-7 w-7 rounded-full bg-muted" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-3/4 rounded bg-muted" />
                  <div className="h-3 w-1/4 rounded bg-muted" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Atividade Recente</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[200px] pr-4">
          <div className="space-y-4">
            {activities.map((activity) => {
              const Icon = ACTIVITY_ICONS[activity.tipo] || MessageSquare
              const colorClass = ACTIVITY_COLORS[activity.tipo] || 'text-gray-500 bg-gray-50'

              return (
                <div key={activity.id} className="flex items-start gap-3">
                  <div className={`rounded-full p-1.5 ${colorClass}`}>
                    <Icon className="h-3.5 w-3.5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm">{activity.descricao}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatRelativeTime(activity.created_at)}
                    </p>
                  </div>
                </div>
              )
            })}

            {activities.length === 0 && (
              <div className="py-8 text-center text-muted-foreground">
                Nenhuma atividade recente
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
