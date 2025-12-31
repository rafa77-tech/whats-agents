# E03: Layout Base Responsivo

**Épico:** Sidebar + Header + Mobile nav
**Estimativa:** 6h
**Prioridade:** P0 (Bloqueante)
**Dependências:** E01, E02

---

## Objetivo

Criar layout responsivo completo:
- **Desktop (lg+):** Sidebar fixa à esquerda + header superior
- **Tablet (md):** Sidebar colapsável + header
- **Mobile (< md):** Bottom navigation + header compacto

---

## Estrutura de Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DESKTOP (lg+)                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ ┌──────────────┐ ┌────────────────────────────────────────────────────────┐ │
│ │              │ │ Header                                    [👤 User]    │ │
│ │   Sidebar    │ ├────────────────────────────────────────────────────────┤ │
│ │              │ │                                                        │ │
│ │  • Dashboard │ │                                                        │ │
│ │  • Conversas │ │                    Main Content                        │ │
│ │  • Médicos   │ │                                                        │ │
│ │  • Vagas     │ │                                                        │ │
│ │  • Campanhas │ │                                                        │ │
│ │  • Métricas  │ │                                                        │ │
│ │  ─────────── │ │                                                        │ │
│ │  • Sistema   │ │                                                        │ │
│ │  • Config    │ │                                                        │ │
│ │              │ │                                                        │ │
│ └──────────────┘ └────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              MOBILE (< md)                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ ┌────────────────────────────────────────────────────────────────────────┐  │
│ │ [☰ Menu]       Julia Dashboard                           [🔔] [👤]    │  │
│ ├────────────────────────────────────────────────────────────────────────┤  │
│ │                                                                        │  │
│ │                                                                        │  │
│ │                                                                        │  │
│ │                          Main Content                                  │  │
│ │                       (scroll vertical)                                │  │
│ │                                                                        │  │
│ │                                                                        │  │
│ │                                                                        │  │
│ │                                                                        │  │
│ ├────────────────────────────────────────────────────────────────────────┤  │
│ │   [🏠]        [💬]        [👥]        [📊]        [⚙️]                 │  │
│ │  Dashboard   Conversas   Médicos    Métricas    Sistema               │  │
│ └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Stories

### S03.1: Root Layout

**Arquivo:** `app/layout.tsx`

```tsx
import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Providers } from '@/components/providers'
import { Toaster } from '@/components/ui/toaster'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: {
    default: 'Julia Dashboard',
    template: '%s | Julia Dashboard',
  },
  description: 'Painel de controle do Agente Julia - Revoluna',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'Julia',
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0c0a09' },
  ],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          {children}
          <Toaster />
        </Providers>
      </body>
    </html>
  )
}
```

**Arquivo:** `components/providers/index.tsx`

```tsx
'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { ThemeProvider } from './theme-provider'
import { AuthProvider } from './auth-provider'
import { useState } from 'react'

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minuto
            refetchOnWindowFocus: false,
          },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
      >
        <AuthProvider>
          {children}
        </AuthProvider>
      </ThemeProvider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
```

**DoD:**
- [ ] Layout base configurado
- [ ] Providers encadeados
- [ ] Metadata e viewport configurados
- [ ] PWA manifest referenciado

---

### S03.2: Dashboard Layout

**Arquivo:** `app/(dashboard)/layout.tsx`

```tsx
import { Sidebar } from '@/components/layout/sidebar'
import { Header } from '@/components/layout/header'
import { BottomNav } from '@/components/layout/bottom-nav'
import { MobileDrawer } from '@/components/layout/mobile-drawer'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar - Desktop only */}
      <aside className="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-64 lg:flex-col">
        <Sidebar />
      </aside>

      {/* Mobile Drawer */}
      <MobileDrawer />

      {/* Main content area */}
      <div className="lg:pl-64">
        {/* Header */}
        <Header />

        {/* Page content */}
        <main className="py-4 px-4 sm:px-6 lg:px-8 pb-20 lg:pb-4">
          {children}
        </main>
      </div>

      {/* Bottom Navigation - Mobile only */}
      <BottomNav />
    </div>
  )
}
```

