# Sprint 34 - UX Refinements Dashboard

## Visao Geral

**Objetivo:** Refinar a experiencia do usuario no dashboard com foco em feedback de acoes, consistencia de estados e resiliencia de formularios.

**Inicio:** 17/01/2026
**Duracao Estimada:** 1 semana
**Responsavel:** Dev

---

## Contexto

Apos a Sprint 33 (Dashboard de Performance), identificamos 5 pontos de melhoria na experiencia do usuario:

1. **Feedback de Acoes Assincronas** - Mensagens de erro genericas
2. **Consistencia de Auto-Refresh** - Intervalos hardcoded dispersos
3. **Componentizacao Excessiva** - Wizard de campanha com 634 linhas
4. **Paginacao Funnel Drilldown** - Feedback visual limitado
5. **Formularios Multi-Step** - Perda de progresso ao fechar modal

---

## Stack de UI

O dashboard usa **shadcn/ui** (estilo new-york) com:
- Tailwind CSS para estilizacao
- Radix UI para primitivos acessiveis
- CVA para variantes de componentes
- Lucide React para icones

---

## Epicos da Sprint

### E00 - Setup Componentes shadcn

**Objetivo:** Instalar componentes shadcn necessarios para os demais epicos.

**Comandos:**
```bash
cd dashboard
npx shadcn@latest add skeleton
npx shadcn@latest add form
npx shadcn@latest add alert
npx shadcn@latest add sheet
npx shadcn@latest add sonner
```

**Componentes e Uso:**

| Componente | Uso | Epico |
|------------|-----|-------|
| Skeleton | Loading states em tabelas | E04 |
| Form | Validacao integrada zod + react-hook-form | E03, E05 |
| Alert | Mensagens de erro inline | E01 |
| Sheet | Wizard como drawer no mobile | E03 |
| Sonner | Toasts modernos com acoes | E01 |

**Criterios de Aceite:**
- [ ] Todos os componentes instalados
- [ ] Build passa sem erros
- [ ] Componentes aparecem em `components/ui/`

---

### E01 - Sistema de Erros Amigaveis

**Objetivo:** Mapear erros da API para mensagens especificas e acionaveis usando Alert + Sonner.

**Arquivos a criar/modificar:**
- `dashboard/lib/errors.ts` (novo)
- `dashboard/hooks/use-api-error.ts` (novo)
- `dashboard/components/campanhas/nova-campanha-wizard.tsx`
- `dashboard/components/instrucoes/nova-instrucao-dialog.tsx`
- `dashboard/app/(dashboard)/sistema/page.tsx`
- `dashboard/app/layout.tsx` (adicionar Sonner provider)

**Tarefas:**

| Task | Descricao | Arquivo |
|------|-----------|---------|
| E01.1 | Criar mapeamento de erros da API | `lib/errors.ts` |
| E01.2 | Criar hook `useApiError` | `hooks/use-api-error.ts` |
| E01.3 | Configurar Sonner no layout | `app/layout.tsx` |
| E01.4 | Integrar no wizard de campanhas | `nova-campanha-wizard.tsx` |
| E01.5 | Integrar no dialog de instrucoes | `nova-instrucao-dialog.tsx` |
| E01.6 | Integrar na pagina de sistema | `sistema/page.tsx` |

**Mapeamento de Erros:**

```typescript
// lib/errors.ts
export const API_ERROR_MESSAGES: Record<string, ErrorConfig> = {
  // Campanhas
  'campanha_nome_duplicado': {
    message: 'Ja existe uma campanha com esse nome.',
    action: { label: 'Ver campanhas', href: '/campanhas' }
  },
  'campanha_sem_destinatarios': {
    message: 'Nenhum medico corresponde aos filtros selecionados.',
    action: { label: 'Ajustar filtros', onClick: 'focus-filters' }
  },
  'campanha_corpo_invalido': {
    message: 'A mensagem contem variaveis invalidas.',
  },

  // Diretrizes
  'diretriz_conflito': {
    message: 'Ja existe uma instrucao ativa com esse escopo.',
  },
  'diretriz_vaga_nao_encontrada': {
    message: 'A vaga selecionada nao foi encontrada.',
  },

  // Generico
  'rate_limit': {
    message: 'Muitas requisicoes. Aguarde alguns segundos.',
    duration: 5000,
  },
  'unauthorized': {
    message: 'Sessao expirada. Faca login novamente.',
    action: { label: 'Fazer login', href: '/login' }
  },
  'server_error': {
    message: 'Erro interno. Nossa equipe foi notificada.',
  },
  'network_error': {
    message: 'Erro de conexao. Verifique sua internet.',
    action: { label: 'Tentar novamente', onClick: 'retry' }
  },
}
```

