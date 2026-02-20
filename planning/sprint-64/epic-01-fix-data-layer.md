# EPICO 01: Fix Data Layer (Bugs Criticos)

## Contexto

A pagina /conversas tem bugs criticos que fazem conversas desaparecerem e funcionalidades quebrarem silenciosamente. O filtro por chip nao mostra conversas antigas, feedback de mensagens gera NaN, e notas do supervisor nao recarregam.

## Escopo

- **Incluido**: Backfill conversation_chips, fix bugs de codigo (NotesSection, feedback, unread_count), fix query de last_message
- **Excluido**: Mudancas de layout/UX (Epic 04-05), otimizacoes de performance (Epic 02), mobile (Epic 03)

---

## Tarefa 1.1: Backfill conversation_chips para conversas antigas

### Objetivo

Garantir que TODA conversa no banco tenha um registro em `conversation_chips` com o chip correto, para que filtros por chip funcionem.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Criar | `migrations/sprint-64/001_backfill_conversation_chips.sql` |

### Implementacao

```sql
-- Backfill: criar entries em conversation_chips para conversas que tem instance_id
-- mas nao tem registro na tabela de mapeamento

INSERT INTO conversation_chips (conversa_id, chip_id, active, created_at, updated_at)
SELECT
  c.id AS conversa_id,
  ch.id AS chip_id,
  true AS active,
  c.created_at,
  NOW()
FROM conversations c
JOIN whatsapp_instances wi ON c.instance_id = wi.instance_id
JOIN chips ch ON ch.instance_name = wi.instance_name
LEFT JOIN conversation_chips cc ON cc.conversa_id = c.id AND cc.active = true
WHERE cc.conversa_id IS NULL
  AND c.instance_id IS NOT NULL;
```

**Nota:** Rodar em batches se houver muitas conversas. Verificar que nao duplica entries existentes.

### Testes Obrigatorios

**Antes de rodar:**
- [ ] Contar conversas sem mapeamento: `SELECT COUNT(*) FROM conversations c LEFT JOIN conversation_chips cc ON c.id = cc.conversa_id WHERE cc.id IS NULL`
- [ ] Verificar que join instance_id → instance_name → chip funciona para amostra

**Depois de rodar:**
- [ ] Zero conversas sem mapeamento (exceto as que nao tem instance_id)
- [ ] Filtro por chip no dashboard mostra conversas antigas
- [ ] Tab counts batem com total de "Todos"

### Definition of Done

- [ ] Migration aplicada em producao
- [ ] Zero conversas com instance_id ficando sem conversation_chips
- [ ] Dashboard mostra todas conversas ao filtrar por chip

### Estimativa

2h (inclui validacao em producao)

---

## Tarefa 1.2: Fix NotesSection — useState para useEffect

### Objetivo

Corrigir o bug onde notas do supervisor nao recarregam ao trocar de conversa.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `dashboard/app/(dashboard)/conversas/components/doctor-context-panel.tsx` |

### Implementacao

```typescript
// ANTES (bug): useState como initializer para fetch
// Linha ~334
useState(() => {
  fetch(`/api/conversas/${conversationId}/notes`)
    .then(...)
})

// DEPOIS (correto): useEffect com dependencia em conversationId
useEffect(() => {
  let cancelled = false
  setLoaded(false)

  fetch(`/api/conversas/${conversationId}/notes`)
    .then((r) => r.json())
    .then((data) => {
      if (!cancelled) {
        setNotes((data.notes || []) as SupervisorNote[])
        setLoaded(true)
      }
    })
    .catch(() => {
      if (!cancelled) setLoaded(true)
    })

  return () => { cancelled = true }
}, [conversationId])
```

### Testes Obrigatorios

**Unitarios:**
- [ ] NotesSection carrega notas ao montar
- [ ] NotesSection recarrega notas ao mudar conversationId
- [ ] Cleanup cancela fetch pendente ao desmontar
- [ ] Estado de loading reseta ao trocar conversa

### Definition of Done

- [ ] `useEffect` com cleanup e dependencia em conversationId
- [ ] Notas recarregam ao clicar em outra conversa
- [ ] Sem race conditions (cancelled flag)
- [ ] Testes passando

### Estimativa

30min

---

## Tarefa 1.3: Fix feedback parseInt(UUID)

### Objetivo

Corrigir o envio de feedback em mensagens da Julia. Atualmente `parseInt(message.id)` retorna NaN quando o ID e UUID.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `dashboard/app/(dashboard)/conversas/components/chat-panel.tsx` |
| Modificar | `dashboard/app/api/conversas/[id]/feedback/route.ts` (se necessario) |

### Implementacao