**DoD:**
- [ ] Layout responsivo funcionando
- [ ] Sidebar fixa no desktop
- [ ] Bottom nav no mobile
- [ ] Padding correto para não sobrepor nav

---

### S03.3: Sidebar

**Arquivo:** `components/layout/sidebar.tsx`

```tsx
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { useAuth } from '@/hooks/use-auth'
import {
  LayoutDashboard,
  MessageSquare,
  Users,
  Briefcase,
  Megaphone,
  BarChart3,
  Settings,
  Shield,
  ScrollText,
  Cpu,
  ChevronDown,
} from 'lucide-react'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Badge } from '@/components/ui/badge'
import { useState } from 'react'

interface NavItem {
  title: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  badge?: number | string
  requiredRole?: 'viewer' | 'operator' | 'manager' | 'admin'
  children?: NavItem[]
}

const navigation: NavItem[] = [
  {
    title: 'Dashboard',
    href: '/',
    icon: LayoutDashboard,
  },
  {
    title: 'Conversas',
    href: '/conversas',
    icon: MessageSquare,
    badge: 12, // Dinâmico depois
  },
  {
    title: 'Médicos',
    href: '/medicos',
    icon: Users,
  },
  {
    title: 'Vagas',
    href: '/vagas',
    icon: Briefcase,
  },
  {
    title: 'Campanhas',
    href: '/campanhas',
    icon: Megaphone,
    requiredRole: 'manager',
  },
  {
    title: 'Métricas',
    href: '/metricas',
    icon: BarChart3,
  },
]

const systemNavigation: NavItem[] = [
  {
    title: 'Sistema',
    href: '/sistema',
    icon: Settings,
    requiredRole: 'operator',
    children: [
      { title: 'Status', href: '/sistema', icon: Cpu },
      { title: 'Feature Flags', href: '/sistema/flags', icon: Shield },
      { title: 'Briefing', href: '/sistema/briefing', icon: ScrollText },
    ],
  },
  {
    title: 'Auditoria',
    href: '/auditoria',
    icon: ScrollText,
    requiredRole: 'admin',
  },
]

export function Sidebar() {
  const pathname = usePathname()
  const { hasPermission, dashboardUser } = useAuth()
  const [openSections, setOpenSections] = useState<string[]>(['Sistema'])

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/'
    return pathname.startsWith(href)
  }

  const toggleSection = (title: string) => {
    setOpenSections(prev =>
      prev.includes(title)
        ? prev.filter(t => t !== title)
        : [...prev, title]
    )
  }

  const renderNavItem = (item: NavItem) => {
    // Check permission
    if (item.requiredRole && !hasPermission(item.requiredRole)) {
      return null
    }

    // With children (collapsible)
    if (item.children) {
      return (
        <Collapsible
          key={item.title}
          open={openSections.includes(item.title)}
          onOpenChange={() => toggleSection(item.title)}
        >
          <CollapsibleTrigger className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors">
            <item.icon className="h-5 w-5" />
            <span className="flex-1 text-left">{item.title}</span>
            <ChevronDown
              className={cn(
                'h-4 w-4 transition-transform',
                openSections.includes(item.title) && 'rotate-180'
              )}
            />
          </CollapsibleTrigger>
          <CollapsibleContent className="pl-4 space-y-1">
            {item.children.map(child => (
              <Link
                key={child.href}
                href={child.href}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 transition-colors',
                  isActive(child.href)
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )}
              >
                <child.icon className="h-4 w-4" />
                <span className="text-sm">{child.title}</span>
              </Link>
            ))}
          </CollapsibleContent>
        </Collapsible>
      )
    }

    // Simple link
    return (
      <Link
        key={item.href}
        href={item.href}
        className={cn(
          'flex items-center gap-3 rounded-lg px-3 py-2 transition-colors',
          isActive(item.href)
            ? 'bg-primary text-primary-foreground'
            : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
        )}
      >
        <item.icon className="h-5 w-5" />
        <span className="flex-1">{item.title}</span>
        {item.badge && (
          <Badge variant="secondary" className="ml-auto">
            {item.badge}
          </Badge>
        )}
      </Link>
    )
  }

  return (
    <div className="flex h-full flex-col gap-2 border-r bg-card px-3 py-4">
      {/* Logo */}
      <div className="flex h-14 items-center px-3 mb-4">
        <Link href="/" className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold">J</span>
          </div>
          <span className="font-semibold text-lg">Julia</span>
        </Link>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 space-y-1">
        {navigation.map(renderNavItem)}

        <div className="my-4 border-t" />

        {systemNavigation.map(renderNavItem)}
      </nav>

      {/* User info (bottom) */}
      <div className="border-t pt-4">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center">
            <span className="text-sm font-medium">
              {dashboardUser?.nome.charAt(0)}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">
              {dashboardUser?.nome}
            </p>
            <p className="text-xs text-muted-foreground capitalize">
              {dashboardUser?.role}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
```