**Exemplo de Uso com Sonner:**

```tsx
// Antes
toast({
  variant: 'destructive',
  title: 'Erro',
  description: 'Nao foi possivel criar a campanha.',
})

// Depois
import { toast } from 'sonner'

toast.error('Ja existe uma campanha com esse nome', {
  action: {
    label: 'Ver existente',
    onClick: () => router.push('/campanhas')
  }
})
```

**Criterios de Aceite:**
- [ ] Sonner configurado no layout
- [ ] Erros da API mostram mensagens especificas
- [ ] Erros de rede mostram "Erro de conexao" com retry
- [ ] Erros 401 redirecionam para login
- [ ] Erros 429 mostram mensagem de rate limit
- [ ] Toast inclui acao quando aplicavel

---

### E02 - Centralizacao de Config Auto-Refresh

**Objetivo:** Criar configuracao centralizada para intervalos de auto-refresh por criticidade.

**Arquivos a criar/modificar:**
- `dashboard/lib/config.ts` (novo ou existente)
- `dashboard/components/dashboard/alerts-list.tsx`
- `dashboard/components/dashboard/activity-feed.tsx`
- `dashboard/app/(dashboard)/dashboard/page.tsx`

**Tarefas:**

| Task | Descricao | Arquivo |
|------|-----------|---------|
| E02.1 | Criar constantes de refresh por criticidade | `lib/config.ts` |
| E02.2 | Atualizar AlertsList para usar config | `alerts-list.tsx` |
| E02.3 | Atualizar ActivityFeed para usar config | `activity-feed.tsx` |
| E02.4 | Documentar uso | Comentarios inline |

**Configuracao:**

```typescript
// lib/config.ts
export const REFRESH_INTERVALS = {
  CRITICAL: 15_000,    // 15s - Alertas criticos, status Julia
  HIGH: 30_000,        // 30s - Metricas principais, funil
  NORMAL: 60_000,      // 60s - Activity feed, historico
  LOW: 120_000,        // 2min - Chips, dados menos volateis
} as const

export type RefreshPriority = keyof typeof REFRESH_INTERVALS
```

**Mapeamento de Componentes:**

| Componente | Antes | Depois |
|-----------|-------|--------|
| AlertsList | 30000 (hardcoded) | REFRESH_INTERVALS.CRITICAL |
| ActivityFeed | 30000 (hardcoded) | REFRESH_INTERVALS.NORMAL |
| StatusJulia | - | REFRESH_INTERVALS.CRITICAL |
| ChipPoolMetrics | - | REFRESH_INTERVALS.LOW |

**Criterios de Aceite:**
- [ ] Todos os intervalos vem de `REFRESH_INTERVALS`
- [ ] Nenhum magic number de intervalo no codigo
- [ ] Alertas criticos atualizam a cada 15s
- [ ] Activity feed atualiza a cada 60s

---

### E03 - Refatoracao Wizard Campanhas

**Objetivo:** Dividir o wizard de 634 linhas em componentes menores usando shadcn/form e sheet para mobile.

**Arquivos a criar/modificar:**
- `dashboard/components/campanhas/wizard/` (diretorio novo)
  - `index.ts`
  - `types.ts`
  - `schema.ts`
  - `use-campanha-form.ts`
  - `wizard-container.tsx`
  - `wizard-steps.tsx`
  - `step-configuracao.tsx`
  - `step-audiencia.tsx`
  - `step-mensagem.tsx`
  - `step-revisao.tsx`
- `dashboard/components/campanhas/nova-campanha-wizard.tsx` (refatorar)

**Tarefas:**

