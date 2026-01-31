# Epic 06: Sidebar Navigation

## Objetivo

Adicionar entrada "Monitor" no sidemenu principal do dashboard.

## Contexto

A página `/monitor` precisa ser acessível pelo sidemenu. A entrada deve ficar entre "Pool de Chips" e "Instruções".

---

## Story 6.1: Atualizar Sidebar Desktop

### Objetivo
Adicionar item "Monitor" no sidebar principal.

### Tarefas

1. **Editar sidebar.tsx:**

**Arquivo:** `dashboard/components/dashboard/sidebar.tsx`

```typescript
'use client'

import Link from 'next/link'
import type { Route } from 'next'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  Megaphone,
  FileText,
  Building2,
  Settings,
  HelpCircle,
  Power,
  Smartphone,
  Activity,  // ADICIONAR
  type LucideIcon,
} from 'lucide-react'

interface NavItem {
  name: string
  href: string
  icon: LucideIcon
}

const navigation: NavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Campanhas', href: '/campanhas', icon: Megaphone },
  { name: 'Pool de Chips', href: '/chips', icon: Smartphone },
  { name: 'Monitor', href: '/monitor', icon: Activity },  // ADICIONAR
  { name: 'Instrucoes', href: '/instrucoes', icon: FileText },
  { name: 'Hospitais Bloqueados', href: '/hospitais/bloqueados', icon: Building2 },
  { name: 'Sistema', href: '/sistema', icon: Settings },
  { name: 'Ajuda', href: '/ajuda', icon: HelpCircle },
]

// ... resto do componente permanece igual
```

### DoD

- [ ] Import de `Activity` adicionado
- [ ] Item "Monitor" adicionado ao array `navigation`
- [ ] Posicionado após "Pool de Chips"
- [ ] Link aponta para `/monitor`
- [ ] Navegação funciona

---

## Story 6.2: Atualizar Bottom Nav Mobile

### Objetivo
Adicionar "Monitor" na navegação mobile (se aplicável).

### Tarefas

1. **Verificar se bottom-nav.tsx existe e incluir Monitor:**

**Arquivo:** `dashboard/components/dashboard/bottom-nav.tsx` (se existir)

```typescript
// Adicionar ao array de navegação:
{ name: 'Monitor', href: '/monitor', icon: Activity },
```

> **Nota:** O bottom nav mobile geralmente tem espaço limitado (4-5 itens).
> Se já estiver cheio, pode ser necessário:
> - Agrupar itens em um menu "Mais"
> - Ou não incluir Monitor no mobile (acessível pelo menu hamburguer)

### DoD

- [ ] Verificar se bottom-nav existe
- [ ] Se existir espaço, adicionar Monitor
- [ ] Se não existir espaço, documentar decisão

---

## Story 6.3: Verificar Highlight de Rota Ativa

### Objetivo
Garantir que o item "Monitor" fica destacado quando a rota está ativa.

### Tarefas

1. **Verificar lógica de isActive no sidebar:**

```typescript
// A lógica existente deve funcionar:
const isActive =
  pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href))

// Para /monitor, isso significa:
// - pathname === '/monitor' → true
// - pathname.startsWith('/monitor') → true (para sub-rotas futuras)
```

2. **Testar navegação:**
- Acessar `/monitor`
- Verificar que o item fica destacado (cor/background diferentes)

### DoD

- [ ] Item Monitor destacado quando ativo
- [ ] Navegação entre páginas funciona
- [ ] Highlight não permanece incorretamente em outras páginas

---

## Checklist do Épico

- [ ] **S42.E06.1** - Sidebar desktop atualizado
- [ ] **S42.E06.2** - Bottom nav atualizado (ou decisão documentada)
- [ ] **S42.E06.3** - Highlight de rota ativa funcionando
- [ ] Navegação `/monitor` acessível
- [ ] Ícone `Activity` visível
- [ ] Build passa sem erros

---

## Validação

```bash
cd dashboard

# Build
npm run build

# Dev server
npm run dev

# Verificar:
# 1. Sidebar mostra "Monitor" entre "Pool de Chips" e "Instruções"
# 2. Clicar em "Monitor" navega para /monitor
# 3. Item fica destacado quando em /monitor
# 4. Navegação para outras páginas remove highlight
```
