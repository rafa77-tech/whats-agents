'use client'

import { useCallback, useEffect, useState } from 'react'
import { Flag, Search } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/hooks/use-auth'

interface FeatureFlag {
  id: string
  name: string
  description: string
  enabled: boolean
  category: string
  updated_at: string
  updated_by?: string
}

function FlagsPageSkeleton() {
  return (
    <div className="space-y-6 p-6">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-10 w-64" />
      <Skeleton className="h-64 w-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  )
}

export default function FeatureFlagsPage() {
  const { session, user } = useAuth()
  const [flags, setFlags] = useState<FeatureFlag[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [updating, setUpdating] = useState<string | null>(null)

  const canEdit = user?.role && ['manager', 'admin'].includes(user.role)

  const fetchFlags = useCallback(async () => {
    if (!session?.access_token) return

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/dashboard/controls/flags`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      })

      if (response.ok) {
        const result = await response.json()
        setFlags(result.flags || [])
      }
    } catch (err) {
      console.error('Failed to fetch flags:', err)
    } finally {
      setLoading(false)
    }
  }, [session?.access_token])

  useEffect(() => {
    fetchFlags()
  }, [fetchFlags])

  const handleToggle = async (name: string, enabled: boolean) => {
    if (!session?.access_token) return

    setUpdating(name)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      await fetch(`${apiUrl}/dashboard/controls/flags/${name}`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ enabled }),
      })

      await fetchFlags()
    } finally {
      setUpdating(null)
    }
  }

  if (loading) {
    return <FlagsPageSkeleton />
  }

  const filteredFlags = flags.filter(
    (f) =>
      f.name.toLowerCase().includes(search.toLowerCase()) ||
      f.description.toLowerCase().includes(search.toLowerCase())
  )

  // Agrupar por categoria
  const groupedFlags = filteredFlags.reduce(
    (acc, flag) => {
      const cat = flag.category || 'Geral'
      if (!acc[cat]) acc[cat] = []
      acc[cat].push(flag)
      return acc
    },
    {} as Record<string, FeatureFlag[]>
  )

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Feature Flags</h1>
        <p className="text-muted-foreground">Controle funcionalidades do sistema</p>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Buscar flags..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Grouped flags */}
      {Object.entries(groupedFlags).map(([category, categoryFlags]) => (
        <Card key={category}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Flag className="h-4 w-4" />
              {category}
            </CardTitle>
            <CardDescription>
              {categoryFlags.length} flag{categoryFlags.length !== 1 && 's'}
            </CardDescription>
          </CardHeader>

          <CardContent>
            <div className="space-y-4">
              {categoryFlags.map((flag) => (
                <div
                  key={flag.id}
                  className="flex items-center justify-between rounded-lg bg-muted p-4"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-mono text-sm font-medium">{flag.name}</p>
                      <Badge variant={flag.enabled ? 'default' : 'secondary'}>
                        {flag.enabled ? 'ON' : 'OFF'}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">{flag.description}</p>
                    {flag.updated_by && (
                      <p className="mt-2 text-xs text-muted-foreground">
                        Atualizado por {flag.updated_by}
                      </p>
                    )}
                  </div>

                  <Switch
                    checked={flag.enabled}
                    onCheckedChange={(enabled) => handleToggle(flag.name, enabled)}
                    disabled={!canEdit || updating === flag.name}
                  />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}

      {filteredFlags.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            {flags.length === 0 ? 'Nenhuma feature flag configurada' : 'Nenhuma flag encontrada'}
          </CardContent>
        </Card>
      )}

      {!canEdit && (
        <p className="text-center text-sm text-muted-foreground">
          Voce precisa de permissao de Manager para editar flags
        </p>
      )}
    </div>
  )
}