**DoD:**
- [ ] Navegação completa
- [ ] Active state funcionando
- [ ] Seções colapsáveis
- [ ] Permissões respeitadas
- [ ] Badges de contagem

---

### S03.4: Header

**Arquivo:** `components/layout/header.tsx`

```tsx
'use client'

import { Menu, Bell, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { UserMenu } from './user-menu'
import { NotificationBell } from './notification-bell'
import { JuliaStatus } from './julia-status'
import { useMobileDrawer } from '@/hooks/use-mobile-drawer'

export function Header() {
  const { open } = useMobileDrawer()

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center gap-4 px-4 sm:px-6 lg:px-8">
        {/* Mobile menu button */}
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          onClick={open}
        >
          <Menu className="h-5 w-5" />
          <span className="sr-only">Abrir menu</span>
        </Button>

        {/* Logo mobile */}
        <div className="lg:hidden flex items-center gap-2">
          <div className="h-6 w-6 rounded-full bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-sm">J</span>
          </div>
          <span className="font-semibold">Julia</span>
        </div>

        {/* Julia Status Indicator */}
        <div className="hidden sm:flex">
          <JuliaStatus />
        </div>

        {/* Search - Desktop only */}
        <div className="hidden md:flex flex-1 max-w-md ml-4">
          <div className="relative w-full">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Buscar médicos, vagas..."
              className="pl-8 w-full"
            />
          </div>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Right side actions */}
        <div className="flex items-center gap-2">
          {/* Notifications */}
          <NotificationBell />

          {/* User Menu */}
          <UserMenu />
        </div>
      </div>
    </header>
  )
}
```

**Arquivo:** `components/layout/julia-status.tsx`

```tsx
'use client'

import { useQuery } from '@tanstack/react-query'
import { Badge } from '@/components/ui/badge'
import { Loader2 } from 'lucide-react'
import { api } from '@/lib/api/client'

interface JuliaStatusData {
  status: 'ativo' | 'pausado'
  motivo?: string
}

export function JuliaStatus() {
  const { data, isLoading } = useQuery<JuliaStatusData>({
    queryKey: ['julia-status'],
    queryFn: () => api.get('/api/v1/dashboard/status'),
    refetchInterval: 30000, // 30s
  })

  if (isLoading) {
    return <Loader2 className="h-4 w-4 animate-spin" />
  }

  const isActive = data?.status === 'ativo'

  return (
    <Badge
      variant={isActive ? 'default' : 'destructive'}
      className="gap-1.5"
    >
      <span
        className={`h-2 w-2 rounded-full ${
          isActive ? 'bg-green-400 animate-pulse' : 'bg-red-400'
        }`}
      />
      Julia {isActive ? 'Ativa' : 'Pausada'}
    </Badge>
  )
}
```

**DoD:**
- [ ] Header responsivo
- [ ] Menu hamburguer no mobile
- [ ] Search bar no desktop
- [ ] Status Julia visível
- [ ] Notificações e user menu

---

### S03.5: Bottom Navigation (Mobile)

