# E09 - APIs de Chips

## Objetivo

Criar as APIs que fornecem dados dos chips para o dashboard, incluindo visao agregada do pool e lista detalhada.

## Contexto

Os chips sao gerenciados na tabela `chips` do Supabase. As APIs precisam:
- Agregar contagens por status
- Calcular distribuicao por trust level
- Listar chips com detalhes
- Retornar alertas ativos

## Requisitos Funcionais

### APIs a Criar

| Endpoint | Descricao |
|----------|-----------|
| `GET /api/dashboard/chips` | Visao agregada do pool |
| `GET /api/dashboard/chips/list` | Lista detalhada de chips |
| `GET /api/dashboard/chips/[id]` | Detalhes de um chip especifico |

## Requisitos Tecnicos

### Arquivos a Criar

```
/app/api/dashboard/chips/route.ts
/app/api/dashboard/chips/list/route.ts
/app/api/dashboard/chips/[id]/route.ts
```

---

## API: GET /api/dashboard/chips

### Response

```typescript
interface ChipPoolResponse {
  statusCounts: Array<{ status: string; count: number }>;
  trustDistribution: Array<{
    level: "verde" | "amarelo" | "laranja" | "vermelho";
    count: number;
    percentage: number;
  }>;
  metrics: {
    totalMessagesSent: number;
    avgResponseRate: number;
    avgBlockRate: number;
    totalErrors: number;
    // Comparativos
    previousMessagesSent: number;
    previousResponseRate: number;
    previousBlockRate: number;
    previousErrors: number;
  };
}
```

### Codigo Base

```typescript
// app/api/dashboard/chips/route.ts
import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { getPeriodDates } from "@/lib/dashboard/calculations";

function getTrustLevel(score: number): "verde" | "amarelo" | "laranja" | "vermelho" {
  if (score >= 75) return "verde";
  if (score >= 50) return "amarelo";
  if (score >= 35) return "laranja";
  return "vermelho";
}

export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient();
    const period = request.nextUrl.searchParams.get("period") || "7d";
    const { currentStart, currentEnd, previousStart, previousEnd } = getPeriodDates(period);

    // Buscar todos os chips
    const { data: chips, error } = await supabase
      .from("chips")
      .select(`
        id,
        status,
        trust_score,
        msgs_enviadas_total,
        taxa_resposta,
        taxa_block,
        erros_ultimas_24h
      `);

    if (error) throw error;

    // Contagem por status
    const statusCounts: Record<string, number> = {};
    chips?.forEach((chip) => {
      statusCounts[chip.status] = (statusCounts[chip.status] || 0) + 1;
    });

    // Distribuicao por trust level
    const trustCounts: Record<string, number> = {
      verde: 0,
      amarelo: 0,
      laranja: 0,
      vermelho: 0,
    };

    chips?.forEach((chip) => {
      const level = getTrustLevel(chip.trust_score || 0);
      trustCounts[level]++;
    });

    const totalChips = chips?.length || 1;
    const trustDistribution = Object.entries(trustCounts).map(([level, count]) => ({
      level: level as "verde" | "amarelo" | "laranja" | "vermelho",
      count,
      percentage: Math.round((count / totalChips) * 100),
    }));

    // Metricas agregadas (periodo atual)
    const activeChips = chips?.filter((c) => c.status === "active") || [];

    const totalMessagesSent = activeChips.reduce(
      (sum, c) => sum + (c.msgs_enviadas_total || 0),
      0
    );
    const avgResponseRate =
      activeChips.length > 0
        ? activeChips.reduce((sum, c) => sum + (c.taxa_resposta || 0), 0) /
          activeChips.length
        : 0;
    const avgBlockRate =
      activeChips.length > 0
        ? activeChips.reduce((sum, c) => sum + (c.taxa_block || 0), 0) /
          activeChips.length
        : 0;
    const totalErrors = chips?.reduce(
      (sum, c) => sum + (c.erros_ultimas_24h || 0),
      0
    ) || 0;

    // TODO: Implementar comparativo com periodo anterior
    // Por enquanto, usar valores simulados
    const previousMessagesSent = Math.round(totalMessagesSent * 0.87);
    const previousResponseRate = avgResponseRate * 0.98;
    const previousBlockRate = avgBlockRate * 1.1;
    const previousErrors = Math.round(totalErrors * 1.25);

    return NextResponse.json({
      statusCounts: Object.entries(statusCounts).map(([status, count]) => ({
        status,
        count,
      })),
      trustDistribution,
      metrics: {
        totalMessagesSent,
        avgResponseRate: Number((avgResponseRate * 100).toFixed(1)),
        avgBlockRate: Number((avgBlockRate * 100).toFixed(1)),
        totalErrors,
        previousMessagesSent,
        previousResponseRate: Number((previousResponseRate * 100).toFixed(1)),
        previousBlockRate: Number((previousBlockRate * 100).toFixed(1)),
        previousErrors,
      },
    });
  } catch (error) {
    console.error("Error fetching chip pool:", error);
    return NextResponse.json(
      { error: "Failed to fetch chip pool data" },
      { status: 500 }
    );
  }
}
```

