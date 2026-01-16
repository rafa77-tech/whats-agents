# E08 - APIs de Metricas Gerais

## Objetivo

Criar as APIs backend que fornecerao dados reais para o dashboard, substituindo os mocks.

## Contexto

Ate agora, os componentes do dashboard usam dados mock. Este epico cria as APIs que buscam dados reais do Supabase e calculam as metricas necessarias.

As APIs devem suportar:
- Filtro por periodo (7d, 14d, 30d)
- Retornar dados atuais E do periodo anterior (para comparativos)

## Requisitos Funcionais

### APIs a Criar

| Endpoint | Descricao |
|----------|-----------|
| `GET /api/dashboard/status` | Status Julia, uptime, ultimo heartbeat |
| `GET /api/dashboard/metrics` | Metricas vs meta (taxa resposta, conversoes, fechamentos) |
| `GET /api/dashboard/quality` | Metricas de qualidade (bot detection, latencia, handoff) |
| `GET /api/dashboard/operational` | Rate limits, fila, LLM usage, instancias |
| `GET /api/dashboard/funnel` | Dados do funil de conversao |

### Query Parameters

Todas as APIs aceitam:
- `period`: "7d" | "14d" | "30d" (default: "7d")

## Requisitos Tecnicos

### Arquivos a Criar

```
/app/api/dashboard/status/route.ts
/app/api/dashboard/metrics/route.ts
/app/api/dashboard/quality/route.ts
/app/api/dashboard/operational/route.ts
/app/api/dashboard/funnel/route.ts
/lib/dashboard/queries.ts         # Funcoes de query reutilizaveis
/lib/dashboard/calculations.ts    # Funcoes de calculo
```

### Estrutura de Resposta Padrao

```typescript
interface DashboardAPIResponse<T> {
  data: T;
  period: {
    start: string; // ISO date
    end: string;   // ISO date
    days: number;
  };
  previousPeriod: {
    start: string;
    end: string;
  };
  generatedAt: string; // ISO timestamp
}
```

---

## API: GET /api/dashboard/status

### Response

```typescript
interface DashboardStatusResponse {
  juliaStatus: "online" | "offline";
  lastHeartbeat: string | null; // ISO timestamp
  uptime30d: number; // 0-100
}
```

### Logica

```typescript
// Verificar status Julia
// 1. Buscar ultimo registro em julia_status
// 2. Se heartbeat < 5 min atras -> online
// 3. Calcular uptime: healthchecks OK / total nos ultimos 30d
```

### Codigo Base

```typescript
// app/api/dashboard/status/route.ts
import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET() {
  try {
    const supabase = await createClient();

    // Buscar ultimo status
    const { data: statusData } = await supabase
      .from("julia_status")
      .select("status, updated_at")
      .order("updated_at", { ascending: false })
      .limit(1)
      .single();

    // Calcular uptime 30d
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    const { count: totalChecks } = await supabase
      .from("julia_status")
      .select("*", { count: "exact", head: true })
      .gte("updated_at", thirtyDaysAgo.toISOString());

    const { count: successfulChecks } = await supabase
      .from("julia_status")
      .select("*", { count: "exact", head: true })
      .gte("updated_at", thirtyDaysAgo.toISOString())
      .eq("status", "online");

    const uptime = totalChecks ? ((successfulChecks || 0) / totalChecks) * 100 : 100;

    // Verificar se online (heartbeat < 5 min)
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
    const isOnline = statusData?.updated_at
      ? new Date(statusData.updated_at) > fiveMinutesAgo
      : false;

    return NextResponse.json({
      juliaStatus: isOnline ? "online" : "offline",
      lastHeartbeat: statusData?.updated_at || null,
      uptime30d: Number(uptime.toFixed(1)),
    });
  } catch (error) {
    console.error("Error fetching dashboard status:", error);
    return NextResponse.json(
      { error: "Failed to fetch status" },
      { status: 500 }
    );
  }
}
```

---

## API: GET /api/dashboard/metrics

### Response