**Arquivo:** `components/layout/bottom-nav.tsx`

```tsx
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  MessageSquare,
  Users,
  BarChart3,
  Settings,
} from 'lucide-react'

const navItems = [
  {
    title: 'Home',
    href: '/',
    icon: LayoutDashboard,
  },
  {
    title: 'Conversas',
    href: '/conversas',
    icon: MessageSquare,
  },
  {
    title: 'Médicos',
    href: '/medicos',
    icon: Users,
  },
  {
    title: 'Métricas',
    href: '/metricas',
    icon: BarChart3,
  },
  {
    title: 'Sistema',
    href: '/sistema',
    icon: Settings,
  },
]

export function BottomNav() {
  const pathname = usePathname()

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/'
    return pathname.startsWith(href)
  }

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t bg-background lg:hidden">
      <div className="flex h-16 items-center justify-around px-2">
        {navItems.map((item) => {
          const active = isActive(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex flex-col items-center justify-center gap-1 px-3 py-2 min-w-[64px] rounded-lg transition-colors',
                active
                  ? 'text-primary'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <item.icon
                className={cn(
                  'h-5 w-5 transition-transform',
                  active && 'scale-110'
                )}
              />
              <span className="text-xs font-medium">{item.title}</span>
            </Link>
          )
        })}
      </div>

      {/* Safe area for iOS */}
      <div className="h-[env(safe-area-inset-bottom)]" />
    </nav>
  )
}
```

**DoD:**
- [ ] 5 itens principais visíveis
- [ ] Active state claro
- [ ] Touch targets 44px+
- [ ] Safe area para iOS

---

### S03.6: Mobile Drawer

**Arquivo:** `hooks/use-mobile-drawer.ts`

```typescript
import { create } from 'zustand'

interface MobileDrawerStore {
  isOpen: boolean
  open: () => void
  close: () => void
  toggle: () => void
}

export const useMobileDrawer = create<MobileDrawerStore>((set) => ({
  isOpen: false,
  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),
  toggle: () => set((state) => ({ isOpen: !state.isOpen })),
}))
```

**Arquivo:** `components/layout/mobile-drawer.tsx`

```tsx
'use client'

import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { useMobileDrawer } from '@/hooks/use-mobile-drawer'
import { Sidebar } from './sidebar'

export function MobileDrawer() {
  const { isOpen, close } = useMobileDrawer()

  return (
    <Sheet open={isOpen} onOpenChange={close}>
      <SheetContent side="left" className="p-0 w-72">
        <SheetHeader className="sr-only">
          <SheetTitle>Menu de navegação</SheetTitle>
        </SheetHeader>
        <Sidebar />
      </SheetContent>
    </Sheet>
  )
}
```

**DoD:**
- [ ] Drawer abre do lado esquerdo
- [ ] Reutiliza Sidebar component
- [ ] Fecha ao clicar fora
- [ ] Fecha ao navegar

---

## Testes de Responsividade

### Breakpoints a testar

| Device | Width | O que verificar |
|--------|-------|-----------------|
| iPhone SE | 375px | Bottom nav, cards empilham |
| iPhone 14 | 390px | Layout básico |
| iPhone 14 Pro Max | 430px | Layout básico |
| iPad | 768px | Transição para tablet |
| iPad Pro | 1024px | Sidebar aparece |
| Desktop | 1280px+ | Layout completo |

### Checklist Mobile

- [ ] Touch targets mínimo 44x44px
- [ ] Sem scroll horizontal
- [ ] Texto legível sem zoom
- [ ] Bottom nav não sobrepõe conteúdo
- [ ] Pull to refresh funciona
- [ ] Orientação landscape funciona

---

## Checklist Final

- [ ] Root layout com providers
- [ ] Dashboard layout responsivo
- [ ] Sidebar desktop
- [ ] Header responsivo
- [ ] Bottom nav mobile
- [ ] Mobile drawer
- [ ] Status Julia visível
- [ ] Navegação funcionando
- [ ] Permissões respeitadas
- [ ] Testes em todos breakpoints
