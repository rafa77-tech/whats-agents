# ÉPICO 4: Integração na Dashboard

## Contexto

Conectar o widget ao page.tsx do dashboard, adicionar polling 5s, e garantir que funciona harmoniosamente com os outros 12 widgets existentes.

## Escopo

- **Incluído**: Fetch function, polling 5s, integração no layout, barrel export, testes de integração
- **Excluído**: Mudanças em outros widgets, novas funcionalidades

---

## Tarefa 4.1: Barrel Export do módulo

### Objetivo

Criar index.ts para exportar todos os componentes do message-flow de forma limpa.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Criar | `dashboard/components/dashboard/message-flow/index.ts` |

### Implementação

```typescript
export { MessageFlowWidget } from './message-flow-widget'
export { RadialGraph } from './radial-graph'
export { MobilePulse } from './mobile-pulse'
export { FlowLegend } from './flow-legend'
export { ParticleSystem } from './particle-system'
export { useParticles } from './use-particles'
```

### Definition of Done

- [ ] Import `from '@/components/dashboard/message-flow'` funciona
- [ ] `npm run typecheck` passa

### Estimativa

0.5 ponto

---

## Tarefa 4.2: Integrar no `page.tsx`

### Objetivo

Adicionar o fetch function, state, polling 5s, e o componente no layout do dashboard entre Operational Status e Chip Pool.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Modificar | `dashboard/app/(dashboard)/dashboard/page.tsx` |

### Implementação

**1. Adicionar import:**
```typescript
import { MessageFlowWidget } from '@/components/dashboard/message-flow'
import type { MessageFlowData } from '@/types/dashboard'
```

**2. Adicionar state:**
```typescript
const [messageFlowData, setMessageFlowData] = useState<MessageFlowData | null>(null)
```

**3. Adicionar fetch function:**
```typescript
const fetchMessageFlow = useCallback(async (): Promise<void> => {
  try {
    const response = await fetch('/api/dashboard/message-flow')
    if (!response.ok) throw new Error('Failed to fetch message flow')
    const data: MessageFlowData = await response.json()
    setMessageFlowData(data)
  } catch (error) {
    console.error('[dashboard] message-flow fetch error:', error)
    // Não limpar dados anteriores — manter último estado válido
  }
}, [])
```

**4. Adicionar ao useEffect de initial fetch:**
```typescript
// No Promise.all existente, adicionar fetchMessageFlow()
await Promise.all([
  fetchMetrics(),
  fetchQuality(),
  fetchOperational(),
  fetchMessageFlow(),  // ← adicionar
  // ... restante
])
```

**5. Polling 5s dedicado:**
```typescript
useEffect(() => {
  const interval = setInterval(() => {
    void fetchMessageFlow()
  }, 5000)

  return () => clearInterval(interval)
}, [fetchMessageFlow])
```

**6. Adicionar no JSX entre Operational Status e Chip Pool:**
```tsx
{/* Operational Status — existente */}
<section aria-label="Status operacional">
  <OperationalStatus data={operationalData} />
</section>

{/* ← NOVO: Message Flow Widget */}
<section aria-label="Fluxo de mensagens">
  <MessageFlowWidget
    data={messageFlowData}
    isLoading={isLoading}
  />
</section>

{/* Chip Pool — existente */}
<section aria-label="Pool de chips">
  ...
</section>
```

**7. Incluir no refresh manual:**
```typescript
// Na função handleRefresh existente, adicionar
await fetchMessageFlow()
```

### Performance

- Polling 5s é independente dos outros widgets
- Fetch silencioso (não mostra loading spinner em updates subsequentes)
- Em caso de erro, mantém último estado válido (sem flicker)
- Cleanup do interval no unmount

### Testes Obrigatórios

**Unitários:**
- [ ] fetchMessageFlow chama endpoint correto (`/api/dashboard/message-flow`)
- [ ] State atualiza com dados válidos
- [ ] Erro não limpa dados anteriores (resiliente)
- [ ] Polling 5s funciona (setInterval chamado com 5000)
- [ ] Cleanup do interval no unmount

**Integração:**
- [ ] Widget aparece entre Operational Status e Chip Pool no DOM
- [ ] `aria-label="Fluxo de mensagens"` presente na section
- [ ] Refresh manual inclui message-flow
- [ ] Initial fetch inclui message-flow no Promise.all

### Definition of Done

- [ ] Widget integrado no layout correto
- [ ] Polling 5s funciona
- [ ] Resiliente a erros de fetch
- [ ] Não quebra nenhum widget existente
- [ ] `npm run validate` passa
- [ ] `npm run build` passa

### Estimativa

3 pontos

---

## Tarefa 4.3: Testes de integração end-to-end do widget

### Objetivo

Garantir que o widget funciona com dados reais do Supabase e não introduz regressões no dashboard.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Criar | `dashboard/__tests__/components/dashboard/message-flow/message-flow-widget.test.tsx` |
| Criar | `dashboard/__tests__/api/dashboard/message-flow.test.ts` |

### Testes Obrigatórios

**API Route Tests (`message-flow.test.ts`):**
- [ ] GET retorna 200 com formato MessageFlowData
- [ ] chips[] contém apenas chips com status válido
- [ ] recentMessages[] contém apenas mensagens dos últimos 5 min
- [ ] messagesPerMinute é number >= 0
- [ ] updatedAt é ISO timestamp válido
- [ ] Resposta < 5KB payload
- [ ] Retorna 500 com error message em caso de falha

**Widget Component Tests (`message-flow-widget.test.tsx`):**
- [ ] Renderiza skeleton durante loading
- [ ] Renderiza "Nenhum chip ativo" com chips=[]
- [ ] Renderiza RadialGraph em desktop viewport
- [ ] Renderiza MobilePulse em mobile viewport
- [ ] Partículas aparecem quando recentMessages tem dados
- [ ] Badge msg/min atualiza com messagesPerMinute
- [ ] Não crasha com dados null
- [ ] Não crasha com dados parciais
- [ ] aria-label presente para acessibilidade
- [ ] prefers-reduced-motion: animações desabilitadas

**Regressão:**
- [ ] Dashboard page renderiza sem erros
- [ ] Todos os widgets existentes continuam funcionando
- [ ] Build passa sem warnings

### Definition of Done

- [ ] Todos os testes passando
- [ ] `npm run validate` passa (typecheck + lint + format + tests)
- [ ] `npm run build` passa
- [ ] Sem regressões nos testes existentes

### Estimativa

3 pontos

---

## Tarefa 4.4: Validação final

### Objetivo

Checklist final antes de considerar a sprint completa.

### Checklist

**Funcional:**
- [ ] Widget mostra chips ativos em tempo real
- [ ] Partículas animam para mensagens novas
- [ ] Julia "respira" quando idle
- [ ] Chips pulsam quando ativos
- [ ] Mobile mostra versão compacta
- [ ] Tablet mostra versão simplificada
- [ ] Desktop mostra grafo completo com legenda

**Qualidade:**
- [ ] `npm run validate` passa
- [ ] `npm run build` passa
- [ ] Zero `any` no código novo
- [ ] Zero warnings no build
- [ ] `prefers-reduced-motion` respeitado
- [ ] Dark mode funciona
- [ ] aria-labels presentes

**Performance:**
- [ ] 60fps com 20 partículas simultâneas
- [ ] Polling 5s não causa flicker
- [ ] API response < 200ms
- [ ] Payload < 5KB
- [ ] Sem memory leaks no polling

### Estimativa

1 ponto
