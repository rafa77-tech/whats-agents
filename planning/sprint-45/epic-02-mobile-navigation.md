# Epic 02 - Navegacao Mobile

## Objetivo
Expandir a navegacao mobile para garantir paridade com desktop, adicionando acesso a todas as rotas via drawer de menu.

## Contexto

### Problema Critico
O bottom nav mobile atualmente tem apenas 5 itens:
- Dashboard
- Campanhas
- Chips
- Instrucoes
- Sistema

**FALTANDO funcionalidades criticas:**
- Conversas (centro do trabalho!)
- Medicos
- Vagas
- Monitor
- Health
- E mais 8 outras rotas...

### Solucao
1. Substituir "Instrucoes" por "Conversas" (mais usado)
2. Substituir "Sistema" por "Menu"
3. Menu abre drawer com navegacao completa agrupada

## Stories

---

### S45.E2.1 - Atualizar Itens do Bottom Nav

**Objetivo:** Trocar itens menos usados por funcionalidades criticas.

**Arquivo:** `dashboard/components/dashboard/bottom-nav.tsx`

**De:**
```tsx
const navigation: NavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Campanhas', href: '/campanhas', icon: Megaphone },
  { name: 'Chips', href: '/chips', icon: Smartphone },
  { name: 'Instrucoes', href: '/instrucoes', icon: FileText },
  { name: 'Sistema', href: '/sistema', icon: Settings },
]
```

**Para:**
```tsx
const navigation: NavItem[] = [
  { name: 'Home', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Conversas', href: '/conversas', icon: MessageSquare },
  { name: 'Campanhas', href: '/campanhas', icon: Megaphone },
  { name: 'Chips', href: '/chips', icon: Smartphone },
]

// Menu sera tratado separadamente (nao e um link)
```

**Tarefas:**
1. Atualizar array `navigation`
2. Renomear "Dashboard" para "Home" (mais curto para mobile)
3. Adicionar Conversas (import MessageSquare)
4. Remover Instrucoes e Sistema
5. Deixar espaco para botao Menu

**DoD:**
- [ ] Bottom nav com 4 links + 1 botao Menu
- [ ] Conversas acessivel no mobile
- [ ] Labels curtos para caber na tela
- [ ] Icones corretos importados

---

### S45.E2.2 - Criar Componente MobileDrawer

**Objetivo:** Criar drawer lateral com navegacao completa para mobile.

**Arquivo:** `dashboard/components/dashboard/mobile-drawer.tsx`

**Implementacao:**

```tsx
'use client'

import { useState } from 'react'
import Link from 'next/link'
import type { Route } from 'next'
import { usePathname } from 'next/navigation'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
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
  Power,
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
      { name: 'Vagas', href: '/vagas', icon: Briefcase },
    ]
  },
  {
    label: 'Cadastros',
    items: [
      { name: 'Medicos', href: '/medicos', icon: Stethoscope },
      { name: 'Hospitais', href: '/hospitais/bloqueados', icon: Building2 },
    ]
  },
  {
    label: 'WhatsApp',
    items: [
      { name: 'Chips', href: '/chips', icon: Smartphone },
      { name: 'Grupos', href: '/grupos', icon: Users },
    ]
  },
  {
    label: 'Monitoramento',
    items: [
      { name: 'Monitor', href: '/monitor', icon: Activity },
      { name: 'Health', href: '/health', icon: HeartPulse },
      { name: 'Integridade', href: '/integridade', icon: ShieldCheck },
      { name: 'Metricas', href: '/metricas', icon: BarChart3 },
    ]
  },
  {
    label: 'Qualidade',
    items: [
      { name: 'Avaliacoes', href: '/qualidade', icon: Star },
      { name: 'Auditoria', href: '/auditoria', icon: ClipboardList },
    ]
  },
  {
    label: 'Configuracao',
    items: [
      { name: 'Instrucoes', href: '/instrucoes', icon: FileText },
      { name: 'Sistema', href: '/sistema', icon: Settings },
      { name: 'Ajuda', href: '/ajuda', icon: HelpCircle },
    ]
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
          <SheetTitle className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-revoluna-400">
              <span className="text-sm font-bold text-white">J</span>
            </div>
            <span>Menu</span>
          </SheetTitle>
        </SheetHeader>

        <nav className="flex-1 overflow-y-auto p-4">
          {navigationGroups.map((group) => (
            <div key={group.label} className="mb-6">
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {group.label}
              </h3>
              <div className="space-y-1">
                {group.items.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href as Route}
                    onClick={() => onOpenChange(false)}
                    className={cn(
                      'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                      isActive(item.href)
                        ? 'bg-revoluna-50 text-revoluna-700'
                        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                    )}
                  >
                    <item.icon
                      className={cn(
                        'h-5 w-5',
                        isActive(item.href) ? 'text-revoluna-400' : 'text-muted-foreground/70'
                      )}
                    />
                    {item.name}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div className="border-t border-border p-4">
          <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted">
            <Power className="h-5 w-5 text-muted-foreground/70" />
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
      className="flex min-w-[64px] flex-col items-center gap-1 rounded-lg px-3 py-2 text-gray-500 transition-colors"
    >
      <Menu className="h-6 w-6" />
      <span className="text-xs font-medium">Menu</span>
    </button>
  )
}
```