```typescript
interface DashboardMetricsResponse {
  metrics: {
    responseRate: { value: number; previous: number; meta: number };
    conversionRate: { value: number; previous: number; meta: number };
    closingsPerWeek: { value: number; previous: number; meta: number };
  };
  period: { start: string; end: string; days: number };
}
```

### Tabelas Envolvidas

- `envios` - mensagens enviadas
- `interacoes` - respostas recebidas
- `conversas` - status de conversas

### Codigo Base

```typescript
// app/api/dashboard/metrics/route.ts
import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { getPeriodDates } from "@/lib/dashboard/calculations";

export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient();
    const period = request.nextUrl.searchParams.get("period") || "7d";

    const { currentStart, currentEnd, previousStart, previousEnd } =
      getPeriodDates(period);

    // Taxa de Resposta (current)
    const { count: enviadasCurrent } = await supabase
      .from("envios")
      .select("*", { count: "exact", head: true })
      .gte("created_at", currentStart)
      .lte("created_at", currentEnd);

    const { count: respostasCurrent } = await supabase
      .from("interacoes")
      .select("*", { count: "exact", head: true })
      .eq("tipo", "resposta_medico")
      .gte("created_at", currentStart)
      .lte("created_at", currentEnd);

    // Taxa de Resposta (previous)
    const { count: enviadasPrevious } = await supabase
      .from("envios")
      .select("*", { count: "exact", head: true })
      .gte("created_at", previousStart)
      .lte("created_at", previousEnd);

    const { count: respostasPrevious } = await supabase
      .from("interacoes")
      .select("*", { count: "exact", head: true })
      .eq("tipo", "resposta_medico")
      .gte("created_at", previousStart)
      .lte("created_at", previousEnd);

    // Fechamentos (current)
    const { count: fechamentosCurrent } = await supabase
      .from("conversas")
      .select("*", { count: "exact", head: true })
      .eq("status", "fechado")
      .gte("updated_at", currentStart)
      .lte("updated_at", currentEnd);

    // Fechamentos (previous)
    const { count: fechamentosPrevious } = await supabase
      .from("conversas")
      .select("*", { count: "exact", head: true })
      .eq("status", "fechado")
      .gte("updated_at", previousStart)
      .lte("updated_at", previousEnd);

    // Calculos
    const responseRateCurrent = enviadasCurrent
      ? ((respostasCurrent || 0) / enviadasCurrent) * 100
      : 0;
    const responseRatePrevious = enviadasPrevious
      ? ((respostasPrevious || 0) / enviadasPrevious) * 100
      : 0;

    // Conversao: fechamentos / respostas
    const conversionCurrent = respostasCurrent
      ? ((fechamentosCurrent || 0) / respostasCurrent) * 100
      : 0;
    const conversionPrevious = respostasPrevious
      ? ((fechamentosPrevious || 0) / respostasPrevious) * 100
      : 0;

    return NextResponse.json({
      metrics: {
        responseRate: {
          value: Number(responseRateCurrent.toFixed(1)),
          previous: Number(responseRatePrevious.toFixed(1)),
          meta: 30,
        },
        conversionRate: {
          value: Number(conversionCurrent.toFixed(1)),
          previous: Number(conversionPrevious.toFixed(1)),
          meta: 25,
        },
        closingsPerWeek: {
          value: fechamentosCurrent || 0,
          previous: fechamentosPrevious || 0,
          meta: 15,
        },
      },
      period: {
        start: currentStart,
        end: currentEnd,
        days: parseInt(period),
      },
    });
  } catch (error) {
    console.error("Error fetching dashboard metrics:", error);
    return NextResponse.json(
      { error: "Failed to fetch metrics" },
      { status: 500 }
    );
  }
}
```

---

## Funcao Auxiliar: getPeriodDates

