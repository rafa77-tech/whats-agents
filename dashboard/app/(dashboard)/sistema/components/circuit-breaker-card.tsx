'use client'

import { useState } from 'react'
import { Activity, RefreshCcw } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/use-auth'

interface CircuitStatus {
  evolution: string
  claude: string
  supabase: string
}

interface Props {
  status: CircuitStatus
  onReset?: (service: string) => Promise<void>
}

const SERVICES = [
  { key: 'evolution', label: 'Evolution API', description: 'WhatsApp' },
  { key: 'claude', label: 'Claude AI', description: 'LLM' },
  { key: 'supabase', label: 'Supabase', description: 'Database' },
]

export function CircuitBreakerCard({ status, onReset }: Props) {
  const [resetting, setResetting] = useState<string | null>(null)

  const { user } = useAuth()
  const canReset = user?.role && ['manager', 'admin'].includes(user.role)

  const handleReset = async (service: string) => {
    if (!onReset) return
    setResetting(service)
    try {
      await onReset(service)
    } finally {
      setResetting(null)
    }
  }

  const getStatusBadge = (state: string) => {
    switch (state) {
      case 'closed':
        return <Badge className="bg-green-500">Fechado</Badge>
      case 'open':
        return <Badge variant="destructive">Aberto</Badge>
      case 'half_open':
      case 'half-open':
        return <Badge variant="secondary">Half-Open</Badge>
      default:
        return <Badge variant="outline">Desconhecido</Badge>
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <div className="rounded-full bg-purple-100 p-2">
            <Activity className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <CardTitle className="text-lg">Circuit Breakers</CardTitle>
            <CardDescription>Status das integracoes</CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-3">
          {SERVICES.map((service) => {
            const state = status[service.key as keyof CircuitStatus]
            const isOpen = state === 'open'

            return (
              <div
                key={service.key}
                className="flex items-center justify-between rounded-lg bg-muted p-3"
              >
                <div>
                  <p className="font-medium">{service.label}</p>
                  <p className="text-xs text-muted-foreground">{service.description}</p>
                </div>
                <div className="flex items-center gap-2">
                  {getStatusBadge(state)}
                  {isOpen && canReset && onReset && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleReset(service.key)}
                      disabled={resetting === service.key}
                    >
                      <RefreshCcw
                        className={`h-4 w-4 ${resetting === service.key ? 'animate-spin' : ''}`}
                      />
                    </Button>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {Object.values(status).some((s) => s === 'open') && (
          <div className="mt-4 rounded bg-red-50 p-3 text-sm">
            <p className="font-medium text-red-600">Atencao!</p>
            <p className="text-muted-foreground">
              Ha circuits abertos. Algumas funcionalidades podem estar indisponiveis.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
