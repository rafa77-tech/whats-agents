# EPICO 02: Performance & Real-Time

## Contexto

A pagina /conversas tem problemas de performance significativos: polling duplo quando SSE falha, query N+1 para buscar last_message (busca TODAS as interacoes), categorização feita em JS apos `.limit(200)` (perde conversas), e chat-panel usa fetch manual ao inves de SWR.

## Escopo

- **Incluido**: Eliminar polling duplo, otimizar query last_message, mover categorização para SQL, migrar chat-panel para SWR
- **Excluido**: Mudanças de layout/UX (Epics 04-05), bugs de dados (Epic 01)

---

## Tarefa 2.1: Eliminar polling duplo no chat-panel

### Objetivo

Remover o `setInterval(fetchConversation, 10000)` do chat-panel.tsx pois `useConversationStream` ja tem fallback de 10s polling via SWR invalidation.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `dashboard/app/(dashboard)/conversas/components/chat-panel.tsx` |

### Implementacao

```typescript
// REMOVER este useEffect inteiro (linhas 190-198):
useEffect(() => {
  setLoading(true)
  setFeedbackMap({})
  fetchConversation()
  const interval = setInterval(fetchConversation, 10000) // ← REMOVER
  return () => clearInterval(interval)                     // ← REMOVER
}, [fetchConversation])

// SUBSTITUIR por:
useEffect(() => {
  setLoading(true)
  setFeedbackMap({})
  fetchConversation()
}, [fetchConversation])

// O useConversationStream ja faz:
// 1. SSE quando disponivel → invalida SWR → refetch
// 2. Fallback polling 10s quando SSE falha → invalida SWR → refetch
```

### Testes Obrigatorios

**Unitarios:**
- [ ] Mensagens atualizam via SSE (event handler chamado)
- [ ] Mensagens atualizam via fallback polling quando SSE falha
- [ ] Nenhum setInterval residual apos unmount

### Definition of Done

- [ ] Zero `setInterval` no chat-panel.tsx
- [ ] Real-time funcional via SSE com fallback
- [ ] Testes passando

### Estimativa

30min

---

## Tarefa 2.2: Migrar chat-panel para SWR

### Objetivo

Substituir fetch manual + useState no chat-panel por `useConversationDetail` hook (que ja existe em hooks.ts). Isso elimina duplicacao, adiciona cache deduplication, e integra com o SSE invalidation.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `dashboard/app/(dashboard)/conversas/components/chat-panel.tsx` |

### Implementacao

```typescript
// ANTES: fetch manual com useState
const [loading, setLoading] = useState(true)
const [conversation, setConversation] = useState<ConversationDetail | null>(null)

const fetchConversation = useCallback(async () => {
  const response = await fetch(`/api/conversas/${conversationId}`)
  // ...
}, [conversationId])

// DEPOIS: SWR hook
import { useConversationDetail } from '@/lib/conversas/hooks'

const { conversation, isLoading: loading, refresh } = useConversationDetail(conversationId)

// SSE agora invalida o SWR cache automaticamente (ja faz isso em use-conversation-stream.ts:49)
useConversationStream(conversationId, {
  onEvent: () => refresh(), // Forca revalidacao imediata
})
```

**Remover:** `fetchConversation`, o `useState` de conversation e loading, o useEffect de polling.

**Manter:** `feedbackMap`, `changingControl`, `sendError` como estado local (nao sao dados do servidor).

### Testes Obrigatorios

**Unitarios:**
- [ ] Chat-panel renderiza com dados do SWR hook
- [ ] SSE event trigger revalidacao do SWR
- [ ] Estado de loading funciona corretamente
- [ ] Troca de conversationId limpa feedbackMap

### Definition of Done

- [ ] Zero fetch manual no chat-panel
- [ ] Usa useConversationDetail do hooks.ts
- [ ] Cache SWR compartilhado com sidebar
- [ ] Testes passando

### Estimativa

2h

---

## Tarefa 2.3: Otimizar query de last_message (eliminar N+1)

### Objetivo

A query atual busca TODAS as interacoes de todas as conversas do batch para extrair apenas a ultima mensagem de cada. Substituir por query otimizada que busca 1 por conversa.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `dashboard/app/api/conversas/route.ts` |

### Implementacao

**Opcao A — Subquery com DISTINCT ON (recomendada):**

