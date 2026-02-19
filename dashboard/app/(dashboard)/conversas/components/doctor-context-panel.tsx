'use client'

import { useEffect, useState } from 'react'
import { formatDistanceToNow, format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import {
  User,
  Brain,
  BarChart3,
  AlertTriangle,
  Activity,
  StickyNote,
  ChevronDown,
  ChevronRight,
  MapPin,
  Phone,
  Stethoscope,
  Shield,
  X,
  Bot,
  FileText,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { STAGE_COLORS } from '@/lib/conversas/constants'
import { useDoctorContext } from '@/lib/conversas/hooks'
import { SupervisorChannel } from './supervisor-channel'
import type { DoctorContextData, DoctorMemoryItem, SupervisorNote } from '@/types/conversas'

interface Props {
  conversationId: string
  onClose?: () => void
}

// ============================================
// Collapsible Section
// ============================================

interface SectionProps {
  title: string
  icon: React.ReactNode
  defaultOpen?: boolean
  badge?: string | number
  children: React.ReactNode
}

function CollapsibleSection({ title, icon, defaultOpen = false, badge, children }: SectionProps) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="border-b last:border-b-0">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium hover:bg-muted/50"
      >
        <div className="flex items-center gap-2">
          {icon}
          {title}
          {badge !== undefined && (
            <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
              {badge}
            </span>
          )}
        </div>
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </button>
      {open && <div className="px-3 pb-3">{children}</div>}
    </div>
  )
}

// ============================================
// Profile Section
// ============================================

