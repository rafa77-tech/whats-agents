# Epic 03 - Command Palette

## Objetivo
Implementar busca global (Cmd+K / Ctrl+K) para navegacao rapida, acoes e busca de entidades.

## Contexto

### Por que Command Palette?

| Beneficio | Descricao |
|-----------|-----------|
| Power users | Usuarios frequentes navegam mais rapido |
| Descobribilidade | Usuarios encontram funcionalidades que nao conheciam |
| Acessibilidade | Navegacao por teclado completa |
| Padrao de mercado | Linear, Notion, VS Code, Slack usam |

### Funcionalidades Planejadas

1. **Navegacao** - Ir para qualquer pagina
2. **Recentes** - Ultimas paginas visitadas
3. **Acoes rapidas** - Nova campanha, novo medico, etc.
4. **Busca de entidades** - (futuro) Buscar medicos, campanhas por nome

## Stories

---

### S45.E3.1 - Estrutura Base do Command Palette

**Objetivo:** Criar o componente base do command palette usando cmdk.

**Dependencia:** Instalar `cmdk` (biblioteca de command menu)

```bash
cd dashboard && npm install cmdk
```

**Arquivo:** `dashboard/components/command-palette/command-palette.tsx`

**Implementacao:**

```tsx
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
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface CommandItem {
  id: string
  label: string
  icon: LucideIcon
  href?: string
  action?: () => void
  keywords?: string[]
  group: 'recent' | 'actions' | 'pages'
}

const pages: CommandItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, href: '/dashboard', group: 'pages', keywords: ['home', 'inicio'] },
  { id: 'conversas', label: 'Conversas', icon: MessageSquare, href: '/conversas', group: 'pages', keywords: ['chat', 'mensagens'] },
  { id: 'campanhas', label: 'Campanhas', icon: Megaphone, href: '/campanhas', group: 'pages', keywords: ['campanha', 'disparo'] },
  { id: 'vagas', label: 'Vagas', icon: Briefcase, href: '/vagas', group: 'pages', keywords: ['plantao', 'plantoes'] },
  { id: 'medicos', label: 'Medicos', icon: Stethoscope, href: '/medicos', group: 'pages', keywords: ['doutor', 'dr'] },
  { id: 'hospitais', label: 'Hospitais', icon: Building2, href: '/hospitais/bloqueados', group: 'pages', keywords: ['hospital', 'bloqueado'] },
  { id: 'chips', label: 'Chips', icon: Smartphone, href: '/chips', group: 'pages', keywords: ['whatsapp', 'numero'] },
  { id: 'grupos', label: 'Grupos', icon: Users, href: '/grupos', group: 'pages', keywords: ['grupo', 'whatsapp'] },
  { id: 'monitor', label: 'Monitor', icon: Activity, href: '/monitor', group: 'pages', keywords: ['jobs', 'tarefas'] },
  { id: 'health', label: 'Health Center', icon: HeartPulse, href: '/health', group: 'pages', keywords: ['saude', 'status'] },
  { id: 'integridade', label: 'Integridade', icon: ShieldCheck, href: '/integridade', group: 'pages', keywords: ['anomalia', 'dados'] },
  { id: 'metricas', label: 'Metricas', icon: BarChart3, href: '/metricas', group: 'pages', keywords: ['analytics', 'graficos'] },
  { id: 'qualidade', label: 'Avaliacoes', icon: Star, href: '/qualidade', group: 'pages', keywords: ['qualidade', 'review'] },
  { id: 'auditoria', label: 'Auditoria', icon: ClipboardList, href: '/auditoria', group: 'pages', keywords: ['logs', 'historico'] },
  { id: 'instrucoes', label: 'Instrucoes', icon: FileText, href: '/instrucoes', group: 'pages', keywords: ['diretrizes', 'regras'] },
  { id: 'sistema', label: 'Sistema', icon: Settings, href: '/sistema', group: 'pages', keywords: ['config', 'configuracao'] },
  { id: 'ajuda', label: 'Ajuda', icon: HelpCircle, href: '/ajuda', group: 'pages', keywords: ['help', 'suporte'] },
]

interface CommandPaletteProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const router = useRouter()
  const [search, setSearch] = useState('')

  const runCommand = useCallback((command: () => void) => {
    onOpenChange(false)
    command()
  }, [onOpenChange])

  // Reset search when opening
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
        className="fixed inset-0 bg-black/50"
        onClick={() => onOpenChange(false)}
      />

      {/* Command Menu */}
      <div className="fixed left-1/2 top-[20%] w-full max-w-lg -translate-x-1/2">
        <Command
          className="rounded-xl border border-border bg-popover shadow-2xl"
          shouldFilter={true}
        >
          <div className="flex items-center border-b border-border px-4">
            <Search className="mr-2 h-4 w-4 shrink-0 text-muted-foreground" />
            <Command.Input
              value={search}
              onValueChange={setSearch}
              placeholder="Buscar pagina ou acao..."
              className="flex h-12 w-full bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground"
            />
            <kbd className="pointer-events-none ml-2 hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground sm:flex">
              esc
            </kbd>
          </div>

          <Command.List className="max-h-[400px] overflow-y-auto p-2">
            <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
              Nenhum resultado encontrado.
            </Command.Empty>

            {/* Acoes Rapidas */}
            <Command.Group heading="Acoes Rapidas" className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
              <Command.Item
                onSelect={() => runCommand(() => router.push('/campanhas?new=true'))}
                className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-sm hover:bg-accent"
              >
                <Plus className="h-4 w-4 text-muted-foreground" />
                Nova Campanha
              </Command.Item>
              <Command.Item
                onSelect={() => runCommand(() => router.push('/medicos?new=true'))}
                className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-sm hover:bg-accent"
              >
                <Plus className="h-4 w-4 text-muted-foreground" />
                Novo Medico
              </Command.Item>
              <Command.Item
                onSelect={() => runCommand(() => window.location.reload())}
                className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-sm hover:bg-accent"
              >
                <RefreshCw className="h-4 w-4 text-muted-foreground" />
                Atualizar Pagina
              </Command.Item>
            </Command.Group>

            {/* Paginas */}
            <Command.Group heading="Paginas" className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
              {pages.map((page) => (
                <Command.Item
                  key={page.id}
                  value={`${page.label} ${page.keywords?.join(' ') || ''}`}
                  onSelect={() => runCommand(() => router.push(page.href!))}
                  className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-sm hover:bg-accent"
                >
                  <page.icon className="h-4 w-4 text-muted-foreground" />
                  {page.label}
                </Command.Item>
              ))}
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  )
}
```

