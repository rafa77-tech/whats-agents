/**
 * CommandPalette - Sprint 45
 *
 * Busca global com navegacao rapida, acoes e recentes.
 * Abre com Cmd+K (Mac) ou Ctrl+K (Windows/Linux).
 */

'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Command } from 'cmdk'
import {
  LayoutDashboard,
  MessageSquare,
  Megaphone,
  Briefcase,
  Stethoscope,
  Building2,
  Smartphone,
  Users,
  Activity,
  HeartPulse,
  ShieldCheck,
  BarChart3,
  Star,
  ClipboardList,
  FileText,
  Settings,
  HelpCircle,
  Plus,
  RefreshCw,
  Search,
  Clock,
  ArrowRight,
  CloudCog,
  type LucideIcon,
} from 'lucide-react'
import type { Route } from 'next'

interface PageItem {
  id: string
  label: string
  icon: LucideIcon
  href: string
  keywords?: string[]
  description?: string
}

// Todas as paginas disponiveis
const pages: PageItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: LayoutDashboard,
    href: '/dashboard',
    keywords: ['home', 'inicio', 'principal'],
    description: 'Visao geral e KPIs',
  },
  {
    id: 'conversas',
    label: 'Conversas',
    icon: MessageSquare,
    href: '/conversas',
    keywords: ['chat', 'mensagens', 'whatsapp', 'medico'],
    description: 'Chat com medicos',
  },
  {
    id: 'campanhas',
    label: 'Campanhas',
    icon: Megaphone,
    href: '/campanhas',
    keywords: ['campanha', 'disparo', 'envio', 'marketing'],
    description: 'Gestao de campanhas',
  },
  {
    id: 'vagas',
    label: 'Vagas',
    icon: Briefcase,
    href: '/vagas',
    keywords: ['plantao', 'plantoes', 'escala', 'trabalho'],
    description: 'Plantoes disponiveis',
  },
  {
    id: 'medicos',
    label: 'Medicos',
    icon: Stethoscope,
    href: '/medicos',
    keywords: ['doutor', 'dr', 'profissional', 'contato'],
    description: 'Banco de medicos',
  },
  {
    id: 'hospitais',
    label: 'Hospitais',
    icon: Building2,
    href: '/hospitais',
    keywords: ['hospital', 'bloqueado', 'instituicao'],
    description: 'Hospitais bloqueados',
  },
  {
    id: 'chips',
    label: 'Chips',
    icon: Smartphone,
    href: '/chips',
    keywords: ['whatsapp', 'numero', 'telefone', 'pool'],
    description: 'Pool de chips WhatsApp',
  },
  {
    id: 'grupos',
    label: 'Grupos',
    icon: Users,
    href: '/chips/grupos',
    keywords: ['grupo', 'whatsapp', 'comunidade'],
    description: 'Grupos WhatsApp',
  },
  {
    id: 'meta',
    label: 'Meta',
    icon: CloudCog,
    href: '/meta',
    keywords: ['meta', 'cloud', 'api', 'template', 'qualidade', 'custo', 'flow'],
    description: 'Meta WhatsApp Cloud API',
  },
  {
    id: 'monitor',
    label: 'Monitor',
    icon: Activity,
    href: '/monitor',
    keywords: ['jobs', 'tarefas', 'background', 'fila'],
    description: 'Jobs em background',
  },
  {
    id: 'health',
    label: 'Health Center',
    icon: HeartPulse,
    href: '/health',
    keywords: ['saude', 'status', 'sistema', 'circuit'],
    description: 'Saude do sistema',
  },
  {
    id: 'integridade',
    label: 'Integridade',
    icon: ShieldCheck,
    href: '/integridade',
    keywords: ['anomalia', 'dados', 'qualidade', 'erro'],
    description: 'Anomalias e KPIs',
  },
  {
    id: 'metricas',
    label: 'Metricas',
    icon: BarChart3,
    href: '/metricas',
    keywords: ['analytics', 'graficos', 'relatorio', 'dados'],
    description: 'Analytics detalhado',
  },
  {
    id: 'qualidade',
    label: 'Avaliacoes',
    icon: Star,
    href: '/qualidade',
    keywords: ['qualidade', 'review', 'nota', 'feedback'],
    description: 'Avaliacoes de conversas',
  },
  {
    id: 'auditoria',
    label: 'Auditoria',
    icon: ClipboardList,
    href: '/auditoria',
    keywords: ['logs', 'historico', 'registro', 'trilha'],
    description: 'Logs de auditoria',
  },
  {
    id: 'instrucoes',
    label: 'Instrucoes',
    icon: FileText,
    href: '/instrucoes',
    keywords: ['diretrizes', 'regras', 'prompt', 'config'],
    description: 'Diretrizes da Julia',
  },
  {
    id: 'sistema',
    label: 'Sistema',
    icon: Settings,
    href: '/sistema',
    keywords: ['config', 'configuracao', 'opcoes', 'preferencias'],
    description: 'Configuracoes gerais',
  },
  {
    id: 'ajuda',
    label: 'Ajuda',
    icon: HelpCircle,
    href: '/ajuda',
    keywords: ['help', 'suporte', 'duvida', 'faq'],
    description: 'Ajuda e suporte',
  },
]