---

## API: GET /api/dashboard/chips/list

### Query Parameters

- `limit`: numero maximo de chips (default: 10)
- `offset`: paginacao (default: 0)
- `status`: filtrar por status (opcional)
- `sortBy`: "trust" | "errors" | "messages" (default: "trust")
- `order`: "asc" | "desc" (default: "asc" para trust)

### Response

```typescript
interface ChipListResponse {
  chips: Array<{
    id: string;
    name: string;
    telefone: string;
    status: string;
    trustScore: number;
    trustLevel: string;
    messagesToday: number;
    dailyLimit: number;
    responseRate: number;
    errorsLast24h: number;
    hasActiveAlert: boolean;
    alertMessage?: string;
    warmingDay?: number;
  }>;
  total: number;
  limit: number;
  offset: number;
}
```

### Codigo Base

```typescript
// app/api/dashboard/chips/list/route.ts
import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

function getTrustLevel(score: number): string {
  if (score >= 75) return "verde";
  if (score >= 50) return "amarelo";
  if (score >= 35) return "laranja";
  return "vermelho";
}

function getDailyLimit(status: string, fase_warmup?: string): number {
  if (status === "active") return 100;
  if (status === "warming") {
    switch (fase_warmup) {
      case "primeiros_contatos": return 10;
      case "expansao": return 30;
      case "pre_operacao": return 50;
      default: return 30;
    }
  }
  if (status === "degraded") return 30;
  return 0;
}

export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient();
    const searchParams = request.nextUrl.searchParams;

    const limit = parseInt(searchParams.get("limit") || "10");
    const offset = parseInt(searchParams.get("offset") || "0");
    const status = searchParams.get("status");
    const sortBy = searchParams.get("sortBy") || "trust";
    const order = searchParams.get("order") || "asc";

    // Query base
    let query = supabase
      .from("chips")
      .select(`
        id,
        instance_name,
        telefone,
        status,
        trust_score,
        msgs_enviadas_hoje,
        taxa_resposta,
        erros_ultimas_24h,
        fase_warmup,
        warming_day
      `, { count: "exact" });

    // Filtro por status
    if (status) {
      query = query.eq("status", status);
    }

    // Ordenacao
    const sortColumn = sortBy === "trust" ? "trust_score" :
                       sortBy === "errors" ? "erros_ultimas_24h" :
                       "msgs_enviadas_hoje";
    query = query.order(sortColumn, { ascending: order === "asc" });

    // Paginacao
    query = query.range(offset, offset + limit - 1);

    const { data: chips, count, error } = await query;

    if (error) throw error;

    // Buscar alertas ativos
    const chipIds = chips?.map((c) => c.id) || [];
    const { data: alerts } = await supabase
      .from("chip_alerts")
      .select("chip_id, message, severity")
      .in("chip_id", chipIds)
      .eq("resolved", false);

    const alertsMap = new Map(
      alerts?.map((a) => [a.chip_id, a.message]) || []
    );

    // Formatar resposta
    const formattedChips = chips?.map((chip) => ({
      id: chip.id,
      name: chip.instance_name || `Chip-${chip.id.slice(0, 4)}`,
      telefone: chip.telefone,
      status: chip.status,
      trustScore: chip.trust_score || 0,
      trustLevel: getTrustLevel(chip.trust_score || 0),
      messagesToday: chip.msgs_enviadas_hoje || 0,
      dailyLimit: getDailyLimit(chip.status, chip.fase_warmup),
      responseRate: (chip.taxa_resposta || 0) * 100,
      errorsLast24h: chip.erros_ultimas_24h || 0,
      hasActiveAlert: alertsMap.has(chip.id),
      alertMessage: alertsMap.get(chip.id),
      warmingDay: chip.warming_day,
    })) || [];

    return NextResponse.json({
      chips: formattedChips,
      total: count || 0,
      limit,
      offset,
    });
  } catch (error) {
    console.error("Error fetching chip list:", error);
    return NextResponse.json(
      { error: "Failed to fetch chip list" },
      { status: 500 }
    );
  }
}
```

---

## API: GET /api/dashboard/chips/[id]

### Response

```typescript
interface ChipDetailResponse {
  chip: {
    id: string;
    name: string;
    telefone: string;
    status: string;
    trustScore: number;
    trustLevel: string;
    // Metricas
    messagesToday: number;
    messagesTotal: number;
    dailyLimit: number;
    responseRate: number;
    blockRate: number;
    errorsLast24h: number;
    daysWithoutError: number;
    // Warming
    warmingPhase?: string;
    warmingDay?: number;
    warmingStartedAt?: string;
    // Timestamps
    createdAt: string;
    promotedToActiveAt?: string;
    lastActivityAt?: string;
  };
  alerts: Array<{
    id: string;
    severity: string;
    message: string;
    createdAt: string;
  }>;
  recentTransitions: Array<{
    fromStatus: string;
    toStatus: string;
    fromTrust: number;
    toTrust: number;
    triggeredBy: string;
    createdAt: string;
  }>;
}
```

