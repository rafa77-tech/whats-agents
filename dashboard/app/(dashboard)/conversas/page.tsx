'use client'

import { useCallback, useEffect, useState } from 'react'
import { Search, MessageSquare, Smartphone, X } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area'
import { ChatSidebar } from './components/chat-sidebar'
import { ChatPanel } from './components/chat-panel'
import { SupervisionTabs } from './components/supervision-tabs'
import { DoctorContextPanel } from './components/doctor-context-panel'
import { NewConversationDialog } from './components/new-conversation-dialog'
import { cn, formatPhone } from '@/lib/utils'
import { useConversationList, useTabCounts } from '@/lib/conversas/hooks'
import type { SupervisionTab } from '@/types/conversas'

interface Chip {
  id: string
  telefone: string
  instance_name: string
  status: string
  trust_level: string
  conversation_count: number
}

export default function ConversasPage() {
  const [activeTab, setActiveTab] = useState<SupervisionTab>('atencao')
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedChipId, setSelectedChipId] = useState<string | null>(null)
  const [showContext, setShowContext] = useState(false)
  const [chips, setChips] = useState<Chip[]>([])
  const [chipsLoading, setChipsLoading] = useState(true)

  // SWR hooks
  const {
    conversations: data,
    isLoading: loading,
    mutate: mutateConversations,
  } = useConversationList({
    tab: activeTab,
    search: search || undefined,
    chipId: selectedChipId,
    page,
  })

  const { counts } = useTabCounts(selectedChipId)

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
    } finally {
      setChipsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchChips()
  }, [fetchChips])

  // Auto-select first conversation
  useEffect(() => {
    if (!selectedId && data?.data && data.data.length > 0) {
      const firstConversation = data.data[0]
      if (firstConversation) {
        setSelectedId(firstConversation.id)
      }
    }
  }, [selectedId, data])

  const handleSearch = (value: string) => {
    setSearch(value)
    setPage(1)
  }

  const handleTabChange = (tab: SupervisionTab) => {
    setActiveTab(tab)
    setPage(1)
    setSelectedId(null)
  }

  const handleChipSelect = (chipId: string | null) => {
    setSelectedChipId(chipId)
    setSelectedId(null)
    setPage(1)
  }

  const handleLoadMore = () => {
    if (data && page < data.pages) {
      setPage((prev) => prev + 1)
    }
  }

  const handleNewConversation = async (phone: string, doctorId?: string) => {
    try {
      const response = await fetch('/api/conversas/new', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, doctor_id: doctorId }),
      })

      if (response.ok) {
        const result = await response.json()
        await mutateConversations()
        setSelectedId(result.conversation_id)
      }
    } catch (err) {
      console.error('Failed to start conversation:', err)
    }
  }

  const selectedChip = chips.find((c) => c.id === selectedChipId)
  const totalConversations = selectedChipId
    ? data?.total || 0
    : chips.reduce((sum, c) => sum + c.conversation_count, 0)

  if (loading && !data && chipsLoading) {
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
        {/* Header */}
        <div className="flex items-center justify-between border-b bg-state-ai px-3 py-2">
          <div className="flex items-center gap-2">
            <Smartphone className="h-4 w-4 text-state-ai-muted" />
            <span className="text-xs text-state-ai-muted">
              {chips.length} chips • {totalConversations} conversas
            </span>
          </div>
          <NewConversationDialog onStart={handleNewConversation} />
        </div>

        {/* Chip Pills */}
        <ScrollArea className="w-full border-b">
          <div className="flex w-max gap-1.5 p-2">
            <button
              onClick={() => handleChipSelect(null)}
              className={cn(
                'flex flex-shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
                !selectedChipId
                  ? 'bg-state-ai-button text-white'
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
                    ? 'bg-state-ai-button text-white'
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
                    ? 'bg-success-light text-success-dark'
                    : selectedChip.trust_level === 'amarelo'
                      ? 'bg-warning-light text-warning-dark'
                      : 'bg-destructive/10 text-destructive'
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

        {/* Supervision Tabs */}
        <SupervisionTabs
          activeTab={activeTab}
          counts={counts || { atencao: 0, julia_ativa: 0, aguardando: 0, encerradas: 0 }}
          onTabChange={handleTabChange}
        />

        {/* Search */}
        <div className="border-b bg-muted/30 p-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Pesquisar conversa..."
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
              className="h-9 bg-background pl-9"
            />
          </div>
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

      {/* Center Panel - Chat */}
      <div className="hidden h-full min-h-0 flex-1 md:flex">
        {selectedId ? (
          <ChatPanel
            conversationId={selectedId}
            onControlChange={() => mutateConversations()}
            showContextPanel={showContext}
            onToggleContext={() => setShowContext((prev) => !prev)}
          />
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

      {/* Right Panel - Doctor Context (collapsible) */}
      {showContext && selectedId && (
        <div className="hidden h-full w-[340px] border-l xl:block">
          <DoctorContextPanel
            conversationId={selectedId}
            onClose={() => setShowContext(false)}
          />
        </div>
      )}
    </div>
  )
}