Criar uma RPC SQL ou usar raw query:

```sql
-- Buscar ultima interacao por conversa
SELECT DISTINCT ON (conversation_id)
  conversation_id,
  conteudo,
  autor_tipo,
  created_at
FROM interacoes
WHERE conversation_id = ANY($1)
ORDER BY conversation_id, created_at DESC;
```

**Opcao B — Usar campo last_message da tabela conversations:**

Se a tabela `conversations` ja tiver um campo ou puder ser adicionado, e a melhor opcao. Verificar se existe `last_message_content` ou similar.

**Opcao C — Lateral Join via RPC:**

```sql
SELECT c.id, lm.*
FROM conversations c
LEFT JOIN LATERAL (
  SELECT conteudo, autor_tipo, created_at
  FROM interacoes
  WHERE conversation_id = c.id
  ORDER BY created_at DESC
  LIMIT 1
) lm ON true
WHERE c.id = ANY($1);
```

### Testes Obrigatorios

**Unitarios:**
- [ ] Retorna exatamente 1 mensagem por conversa
- [ ] Retorna a mensagem mais recente
- [ ] Conversa sem mensagens retorna null
- [ ] Performance: < 100ms para 200 conversas

**Integracao:**
- [ ] API /api/conversas retorna last_message correto
- [ ] last_message_direction correto (entrada/saida)

### Definition of Done

- [ ] Query busca exatamente 1 msg por conversa (nao todas)
- [ ] Performance mensuravel (< 100ms para batch de 200)
- [ ] Testes passando

### Estimativa

3h

---

## Tarefa 2.4: Mover categorização de tabs para SQL (server-side)

### Objetivo

Atualmente a API busca `.limit(200)` conversas e categoriza em JS. Se houver mais de 200 conversas, as que ficam fora do limit podem ser de "Atencao" e nao aparecem. Mover a categorização para o lado SQL.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `dashboard/app/api/conversas/route.ts` |
| Criar (opcional) | Migration com RPC `list_supervised_conversations` |

### Implementacao

**Opcao A — Filtro SQL por tab (recomendada):**

Adicionar WHERE clauses ao query principal baseado no tab:

```typescript
if (tab === 'atencao') {
  // Handoff OU sentimento negativo OU espera > 60min
  query = query.or(
    'controlled_by.eq.human,' +
    'sentimento_score.lte.-2'
  )
  // Para espera > 60min: filtrar em JS apenas entre os resultados
  // (mais simples que subquery)
}

if (tab === 'encerradas') {
  query = query.in('status', ['completed', 'archived'])
    .gte('updated_at', twoDaysAgo)
}

if (tab === 'aguardando') {
  query = query.eq('controlled_by', 'ai')
    .eq('status', 'active')
  // Filtrar em JS: last_message_direction === 'saida'
}

if (tab === 'julia_ativa') {
  query = query.eq('controlled_by', 'ai')
    .eq('status', 'active')
  // Filtrar em JS: last_message_direction !== 'saida' ou sem filtro
}
```

**Opcao B — RPC SQL completa:**

Criar function que retorna conversas ja categorizadas com paginação real.

### Consideracoes

- Manter `.limit()` adequado por tab (ex: 100 para atencao, 200 para julia_ativa)
- Paginacao deve ser server-side agora (SQL OFFSET/LIMIT)
- Remover categorização em JS (`categorizeConversation` vira helper para fallback apenas)

### Testes Obrigatorios

**Unitarios:**
- [ ] Tab atencao retorna handoffs + sentimento negativo + espera longa
- [ ] Tab julia_ativa retorna apenas conversas AI ativas respondendo
- [ ] Tab aguardando retorna apenas conversas AI aguardando medico
- [ ] Tab encerradas retorna completadas das ultimas 48h
- [ ] Paginacao funcional por tab (page 1, page 2)
- [ ] Total count correto por tab

**Integracao:**
- [ ] API com tab=atencao nao perde conversas por causa de limit
- [ ] Performance aceitavel (< 200ms por request)

### Definition of Done

- [ ] Categorização acontece no SQL (WHERE clauses), nao em JS
- [ ] Paginacao real (SQL OFFSET/LIMIT), nao slice em JS
- [ ] Tab atencao mostra TODAS as conversas que precisam de atencao
- [ ] Testes passando

### Estimativa

4h