function ProfileSection({ context }: { context: DoctorContextData }) {
  const { doctor } = context
  const stageColor = doctor.stage_jornada
    ? STAGE_COLORS[doctor.stage_jornada] || 'bg-gray-100 text-gray-600'
    : ''

  return (
    <div className="space-y-3">
      {/* Name + Stage */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold">{doctor.nome}</span>
        {doctor.stage_jornada && (
          <span className={cn('rounded px-1.5 py-0.5 text-[10px] font-medium', stageColor)}>
            {doctor.stage_jornada}
          </span>
        )}
      </div>

      {/* Details grid */}
      <div className="space-y-1.5 text-xs">
        {doctor.telefone && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Phone className="h-3 w-3" />
            {doctor.telefone}
          </div>
        )}
        {doctor.crm && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Shield className="h-3 w-3" />
            CRM {doctor.crm}
          </div>
        )}
        {doctor.especialidade && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Stethoscope className="h-3 w-3" />
            {doctor.especialidade}
          </div>
        )}
        {(doctor.cidade || doctor.estado) && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <MapPin className="h-3 w-3" />
            {[doctor.cidade, doctor.estado].filter(Boolean).join(', ')}
          </div>
        )}
      </div>

      {/* Pressure + OptOut + Conversations */}
      <div className="flex flex-wrap gap-2">
        {doctor.pressure_score !== undefined && (
          <span
            className={cn(
              'rounded px-1.5 py-0.5 text-[10px] font-medium',
              doctor.pressure_score > 7
                ? 'bg-destructive/10 text-destructive'
                : doctor.pressure_score > 4
                  ? 'bg-status-warning text-status-warning-foreground'
                  : 'bg-status-success text-status-success-foreground'
            )}
          >
            Pressao: {doctor.pressure_score}/10
          </span>
        )}
        {doctor.opt_out && (
          <span className="rounded bg-destructive/10 px-1.5 py-0.5 text-[10px] font-medium text-destructive">
            OPT-OUT
          </span>
        )}
        <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
          {context.conversation_count} conversa{context.conversation_count !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Tags */}
      {doctor.tags && doctor.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {doctor.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

// ============================================
// Memory Section
// ============================================

function MemorySection({ memory }: { memory: DoctorMemoryItem[] }) {
  if (memory.length === 0) {
    return <p className="text-xs text-muted-foreground">Nenhuma memoria registrada</p>
  }

  // Group by tipo
  const grouped = memory.reduce<Record<string, DoctorMemoryItem[]>>((acc, item) => {
    const key = item.tipo || 'geral'
    if (!acc[key]) acc[key] = []
    acc[key]?.push(item)
    return acc
  }, {})

  return (
    <div className="space-y-2">
      {Object.entries(grouped).map(([tipo, items]) => (
        <div key={tipo}>
          <span className="text-[10px] font-medium uppercase text-muted-foreground">{tipo}</span>
          <div className="mt-1 space-y-1">
            {items.map((item, i) => (
              <div key={i} className="rounded bg-muted/50 px-2 py-1.5 text-xs">
                {item.content}
                <span className="ml-2 text-[10px] text-muted-foreground">
                  {formatDistanceToNow(new Date(item.created_at), {
                    addSuffix: true,
                    locale: ptBR,
                  })}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

// ============================================
// Metrics Section
// ============================================

function MetricsSection({ context }: { context: DoctorContextData }) {
  const { metrics } = context

  return (
    <div className="grid grid-cols-2 gap-2">
      <div className="rounded-lg bg-muted/50 p-2 text-center">
        <div className="text-lg font-semibold">{metrics.total_msg_medico}</div>
        <div className="text-[10px] text-muted-foreground">Msgs medico</div>
      </div>
      <div className="rounded-lg bg-muted/50 p-2 text-center">
        <div className="text-lg font-semibold">{metrics.total_msg_julia}</div>
        <div className="text-[10px] text-muted-foreground">Msgs Julia</div>
      </div>
      <div className="rounded-lg bg-muted/50 p-2 text-center">
        <div className="text-lg font-semibold">
          {metrics.tempo_medio_resposta > 0
            ? `${Math.round(metrics.tempo_medio_resposta / 60)}min`
            : '-'}
        </div>
        <div className="text-[10px] text-muted-foreground">Tempo medio</div>
      </div>
      <div className="rounded-lg bg-muted/50 p-2 text-center">
        <div className="text-lg font-semibold">
          {metrics.duracao_minutos > 0 ? `${Math.round(metrics.duracao_minutos)}min` : '-'}
        </div>
        <div className="text-[10px] text-muted-foreground">Duracao</div>
      </div>
    </div>
  )
}

// ============================================
// Handoff Timeline
// ============================================

function HandoffTimeline({ context }: { context: DoctorContextData }) {
  const { handoff_history } = context

  if (handoff_history.length === 0) {
    return <p className="text-xs text-muted-foreground">Nenhum handoff registrado</p>
  }

  return (
    <div className="space-y-2">
      {handoff_history.map((h, i) => (
        <div key={i} className="flex gap-2">
          <div className="mt-1 flex flex-col items-center">
            <div
              className={cn(
                'h-2 w-2 rounded-full',
                h.status === 'pendente' ? 'bg-status-warning-solid' : 'bg-status-success-solid'
              )}
            />
            {i < handoff_history.length - 1 && <div className="mt-1 h-full w-px bg-border" />}
          </div>
          <div className="flex-1 pb-2">
            <div className="flex items-center gap-2 text-xs">
              <span className="font-medium">{h.motivo || 'Sem motivo'}</span>
              <span
                className={cn(
                  'rounded px-1 py-0.5 text-[10px]',
                  h.status === 'pendente'
                    ? 'bg-status-warning text-status-warning-foreground'
                    : 'bg-muted text-muted-foreground'
                )}
              >
                {h.status}
              </span>
            </div>
            {h.trigger_type && (
              <div className="text-[10px] text-muted-foreground">Trigger: {h.trigger_type}</div>
            )}
            {h.notas && (
              <div className="mt-0.5 text-[10px] italic text-muted-foreground">{h.notas}</div>
            )}
            <div className="text-[10px] text-muted-foreground">
              {h.created_at ? format(new Date(h.created_at), 'dd/MM HH:mm', { locale: ptBR }) : ''}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

// ============================================
// Events Timeline
// ============================================

function EventsTimeline({ context }: { context: DoctorContextData }) {
  const { recent_events } = context

  if (recent_events.length === 0) {
    return <p className="text-xs text-muted-foreground">Nenhum evento registrado</p>
  }

  return (
    <div className="space-y-1">
      {recent_events.map((e, i) => (
        <div key={i} className="flex items-start justify-between rounded bg-muted/30 px-2 py-1.5">
          <div>
            <span className="text-xs font-medium">{e.event_type.replace(/_/g, ' ')}</span>
          </div>
          <span className="flex-shrink-0 text-[10px] text-muted-foreground">
            {e.ts ? formatDistanceToNow(new Date(e.ts), { addSuffix: true, locale: ptBR }) : ''}
          </span>
        </div>
      ))}
    </div>
  )
}

// ============================================
// Notes Section
// ============================================

function NotesSection({ conversationId }: { conversationId: string }) {
  const [notes, setNotes] = useState<SupervisorNote[]>([])
  const [newNote, setNewNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [loaded, setLoaded] = useState(false)

  // Load notes when conversationId changes
  useEffect(() => {
    let cancelled = false
    setLoaded(false)
    setNotes([])

    fetch(`/api/conversas/${conversationId}/notes`)
      .then((r) => r.json())
      .then((data) => {
        if (!cancelled && data.notes) setNotes(data.notes as SupervisorNote[])
        if (!cancelled) setLoaded(true)
      })
      .catch(() => {
        if (!cancelled) setLoaded(true)
      })

    return () => {
      cancelled = true
    }
  }, [conversationId])

  const handleAddNote = async (): Promise<void> => {
    if (!newNote.trim()) return
    setSaving(true)
    try {
      const response = await fetch(`/api/conversas/${conversationId}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: newNote.trim() }),
      })
      if (response.ok) {
        const result = await response.json()
        if (result.note) {
          setNotes((prev) => [result.note as SupervisorNote, ...prev])
        }
        setNewNote('')
      }
    } catch (err) {
      console.error('Failed to add note:', err)
    } finally {
      setSaving(false)
    }
  }

  if (!loaded) {
    return <Skeleton className="h-16" />
  }

  return (
    <div className="space-y-2">
      {/* Add note */}
      <div className="flex gap-1">
        <input
          type="text"
          value={newNote}
          onChange={(e) => setNewNote(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') void handleAddNote()
          }}
          placeholder="Adicionar nota..."
          className="flex-1 rounded border bg-background px-2 py-1 text-xs"
          disabled={saving}
        />
        <Button
          size="sm"
          variant="outline"
          className="h-7 px-2 text-xs"
          onClick={() => void handleAddNote()}
          disabled={saving || !newNote.trim()}
        >
          +
        </Button>
      </div>

      {/* Existing notes */}
      {notes.length === 0 ? (
        <p className="text-xs text-muted-foreground">Nenhuma nota</p>
      ) : (
        <div className="space-y-1">
          {notes.map((note) => (
            <div key={note.id} className="rounded bg-status-warning/20 px-2 py-1.5 text-xs">
              {note.content}
              <div className="mt-0.5 text-[10px] text-muted-foreground">
                {note.created_at
                  ? formatDistanceToNow(new Date(note.created_at), {
                      addSuffix: true,
                      locale: ptBR,
                    })
                  : ''}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ============================================
// Main Component
// ============================================

type PanelTab = 'contexto' | 'julia'

export function DoctorContextPanel({ conversationId, onClose }: Props) {
  const [activeTab, setActiveTab] = useState<PanelTab>('contexto')
  const { context, isLoading } = useDoctorContext(conversationId)

  if (isLoading) {
    return (
      <div className="flex h-full w-[340px] flex-col border-l bg-background">
        <div className="border-b p-3">
          <Skeleton className="h-5 w-32" />
        </div>
        <div className="space-y-3 p-3">
          <Skeleton className="h-20" />
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full w-[340px] flex-col border-l bg-background">
      {/* Header with tabs */}
      <div className="flex items-center justify-between border-b px-3 py-2">
        <div className="flex gap-1">
          <button
            onClick={() => setActiveTab('contexto')}
            className={cn(
              'flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition-colors',
              activeTab === 'contexto'
                ? 'bg-muted text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <FileText className="h-3 w-3" />
            Contexto
          </button>
          <button
            onClick={() => setActiveTab('julia')}
            className={cn(
              'flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition-colors',
              activeTab === 'julia'
                ? 'bg-primary/10 text-primary'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <Bot className="h-3 w-3" />
            Julia
          </button>
        </div>
        {onClose && (
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onClose}>
            <X className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>

      {/* Tab Content */}
      {activeTab === 'julia' ? (
        <SupervisorChannel conversationId={conversationId} />
      ) : !context ? (
        <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
          Contexto nao disponivel
        </div>
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto">
          <CollapsibleSection title="Perfil" icon={<User className="h-3.5 w-3.5" />} defaultOpen>
            <ProfileSection context={context} />
          </CollapsibleSection>

          <CollapsibleSection
            title="Notas"
            icon={<StickyNote className="h-3.5 w-3.5" />}
            defaultOpen
          >
            <NotesSection conversationId={conversationId} />
          </CollapsibleSection>

          <CollapsibleSection
            title="Handoffs"
            icon={<AlertTriangle className="h-3.5 w-3.5" />}
            badge={context.handoff_history.length}
            defaultOpen={context.handoff_history.some((h) => h.status === 'pendente')}
          >
            <HandoffTimeline context={context} />
          </CollapsibleSection>

          <CollapsibleSection
            title="Memoria Julia"
            icon={<Brain className="h-3.5 w-3.5" />}
            badge={context.memory.length}
          >
            <MemorySection memory={context.memory} />
          </CollapsibleSection>

          <CollapsibleSection title="Metricas" icon={<BarChart3 className="h-3.5 w-3.5" />}>
            <MetricsSection context={context} />
          </CollapsibleSection>

          <CollapsibleSection
            title="Eventos"
            icon={<Activity className="h-3.5 w-3.5" />}
            badge={context.recent_events.length}
          >
            <EventsTimeline context={context} />
          </CollapsibleSection>
        </div>
      )}
    </div>
  )
}
