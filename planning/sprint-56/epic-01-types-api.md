# ÉPICO 1: Types & API Route

## Contexto

O widget precisa de dados em tempo real sobre chips ativos e mensagens recentes. Este épico cria a fundação: tipos TypeScript e a API route que alimenta o widget com polling 5s.

## Escopo

- **Incluído**: Tipos do widget, API route, query otimizada para polling rápido
- **Excluído**: Componentes visuais (Epic 2-3), integração na page (Epic 4)

---

## Tarefa 1.1: Definir tipos TypeScript

### Objetivo

Criar as interfaces que descrevem os dados do widget de message flow.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Modificar | `dashboard/types/dashboard.ts` |

### Implementação

Adicionar ao final do arquivo `dashboard.ts`:

```typescript
// ===== Message Flow Visualization =====

/** Direção da mensagem no fluxo visual */
export type MessageDirection = 'inbound' | 'outbound'

/** Status visual de um chip no grafo */
export type ChipNodeStatus = 'active' | 'warming' | 'degraded' | 'paused' | 'offline'

/** Um nó de chip no grafo radial */
export interface ChipNode {
  id: string
  name: string
  status: ChipNodeStatus
  trustScore: number
  /** Mensagens enviadas nos últimos 5 minutos */
  recentOutbound: number
  /** Mensagens recebidas nos últimos 5 minutos */
  recentInbound: number
  /** Se o chip está em conversa ativa agora */
  isActive: boolean
}

/** Uma mensagem recente para animar como partícula */
export interface RecentMessage {
  id: string
  chipId: string
  direction: MessageDirection
  /** Timestamp ISO para ordenação */
  timestamp: string
}

/** Dados completos do widget de message flow */
export interface MessageFlowData {
  chips: ChipNode[]
  recentMessages: RecentMessage[]
  /** Total de mensagens/minuto (inbound + outbound) */
  messagesPerMinute: number
  /** Timestamp da última atualização */
  updatedAt: string
}
```

### Testes Obrigatórios

**Unitários:**
- [ ] Tipos compilam sem erro (verificado pelo typecheck)
- [ ] Nenhum uso de `any`

### Definition of Done

- [ ] Tipos adicionados a `dashboard/types/dashboard.ts`
- [ ] `npm run typecheck` passa
- [ ] Tipos exportados e acessíveis via `@/types/dashboard`

### Estimativa

1 ponto

---

## Tarefa 1.2: Criar API Route `/api/dashboard/message-flow`

### Objetivo

Endpoint que retorna chips ativos com métricas recentes e mensagens dos últimos 5 minutos para animação. Deve ser leve o suficiente para polling 5s.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Criar | `dashboard/app/api/dashboard/message-flow/route.ts` |

### Implementação

```typescript
// Seguir padrão existente: force-dynamic, createClient(), try-catch

export const dynamic = 'force-dynamic'

export async function GET(): Promise<NextResponse> {
  try {
    const supabase = await createClient()

    // 1. Buscar chips ativos (status in active, warming, degraded, paused)
    // Campos: id, instance_name, status, trust_score,
    //         msgs_enviadas_hoje, msgs_recebidas_hoje
    // Limitar a 15 chips, ordenar por trust_score desc

    // 2. Buscar mensagens dos últimos 5 minutos
    // Tabela: interacoes
    // Campos: id, chip_id, tipo (entrada/saida), created_at
    // Filtro: created_at >= now() - 5min, chip_id IS NOT NULL
    // Limitar a 50 mensagens mais recentes

    // 3. Calcular mensagens/minuto
    // COUNT de interacoes no último minuto

    // 4. Mapear para ChipNode[] e RecentMessage[]
    // chip.status -> ChipNodeStatus mapping:
    //   'active' -> 'active'
    //   'warming','ready' -> 'warming'
    //   'degraded' -> 'degraded'
    //   'paused' -> 'paused'
    //   outros -> 'offline'

    // 5. isActive = chip tem mensagem nos últimos 2 minutos

    return NextResponse.json(data satisfies MessageFlowData)
  } catch (error) {
    console.error('[message-flow] Error:', error)
    return NextResponse.json(
      { error: 'Failed to fetch message flow data' },
      { status: 500 }
    )
  }
}
```

**Queries SQL esperadas:**

```sql
-- Query 1: Chips ativos
SELECT id, instance_name, status, trust_score,
       msgs_enviadas_hoje, msgs_recebidas_hoje
FROM chips
WHERE status IN ('active', 'warming', 'ready', 'degraded', 'paused')
ORDER BY trust_score DESC
LIMIT 15;

-- Query 2: Mensagens recentes (5 min)
SELECT id, chip_id, tipo, created_at
FROM interacoes
WHERE created_at >= NOW() - INTERVAL '5 minutes'
  AND chip_id IS NOT NULL
ORDER BY created_at DESC
LIMIT 50;

-- Query 3: Mensagens/minuto
SELECT COUNT(*)
FROM interacoes
WHERE created_at >= NOW() - INTERVAL '1 minute';
```

### Performance

- 3 queries simples com índices existentes (`created_at`, `chip_id`, `status`)
- Payload estimado: ~2-5 KB (15 chips + 50 mensagens)
- Tempo esperado: < 100ms

### Testes Obrigatórios

**Unitários:**
- [ ] Retorna 200 com shape correto (chips[], recentMessages[], messagesPerMinute)
- [ ] Retorna chips vazios quando nenhum chip ativo
- [ ] Retorna mensagens vazias quando sem tráfego recente
- [ ] Mapeia status do banco para ChipNodeStatus corretamente
- [ ] isActive = true quando chip tem mensagem em 2 min
- [ ] isActive = false quando chip sem atividade recente
- [ ] Limita a 15 chips
- [ ] Limita a 50 mensagens

**Integração:**
- [ ] Endpoint responde em < 200ms com dados reais (Supabase)
- [ ] Formato do JSON bate com `MessageFlowData`

### Definition of Done

- [ ] Endpoint retorna dados no formato `MessageFlowData`
- [ ] Queries otimizadas (< 200ms response time)
- [ ] Tratamento de erro com status 500
- [ ] `npm run typecheck` passa
- [ ] Testes unitários passando

### Estimativa

3 pontos

---

## Dependências

| Este épico | Depende de | Status |
|-----------|-----------|--------|
| Epic 1 | Nenhum | — |
| Epic 2 | Epic 1 (tipos) | Bloqueado |
| Epic 3 | Epic 2 (SVG base) | Bloqueado |
| Epic 4 | Epic 1 + 2 + 3 | Bloqueado |
