# E08: Gestão de Conversas

**Épico:** Lista de Conversas + Detalhes + Ações
**Estimativa:** 8h
**Prioridade:** P1 (Core)
**Dependências:** E01, E02, E04

---

## Objetivo

Implementar visualização e gestão de conversas:
- Lista paginada com filtros
- Visualização de mensagens
- Ações de handoff/return
- Busca por médico
- Status em tempo real

---

## Estrutura de Arquivos

```
app/(dashboard)/conversas/
├── page.tsx                   # Lista de conversas
├── [id]/
│   └── page.tsx               # Detalhe da conversa
├── components/
│   ├── conversation-list.tsx
│   ├── conversation-card.tsx
│   ├── conversation-filters.tsx
│   ├── conversation-detail.tsx
│   ├── message-list.tsx
│   ├── message-bubble.tsx
│   └── conversation-actions.tsx
└── hooks/
    └── use-conversations.ts
```

---

## Stories

### S08.1: Lista de Conversas

**Arquivo:** `app/(dashboard)/conversas/page.tsx`

```typescript
'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { MessageSquare, Filter } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import { api } from '@/lib/api/client'
import { ConversationList } from './components/conversation-list'
import { ConversationFilters } from './components/conversation-filters'

interface Filters {
  status?: string
  controlled_by?: string
  search?: string
}

export default function ConversasPage() {
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<Filters>({})
  const [search, setSearch] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['conversations', page, filters],
    queryFn: () => api.get('/dashboard/conversations', {
      params: {
        page,
        per_page: 20,
        ...filters,
        search: search || undefined
      }
    })
  })

  const handleSearch = (value: string) => {
    setSearch(value)
    setFilters(prev => ({ ...prev, search: value || undefined }))
    setPage(1)
  }

  const handleFilterChange = (newFilters: Filters) => {
    setFilters(prev => ({ ...prev, ...newFilters }))
    setPage(1)
    setShowFilters(false)
  }

  const activeFiltersCount = Object.values(filters).filter(Boolean).length

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 md:p-6 border-b">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold">Conversas</h1>
            <p className="text-muted-foreground">
              {data?.total || 0} conversas encontradas
            </p>
          </div>
        </div>

        {/* Search e Filters */}
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <MessageSquare className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
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
                  <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-primary text-primary-foreground text-xs flex items-center justify-center">
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
        {isLoading ? (
          <div className="p-4 space-y-4">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-20" />
            ))}
          </div>
        ) : (
          <ConversationList
            conversations={data?.data || []}
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
```

**DoD:**
- [ ] Lista responsiva
- [ ] Busca por texto
- [ ] Filtros em sheet mobile
- [ ] Paginação

---

### S08.2: Conversation Card

**Arquivo:** `app/(dashboard)/conversas/components/conversation-card.tsx`