### Codigo Base

```typescript
// app/api/dashboard/chips/[id]/route.ts
import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const supabase = await createClient();
    const chipId = params.id;

    // Buscar chip
    const { data: chip, error: chipError } = await supabase
      .from("chips")
      .select("*")
      .eq("id", chipId)
      .single();

    if (chipError || !chip) {
      return NextResponse.json(
        { error: "Chip not found" },
        { status: 404 }
      );
    }

    // Buscar alertas ativos
    const { data: alerts } = await supabase
      .from("chip_alerts")
      .select("id, severity, message, created_at")
      .eq("chip_id", chipId)
      .eq("resolved", false)
      .order("created_at", { ascending: false })
      .limit(5);

    // Buscar transicoes recentes
    const { data: transitions } = await supabase
      .from("chip_transitions")
      .select("from_status, to_status, from_trust_score, to_trust_score, triggered_by, created_at")
      .eq("chip_id", chipId)
      .order("created_at", { ascending: false })
      .limit(10);

    // Formatar resposta
    const getTrustLevel = (score: number) => {
      if (score >= 75) return "verde";
      if (score >= 50) return "amarelo";
      if (score >= 35) return "laranja";
      return "vermelho";
    };

    return NextResponse.json({
      chip: {
        id: chip.id,
        name: chip.instance_name || `Chip-${chip.id.slice(0, 4)}`,
        telefone: chip.telefone,
        status: chip.status,
        trustScore: chip.trust_score || 0,
        trustLevel: getTrustLevel(chip.trust_score || 0),
        messagesToday: chip.msgs_enviadas_hoje || 0,
        messagesTotal: chip.msgs_enviadas_total || 0,
        dailyLimit: 100, // Simplificado
        responseRate: (chip.taxa_resposta || 0) * 100,
        blockRate: (chip.taxa_block || 0) * 100,
        errorsLast24h: chip.erros_ultimas_24h || 0,
        daysWithoutError: chip.dias_sem_erro || 0,
        warmingPhase: chip.fase_warmup,
        warmingDay: chip.warming_day,
        warmingStartedAt: chip.warming_started_at,
        createdAt: chip.created_at,
        promotedToActiveAt: chip.promoted_to_active_at,
        lastActivityAt: chip.last_activity_start,
      },
      alerts: alerts?.map((a) => ({
        id: a.id,
        severity: a.severity,
        message: a.message,
        createdAt: a.created_at,
      })) || [],
      recentTransitions: transitions?.map((t) => ({
        fromStatus: t.from_status,
        toStatus: t.to_status,
        fromTrust: t.from_trust_score,
        toTrust: t.to_trust_score,
        triggeredBy: t.triggered_by,
        createdAt: t.created_at,
      })) || [],
    });
  } catch (error) {
    console.error("Error fetching chip detail:", error);
    return NextResponse.json(
      { error: "Failed to fetch chip detail" },
      { status: 500 }
    );
  }
}
```

---

## Criterios de Aceite

- [ ] API `/api/dashboard/chips` retorna contagens por status e trust
- [ ] API `/api/dashboard/chips/list` retorna lista paginada de chips
- [ ] API `/api/dashboard/chips/[id]` retorna detalhes de um chip
- [ ] Lista suporta filtro por status
- [ ] Lista suporta ordenacao por trust, errors, messages
- [ ] Alertas ativos sao incluidos na lista de chips
- [ ] Tratamento de chip nao encontrado (404)
- [ ] Tratamento de erros (500)

## Definition of Done (DoD)

- [ ] Todos os arquivos de API criados
- [ ] APIs retornam dados no formato especificado
- [ ] Funcao `getTrustLevel` reutilizada em todas as APIs
- [ ] APIs testadas manualmente
- [ ] Paginacao funcionando corretamente
- [ ] Sem erros de TypeScript
- [ ] `npm run build` passa sem erros

## Dependencias

- E08 (funcoes auxiliares compartilhadas)

## Complexidade

**Media** - Queries com joins e agregacoes.

## Tempo Estimado

6-8 horas

## Notas para o Desenvolvedor

1. **Verificar schema:** Os nomes das colunas podem variar. Consultar tabela `chips`:
   ```sql
   SELECT column_name, data_type FROM information_schema.columns
   WHERE table_name = 'chips';
   ```

2. **Tabelas relacionadas:**
   - `chips` - dados principais
   - `chip_alerts` - alertas ativos
   - `chip_transitions` - historico de mudancas

3. **Trust levels:**
   - Verde: >= 75
   - Amarelo: 50-74
   - Laranja: 35-49
   - Vermelho: < 35

4. **Limites diarios por fase de warming:**
   - repouso: 0
   - setup: 0
   - primeiros_contatos: 10
   - expansao: 30
   - pre_operacao: 50
   - operacao: 100

5. Para o comparativo de metricas, idealmente usar tabela `chip_trust_history` que guarda snapshots diarios. Se nao existir, simular valores.
