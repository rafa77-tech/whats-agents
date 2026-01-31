# Epic 01: Rename Scheduler → Warmup

## Objetivo

Renomear a rota `/chips/scheduler` para `/chips/warmup`, atualizando todos os arquivos relacionados (componentes, APIs, navegação, testes).

## Contexto

A página atual "Scheduler" dentro de `/chips` é dedicada a **atividades de warmup** dos chips (conversa par, marcar lido, entrar grupo, etc.). O nome "Scheduler" é genérico e não comunica a função real.

"Warmup" é mais específico e alinhado com a terminologia do sistema.

### Arquivos Afetados

| Categoria | Arquivo | Mudança |
|-----------|---------|---------|
| **Page** | `app/(dashboard)/chips/scheduler/page.tsx` | Mover para `warmup/page.tsx` |
| **API** | `app/api/dashboard/chips/scheduler/route.ts` | Mover para `warmup/route.ts` |
| **API Stats** | `app/api/dashboard/chips/scheduler/stats/route.ts` | Mover para `warmup/stats/route.ts` |
| **Component** | `components/chips/scheduler-page-content.tsx` | Renomear para `warmup-page-content.tsx` |
| **Nav Desktop** | `components/chips/chips-module-sidebar.tsx` | Atualizar href e label |
| **Nav Mobile** | `components/chips/chips-mobile-nav.tsx` | Atualizar href |
| **Index** | `components/chips/index.ts` | Atualizar export |
| **API Client** | `lib/api/chips.ts` | Atualizar URLs |
| **E2E Test** | `e2e/chips.e2e.ts` | Atualizar URLs e labels |

---

## Story 1.1: Mover Diretório da Page

### Objetivo
Renomear o diretório da página de scheduler para warmup.

### Tarefas

1. **Criar novo diretório:**
```bash
mkdir -p dashboard/app/(dashboard)/chips/warmup
```

2. **Mover e atualizar page.tsx:**

**Arquivo:** `dashboard/app/(dashboard)/chips/warmup/page.tsx`
```typescript
/**
 * Warmup Page - Sprint 42
 *
 * Página de atividades de warmup dos chips.
 * Renomeado de /chips/scheduler para /chips/warmup.
 */

import { Suspense } from 'react'
import { Metadata } from 'next'
import { WarmupPageContent } from '@/components/chips/warmup-page-content'

export const metadata: Metadata = {
  title: 'Warmup | Chips | Julia Dashboard',
  description: 'Atividades de warmup dos chips',
}

function WarmupSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-8 w-48 rounded bg-gray-200" />
      <div className="grid grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 rounded bg-gray-200" />
        ))}
      </div>
      <div className="h-96 rounded bg-gray-200" />
    </div>
  )
}

export default function WarmupPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-[1400px] p-6">
        <Suspense fallback={<WarmupSkeleton />}>
          <WarmupPageContent />
        </Suspense>
      </div>
    </div>
  )
}
```

3. **Remover diretório antigo:**
```bash
rm -rf dashboard/app/(dashboard)/chips/scheduler
```

### DoD

- [ ] Diretório `chips/warmup` criado
- [ ] `page.tsx` movido e atualizado
- [ ] Diretório `chips/scheduler` removido
- [ ] Import de `WarmupPageContent` correto
- [ ] Metadata atualizado

---

## Story 1.2: Mover Diretórios das APIs

### Objetivo
Renomear as rotas de API de scheduler para warmup.

### Tarefas

1. **Criar estrutura de diretórios:**
```bash
mkdir -p dashboard/app/api/dashboard/chips/warmup/stats
```

2. **Mover route.ts principal:**

**Arquivo:** `dashboard/app/api/dashboard/chips/warmup/route.ts`
```typescript
/**
 * API: GET /api/dashboard/chips/warmup
 *
 * Lista atividades de warmup.
 * Renomeado de /scheduler para /warmup (Sprint 42).
 */

import { NextRequest, NextResponse } from 'next/server'
import type { ScheduledActivity } from '@/types/chips'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const todayInSP = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Sao_Paulo' })
  const date = searchParams.get('date') || todayInSP

  // TODO: Substituir por dados reais quando tabela de warmup existir
  const activities: ScheduledActivity[] = [
    // ... mock data mantido
  ]

  return NextResponse.json(activities)
}
```