```typescript
'use client'

import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { useRouter } from 'next/navigation'
import { User, MessageCircle, AlertTriangle, Bot, UserCheck } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'

interface Conversation {
  id: string
  cliente_nome: string
  cliente_telefone: string
  status: string
  controlled_by: string
  last_message?: string
  last_message_at?: string
  unread_count: number
}

interface Props {
  conversation: Conversation
}

export function ConversationCard({ conversation }: Props) {
  const router = useRouter()

  const getStatusBadge = () => {
    if (conversation.controlled_by === 'human') {
      return (
        <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
          <UserCheck className="h-3 w-3 mr-1" />
          Handoff
        </Badge>
      )
    }
    if (conversation.status === 'active') {
      return (
        <Badge className="bg-green-100 text-green-800">
          <Bot className="h-3 w-3 mr-1" />
          Julia
        </Badge>
      )
    }
    return (
      <Badge variant="outline">
        {conversation.status}
      </Badge>
    )
  }

  const timeAgo = conversation.last_message_at
    ? formatDistanceToNow(new Date(conversation.last_message_at), {
        addSuffix: true,
        locale: ptBR
      })
    : null

  const initials = conversation.cliente_nome
    .split(' ')
    .slice(0, 2)
    .map(n => n[0])
    .join('')
    .toUpperCase()

  return (
    <Card
      className={cn(
        'cursor-pointer hover:bg-muted/50 transition-colors',
        conversation.unread_count > 0 && 'border-l-4 border-l-blue-500'
      )}
      onClick={() => router.push(`/conversas/${conversation.id}`)}
    >
      <CardContent className="p-4">
        <div className="flex gap-3">
          <Avatar className="h-12 w-12">
            <AvatarFallback className="bg-primary/10 text-primary">
              {initials}
            </AvatarFallback>
          </Avatar>

          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="font-medium truncate">
                  {conversation.cliente_nome}
                </p>
                <p className="text-sm text-muted-foreground">
                  {conversation.cliente_telefone}
                </p>
              </div>
              <div className="flex flex-col items-end gap-1">
                {getStatusBadge()}
                {timeAgo && (
                  <span className="text-xs text-muted-foreground">
                    {timeAgo}
                  </span>
                )}
              </div>
            </div>

            {conversation.last_message && (
              <p className="text-sm text-muted-foreground mt-2 line-clamp-2">
                {conversation.last_message}
              </p>
            )}

            {conversation.unread_count > 0 && (
              <div className="flex items-center gap-1 mt-2">
                <MessageCircle className="h-3 w-3 text-blue-500" />
                <span className="text-xs text-blue-500 font-medium">
                  {conversation.unread_count} não lida{conversation.unread_count > 1 && 's'}
                </span>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
```

**DoD:**
- [ ] Avatar com iniciais
- [ ] Badge de status/controlled_by
- [ ] Preview da última mensagem
- [ ] Contador de não lidas
- [ ] Indicador visual de não lida

---

### S08.3: Detalhe da Conversa

**Arquivo:** `app/(dashboard)/conversas/[id]/page.tsx`

```typescript
'use client'

import { useQuery } from '@tanstack/react-query'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, Phone, User, MoreVertical } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { api } from '@/lib/api/client'
import { MessageList } from '../components/message-list'
import { ConversationActions } from '../components/conversation-actions'

export default function ConversationDetailPage() {
  const params = useParams()
  const router = useRouter()
  const conversationId = params.id as string

  const { data, isLoading } = useQuery({
    queryKey: ['conversation', conversationId],
    queryFn: () => api.get(`/dashboard/conversations/${conversationId}`),
    refetchInterval: 10000 // Refresh a cada 10s
  })

  if (isLoading) {
    return (
      <div className="flex flex-col h-full">
        <div className="p-4 border-b">
          <Skeleton className="h-10 w-48" />
        </div>
        <div className="flex-1 p-4 space-y-4">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
      </div>
    )
  }

  const conversation = data
  const cliente = conversation?.cliente || {}

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b bg-background sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.back()}
            className="md:hidden"
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="font-semibold truncate">
                {cliente.nome || 'Desconhecido'}
              </h1>
              {conversation?.controlled_by === 'human' && (
                <span className="px-2 py-0.5 text-xs bg-yellow-100 text-yellow-800 rounded">
                  Handoff
                </span>
              )}
            </div>
            <p className="text-sm text-muted-foreground flex items-center gap-1">
              <Phone className="h-3 w-3" />
              {cliente.telefone}
            </p>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <MoreVertical className="h-5 w-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => router.push(`/medicos/${cliente.id}`)}>
                <User className="h-4 w-4 mr-2" />
                Ver perfil do médico
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto">
        <MessageList messages={conversation?.messages || []} />
      </div>

      {/* Actions */}
      <ConversationActions
        conversationId={conversationId}
        controlledBy={conversation?.controlled_by}
      />
    </div>
  )
}
```

**DoD:**
- [ ] Header com info do médico
- [ ] Lista de mensagens scrollável
- [ ] Back button mobile
- [ ] Refresh automático

---

### S08.4: Message List e Bubble

**Arquivo:** `app/(dashboard)/conversas/components/message-list.tsx`

