'use client'

import { useCallback, useEffect, useState } from 'react'
import { Shield, Filter, Download } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { useAuth } from '@/hooks/use-auth'
import { AuditList } from './components/audit-list'
import { AuditFilters } from './components/audit-filters'

interface Filters {
  action?: string | undefined
  actor_email?: string | undefined
  from_date?: string | undefined
  to_date?: string | undefined
}

interface AuditLog {
  id: string
  action: string
  actor_email: string
  actor_role: string
  details: Record<string, unknown>
  created_at: string
}

interface AuditResponse {
  data: AuditLog[]
  total: number
  page: number
  per_page: number
  pages: number
}

export default function AuditoriaPage() {
  const { session, hasPermission } = useAuth()
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<Filters>({})
  const [showFilters, setShowFilters] = useState(false)
  const [searchInput, setSearchInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<AuditResponse | null>(null)

  const fetchLogs = useCallback(async () => {
    if (!session?.access_token) return

    setLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const params = new URLSearchParams({
        page: String(page),
        per_page: '50',
      })

      if (filters.action) params.set('action', filters.action)
      if (filters.actor_email) params.set('actor_email', filters.actor_email)
      if (filters.from_date) params.set('from_date', filters.from_date)
      if (filters.to_date) params.set('to_date', filters.to_date)

      const response = await fetch(`${apiUrl}/dashboard/audit?${params}`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      })

      if (response.ok) {
        const result: AuditResponse = await response.json()
        setData(result)
      }
    } catch (err) {
      console.error('Failed to fetch audit logs:', err)
    } finally {
      setLoading(false)
    }
  }, [session?.access_token, page, filters])

  useEffect(() => {
    fetchLogs()
  }, [fetchLogs])

  const handleSearch = (value: string) => {
    setSearchInput(value)
    setFilters((prev) => ({
      ...prev,
      actor_email: value || undefined,
    }))
    setPage(1)
  }

  const handleExport = async () => {
    if (!session?.access_token) return

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const params = new URLSearchParams()
      if (filters.action) params.set('action', filters.action)
      if (filters.actor_email) params.set('actor_email', filters.actor_email)
      if (filters.from_date) params.set('from_date', filters.from_date)
      if (filters.to_date) params.set('to_date', filters.to_date)

      const response = await fetch(`${apiUrl}/dashboard/audit/export?${params}`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      })

      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.setAttribute('download', `audit_logs_${new Date().toISOString().split('T')[0]}.csv`)
        document.body.appendChild(link)
        link.click()
        link.remove()
        window.URL.revokeObjectURL(url)
      }
    } catch (err) {
      console.error('Failed to export audit logs:', err)
    }
  }

  const handleApplyFilters = (newFilters: Filters) => {
    setFilters(newFilters)
    setShowFilters(false)
    setPage(1)
  }

  const handleClearFilters = () => {
    setFilters({})
    setSearchInput('')
    setShowFilters(false)
    setPage(1)
  }

  // Check permission
  if (!hasPermission('manager')) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-muted-foreground">Acesso restrito a gestores</p>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-4 md:p-6">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="h-6 w-6 text-primary" />
            <div>
              <h1 className="text-2xl font-bold">Auditoria</h1>
              <p className="text-muted-foreground">Historico de acoes no sistema</p>
            </div>
          </div>
          <Button variant="outline" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            <span className="hidden md:inline">Exportar</span>
          </Button>
        </div>

        <div className="flex gap-2">
          <Input
            placeholder="Buscar por email..."
            className="flex-1"
            value={searchInput}
            onChange={(e) => handleSearch(e.target.value)}
          />

          <Sheet open={showFilters} onOpenChange={setShowFilters}>
            <SheetTrigger asChild>
              <Button variant="outline">
                <Filter className="h-4 w-4" />
              </Button>
            </SheetTrigger>
            <SheetContent>
              <SheetHeader>
                <SheetTitle>Filtros</SheetTitle>
              </SheetHeader>
              <AuditFilters
                filters={filters}
                onApply={handleApplyFilters}
                onClear={handleClearFilters}
              />
            </SheetContent>
          </Sheet>
        </div>
      </div>

      {/* Lista */}
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="space-y-2 p-4">
            {[...Array(10)].map((_, i) => (
              <Skeleton key={i} className="h-16" />
            ))}
          </div>
        ) : (
          <AuditList
            logs={data?.data ?? []}
            total={data?.total ?? 0}
            page={page}
            pages={data?.pages ?? 1}
            onPageChange={setPage}
          />
        )}
      </div>
    </div>
  )
}
