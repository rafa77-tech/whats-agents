'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useAuth } from '@/hooks/use-auth'
import { CampaignList } from './components/campaign-list'
import type { Campaign } from './components/campaign-card'

type StatusFilter = 'all' | 'draft' | 'scheduled' | 'running' | 'completed' | 'paused'

export default function CampanhasPage() {
  const router = useRouter()
  const { session } = useAuth()
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<{
    data: Campaign[]
    total: number
    pages: number
  } | null>(null)

  const fetchCampaigns = useCallback(async () => {
    if (!session?.access_token) return

    setLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const params = new URLSearchParams({
        page: String(page),
        per_page: '20',
      })

      if (statusFilter !== 'all') {
        params.set('status', statusFilter)
      }

      const response = await fetch(`${apiUrl}/dashboard/campaigns?${params}`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      })

      if (response.ok) {
        const result = await response.json()
        setData(result)
      }
    } catch (err) {
      console.error('Failed to fetch campaigns:', err)
    } finally {
      setLoading(false)
    }
  }, [session?.access_token, page, statusFilter])

  useEffect(() => {
    fetchCampaigns()
  }, [fetchCampaigns])

  const handleStatusChange = (value: string) => {
    setStatusFilter(value as StatusFilter)
    setPage(1)
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-4 md:p-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Campanhas</h1>
            <p className="text-muted-foreground">{data?.total || 0} campanhas</p>
          </div>
          <Button onClick={() => router.push('/campanhas/nova')}>
            <Plus className="mr-2 h-4 w-4" />
            <span className="hidden md:inline">Nova Campanha</span>
          </Button>
        </div>

        <Tabs value={statusFilter} onValueChange={handleStatusChange}>
          <TabsList className="w-full overflow-x-auto md:w-auto">
            <TabsTrigger value="all">Todas</TabsTrigger>
            <TabsTrigger value="draft">Rascunho</TabsTrigger>
            <TabsTrigger value="scheduled">Agendada</TabsTrigger>
            <TabsTrigger value="running">Em execucao</TabsTrigger>
            <TabsTrigger value="completed">Concluida</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Lista */}
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="space-y-4 p-4">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-32" />
            ))}
          </div>
        ) : (
          <CampaignList
            campaigns={data?.data || []}
            total={data?.total || 0}
            page={page}
            pages={data?.pages || 1}
            onPageChange={setPage}
          />
        )}
      </div>
    </div>
  )
}
