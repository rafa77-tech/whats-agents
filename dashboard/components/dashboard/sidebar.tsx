/**
 * Sidebar - Sprint 45
 *
 * Navegacao lateral do dashboard com grupos semanticos.
 * Redesenhada com identidade visual Jull.ia.
 */

'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import type { Route } from 'next'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { SidebarSection } from './sidebar-section'
import {
  LayoutDashboard,
  Megaphone,
  FileText,
  Building2,
  Settings,
  HelpCircle,
  Power,
  Smartphone,
  Activity,
  HeartPulse,
  ShieldCheck,
  Star,
  BarChart3,
  Briefcase,
  MessageSquare,
  Stethoscope,
  ClipboardList,
  Users,
  Target,
  CloudCog,
  type LucideIcon,
} from 'lucide-react'

interface NavItem {
  name: string
  href: string
  icon: LucideIcon
}

interface NavGroup {
  label: string | null
  items: NavItem[]
}

// Navegacao agrupada por dominio de responsabilidade
const navigationGroups: NavGroup[] = [
  {
    label: null, // Dashboard fica sem label (sempre visivel no topo)
    items: [{ name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard }],
  },
  {
    label: 'Operacoes',
    items: [
      { name: 'Conversas', href: '/conversas', icon: MessageSquare },
      { name: 'Campanhas', href: '/campanhas', icon: Megaphone },
      { name: 'Oportunidades', href: '/oportunidades', icon: Target },
      { name: 'Vagas', href: '/vagas', icon: Briefcase },
      { name: 'Instrucoes', href: '/instrucoes', icon: FileText },
    ],
  },
  {
    label: 'Cadastros',
    items: [
      { name: 'Medicos', href: '/medicos', icon: Stethoscope },
      { name: 'Hospitais', href: '/hospitais', icon: Building2 },
      { name: 'Grupos', href: '/grupos', icon: Users },
    ],
  },
  {
    label: 'WhatsApp',
    items: [
      { name: 'Chips', href: '/chips', icon: Smartphone },
      { name: 'Meta', href: '/meta', icon: CloudCog },
    ],
  },
  {
    label: 'Monitoramento',
    items: [
      { name: 'Monitor', href: '/monitor', icon: Activity },
      { name: 'Health', href: '/health', icon: HeartPulse },
      { name: 'Integridade', href: '/integridade', icon: ShieldCheck },
      { name: 'Metricas', href: '/metricas', icon: BarChart3 },
    ],
  },
  {
    label: 'Qualidade',
    items: [
      { name: 'Avaliacoes', href: '/qualidade', icon: Star },
      { name: 'Auditoria', href: '/auditoria', icon: ClipboardList },
    ],
  },
]

// Itens do footer (configuracao e ajuda)
const footerNavigation: NavItem[] = [
  { name: 'Sistema', href: '/sistema', icon: Settings },
  { name: 'Ajuda', href: '/ajuda', icon: HelpCircle },
]

export function Sidebar() {
  const pathname = usePathname()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const isActive = (href: string) => {
    if (!mounted) return false
    return pathname === href || (href !== '/dashboard' && pathname.startsWith(href))
  }

  const renderNavItem = (item: NavItem) => {
    const active = isActive(item.href)

    return (
      <Link
        key={item.name}
        href={item.href as Route}
        className={cn(
          'group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200',
          active
            ? 'bg-primary/10 text-primary'
            : 'text-foreground/90 hover:bg-muted hover:text-foreground'
        )}
      >
        <item.icon
          className={cn(
            'h-[18px] w-[18px] transition-colors',
            active ? 'text-primary' : 'text-foreground/70 group-hover:text-foreground'
          )}
        />
        <span className="truncate">{item.name}</span>
        {/* Indicador de rota ativa */}
        {active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-primary" />}
      </Link>
    )
  }

  return (
    <div className="sidebar-bg-white flex h-full flex-col">
      {/* Header com logo Jull.ia */}
      <div className="flex items-center gap-3 border-b border-border px-5 py-4">
        <div className="bg-jullia-gradient flex h-9 w-9 items-center justify-center rounded-xl shadow-sm">
          <span className="text-base font-bold text-white">J</span>
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-semibold text-foreground">Jull.ia</span>
          <span className="text-[10px] text-muted-foreground">Dashboard v2.0</span>
        </div>
      </div>

      {/* Navegacao principal com scroll */}
      <nav className="flex-1 overflow-y-auto px-3 py-3">
        {navigationGroups.map((group, idx) =>
          group.label ? (
            <SidebarSection key={group.label} label={group.label}>
              {group.items.map(renderNavItem)}
            </SidebarSection>
          ) : (
            <div key={idx} className="space-y-0.5">
              {group.items.map(renderNavItem)}
            </div>
          )
        )}
      </nav>

      {/* Footer com separador visual */}
      <div className="border-t border-border px-3 py-3">
        <div className="space-y-0.5">{footerNavigation.map(renderNavItem)}</div>

        {/* Botao de sair */}
        <button
          className="mt-3 flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
          onClick={() => {
            // TODO: Implementar logout
            console.log('Logout clicked')
          }}
        >
          <Power className="h-[18px] w-[18px]" />
          <span>Sair</span>
        </button>
      </div>
    </div>
  )
}
