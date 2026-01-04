'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Activity, MessageSquare, Zap } from 'lucide-react'
import { useAuth } from '@/hooks/use-auth'
import { Skeleton } from '@/components/ui/skeleton'

interface DashboardStatus {
  julia: {
    is_active: boolean
    mode: string
    paused_until?: string
    pause_reason?: string
  }
  rate_limit: {
    messages_hour: number
    messages_day: number
    limit_hour: number
    limit_day: number
    percent_hour: number
    percent_day: number
  }
  circuits: {
    evolution: string
    claude: string
    supabase: string
  }
  health: {
    api: string
    database: string
    redis: string
    evolution: string
    chatwoot: string
  }
  conversations: {
    active: number
    waiting_response: number
    handoff: number
    today_new: number
  }
  funnel: {
    prospecting: number
    engaged: number
    negotiating: number
    converted: number
    total: number
  }
}

function StatusCardsSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {[...Array(4)].map((_, i) => (
        <Card key={i}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-4" />
          </CardHeader>
          <CardContent>
            <Skeleton className="mb-2 h-8 w-16" />
            <Skeleton className="h-3 w-24" />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export function StatusCards() {
  const { session } = useAuth()
  const [status, setStatus] = useState<DashboardStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchStatus() {
      if (!session?.access_token) return

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const response = await fetch(`${apiUrl}/dashboard/status`, {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        })

        if (!response.ok) {
          throw new Error('Failed to fetch status')
        }

        const data = await response.json()
        setStatus(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchStatus()
    // Refresh every 30 seconds
    const interval = setInterval(fetchStatus, 30000)
    return () => clearInterval(interval)
  }, [session?.access_token])

  if (loading) {
    return <StatusCardsSkeleton />
  }

  if (error || !status) {
    // Show mock data if API fails
    return (
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Julia</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <Badge variant="secondary">Offline</Badge>
            <p className="mt-1 text-xs text-muted-foreground">API indisponivel</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Rate Limit</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">-/-</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Saude</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">-</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Conversas</CardTitle>
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">-</div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const juliaActive = status.julia.is_active
  const circuits = Object.values(status.circuits)
  const circuitsOk = circuits.filter((c) => c === 'closed').length
  const healthScore = Math.round((circuitsOk / circuits.length) * 100)

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {/* Julia Status */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Julia</CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            <Badge variant={juliaActive ? 'default' : 'destructive'}>
              <span
                className={`mr-1.5 h-2 w-2 rounded-full ${
                  juliaActive ? 'animate-pulse bg-green-400' : 'bg-red-400'
                }`}
              />
              {juliaActive ? 'Ativa' : 'Pausada'}
            </Badge>
          </div>
          {!juliaActive && status.julia.pause_reason && (
            <p className="mt-1 truncate text-xs text-muted-foreground">
              {status.julia.pause_reason}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Rate Limit */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Rate Limit</CardTitle>
          <Zap className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {status.rate_limit.messages_hour}/{status.rate_limit.limit_hour}
            <span className="text-sm font-normal text-muted-foreground">/h</span>
          </div>
          <div className="mt-1 flex items-center gap-2">
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-secondary">
              <div
                className="h-full bg-primary transition-all"
                style={{
                  width: `${status.rate_limit.percent_hour}%`,
                }}
              />
            </div>
            <span className="text-xs text-muted-foreground">
              {status.rate_limit.messages_day}/{status.rate_limit.limit_day}/d
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Health */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Saude</CardTitle>
          <div className="flex gap-0.5">
            {circuits.map((circuit, i) => (
              <span
                key={i}
                className={`h-2 w-2 rounded-full ${
                  circuit === 'closed'
                    ? 'bg-green-500'
                    : circuit === 'open'
                      ? 'bg-red-500'
                      : 'bg-yellow-500'
                }`}
              />
            ))}
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{healthScore}%</div>
          <p className="text-xs text-muted-foreground">
            {healthScore === 100 ? 'Todos sistemas OK' : 'Verificar circuits'}
          </p>
        </CardContent>
      </Card>

      {/* Conversations Today */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Conversas Hoje</CardTitle>
          <MessageSquare className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{status.conversations.today_new}</div>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-muted-foreground">{status.conversations.active} ativas</span>
            {status.conversations.handoff > 0 && (
              <>
                <span className="text-muted-foreground">|</span>
                <span className="text-amber-500">{status.conversations.handoff} handoff</span>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