**Tarefas:**
1. Criar arquivo `mobile-drawer.tsx`
2. Implementar componente com Sheet do shadcn
3. Usar mesmos grupos da sidebar desktop
4. Fechar drawer ao clicar em link
5. Exportar `MobileMenuButton` para uso no bottom-nav

**DoD:**
- [ ] Drawer abre pela direita
- [ ] Navegacao completa agrupada
- [ ] Fecha ao clicar em item
- [ ] Botao Sair funcional
- [ ] Estilo consistente com sidebar desktop

---

### S45.E2.3 - Integrar Drawer no Bottom Nav

**Objetivo:** Conectar o botao Menu ao drawer.

**Arquivo:** `dashboard/components/dashboard/bottom-nav.tsx`

**Implementacao Atualizada:**

```tsx
'use client'

import { useState } from 'react'
import Link from 'next/link'
import type { Route } from 'next'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  Megaphone,
  Smartphone,
  MessageSquare,
  type LucideIcon,
} from 'lucide-react'
import { MobileDrawer, MobileMenuButton } from './mobile-drawer'

interface NavItem {
  name: string
  href: string
  icon: LucideIcon
}

const navigation: NavItem[] = [
  { name: 'Home', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Conversas', href: '/conversas', icon: MessageSquare },
  { name: 'Campanhas', href: '/campanhas', icon: Megaphone },
  { name: 'Chips', href: '/chips', icon: Smartphone },
]

export function BottomNav() {
  const pathname = usePathname()
  const [drawerOpen, setDrawerOpen] = useState(false)

  return (
    <>
      <div className="safe-area-pb border-t border-gray-200 bg-white px-2 py-2">
        <nav className="flex items-center justify-around">
          {navigation.map((item) => {
            const isActive =
              pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href))
            return (
              <Link
                key={item.name}
                href={item.href as Route}
                className={cn(
                  'flex min-w-[64px] flex-col items-center gap-1 rounded-lg px-3 py-2 transition-colors',
                  isActive ? 'text-revoluna-400' : 'text-gray-500'
                )}
              >
                <item.icon className="h-6 w-6" />
                <span className="text-xs font-medium">{item.name}</span>
              </Link>
            )
          })}
          <MobileMenuButton onClick={() => setDrawerOpen(true)} />
        </nav>
      </div>
      <MobileDrawer open={drawerOpen} onOpenChange={setDrawerOpen} />
    </>
  )
}
```

**Tarefas:**
1. Importar `MobileDrawer` e `MobileMenuButton`
2. Adicionar estado `drawerOpen`
3. Renderizar `MobileMenuButton` apos os links
4. Renderizar `MobileDrawer` controlado pelo estado
5. Testar abertura/fechamento