```typescript
// lib/dashboard/calculations.ts

export function getPeriodDates(period: string): {
  currentStart: string;
  currentEnd: string;
  previousStart: string;
  previousEnd: string;
} {
  const days = parseInt(period) || 7;
  const now = new Date();

  const currentEnd = now.toISOString();
  const currentStart = new Date(now);
  currentStart.setDate(currentStart.getDate() - days);

  const previousEnd = currentStart.toISOString();
  const previousStart = new Date(currentStart);
  previousStart.setDate(previousStart.getDate() - days);

  return {
    currentStart: currentStart.toISOString(),
    currentEnd,
    previousStart: previousStart.toISOString(),
    previousEnd,
  };
}
```

---

## API: GET /api/dashboard/quality

### Response

```typescript
interface DashboardQualityResponse {
  metrics: {
    botDetection: { value: number; previous: number };
    avgLatency: { value: number; previous: number };
    handoffRate: { value: number; previous: number };
  };
}
```

### Tabelas Envolvidas

- `metricas_deteccao_bot` - deteccoes de bot
- `interacoes` - latencia de respostas
- `handoffs` - transferencias para humano

---

## API: GET /api/dashboard/operational

### Response

```typescript
interface DashboardOperationalResponse {
  rateLimits: {
    hour: { current: number; max: number };
    day: { current: number; max: number };
  };
  queueSize: number;
  llmUsage: { haiku: number; sonnet: number };
  instances: Array<{
    name: string;
    status: "online" | "offline";
    messagestoday: number;
  }>;
}
```

### Tabelas Envolvidas

- `fila_mensagens` - fila atual
- `interacoes` - contagem de msgs por hora/dia
- `whatsapp_instances` - status das instancias

---

## API: GET /api/dashboard/funnel

### Response

```typescript
interface DashboardFunnelResponse {
  stages: {
    enviadas: { count: number; previous: number };
    entregues: { count: number; previous: number };
    respostas: { count: number; previous: number };
    interesse: { count: number; previous: number };
    fechadas: { count: number; previous: number };
  };
}
```

### Tabelas Envolvidas

- `envios` - enviadas
- `envios` com status - entregues
- `interacoes` - respostas
- `conversas` com status interesse - interesse
- `conversas` com status fechado - fechadas

---

## Criterios de Aceite

- [ ] API `/api/dashboard/status` retorna status Julia, heartbeat, uptime
- [ ] API `/api/dashboard/metrics` retorna metricas vs meta com comparativos
- [ ] API `/api/dashboard/quality` retorna metricas de qualidade
- [ ] API `/api/dashboard/operational` retorna rate limits, fila, instancias
- [ ] API `/api/dashboard/funnel` retorna dados do funil
- [ ] Todas as APIs aceitam query param `period`
- [ ] Comparativos calculados corretamente (periodo atual vs anterior)
- [ ] Tratamento de erros com status 500

## Definition of Done (DoD)

- [ ] Todos os arquivos de API criados em `/app/api/dashboard/`
- [ ] Arquivo `lib/dashboard/calculations.ts` com funcoes auxiliares
- [ ] Todas as APIs retornam dados no formato especificado
- [ ] Funcao `getPeriodDates` testada com diferentes periodos
- [ ] APIs testadas manualmente via curl ou Postman
- [ ] Tratamento de divisao por zero
- [ ] Sem erros de TypeScript
- [ ] `npm run build` passa sem erros

## Dependencias

- Nenhuma (pode ser desenvolvido em paralelo com frontend)

## Complexidade

**Media** - Queries SQL e calculos de agregacao.

## Tempo Estimado

8-10 horas

## Notas para o Desenvolvedor

1. **IMPORTANTE:** As tabelas mencionadas podem ter nomes diferentes no banco real. Verificar schema antes de implementar:
   ```sql
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'public';
   ```

2. Usar o MCP do Supabase para testar queries:
   ```
   mcp__supabase__execute_sql
   ```

3. As metas sao fixas e vem do CLAUDE.md:
   - Taxa resposta: 30%
   - Conversao: 25%
   - Fechamentos/semana: 15
   - Bot detection: < 1%
   - Latencia: < 30s

4. Para evitar N+1 queries, usar agregacoes SQL quando possivel.

5. Se uma tabela nao existir, retornar valores zerados (nao quebrar a API).

6. Considerar cache para metricas que nao mudam com frequencia (ex: uptime 30d).