**Tarefas:**
1. Instalar `cmdk`: `npm install cmdk`
2. Criar diretorio `components/command-palette/`
3. Implementar componente base
4. Definir lista de paginas com keywords
5. Implementar acoes rapidas

**DoD:**
- [ ] cmdk instalado
- [ ] Componente renderiza quando open=true
- [ ] Lista de paginas completa
- [ ] Busca funciona com keywords
- [ ] Acoes rapidas funcionam

---

### S45.E3.2 - Provider e Estado Global

**Objetivo:** Criar context provider para gerenciar estado do command palette globalmente.

**Arquivo:** `dashboard/components/command-palette/command-palette-provider.tsx`

**Implementacao:**

```tsx
'use client'

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import { CommandPalette } from './command-palette'

interface CommandPaletteContextType {
  open: boolean
  setOpen: (open: boolean) => void
  toggle: () => void
}

const CommandPaletteContext = createContext<CommandPaletteContextType | undefined>(undefined)

export function CommandPaletteProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)

  const toggle = useCallback(() => {
    setOpen((prev) => !prev)
  }, [])

  return (
    <CommandPaletteContext.Provider value={{ open, setOpen, toggle }}>
      {children}
      <CommandPalette open={open} onOpenChange={setOpen} />
    </CommandPaletteContext.Provider>
  )
}

export function useCommandPalette() {
  const context = useContext(CommandPaletteContext)
  if (!context) {
    throw new Error('useCommandPalette must be used within CommandPaletteProvider')
  }
  return context
}
```

**Arquivo:** `dashboard/components/command-palette/index.ts`

```tsx
export { CommandPalette } from './command-palette'
export { CommandPaletteProvider, useCommandPalette } from './command-palette-provider'
```

**Tarefas:**
1. Criar context com estado `open`
2. Expor `setOpen` e `toggle`
3. Renderizar `CommandPalette` dentro do provider
4. Criar hook `useCommandPalette`
5. Criar arquivo index para exports