3. **Mover route.ts de stats:**

**Arquivo:** `dashboard/app/api/dashboard/chips/warmup/stats/route.ts`
```typescript
/**
 * API: GET /api/dashboard/chips/warmup/stats
 *
 * Estatísticas de warmup.
 * Renomeado de /scheduler/stats para /warmup/stats (Sprint 42).
 */

// Conteúdo igual ao anterior, apenas renomeado
```

4. **Remover diretórios antigos:**
```bash
rm -rf dashboard/app/api/dashboard/chips/scheduler
```

### DoD

- [ ] Diretório `api/dashboard/chips/warmup` criado
- [ ] `route.ts` movido
- [ ] `stats/route.ts` movido
- [ ] Diretório `api/dashboard/chips/scheduler` removido

---

## Story 1.3: Renomear Componente

### Objetivo
Renomear o componente de scheduler-page-content para warmup-page-content.

### Tarefas

1. **Renomear arquivo:**
```bash
mv dashboard/components/chips/scheduler-page-content.tsx \
   dashboard/components/chips/warmup-page-content.tsx
```

2. **Atualizar conteúdo do componente:**

**Arquivo:** `dashboard/components/chips/warmup-page-content.tsx`

```typescript
/**
 * Warmup Page Content - Sprint 42
 *
 * Conteúdo da página de atividades de warmup.
 * Renomeado de SchedulerPageContent (Sprint 42).
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import type { Route } from 'next'
import { ChevronLeft, RefreshCw, Flame, CheckCircle, XCircle, Clock } from 'lucide-react'
// ... imports

// Renomear export
export function WarmupPageContent() {
  // ... mesmo conteúdo, apenas atualizar:

  // Título
  <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
    <Flame className="h-6 w-6" />  {/* Ícone mais relevante */}
    Warmup de Atividades
  </h1>
  <p className="mt-1 text-sm text-gray-600">
    Visualize e monitore as atividades de warmup agendadas
  </p>

  // Atualizar URLs no fetch:
  const [activitiesData, statsData] = await Promise.all([
    chipsApi.getWarmupActivities(params),  // Renomear função
    chipsApi.getWarmupStats(selectedDate || undefined),  // Renomear função
  ])
}
```

3. **Atualizar index.ts:**

**Arquivo:** `dashboard/components/chips/index.ts`
```typescript
// Remover linha antiga:
// export { SchedulerPageContent } from './scheduler-page-content'

// Adicionar nova:
export { WarmupPageContent } from './warmup-page-content'
```

### DoD

- [ ] Arquivo renomeado para `warmup-page-content.tsx`
- [ ] Export renomeado para `WarmupPageContent`
- [ ] Título e descrição atualizados
- [ ] Ícone atualizado para `Flame` (ou manter `Calendar`)
- [ ] `index.ts` atualizado

---

## Story 1.4: Atualizar Navegação

### Objetivo
Atualizar links de navegação para apontar para `/chips/warmup`.

### Tarefas

1. **Atualizar sidebar desktop:**

**Arquivo:** `dashboard/components/chips/chips-module-sidebar.tsx`

Localizar (aproximadamente linha 47):
```typescript
// ANTES:
{ name: 'Scheduler', href: '/chips/scheduler', icon: Calendar }

// DEPOIS:
{ name: 'Warmup', href: '/chips/warmup', icon: Flame }
```

2. **Atualizar nav mobile:**

**Arquivo:** `dashboard/components/chips/chips-mobile-nav.tsx`

Localizar (aproximadamente linha 21):
```typescript
// ANTES:
{ name: 'Scheduler', href: '/chips/scheduler' }

// DEPOIS:
{ name: 'Warmup', href: '/chips/warmup' }
```

3. **Adicionar import do ícone Flame (se necessário):**
```typescript
import { Flame } from 'lucide-react'
```

### DoD

- [ ] Sidebar desktop atualizado
- [ ] Nav mobile atualizado
- [ ] Ícone Flame importado (se usado)
- [ ] Navegação funciona corretamente

---

## Story 1.5: Atualizar API Client

### Objetivo
Atualizar URLs no cliente de API para usar `/warmup` em vez de `/scheduler`.

### Tarefas

1. **Atualizar lib/api/chips.ts:**

