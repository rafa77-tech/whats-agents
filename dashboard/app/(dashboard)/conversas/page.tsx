'use client'

import { useCallback, useEffect, useState } from 'react'
import { MessageSquare, Filter } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { ConversationList } from './components/conversation-list'
import { ConversationFilters } from './components/conversation-filters'
import type { Conversation } from './components/conversation-card'

interface Filters {
  status?: string | undefined
  controlled_by?: string | undefined
  search?: string | undefined
}

function ConversasPageSkeleton() {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b p-4 md:p-6">
        <Skeleton className="mb-4 h-8 w-48" />
        <Skeleton className="h-10 w-full max-w-md" />
      </div>
      <div className="space-y-4 p-4">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
    </div>
  )
}

export default function ConversasPage() {
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<Filters>({})
  const [search, setSearch] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<{
    data: Conversation[]
    total: number
    pages: number
  } | null>(null)

  const fetchConversations = useCallback(async () => {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: '20',
      })

      if (filters.status) params.append('status', filters.status)
      if (filters.controlled_by) params.append('controlled_by', filters.controlled_by)
      if (search) params.append('search', search)

      const response = await fetch(`/api/conversas?${params}`)

      if (response.ok) {
        const result = await response.json()
        setData(result)
      }
    } catch (err) {
      console.error('Failed to fetch conversations:', err)
    } finally {
      setLoading(false)
    }
  }, [page, filters, search])

  useEffect(() => {
    fetchConversations()
  }, [fetchConversations])

  const handleSearch = (value: string) => {
    setSearch(value)
    setPage(1)
  }

  const handleFilterChange = (newFilters: Filters) => {
    setFilters((prev) => ({ ...prev, ...newFilters }))
    setPage(1)
    setShowFilters(false)
  }

  const activeFiltersCount = Object.values(filters).filter(Boolean).length

  if (loading) {
    return <ConversasPageSkeleton />
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-4 md:p-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Conversas</h1>
            <p className="text-muted-foreground">{data?.total || 0} conversas encontradas</p>
          </div>
        </div>

        {/* Search e Filters */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <MessageSquare className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Buscar por nome ou telefone..."
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-10"
            />
          </div>

          {/* Mobile: Sheet para filtros */}
          <Sheet open={showFilters} onOpenChange={setShowFilters}>
            <SheetTrigger asChild>
              <Button variant="outline" className="relative">
                <Filter className="h-4 w-4 md:mr-2" />
                <span className="hidden md:inline">Filtros</span>
                {activeFiltersCount > 0 && (
                  <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-xs text-primary-foreground">
                    {activeFiltersCount}
                  </span>
                )}
              </Button>
            </SheetTrigger>
            <SheetContent>
              <SheetHeader>
                <SheetTitle>Filtros</SheetTitle>
              </SheetHeader>
              <ConversationFilters
                filters={filters}
                onApply={handleFilterChange}
                onClear={() => {
                  setFilters({})
                  setShowFilters(false)
                }}
              />
            </SheetContent>
          </Sheet>
        </div>
      </div>

      {/* Lista */}
      <div className="flex-1 overflow-auto">
        <ConversationList
          conversations={data?.data || []}
          total={data?.total || 0}
          page={page}
          pages={data?.pages || 1}
          onPageChange={setPage}
        />
      </div>
    </div>
  )
}