```typescript
'use client'

import { useEffect, useRef } from 'react'
import { MessageBubble } from './message-bubble'

interface Message {
  id: string
  tipo: 'entrada' | 'saida'
  conteudo: string
  created_at: string
  metadata?: Record<string, any>
}

interface Props {
  messages: Message[]
}

export function MessageList({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        Nenhuma mensagem ainda
      </div>
    )
  }

  // Agrupar por data
  const groupedMessages: { date: string; messages: Message[] }[] = []
  let currentDate = ''

  messages.forEach((msg) => {
    const msgDate = new Date(msg.created_at).toLocaleDateString('pt-BR')
    if (msgDate !== currentDate) {
      currentDate = msgDate
      groupedMessages.push({ date: msgDate, messages: [] })
    }
    groupedMessages[groupedMessages.length - 1].messages.push(msg)
  })

  return (
    <div className="p-4 space-y-4">
      {groupedMessages.map((group) => (
        <div key={group.date}>
          <div className="flex justify-center mb-4">
            <span className="px-3 py-1 text-xs bg-muted rounded-full">
              {group.date}
            </span>
          </div>
          <div className="space-y-2">
            {group.messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
```

**Arquivo:** `app/(dashboard)/conversas/components/message-bubble.tsx`

```typescript
'use client'

import { format } from 'date-fns'
import { Check, CheckCheck, Bot, User } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Message {
  id: string
  tipo: 'entrada' | 'saida'
  conteudo: string
  created_at: string
  metadata?: {
    model?: string
    delivered?: boolean
    read?: boolean
  }
}

interface Props {
  message: Message
}

export function MessageBubble({ message }: Props) {
  const isOutgoing = message.tipo === 'saida'
  const time = format(new Date(message.created_at), 'HH:mm')

  return (
    <div
      className={cn(
        'flex gap-2 max-w-[85%] md:max-w-[70%]',
        isOutgoing ? 'ml-auto flex-row-reverse' : 'mr-auto'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
          isOutgoing ? 'bg-primary/10' : 'bg-muted'
        )}
      >
        {isOutgoing ? (
          <Bot className="h-4 w-4 text-primary" />
        ) : (
          <User className="h-4 w-4 text-muted-foreground" />
        )}
      </div>

      {/* Bubble */}
      <div
        className={cn(
          'rounded-lg px-4 py-2',
          isOutgoing
            ? 'bg-primary text-primary-foreground rounded-tr-none'
            : 'bg-muted rounded-tl-none'
        )}
      >
        <p className="whitespace-pre-wrap break-words">{message.conteudo}</p>
        <div
          className={cn(
            'flex items-center gap-1 mt-1',
            isOutgoing ? 'justify-end' : 'justify-start'
          )}
        >
          <span className={cn(
            'text-xs',
            isOutgoing ? 'text-primary-foreground/70' : 'text-muted-foreground'
          )}>
            {time}
          </span>
          {isOutgoing && (
            message.metadata?.read ? (
              <CheckCheck className="h-3 w-3 text-blue-400" />
            ) : message.metadata?.delivered ? (
              <CheckCheck className="h-3 w-3" />
            ) : (
              <Check className="h-3 w-3" />
            )
          )}
        </div>
      </div>
    </div>
  )
}
```

**DoD:**
- [ ] Bubbles diferenciadas entrada/saída
- [ ] Agrupamento por data
- [ ] Auto-scroll para última mensagem
- [ ] Ícones de status de entrega

---

### S08.5: Conversation Actions

**Arquivo:** `app/(dashboard)/conversas/components/conversation-actions.tsx`