**Arquivo:** `dashboard/lib/api/chips.ts`

```typescript
// Localizar funções (aproximadamente linhas 220-237):

// ANTES:
async getScheduledActivities(params?: { date?: string; limit?: number }) {
  const searchParams = new URLSearchParams()
  // ...
  const response = await fetch(`/api/dashboard/chips/scheduler?${searchParams}`)
  // ...
}

async getSchedulerStats(date?: string) {
  // ...
  const response = await fetch(`/api/dashboard/chips/scheduler/stats?${searchParams}`)
  // ...
}

// DEPOIS:
async getWarmupActivities(params?: { date?: string; limit?: number }) {
  const searchParams = new URLSearchParams()
  if (params?.date) searchParams.set('date', params.date)
  if (params?.limit) searchParams.set('limit', params.limit.toString())
  const response = await fetch(`/api/dashboard/chips/warmup?${searchParams}`)
  if (!response.ok) throw new Error('Failed to fetch warmup activities')
  return response.json() as Promise<ScheduledActivity[]>
}

async getWarmupStats(date?: string) {
  const searchParams = new URLSearchParams()
  if (date) searchParams.set('date', date)
  const response = await fetch(`/api/dashboard/chips/warmup/stats?${searchParams}`)
  if (!response.ok) throw new Error('Failed to fetch warmup stats')
  return response.json() as Promise<SchedulerStats>
}
```

### DoD

- [ ] Função `getScheduledActivities` → `getWarmupActivities`
- [ ] Função `getSchedulerStats` → `getWarmupStats`
- [ ] URLs atualizadas para `/warmup`
- [ ] Componente `WarmupPageContent` usa novas funções

---

## Story 1.6: Atualizar Testes E2E

### Objetivo
Atualizar testes E2E para refletir o novo path `/warmup`.

### Tarefas

1. **Atualizar e2e/chips.e2e.ts:**

**Arquivo:** `dashboard/e2e/chips.e2e.ts`

```typescript
// Localizar bloco de testes (aproximadamente linhas 92-104):

// ANTES:
describe('Scheduler Page', () => {
  test('should load scheduler page', async ({ page }) => {
    await page.goto('/chips/scheduler')
    await expect(page).toHaveURL(/chips\/scheduler/)
  })

  test('should have scheduler link in navigation', async ({ page }) => {
    await page.goto('/chips/scheduler')
    const nav = page.locator('nav')
    await expect(nav).toContainText('scheduler', { ignoreCase: true })
  })
})

// DEPOIS:
describe('Warmup Page', () => {
  test('should load warmup page', async ({ page }) => {
    await page.goto('/chips/warmup')
    await expect(page).toHaveURL(/chips\/warmup/)
  })

  test('should have warmup link in navigation', async ({ page }) => {
    await page.goto('/chips/warmup')
    const nav = page.locator('nav')
    await expect(nav).toContainText('warmup', { ignoreCase: true })
  })

  test('should display warmup activities title', async ({ page }) => {
    await page.goto('/chips/warmup')
    await expect(page.locator('h1')).toContainText('Warmup')
  })
})
```

### DoD

- [ ] Describe block renomeado para 'Warmup Page'
- [ ] URLs atualizadas para `/chips/warmup`
- [ ] Regex atualizado para `chips\/warmup`
- [ ] Assertions atualizadas para 'warmup'
- [ ] Testes passam localmente

---

## Checklist do Épico

- [ ] **S42.E01.1** - Page movida para `/chips/warmup`
- [ ] **S42.E01.2** - APIs movidas para `/api/dashboard/chips/warmup`
- [ ] **S42.E01.3** - Componente renomeado para `WarmupPageContent`
- [ ] **S42.E01.4** - Navegação atualizada (sidebar + mobile)
- [ ] **S42.E01.5** - API client atualizado
- [ ] **S42.E01.6** - Testes E2E atualizados
- [ ] Diretórios antigos removidos
- [ ] Build passa sem erros
- [ ] Navegação funciona

---

## Comandos de Validação

```bash
cd dashboard

# Verificar que não há referências ao path antigo
grep -r "scheduler" app/ components/ lib/ --include="*.tsx" --include="*.ts" | grep -v node_modules

# Build
npm run build

# Testes
npm run test

# E2E (se configurado)
npm run test:e2e
```