```typescript
// ANTES (bug): parseInt de UUID
handleFeedback(message.id, parseInt(message.id), 'positive')

// DEPOIS: usar o ID diretamente (verificar tipo esperado pela API)
// Se API espera string:
handleFeedback(message.id, message.id, 'positive')

// Se API espera number e interacoes.id e bigint:
// Adicionar campo interacao_id ao tipo Message e usar esse
handleFeedback(message.id, message.interacao_id, 'positive')
```

**Investigar:** O tipo `Message` em `types/conversas.ts` — se `id` e o ID da interacao (bigint) ou UUID. Ajustar a interface `handleFeedback` conforme.

### Testes Obrigatorios

**Unitarios:**
- [ ] Feedback com ID numerico funciona
- [ ] Feedback com ID UUID funciona
- [ ] API recebe o ID correto no body

### Definition of Done

- [ ] Feedback funcional para mensagens da Julia
- [ ] Tipo correto enviado a API
- [ ] Testes passando

### Estimativa

1h

---

## Tarefa 1.4: Fix unread_count (hardcoded 0)

### Objetivo

Calcular unread_count real ao inves de retornar 0 hardcoded.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `dashboard/app/api/conversas/route.ts` |

### Implementacao

Adicionar ao enrichment query:

```typescript
// Opção 1: Contar interações do médico sem "leitura" pelo supervisor
// Definir "lida" como: ultima vez que supervisor abriu a conversa
// Para MVP: contar msgs do medico nas ultimas 24h que nao tem resposta da Julia

// Opção 2 (mais simples): Contar mensagens de entrada (medico)
// desde a ultima mensagem de saida (julia/humano)
const unreadQuery = supabase
  .from('interacoes')
  .select('conversation_id, id')
  .in('conversation_id', conversaIds)
  .eq('autor_tipo', 'medico')
  .order('created_at', { ascending: false })

// Para cada conversa, contar msgs do medico depois da ultima msg da Julia
```

**Decisao necessaria:** Definir o que "nao lida" significa no contexto de supervisao. Sugestao: mensagens do medico que ainda nao tiveram resposta (ultima msg e do medico = 1+ nao lidas).

### Testes Obrigatorios

**Unitarios:**
- [ ] Conversa com ultima msg do medico = unread_count >= 1
- [ ] Conversa com ultima msg da Julia = unread_count 0
- [ ] Conversa sem mensagens = unread_count 0

### Definition of Done

- [ ] unread_count calculado com base em dados reais
- [ ] Badge na sidebar mostra contagem correta
- [ ] Testes passando

### Estimativa

2h

---

## Tarefa 1.5: Fix contagem "Aguardando" (fallback que chuta 30%)

### Objetivo

Substituir o fallback que estima 30% das conversas AI como "aguardando" por uma contagem real.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `dashboard/app/api/conversas/counts/route.ts` |
| Criar (opcional) | Migration para RPC `get_supervision_tab_counts` |

### Implementacao

Reescrever `getCountsFallback()` para fazer a categorização correta:

```typescript
async function getCountsFallback(supabase, conversationFilter, twoDaysAgo) {
  // Buscar conversas ativas com last_message_direction
  let query = supabase
    .from('conversations')
    .select('id, status, controlled_by, last_message_at')
    .in('status', ['active', 'paused'])

  if (conversationFilter) {
    query = query.in('id', conversationFilter)
  }

  const { data: conversations } = await query.limit(1000)

  // Para cada conversa, precisamos saber last_message_direction
  // Alternativa: adicionar coluna last_message_direction a conversations
  // ou fazer subquery nas interacoes

  // Categorizar cada conversa usando a mesma logica do route.ts
  const counts = { atencao: 0, julia_ativa: 0, aguardando: 0, encerradas: 0 }
  // ... categorizar com categorizeConversation()

  // Contar encerradas separadamente (ultimas 48h)
  const { count: encerradasCount } = await supabase
    .from('conversations')
    .select('id', { count: 'exact', head: true })
    .in('status', ['completed', 'archived'])
    .gte('updated_at', twoDaysAgo)

  counts.encerradas = encerradasCount || 0
  return counts
}
```

**Melhor solucao:** Criar RPC SQL que faz tudo server-side (ver Epic 02 para otimização completa).

### Testes Obrigatorios

**Unitarios:**
- [ ] Contagem atencao inclui handoffs + sentimento negativo + espera > 60min
- [ ] Contagem julia_ativa inclui conversas AI com ultima msg do medico respondida
- [ ] Contagem aguardando inclui conversas AI esperando resposta do medico
- [ ] Contagem encerradas filtra ultimas 48h
- [ ] Com chipId: conta apenas conversas do chip

### Definition of Done

- [ ] Zero estimativas (nada de `Math.floor(x * 0.3)`)
- [ ] Contagens reais para todas as tabs
- [ ] Testes passando

### Estimativa

3h