**DoD:**
- [ ] Botao Menu abre drawer
- [ ] Drawer fecha ao clicar em link
- [ ] Drawer fecha ao clicar fora
- [ ] Estado gerenciado corretamente
- [ ] Funciona em todos os tamanhos mobile

---

### S45.E2.4 - Testes e Ajustes Mobile

**Objetivo:** Garantir que a navegacao mobile funcione perfeitamente.

**Cenarios de Teste:**

| Cenario | Acao | Resultado Esperado |
|---------|------|-------------------|
| Abrir menu | Tap em Menu | Drawer abre pela direita |
| Navegar | Tap em item do drawer | Navega e fecha drawer |
| Fechar | Tap fora do drawer | Drawer fecha |
| Swipe | Swipe para direita | Drawer fecha |
| Active state | Navegar para pagina | Item fica destacado |
| Scroll | Muitos itens | Drawer tem scroll interno |

**Dispositivos para Testar:**

| Dispositivo | Viewport |
|-------------|----------|
| iPhone SE | 375 x 667 |
| iPhone 14 | 390 x 844 |
| iPhone 14 Pro Max | 430 x 932 |
| Android (medio) | 360 x 800 |
| Tablet (portrait) | 768 x 1024 |

**Tarefas:**
1. Testar em Chrome DevTools (dispositivos simulados)
2. Verificar safe-area-inset no bottom nav
3. Garantir que drawer nao sobrepoe bottom nav incorretamente
4. Verificar z-index em casos edge
5. Testar com teclado virtual aberto (se aplicavel)

**Ajustes Comuns:**
- Safe area para dispositivos com notch
- Touch targets minimos de 44x44px
- Feedback visual no tap

**DoD:**
- [ ] Funciona em todos os dispositivos testados
- [ ] Touch targets adequados
- [ ] Safe areas respeitadas
- [ ] Sem bugs visuais em edge cases
- [ ] Performance suave nas animacoes

---

## Resultado Final Esperado

### Bottom Nav (Antes)
```
┌────────┬────────┬────────┬────────┬────────┐
│Dashbrd │Campanha│ Chips  │Instruc │Sistema │
│   📊   │   📢   │   📱   │   📄   │   ⚙️   │
└────────┴────────┴────────┴────────┴────────┘
Problema: Falta Conversas, acesso limitado
```

### Bottom Nav (Depois)
```
┌────────┬────────┬────────┬────────┬────────┐
│  Home  │Conversas│Campanha│ Chips  │  Menu  │
│   🏠   │   💬   │   📢   │   📱   │   ☰    │
└────────┴────────┴────────┴────────┴────────┘
Conversas acessivel, Menu abre drawer completo
```

### Drawer Mobile
```
┌──────────────────────────────────────┐
│ [J] Menu                         [X] │
├──────────────────────────────────────┤
│                                      │
│ OPERACOES                            │
│   Dashboard                          │
│   Conversas                     ←    │ (ativo)
│   Campanhas                          │
│   Vagas                              │
│                                      │
│ CADASTROS                            │
│   Medicos                            │
│   Hospitais                          │
│                                      │
│ WHATSAPP                             │
│   Chips                              │
│   Grupos                             │
│                                      │
│ MONITORAMENTO                        │
│   Monitor                            │
│   Health                             │
│   Integridade                        │
│   Metricas                           │
│                                      │
│ QUALIDADE                            │
│   Avaliacoes                         │
│   Auditoria                          │
│                                      │
│ CONFIGURACAO                         │
│   Instrucoes                         │
│   Sistema                            │
│   Ajuda                              │
│                                      │
├──────────────────────────────────────┤
│   [Sair]                             │
└──────────────────────────────────────┘
```

## Consideracoes Tecnicas

- Reutilizar Sheet do shadcn/ui (ja no projeto)
- Manter consistencia de grupos com sidebar desktop
- Considerar acessibilidade (focus trap, ARIA)
- Animacao de entrada/saida suave (ja vem do Sheet)