**DoD:**
- [ ] Provider criado
- [ ] Hook funciona corretamente
- [ ] Estado global acessivel de qualquer componente
- [ ] Exports organizados

---

### S45.E3.3 - Atalho de Teclado (Cmd+K)

**Objetivo:** Implementar listener global para Cmd+K / Ctrl+K.

**Arquivo:** `dashboard/components/command-palette/use-command-shortcut.ts`

**Implementacao:**

```tsx
'use client'

import { useEffect } from 'react'
import { useCommandPalette } from './command-palette-provider'

export function useCommandShortcut() {
  const { toggle, setOpen } = useCommandPalette()

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd+K (Mac) ou Ctrl+K (Windows/Linux)
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        toggle()
      }

      // Escape para fechar
      if (e.key === 'Escape') {
        setOpen(false)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [toggle, setOpen])
}
```

**Usar no Provider:**

```tsx
// Em command-palette-provider.tsx
import { useCommandShortcut } from './use-command-shortcut'

function CommandShortcutListener() {
  useCommandShortcut()
  return null
}

export function CommandPaletteProvider({ children }: { children: ReactNode }) {
  // ...
  return (
    <CommandPaletteContext.Provider value={{ open, setOpen, toggle }}>
      <CommandShortcutListener />
      {children}
      <CommandPalette open={open} onOpenChange={setOpen} />
    </CommandPaletteContext.Provider>
  )
}
```

**Tarefas:**
1. Criar hook `useCommandShortcut`
2. Listener para Cmd+K e Ctrl+K
3. Listener para Escape
4. Prevenir comportamento default do browser
5. Integrar no provider

**DoD:**
- [ ] Cmd+K abre/fecha no Mac
- [ ] Ctrl+K abre/fecha no Windows/Linux
- [ ] Escape fecha
- [ ] Nao interfere com inputs focados
- [ ] Funciona em todas as paginas

---

### S45.E3.4 - Integracao no Layout

**Objetivo:** Adicionar provider no layout e botao trigger no header.

**Arquivo:** `dashboard/app/(dashboard)/layout.tsx`

**Adicionar Provider:**

```tsx
import { CommandPaletteProvider } from '@/components/command-palette'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <CommandPaletteProvider>
      <DashboardLayoutWrapper>
        {children}
      </DashboardLayoutWrapper>
    </CommandPaletteProvider>
  )
}
```

**Arquivo:** `dashboard/components/dashboard/header.tsx`

**Adicionar Botao:**

```tsx
import { useCommandPalette } from '@/components/command-palette'
import { Search } from 'lucide-react'

export function Header() {
  const { setOpen } = useCommandPalette()

  return (
    <header className="...">
      {/* ... outros elementos ... */}

      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 rounded-lg border border-border bg-muted/50 px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted"
      >
        <Search className="h-4 w-4" />
        <span className="hidden sm:inline">Buscar...</span>
        <kbd className="pointer-events-none hidden h-5 select-none items-center gap-1 rounded border bg-background px-1.5 font-mono text-[10px] font-medium sm:flex">
          <span className="text-xs">⌘</span>K
        </kbd>
      </button>
    </header>
  )
}
```

**Tarefas:**
1. Importar e adicionar `CommandPaletteProvider` no layout
2. Adicionar botao de busca no header
3. Mostrar atalho de teclado no botao
4. Estilizar consistente com design system

**DoD:**
- [ ] Provider no layout root
- [ ] Botao visivel no header
- [ ] Atalho de teclado visivel
- [ ] Clique no botao abre command palette
- [ ] Funciona em todas as paginas do dashboard

---

### S45.E3.5 - Recentes e Persistencia

**Objetivo:** Salvar e exibir paginas visitadas recentemente.

**Arquivo:** `dashboard/components/command-palette/use-recent-pages.ts`

**Implementacao:**