```typescript
'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { UserPlus, Bot, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { useToast } from '@/components/ui/use-toast'
import { api } from '@/lib/api/client'
import { useAuth } from '@/hooks/use-auth'

interface Props {
  conversationId: string
  controlledBy: string
}

export function ConversationActions({ conversationId, controlledBy }: Props) {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { hasPermission } = useAuth()

  const canControl = hasPermission('operator')
  const isHuman = controlledBy === 'human'

  const handoffMutation = useMutation({
    mutationFn: () => api.post(`/dashboard/conversations/${conversationId}/handoff`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversation', conversationId] })
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      toast({
        title: 'Handoff realizado',
        description: 'Conversa transferida para atendimento humano'
      })
    },
    onError: () => {
      toast({
        title: 'Erro',
        description: 'Não foi possível realizar o handoff',
        variant: 'destructive'
      })
    }
  })

  const returnMutation = useMutation({
    mutationFn: () => api.post(`/dashboard/conversations/${conversationId}/return-to-julia`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversation', conversationId] })
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      toast({
        title: 'Conversa retornada',
        description: 'Julia voltou a responder esta conversa'
      })
    },
    onError: () => {
      toast({
        title: 'Erro',
        description: 'Não foi possível retornar a conversa',
        variant: 'destructive'
      })
    }
  })

  if (!canControl) {
    return (
      <div className="p-4 border-t bg-muted/50 text-center text-sm text-muted-foreground">
        Visualização apenas. Você precisa de permissão de Operador para gerenciar conversas.
      </div>
    )
  }

  return (
    <div className="p-4 border-t bg-background flex gap-2">
      {isHuman ? (
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button className="flex-1" variant="default">
              <Bot className="h-4 w-4 mr-2" />
              Retornar para Julia
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Retornar para Julia?</AlertDialogTitle>
              <AlertDialogDescription>
                Julia voltará a responder automaticamente esta conversa.
                Certifique-se de que a situação foi resolvida.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction onClick={() => returnMutation.mutate()}>
                Confirmar
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      ) : (
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button className="flex-1" variant="secondary">
              <UserPlus className="h-4 w-4 mr-2" />
              Transferir para Humano
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Transferir para humano?</AlertDialogTitle>
              <AlertDialogDescription>
                Julia parará de responder e um operador deverá assumir via Chatwoot.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction onClick={() => handoffMutation.mutate()}>
                Transferir
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}

      <Button
        variant="outline"
        size="icon"
        onClick={() => queryClient.invalidateQueries({ queryKey: ['conversation', conversationId] })}
      >
        <RefreshCw className="h-4 w-4" />
      </Button>
    </div>
  )
}
```

**DoD:**
- [ ] Botão handoff com confirmação
- [ ] Botão return com confirmação
- [ ] Feedback visual do estado
- [ ] Refresh manual

---

### S08.6: Filtros de Conversas

**Arquivo:** `app/(dashboard)/conversas/components/conversation-filters.tsx`

```typescript
'use client'

import { useState } from 'react'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface Filters {
  status?: string
  controlled_by?: string
}

interface Props {
  filters: Filters
  onApply: (filters: Filters) => void
  onClear: () => void
}

export function ConversationFilters({ filters, onApply, onClear }: Props) {
  const [localFilters, setLocalFilters] = useState(filters)

  const handleApply = () => {
    onApply(localFilters)
  }

  return (
    <div className="space-y-6 py-4">
      <div className="space-y-2">
        <Label>Status</Label>
        <Select
          value={localFilters.status || 'all'}
          onValueChange={(value) =>
            setLocalFilters(prev => ({
              ...prev,
              status: value === 'all' ? undefined : value
            }))
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Todos" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="active">Ativas</SelectItem>
            <SelectItem value="closed">Fechadas</SelectItem>
            <SelectItem value="waiting">Aguardando</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Controle</Label>
        <Select
          value={localFilters.controlled_by || 'all'}
          onValueChange={(value) =>
            setLocalFilters(prev => ({
              ...prev,
              controlled_by: value === 'all' ? undefined : value
            }))
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Todos" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="julia">Julia (IA)</SelectItem>
            <SelectItem value="human">Humano (Handoff)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex gap-2 pt-4">
        <Button variant="outline" className="flex-1" onClick={onClear}>
          Limpar
        </Button>
        <Button className="flex-1" onClick={handleApply}>
          Aplicar
        </Button>
      </div>
    </div>
  )
}
```

**DoD:**
- [ ] Filtro por status
- [ ] Filtro por controlled_by
- [ ] Aplicar/limpar funcionando

---

## Checklist Final

- [ ] Lista de conversas com paginação
- [ ] Busca por nome/telefone
- [ ] Filtros status e controlled_by
- [ ] Card de conversa com preview
- [ ] Detalhe com mensagens
- [ ] Message bubbles diferenciadas
- [ ] Ações handoff/return
- [ ] Realtime updates
- [ ] Mobile responsivo
- [ ] Skeleton loading states