| Task | Descricao | Arquivo |
|------|-----------|---------|
| E03.1 | Extrair types e constantes | `wizard/types.ts` |
| E03.2 | Criar schema zod para validacao | `wizard/schema.ts` |
| E03.3 | Criar hook com react-hook-form | `wizard/use-campanha-form.ts` |
| E03.4 | Extrair Step1Configuracao | `wizard/step-configuracao.tsx` |
| E03.5 | Extrair Step2Audiencia | `wizard/step-audiencia.tsx` |
| E03.6 | Extrair Step3Mensagem | `wizard/step-mensagem.tsx` |
| E03.7 | Extrair Step4Revisao | `wizard/step-revisao.tsx` |
| E03.8 | Criar WizardSteps (progress) | `wizard/wizard-steps.tsx` |
| E03.9 | Criar container com Dialog/Sheet | `wizard/wizard-container.tsx` |
| E03.10 | Atualizar exports | `wizard/index.ts` |
| E03.11 | Refatorar wizard original | `nova-campanha-wizard.tsx` |

**Schema Zod:**

```typescript
// wizard/schema.ts
import { z } from 'zod'

export const campanhaSchema = z.object({
  // Step 1
  nome_template: z.string().min(3, 'Nome deve ter pelo menos 3 caracteres'),
  tipo_campanha: z.enum(['oferta_plantao', 'reativacao', 'followup', 'descoberta']),
  categoria: z.enum(['marketing', 'operacional', 'relacionamento']),
  objetivo: z.string().optional(),

  // Step 2
  audiencia_tipo: z.enum(['todos', 'filtrado']),
  especialidades: z.array(z.string()),
  regioes: z.array(z.string()),
  status_cliente: z.array(z.string()),

  // Step 3
  corpo: z.string().min(10, 'Mensagem deve ter pelo menos 10 caracteres'),
  tom: z.enum(['amigavel', 'profissional', 'urgente', 'casual']),

  // Step 4
  agendar: z.boolean(),
  agendar_para: z.string().optional(),
})

export type CampanhaFormData = z.infer<typeof campanhaSchema>
```

**Estrutura Final:**

```
components/campanhas/
├── nova-campanha-wizard.tsx     <- Re-export simples (~10 linhas)
└── wizard/
    ├── index.ts                 <- Exports publicos
    ├── types.ts                 <- Interfaces e constantes (~50 linhas)
    ├── schema.ts                <- Validacao zod (~40 linhas)
    ├── use-campanha-form.ts     <- Hook de estado (~60 linhas)
    ├── wizard-container.tsx     <- Container Dialog/Sheet (~80 linhas)
    ├── wizard-steps.tsx         <- Progress indicator (~50 linhas)
    ├── step-configuracao.tsx    <- Step 1 (~70 linhas)
    ├── step-audiencia.tsx       <- Step 2 (~80 linhas)
    ├── step-mensagem.tsx        <- Step 3 (~60 linhas)
    └── step-revisao.tsx         <- Step 4 (~80 linhas)
```

**Mobile UX com Sheet:**

```tsx
// wizard-container.tsx
import { useMediaQuery } from '@/hooks/use-media-query'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { Sheet, SheetContent } from '@/components/ui/sheet'

export function WizardContainer({ open, onOpenChange, children }) {
  const isDesktop = useMediaQuery('(min-width: 768px)')

  if (isDesktop) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-4xl">{children}</DialogContent>
      </Dialog>
    )
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="h-[90vh]">{children}</SheetContent>
    </Sheet>
  )
}
```

**Criterios de Aceite:**
- [ ] Nenhum arquivo > 100 linhas
- [ ] Validacao com zod funcionando
- [ ] Mobile usa Sheet (drawer bottom)
- [ ] Desktop usa Dialog
- [ ] Testes para schema e hook
- [ ] Comportamento identico ao atual
- [ ] Build passa sem erros

---

### E04 - Melhorias Paginacao Funnel Drilldown

**Objetivo:** Melhorar feedback visual durante navegacao usando Skeleton.

**Arquivos a modificar:**
- `dashboard/components/dashboard/funnel-drilldown-modal.tsx`
- `dashboard/components/ui/table-skeleton.tsx` (novo)

**Tarefas:**

| Task | Descricao |
|------|-----------|
| E04.1 | Criar componente TableSkeleton |
| E04.2 | Manter dados anteriores durante fetch (com opacity) |
| E04.3 | Adicionar indicador "Mostrando X-Y de Z" |
| E04.4 | Melhorar feedback de busca vazia |

