/**
 * MobileDrawer - Sprint 45
 *
 * Drawer de navegacao completa para mobile.
 * Abre via botao Menu no bottom-nav.
 */

'use client'

import Link from 'next/link'
import type { Route } from 'next'
import { usePathname } from 'next/navigation'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { cn } from '@/lib/utils'
import {
  Menu,
  LayoutDashboard,
  MessageSquare,
  Megaphone,
  Briefcase,
  Stethoscope,
  Building2,
  Smartphone,
  Activity,
  HeartPulse,
  ShieldCheck,
  BarChart3,
  Star,
  ClipboardList,
  FileText,
  Settings,
  HelpCircle,
  Power,
  Users,
  Target,
  type LucideIcon,
} from 'lucide-react'

interface NavItem {
  name: string
  href: string
  icon: LucideIcon
}

interface NavGroup {
  label: string
  items: NavItem[]
}

const navigationGroups: NavGroup[] = [
  {
    label: 'Operacoes',
    items: [
      { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
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
    items: [{ name: 'Chips', href: '/chips', icon: Smartphone }],
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
  {
    label: 'Configuracao',
    items: [
      { name: 'Sistema', href: '/sistema', icon: Settings },
      { name: 'Ajuda', href: '/ajuda', icon: HelpCircle },
    ],
  },
]

interface MobileDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function MobileDrawer({ open, onOpenChange }: MobileDrawerProps) {
  const pathname = usePathname()

  const isActive = (href: string) => {
    return pathname === href || (href !== '/dashboard' && pathname.startsWith(href))
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[300px] p-0">
        <SheetHeader className="border-b border-border px-4 py-4">
          <SheetTitle className="flex items-center gap-3">
            <div className="bg-jullia-gradient flex h-8 w-8 items-center justify-center rounded-lg">
              <span className="text-sm font-bold text-white">J</span>
            </div>
            <span className="text-base font-semibold">Menu</span>
          </SheetTitle>
        </SheetHeader>

        <nav className="flex-1 overflow-y-auto p-4">
          {navigationGroups.map((group) => (
            <div key={group.label} className="mb-5">
              <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/70">
                {group.label}
              </h3>
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const active = isActive(item.href)
                  return (
                    <Link
                      key={item.href}
                      href={item.href as Route}
                      onClick={() => onOpenChange(false)}
                      className={cn(
                        'group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all',
                        active
                          ? 'bg-primary/10 text-primary'
                          : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                      )}
                    >
                      <item.icon
                        className={cn(
                          'h-[18px] w-[18px]',
                          active ? 'text-primary' : 'text-muted-foreground/70'
                        )}
                      />
                      <span>{item.name}</span>
                      {active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-primary" />}
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="border-t border-border p-4">
          <button
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
            onClick={() => {
              onOpenChange(false)
              // TODO: Implementar logout
              console.log('Logout clicked')
            }}
          >
            <Power className="h-[18px] w-[18px]" />
            Sair
          </button>
        </div>
      </SheetContent>
    </Sheet>
  )
}

// Botao trigger para usar no bottom-nav
export function MobileMenuButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex min-w-[56px] flex-col items-center gap-1 rounded-lg px-2 py-2 text-muted-foreground transition-colors active:bg-muted"
      aria-label="Abrir menu"
    >
      <Menu className="h-6 w-6" />
      <span className="text-[10px] font-medium">Menu</span>
    </button>
  )
}
