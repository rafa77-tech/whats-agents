# Epic 01 - Reorganizacao da Sidebar

## Objetivo
Reorganizar os 17 itens da sidebar em 6 grupos semanticos para reduzir carga cognitiva e melhorar descobribilidade.

## Contexto

### Problema
A sidebar atual tem 17 itens em uma lista flat, violando a Lei de Miller (7 +/- 2 itens). Usuarios precisam escanear todos os itens para encontrar o que procuram.

### Solucao
Agrupar itens por dominio de responsabilidade com labels visuais de secao.

## Stories

---

### S45.E1.1 - Criar Componente SidebarSection

**Objetivo:** Criar componente reutilizavel para labels de secao na sidebar.

**Arquivo:** `dashboard/components/dashboard/sidebar-section.tsx`

**Implementacao:**

```tsx
interface SidebarSectionProps {
  label: string
  children: React.ReactNode
}

export function SidebarSection({ label, children }: SidebarSectionProps) {
  return (
    <div className="mt-6 first:mt-0">
      <h3 className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </h3>
      <div className="space-y-1">
        {children}
      </div>
    </div>
  )
}
```

**Tarefas:**
1. Criar arquivo `sidebar-section.tsx`
2. Implementar componente com props `label` e `children`
3. Estilizar com Tailwind (cor muted, uppercase, tracking)
4. Exportar do index de componentes

**DoD:**
- [ ] Componente criado
- [ ] Props tipadas corretamente
- [ ] Estilo consistente com design system
- [ ] Exportado e disponivel para uso

---

### S45.E1.2 - Definir Estrutura de Grupos

**Objetivo:** Definir a estrutura de dados dos grupos de navegacao.

**Arquivo:** `dashboard/components/dashboard/sidebar.tsx`

**Estrutura Proposta:**

```tsx
interface NavGroup {
  label: string | null  // null = sem label (Dashboard, footer)
  items: NavItem[]
}

const navigationGroups: NavGroup[] = [
  {
    label: null,
    items: [
      { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    ]
  },
  {
    label: 'Operacoes',
    items: [
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
]

const footerNavigation: NavItem[] = [
  { name: 'Instrucoes', href: '/instrucoes', icon: FileText },
  { name: 'Sistema', href: '/sistema', icon: Settings },
  { name: 'Ajuda', href: '/ajuda', icon: HelpCircle },
]
```

**Tarefas:**
1. Criar interface `NavGroup`
2. Reorganizar array `navigation` em `navigationGroups`
3. Separar `footerNavigation` para itens de config
4. Manter tipos existentes (`NavItem`)

**DoD:**
- [ ] Interface NavGroup criada
- [ ] navigationGroups com 6 grupos
- [ ] footerNavigation separado
- [ ] Tipos corretos sem erros TS

---

### S45.E1.3 - Refatorar Render da Sidebar

**Objetivo:** Atualizar o render da sidebar para usar grupos com labels.

**Arquivo:** `dashboard/components/dashboard/sidebar.tsx`

**Implementacao:**

```tsx
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

  const renderNavItem = (item: NavItem) => (
    <Link
      key={item.name}
      href={item.href as Route}
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
  )

  return (
    <div className="flex h-full flex-col">
      {/* Logo */}
      <div className="flex items-center gap-3 border-b border-border px-6 py-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-revoluna-400">
          <span className="text-lg font-bold text-white">J</span>
        </div>
        <div>
          <h1 className="font-bold text-foreground">Julia</h1>
          <p className="text-xs text-muted-foreground">Dashboard</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {navigationGroups.map((group, idx) => (
          group.label ? (
            <SidebarSection key={group.label} label={group.label}>
              {group.items.map(renderNavItem)}
            </SidebarSection>
          ) : (
            <div key={idx} className="space-y-1">
              {group.items.map(renderNavItem)}
            </div>
          )
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-border px-3 py-4">
        <div className="space-y-1">
          {footerNavigation.map(renderNavItem)}
        </div>
        <button className="mt-4 flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted">
          <Power className="h-5 w-5 text-muted-foreground/70" />
          Sair
        </button>
      </div>
    </div>
  )
}
```

**Tarefas:**
1. Importar `SidebarSection`
2. Extrair `renderNavItem` como funcao interna
3. Mapear `navigationGroups` com condicional para label
4. Renderizar `footerNavigation` no footer
5. Adicionar `overflow-y-auto` para scroll em telas pequenas

**DoD:**
- [ ] Sidebar renderiza grupos com labels
- [ ] Footer separado com Instrucoes, Sistema, Ajuda
- [ ] Scroll funciona em telas pequenas
- [ ] Visual consistente com design atual
- [ ] Zero erros TypeScript

---

### S45.E1.4 - Ajustes Visuais e Responsividade

**Objetivo:** Refinar espacamentos e garantir que a sidebar funcione bem em diferentes alturas de tela.

**Tarefas:**
1. Ajustar espacamento entre grupos (`mt-6` ou `mt-4`)
2. Testar em diferentes alturas de viewport
3. Garantir que footer sempre visivel (sticky ou scroll)
4. Ajustar cor/peso do label de secao se necessario
5. Testar com tema dark (se aplicavel)

**Cenarios de Teste:**

| Viewport | Comportamento Esperado |
|----------|------------------------|
| Desktop (1080p) | Todos os grupos visiveis, footer fixo |
| Desktop (768px height) | Scroll na navegacao, footer fixo |
| Desktop (600px height) | Scroll na navegacao, footer fixo |

**DoD:**
- [ ] Espacamento harmonico entre grupos
- [ ] Scroll funciona sem cortar itens
- [ ] Footer sempre acessivel
- [ ] Funciona em diferentes viewports
- [ ] Visual aprovado

---

## Resultado Final Esperado

### Antes
```
┌──────────────────────────────────────┐
│ Dashboard                            │
│ Metricas                             │
│ Campanhas                            │
│ Vagas                                │
│ Conversas                            │
│ Medicos                              │
│ Pool de Chips                        │
│ Monitor                              │
│ Health Center                        │
│ Integridade                          │
│ Grupos                               │
│ Qualidade                            │
│ Auditoria                            │
│ Instrucoes                           │
│ Hospitais Bloqueados                 │
│ Sistema                              │
│ Ajuda                                │
└──────────────────────────────────────┘
17 itens, sem agrupamento
```

### Depois
```
┌──────────────────────────────────────┐
│ Dashboard                            │
│                                      │
│ OPERACOES                            │
│   Conversas                          │
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
│ ─────────────────────────            │
│   Instrucoes                         │
│   Sistema                            │
│   Ajuda                              │
│   [Sair]                             │
└──────────────────────────────────────┘
6 grupos + footer, escaneamento hierarquico
```

## Consideracoes Tecnicas

- Manter backwards compatibility (mesmas rotas)
- Nao mudar comportamento de active state
- Componente SidebarSection deve ser reutilizavel
- Considerar futura colapsabilidade dos grupos (out of scope desta sprint)