**TableSkeleton Component:**

```tsx
// components/ui/table-skeleton.tsx
import { Skeleton } from '@/components/ui/skeleton'
import { TableRow, TableCell } from '@/components/ui/table'

interface TableSkeletonProps {
  rows?: number
  columns?: number
}

export function TableSkeleton({ rows = 5, columns = 6 }: TableSkeletonProps) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <TableRow key={i}>
          {Array.from({ length: columns }).map((_, j) => (
            <TableCell key={j}>
              <Skeleton className="h-4 w-full" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  )
}
```

**Melhorias no Modal:**

```tsx
// funnel-drilldown-modal.tsx

// 1. Loading entre paginas - overlay com dados anteriores
{loading && data?.items.length > 0 ? (
  <div className="relative">
    <div className="pointer-events-none opacity-50">
      {/* Tabela com dados anteriores */}
    </div>
    <div className="absolute inset-0 flex items-center justify-center bg-white/50">
      <Loader2 className="h-6 w-6 animate-spin" />
    </div>
  </div>
) : loading ? (
  <TableSkeleton rows={10} columns={6} />
) : (
  /* Dados normais */
)}

// 2. Indicador de total
<div className="flex items-center justify-between text-sm text-gray-500">
  <span>
    Mostrando {((page - 1) * pageSize) + 1}-{Math.min(page * pageSize, data.total)} de {data.total}
  </span>
  <span>Pagina {page} de {totalPages}</span>
</div>

// 3. Busca vazia
{data?.items.length === 0 && debouncedSearch && (
  <div className="py-8 text-center">
    <Search className="mx-auto mb-2 h-8 w-8 text-gray-300" />
    <p className="text-gray-600">Nenhum medico encontrado para "{debouncedSearch}"</p>
    <Button variant="ghost" size="sm" onClick={() => setSearch('')}>
      Limpar busca
    </Button>
  </div>
)}
```

**Criterios de Aceite:**
- [ ] Skeleton no primeiro load
- [ ] Dados anteriores visiveis durante paginacao
- [ ] Mostra "X-Y de Z medicos"
- [ ] Busca sem resultados tem botao "Limpar"
- [ ] Botoes de paginacao desabilitados durante fetch

---

### E05 - Draft State no Wizard de Campanhas

**Objetivo:** Salvar progresso do wizard em localStorage para recuperacao.

**Arquivos a criar/modificar:**
- `dashboard/hooks/use-draft-state.ts` (novo)
- `dashboard/components/campanhas/wizard/use-campanha-form.ts`
- `dashboard/components/campanhas/wizard/wizard-container.tsx`
- `dashboard/components/campanhas/wizard/draft-recovery-dialog.tsx` (novo)

**Tarefas:**

| Task | Descricao |
|------|-----------|
| E05.1 | Criar hook generico `useDraftState` |
| E05.2 | Integrar no `use-campanha-form` |
| E05.3 | Criar dialog de recuperacao de draft |
| E05.4 | Adicionar botao "Descartar rascunho" |
| E05.5 | Limpar draft apos submit |
| E05.6 | Validar draft contra schema (evitar crashes) |

**Hook useDraftState:**

```typescript
// hooks/use-draft-state.ts
import { useState, useEffect, useCallback } from 'react'
import { z } from 'zod'

interface DraftConfig<T> {
  key: string
  schema: z.ZodSchema<T>
  expiryHours?: number
}

interface Draft<T> {
  data: T
  step: number
  savedAt: string
}

export function useDraftState<T>({ key, schema, expiryHours = 24 }: DraftConfig<T>) {
  const [hasDraft, setHasDraft] = useState(false)
  const [draftData, setDraftData] = useState<Draft<T> | null>(null)

  // Verificar se existe draft valido
  useEffect(() => {
    const stored = localStorage.getItem(key)
    if (!stored) return

    try {
      const draft = JSON.parse(stored) as Draft<T>
      const savedAt = new Date(draft.savedAt)
      const now = new Date()
      const hoursAgo = (now.getTime() - savedAt.getTime()) / (1000 * 60 * 60)

      if (hoursAgo > expiryHours) {
        localStorage.removeItem(key)
        return
      }

      // Validar contra schema
      const result = schema.safeParse(draft.data)
      if (result.success) {
        setDraftData(draft)
        setHasDraft(true)
      } else {
        localStorage.removeItem(key)
      }
    } catch {
      localStorage.removeItem(key)
    }
  }, [key, schema, expiryHours])

  const saveDraft = useCallback((data: T, step: number) => {
    const draft: Draft<T> = {
      data,
      step,
      savedAt: new Date().toISOString(),
    }
    localStorage.setItem(key, JSON.stringify(draft))
  }, [key])

  const clearDraft = useCallback(() => {
    localStorage.removeItem(key)
    setHasDraft(false)
    setDraftData(null)
  }, [key])

  const restoreDraft = useCallback(() => {
    return draftData
  }, [draftData])

  return {
    hasDraft,
    saveDraft,
    clearDraft,
    restoreDraft,
  }
}
```

