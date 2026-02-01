'use client'

import { useCallback, useEffect, useState } from 'react'
import { Search, Filter, MessageSquare, Smartphone, X } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area'
import { ConversationFilters } from './components/conversation-filters'
import { ChatSidebar, type ConversationItem } from './components/chat-sidebar'
import { ChatPanel } from './components/chat-panel'
import { cn } from '@/lib/utils'

interface Filters {
  status?: string | undefined
  controlled_by?: string | undefined
  search?: string | undefined
}

interface Chip {
  id: string
  telefone: string
  instance_name: string
  status: string
  trust_level: string
  conversation_count: number
}

function formatPhone(phone: string): string {
  const cleaned = phone.replace(/\D/g, '').slice(-11)
  if (cleaned.length === 11) {
    return `(${cleaned.slice(0, 2)}) ${cleaned.slice(2, 7)}-${cleaned.slice(7)}`
  }
  return phone.slice(-11)
}

export default function ConversasPage() {
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<Filters>({})
  const [search, setSearch] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedChipId, setSelectedChipId] = useState<string | null>(null)
  const [chips, setChips] = useState<Chip[]>([])
  const [data, setData] = useState<{
    data: ConversationItem[]
    total: number
    pages: number
  } | null>(null)

  // Fetch available chips
  const fetchChips = useCallback(async () => {
    try {
      const response = await fetch('/api/chips')
      if (response.ok) {
        const result = await response.json()
        setChips(result.data || [])
      }
    } catch (err) {
      console.error('Failed to fetch chips:', err)
    }
  }, [])

  useEffect(() => {
    fetchChips()
  }, [fetchChips])

  const fetchConversations = useCallback(async () => {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: '50',
      })

      if (filters.status) params.append('status', filters.status)
      if (filters.controlled_by) params.append('controlled_by', filters.controlled_by)
      if (selectedChipId) params.append('chip_id', selectedChipId)
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
  }, [page, filters, search, selectedId, selectedChipId])

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

  const handleChipSelect = (chipId: string | null) => {
    setSelectedChipId(chipId)
    setSelectedId(null)
    setPage(1)
    setLoading(true)
  }

  const handleLoadMore = () => {
    if (data && page < data.pages) {
      setPage((prev) => prev + 1)
    }
  }

  const activeFiltersCount = Object.values(filters).filter(Boolean).length
  const selectedChip = chips.find((c) => c.id === selectedChipId)
  const totalConversations = selectedChipId
    ? data?.total || 0
    : chips.reduce((sum, c) => sum + c.conversation_count, 0)

  if (loading && !data) {
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
      <div className="flex h-full w-full flex-col border-r bg-background md:w-[380px] lg:w-[420px]">
        {/* Chip Selector Header */}
        <div className="border-b bg-emerald-50 px-3 py-2 dark:bg-emerald-950/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Smartphone className="h-4 w-4 text-emerald-600" />
              <span className="text-sm font-medium text-emerald-800 dark:text-emerald-200">
                Inbox Unificada
              </span>
            </div>
            <span className="text-xs text-emerald-600 dark:text-emerald-400">
              {chips.length} chips • {totalConversations} conversas
            </span>
          </div>
        </div>

        {/* Chip Pills */}
        <ScrollArea className="w-full border-b">
          <div className="flex w-max gap-1.5 p-2">
            <button
              onClick={() => handleChipSelect(null)}
              className={cn(
                'flex flex-shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
                !selectedChipId
                  ? 'bg-emerald-600 text-white'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              )}
            >
              Todos
              <span
                className={cn(
                  'rounded-full px-1.5 py-0.5 text-[10px]',
                  !selectedChipId ? 'bg-white/20' : 'bg-background'
                )}
              >
                {chips.reduce((sum, c) => sum + c.conversation_count, 0)}
              </span>
            </button>

            {chips.map((chip) => (
              <button
                key={chip.id}
                onClick={() => handleChipSelect(chip.id)}
                className={cn(
                  'flex flex-shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
                  selectedChipId === chip.id
                    ? 'bg-emerald-600 text-white'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                )}
              >
                {chip.instance_name}
                <span
                  className={cn(
                    'rounded-full px-1.5 py-0.5 text-[10px]',
                    selectedChipId === chip.id ? 'bg-white/20' : 'bg-background'
                  )}
                >
                  {chip.conversation_count}
                </span>
              </button>
            ))}
          </div>
          <ScrollBar orientation="horizontal" />
        </ScrollArea>

        {/* Selected chip info */}
        {selectedChip && (
          <div className="flex items-center justify-between border-b bg-muted/30 px-3 py-1.5">
            <div className="flex items-center gap-2 text-xs">
              <span className="font-medium">{selectedChip.instance_name}</span>
              <span className="text-muted-foreground">{formatPhone(selectedChip.telefone)}</span>
              <span
                className={cn(
                  'rounded px-1.5 py-0.5 text-[10px] font-medium',
                  selectedChip.trust_level === 'verde'
                    ? 'bg-green-100 text-green-700'
                    : selectedChip.trust_level === 'amarelo'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-red-100 text-red-700'
                )}
              >
                {selectedChip.trust_level}
              </span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => handleChipSelect(null)}
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        )}

        {/* Search Header */}
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
        <div className="min-h-0 flex-1 overflow-y-auto">
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
              {selectedChipId && (
                <Button variant="link" size="sm" onClick={() => handleChipSelect(null)}>
                  Ver todas as conversas
                </Button>
              )}
            </div>
          )}
        </div>

        {/* Footer info */}
        <div className="border-t bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
          {data?.total || 0} conversas{selectedChip && ` em ${selectedChip.instance_name}`}
        </div>
      </div>

      {/* Right Panel - Chat */}
      <div className="hidden h-full min-h-0 flex-1 md:flex">
        {selectedId ? (
          <ChatPanel conversationId={selectedId} />
        ) : (
          <div className="flex h-full flex-1 flex-col items-center justify-center gap-4 bg-muted/10">
            <div className="rounded-full bg-muted/50 p-6">
              <MessageSquare className="h-16 w-16 text-muted-foreground/50" />
            </div>
            <div className="text-center">
              <h2 className="text-xl font-medium text-muted-foreground">Inbox Julia</h2>
              <p className="mt-1 text-sm text-muted-foreground/70">
                Selecione uma conversa para visualizar
              </p>
              {chips.length > 0 && (
                <p className="mt-2 text-xs text-muted-foreground/50">
                  {chips.length} chips conectados
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