```tsx
'use client'

import { useEffect, useState, useCallback } from 'react'
import { usePathname } from 'next/navigation'

const STORAGE_KEY = 'julia-recent-pages'
const MAX_RECENT = 5

interface RecentPage {
  href: string
  label: string
  timestamp: number
}

export function useRecentPages() {
  const pathname = usePathname()
  const [recentPages, setRecentPages] = useState<RecentPage[]>([])

  // Carregar do localStorage
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      try {
        setRecentPages(JSON.parse(stored))
      } catch {
        // Ignora erro de parse
      }
    }
  }, [])

  // Salvar pagina atual
  useEffect(() => {
    if (!pathname || pathname === '/') return

    // Mapear pathname para label
    const pageLabels: Record<string, string> = {
      '/dashboard': 'Dashboard',
      '/conversas': 'Conversas',
      '/campanhas': 'Campanhas',
      '/vagas': 'Vagas',
      '/medicos': 'Medicos',
      '/chips': 'Chips',
      '/grupos': 'Grupos',
      '/monitor': 'Monitor',
      '/health': 'Health Center',
      '/integridade': 'Integridade',
      '/metricas': 'Metricas',
      '/qualidade': 'Avaliacoes',
      '/auditoria': 'Auditoria',
      '/instrucoes': 'Instrucoes',
      '/sistema': 'Sistema',
      '/ajuda': 'Ajuda',
      '/hospitais/bloqueados': 'Hospitais',
    }

    const label = pageLabels[pathname]
    if (!label) return

    setRecentPages((prev) => {
      // Remover se ja existe
      const filtered = prev.filter((p) => p.href !== pathname)

      // Adicionar no inicio
      const updated = [
        { href: pathname, label, timestamp: Date.now() },
        ...filtered,
      ].slice(0, MAX_RECENT)

      // Salvar no localStorage
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))

      return updated
    })
  }, [pathname])

  const clearRecent = useCallback(() => {
    setRecentPages([])
    localStorage.removeItem(STORAGE_KEY)
  }, [])

  return { recentPages, clearRecent }
}
```

**Atualizar CommandPalette:**

```tsx
// Em command-palette.tsx
import { useRecentPages } from './use-recent-pages'

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const { recentPages } = useRecentPages()
  // ...

  return (
    // ...
    <Command.List>
      {/* Recentes */}
      {recentPages.length > 0 && (
        <Command.Group heading="Recentes" className="...">
          {recentPages.map((page) => (
            <Command.Item
              key={page.href}
              onSelect={() => runCommand(() => router.push(page.href))}
              className="..."
            >
              <History className="h-4 w-4 text-muted-foreground" />
              {page.label}
            </Command.Item>
          ))}
        </Command.Group>
      )}

      {/* Acoes Rapidas */}
      {/* Paginas */}
    </Command.List>
  )
}
```

**Tarefas:**
1. Criar hook `useRecentPages`
2. Salvar no localStorage
3. Limitar a 5 itens
4. Exibir no topo do command palette
5. Icone de historico para diferenciar

**DoD:**
- [ ] Paginas visitadas sao salvas
- [ ] Maximo de 5 recentes
- [ ] Persiste entre sessoes
- [ ] Exibe no topo do command palette
- [ ] Duplicatas sao removidas

---

## Resultado Final Esperado

### Visual do Command Palette

```
┌─────────────────────────────────────────────────────────────────────┐
│  🔍 Buscar pagina ou acao...                                  esc   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  RECENTES                                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 🕐  Conversas                                               │    │
│  │ 🕐  Campanhas                                               │    │
│  │ 🕐  Medicos                                                 │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ACOES RAPIDAS                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ ➕  Nova Campanha                                           │    │
│  │ ➕  Novo Medico                                             │    │
│  │ 🔄  Atualizar Pagina                                        │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  PAGINAS                                                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 📊  Dashboard                                               │    │
│  │ 💬  Conversas                                               │    │
│  │ 📢  Campanhas                                               │    │
│  │ 📋  Vagas                                                   │    │
│  │ 👨‍⚕️  Medicos                                                 │    │
│  │ ...                                                         │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Botao no Header

```
┌─────────────────────────────────────────────────────────────────────┐
│ [J] Julia    [🔍 Buscar...  ⌘K]    [Notificacoes] [Status] [User]  │
└─────────────────────────────────────────────────────────────────────┘
```

## Consideracoes Tecnicas

- Usar biblioteca `cmdk` (leve, acessivel, bem mantida)
- Busca fuzzy nativa do cmdk
- Keywords para melhorar descobribilidade
- localStorage para recentes (nao precisa de backend)
- Lazy loading do componente (opcional, se performance for problema)

## Extensoes Futuras (Out of Scope)

- Busca de medicos por nome
- Busca de campanhas por nome
- Acoes contextuais (ex: pausar campanha X)
- Temas de comandos (ex: /dark, /light)