**Draft Recovery Dialog:**

```tsx
// wizard/draft-recovery-dialog.tsx
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'

interface DraftRecoveryDialogProps {
  open: boolean
  savedAt: string
  onRestore: () => void
  onDiscard: () => void
}

export function DraftRecoveryDialog({
  open,
  savedAt,
  onRestore,
  onDiscard,
}: DraftRecoveryDialogProps) {
  return (
    <AlertDialog open={open}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Continuar rascunho?</AlertDialogTitle>
          <AlertDialogDescription>
            Voce tem um rascunho salvo de{' '}
            {formatDistanceToNow(new Date(savedAt), { addSuffix: true, locale: ptBR })}.
            Deseja continuar de onde parou?
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={onDiscard}>
            Comecar do zero
          </AlertDialogCancel>
          <AlertDialogAction onClick={onRestore}>
            Continuar rascunho
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
```

**Fluxo:**

```
1. Usuario abre wizard
2. IF localStorage tem draft valido:
   - Mostra DraftRecoveryDialog
   - [Continuar] -> Restaura form data e step
   - [Comecar do zero] -> Limpa draft, inicia vazio
3. A cada mudanca de step: saveDraft(formData, currentStep)
4. Ao submeter com sucesso: clearDraft()
5. Ao cancelar: mantem draft (para proxima vez)
```

**Criterios de Aceite:**
- [ ] Draft salva a cada mudanca de step
- [ ] Draft expira apos 24 horas
- [ ] Dialog pergunta se quer continuar
- [ ] Draft invalido e ignorado (schema validation)
- [ ] Submit limpa draft
- [ ] Botao para descartar draft no footer do wizard

---

## Definition of Done (DoD)

Todos os epicos devem atender:

- [ ] Codigo TypeScript strict (sem `any`)
- [ ] Build sem erros (`npm run build`)
- [ ] Lint sem erros (`npm run lint`)
- [ ] Testes para hooks customizados
- [ ] Comportamento igual ou melhor que anterior
- [ ] Responsivo (funciona em mobile)

---

## Ordem de Execucao

```
E00 (Setup) -> E01 (Erros) -> E02 (Config) -> E03 (Refatoracao) -> E05 (Draft) -> E04 (Paginacao)
     |              |              |               |                   |              |
     v              v              v               v                   v              v
  0.25 dia        1 dia         0.5 dia         1.5 dia              1 dia         0.5 dia
```

**Total estimado: ~4.75 dias**

---

## Checklist de Entrega

- [ ] E00 - Setup Componentes shadcn
- [ ] E01 - Sistema de Erros Amigaveis
- [ ] E02 - Centralizacao Config Auto-Refresh
- [ ] E03 - Refatoracao Wizard Campanhas
- [ ] E04 - Melhorias Paginacao Funnel Drilldown
- [ ] E05 - Draft State no Wizard de Campanhas

---

## Metricas de Sucesso

| Metrica | Antes | Depois |
|---------|-------|--------|
| Linhas no wizard | 634 | < 100 (container) |
| Magic numbers de interval | 4+ | 0 |
| Erros genericos | 100% | < 20% |
| Perda de form ao fechar | 100% | 0% |
| Componentes shadcn | 21 | 26 |

---

## Referencias

- Sprint 33: Dashboard de Performance
- Analise de UX: 17/01/2026
- shadcn/ui: https://ui.shadcn.com
- Convencoes: `app/CONVENTIONS.md`
- Regras Next.js: `docs/best-practices/nextjs-typescript-rules.md`
