'use client'

import { useCallback, useEffect, useState } from 'react'
import { Search, Filter, MessageSquare } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { ConversationFilters } from './components/conversation-filters'
import { ChatSidebar, type ConversationItem } from './components/chat-sidebar'
import { ChatPanel } from './components/chat-panel'

interface Filters {
  status?: string | undefined
  controlled_by?: string | undefined
  search?: string | undefined
}

export default function ConversasPage() {
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<Filters>({})
  const [search, setSearch] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [data, setData] = useState<{
    data: ConversationItem[]
    total: number
    pages: number
  } | null>(null)

  const fetchConversations = useCallback(async () => {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: '50',
      })

      if (filters.status) params.append('status', filters.status)
      if (filters.controlled_by) params.append('controlled_by', filters.controlled_by)
      if (search) params.append('search', search)

      const response = await fetch(`/api/conversas?${params}`)

      if (response.ok) {
        const result = await response.json()
        setData(result)

        // Auto-select first conversation if none selected
        if (!selectedId && result.data?.length > 0) {
          setSelectedId(result.data[0].id)
        }
      }
    } catch (err) {
      console.error('Failed to fetch conversations:', err)
    } finally {
      setLoading(false)
    }
  }, [page, filters, search, selectedId])

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

  const handleLoadMore = () => {
    if (data && page < data.pages) {
      setPage((prev) => prev + 1)
    }
  }

  const activeFiltersCount = Object.values(filters).filter(Boolean).length

  if (loading) {
    return (
      <div className="flex h-full">
        <div className="w-[400px] border-r">
          <div className="p-3">
            <Skeleton className="h-10 w-full" />
          </div>
          <div className="space-y-1 p-2">
            {[...Array(8)].map((_, i) => (
              <Skeleton key={i} className="h-[72px]" />
            ))}
          </div>
        </div>
        <div className="flex-1">
          <Skeleton className="h-full" />
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left Sidebar - Conversation List */}
      <div className="flex w-full flex-col border-r bg-background md:w-[380px] lg:w-[420px]">
        {/* Header */}
        <div className="flex items-center gap-2 border-b bg-muted/30 p-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Pesquisar conversa..."
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
              className="h-9 bg-background pl-9"
            />
          </div>

          <Sheet open={showFilters} onOpenChange={setShowFilters}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="relative h-9 w-9">
                <Filter className="h-4 w-4" />
                {activeFiltersCount > 0 && (
                  <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] text-primary-foreground">
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

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto">
          {data?.data && data.data.length > 0 ? (
            <ChatSidebar
              conversations={data.data}
              selectedId={selectedId}
              onSelect={setSelectedId}
              hasMore={page < (data?.pages || 1)}
              onLoadMore={handleLoadMore}
            />
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
              <MessageSquare className="h-12 w-12 opacity-20" />
              <p>Nenhuma conversa encontrada</p>
            </div>
          )}
        </div>

        {/* Footer info */}
        <div className="border-t bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
          {data?.total || 0} conversas
        </div>
      </div>

      {/* Right Panel - Chat */}
      <div className="hidden flex-1 md:flex">
        {selectedId ? (
          <ChatPanel conversationId={selectedId} onRefresh={fetchConversations} />
        ) : (
          <div className="flex h-full flex-1 flex-col items-center justify-center gap-4 bg-muted/10">
            <div className="rounded-full bg-muted/50 p-6">
              <MessageSquare className="h-16 w-16 text-muted-foreground/50" />
            </div>
            <div className="text-center">
              <h2 className="text-xl font-medium text-muted-foreground">Julia Dashboard</h2>
              <p className="mt-1 text-sm text-muted-foreground/70">
                Selecione uma conversa para visualizar
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