interface ActionItem {
  id: string
  label: string
  icon: LucideIcon
  action: () => void
  keywords?: string[]
}

interface CommandPaletteProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const router = useRouter()
  const [search, setSearch] = useState('')
  const [recentPages, setRecentPages] = useState<string[]>([])

  // Carregar recentes do localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('jullia-recent-pages')
      if (stored) {
        try {
          setRecentPages(JSON.parse(stored))
        } catch {
          // Ignora erro de parse
        }
      }
    }
  }, [open])

  // Salvar pagina nos recentes
  const saveToRecent = useCallback((pageId: string) => {
    setRecentPages((prev) => {
      const filtered = prev.filter((id) => id !== pageId)
      const updated = [pageId, ...filtered].slice(0, 5)
      if (typeof window !== 'undefined') {
        localStorage.setItem('jullia-recent-pages', JSON.stringify(updated))
      }
      return updated
    })
  }, [])

  // Executar comando e fechar
  const runCommand = useCallback(
    (command: () => void) => {
      onOpenChange(false)
      command()
    },
    [onOpenChange]
  )

  // Navegar para pagina
  const navigateTo = useCallback(
    (page: PageItem) => {
      saveToRecent(page.id)
      runCommand(() => router.push(page.href as Route))
    },
    [router, runCommand, saveToRecent]
  )

  // Acoes rapidas
  const actions: ActionItem[] = [
    {
      id: 'nova-campanha',
      label: 'Nova Campanha',
      icon: Plus,
      action: () => {
        saveToRecent('campanhas')
        router.push('/campanhas?new=true' as Route)
      },
      keywords: ['criar', 'nova', 'campanha'],
    },
    {
      id: 'atualizar',
      label: 'Atualizar Pagina',
      icon: RefreshCw,
      action: () => window.location.reload(),
      keywords: ['refresh', 'reload', 'atualizar'],
    },
  ]

  // Paginas recentes
  const recentPageItems = recentPages
    .map((id) => pages.find((p) => p.id === id))
    .filter((p): p is PageItem => p !== undefined)

  // Reset search quando abre
  useEffect(() => {
    if (open) {
      setSearch('')
    }
  }, [open])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-background/80 backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
        aria-hidden="true"
      />

      {/* Command Menu */}
      <div className="fixed left-1/2 top-[15%] w-full max-w-xl -translate-x-1/2 px-4">
        <Command
          className="overflow-hidden rounded-2xl border border-border bg-popover shadow-2xl"
          shouldFilter={true}
          loop
        >
          {/* Input */}
          <div className="flex items-center border-b border-border px-4">
            <Search className="mr-3 h-5 w-5 shrink-0 text-muted-foreground" />
            <Command.Input
              value={search}
              onValueChange={setSearch}
              placeholder="Buscar pagina ou acao..."
              className="flex h-14 w-full bg-transparent text-base outline-none placeholder:text-muted-foreground"
              autoFocus
            />
            <kbd className="pointer-events-none hidden h-6 select-none items-center gap-1 rounded-md border border-border bg-muted px-2 font-mono text-xs text-muted-foreground sm:flex">
              esc
            </kbd>
          </div>

          <Command.List className="max-h-[400px] overflow-y-auto p-2">
            <Command.Empty className="py-8 text-center text-sm text-muted-foreground">
              Nenhum resultado encontrado.
            </Command.Empty>

            {/* Recentes */}
            {recentPageItems.length > 0 && !search && (
              <Command.Group
                heading={
                  <span className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    Recentes
                  </span>
                }
                className="px-1 py-2"
              >
                {recentPageItems.map((page) => (
                  <Command.Item
                    key={`recent-${page.id}`}
                    value={`recent ${page.label}`}
                    onSelect={() => navigateTo(page)}
                    className="group flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors aria-selected:bg-accent"
                  >
                    <page.icon className="h-4 w-4 text-muted-foreground group-aria-selected:text-accent-foreground" />
                    <span className="flex-1 group-aria-selected:text-accent-foreground">
                      {page.label}
                    </span>
                    <ArrowRight className="h-3 w-3 text-muted-foreground opacity-0 transition-opacity group-aria-selected:opacity-100" />
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            {/* Acoes Rapidas */}
            <Command.Group
              heading={
                <span className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <Plus className="h-3 w-3" />
                  Acoes Rapidas
                </span>
              }
              className="px-1 py-2"
            >
              {actions.map((action) => (
                <Command.Item
                  key={action.id}
                  value={`${action.label} ${action.keywords?.join(' ') || ''}`}
                  onSelect={() => runCommand(action.action)}
                  className="group flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors aria-selected:bg-accent"
                >
                  <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10">
                    <action.icon className="h-3.5 w-3.5 text-primary" />
                  </div>
                  <span className="flex-1 group-aria-selected:text-accent-foreground">
                    {action.label}
                  </span>
                </Command.Item>
              ))}
            </Command.Group>

            {/* Todas as Paginas */}
            <Command.Group
              heading={
                <span className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <LayoutDashboard className="h-3 w-3" />
                  Paginas
                </span>
              }
              className="px-1 py-2"
            >
              {pages.map((page) => (
                <Command.Item
                  key={page.id}
                  value={`${page.label} ${page.keywords?.join(' ') || ''}`}
                  onSelect={() => navigateTo(page)}
                  className="group flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors aria-selected:bg-accent"
                >
                  <page.icon className="h-4 w-4 text-muted-foreground group-aria-selected:text-accent-foreground" />
                  <div className="flex flex-1 flex-col">
                    <span className="group-aria-selected:text-accent-foreground">{page.label}</span>
                    {page.description && (
                      <span className="text-xs text-muted-foreground">{page.description}</span>
                    )}
                  </div>
                  <ArrowRight className="h-3 w-3 text-muted-foreground opacity-0 transition-opacity group-aria-selected:opacity-100" />
                </Command.Item>
              ))}
            </Command.Group>
          </Command.List>

          {/* Footer com dicas */}
          <div className="flex items-center justify-between border-t border-border px-4 py-2 text-xs text-muted-foreground">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1">
                <kbd className="rounded border border-border bg-muted px-1.5 py-0.5">↑↓</kbd>
                navegar
              </span>
              <span className="flex items-center gap-1">
                <kbd className="rounded border border-border bg-muted px-1.5 py-0.5">↵</kbd>
                selecionar
              </span>
            </div>
            <span className="hidden text-muted-foreground/70 sm:inline">Jull.ia Command</span>
          </div>
        </Command>
      </div>
    </div>
  )
}
