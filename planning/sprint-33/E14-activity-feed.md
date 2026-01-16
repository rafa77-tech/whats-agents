# E14 - Activity Feed

## Objetivo

Criar o feed de atividades recentes que mostra uma timeline dos eventos importantes do sistema.

## Contexto

O activity feed mostra o que esta acontecendo no sistema em tempo real. E uma forma de acompanhar a "vida" da Julia sem precisar ir em cada area especifica.

Eventos tipicos:
- Plantao fechado
- Handoff realizado
- Campanha enviou mensagens
- Chip graduou do warming
- Trust score mudou significativamente

## Requisitos Funcionais

### Tipos de Eventos

| Tipo | Icone | Cor | Exemplo |
|------|-------|-----|---------|
| fechamento | ✅ | Verde | Julia fechou plantao com Dr. Carlos |
| handoff | 🔄 | Azul | Dra. Maria pediu atendimento humano |
| campanha | 📤 | Roxo | Campanha "Reativacao" enviou 15 msgs |
| resposta | 💬 | Verde | Dr. Pedro respondeu apos 3 dias |
| chip | 🎓 | Amarelo | Julia-03 graduou do warming |
| alerta | ⚠️ | Laranja | Julia-05 trust caiu 8 pontos |

### Formato de Cada Item

- Timestamp (hora:minuto)
- Icone do tipo
- Mensagem descritiva
- Identificacao do chip (quando aplicavel)

## Requisitos Tecnicos

### Arquivos a Criar

```
/components/dashboard/activity-feed.tsx
/components/dashboard/activity-item.tsx
/app/api/dashboard/activity/route.ts
```

### Interfaces

```typescript
// types/dashboard.ts (adicionar)

export type ActivityType =
  | "fechamento"
  | "handoff"
  | "campanha"
  | "resposta"
  | "chip"
  | "alerta";

export interface ActivityEvent {
  id: string;
  type: ActivityType;
  message: string;
  details?: string;
  chipName?: string;
  timestamp: string; // ISO timestamp
  metadata?: Record<string, unknown>;
}

export interface ActivityFeedData {
  events: ActivityEvent[];
  hasMore: boolean;
}
```

### Layout Visual

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ATIVIDADE RECENTE                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 14:32 │ ✅ │ Julia-01 fechou plantao com Dr. Carlos (R$ 2.800)             │
│ 14:28 │ 🔄 │ Julia-02 handoff: Dra. Maria pediu humano                     │
│ 14:15 │ 📤 │ Campanha "Reativacao Janeiro" enviou 15 mensagens             │
│ 14:02 │ 💬 │ Julia-01 Dr. Pedro respondeu apos 3 dias                      │
│ 13:45 │ ⚠️ │ Julia-05 trust caiu 8 pontos (56 → 48)                        │
│ 13:30 │ 🎓 │ Julia-03 graduou do warming (trust: 85)                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Codigo Base - Activity Item

```tsx
// components/dashboard/activity-item.tsx
"use client";

import { ActivityEvent, ActivityType } from "@/types/dashboard";
import {
  CheckCircle,
  RefreshCw,
  Send,
  MessageSquare,
  Award,
  AlertTriangle,
} from "lucide-react";
import { format } from "date-fns";

interface ActivityItemProps {
  event: ActivityEvent;
}

const typeConfig: Record<
  ActivityType,
  { icon: React.ComponentType<{ className?: string }>; bgColor: string; iconColor: string }
> = {
  fechamento: {
    icon: CheckCircle,
    bgColor: "bg-green-100",
    iconColor: "text-green-600",
  },
  handoff: {
    icon: RefreshCw,
    bgColor: "bg-blue-100",
    iconColor: "text-blue-600",
  },
  campanha: {
    icon: Send,
    bgColor: "bg-purple-100",
    iconColor: "text-purple-600",
  },
  resposta: {
    icon: MessageSquare,
    bgColor: "bg-green-100",
    iconColor: "text-green-600",
  },
  chip: {
    icon: Award,
    bgColor: "bg-yellow-100",
    iconColor: "text-yellow-600",
  },
  alerta: {
    icon: AlertTriangle,
    bgColor: "bg-orange-100",
    iconColor: "text-orange-600",
  },
};

export function ActivityItem({ event }: ActivityItemProps) {
  const { type, message, chipName, timestamp } = event;
  const config = typeConfig[type];
  const Icon = config.icon;

  const time = format(new Date(timestamp), "HH:mm");

  return (
    <div className="flex items-start gap-3 py-2">
      {/* Timestamp */}
      <span className="text-xs text-gray-400 w-12 pt-0.5">{time}</span>

      {/* Icon */}
      <div className={`p-1.5 rounded-full ${config.bgColor}`}>
        <Icon className={`h-3.5 w-3.5 ${config.iconColor}`} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-700">
          {chipName && (
            <span className="font-medium text-gray-900">{chipName} </span>
          )}
          {message}
        </p>
      </div>
    </div>
  );
}
```

### Codigo Base - Activity Feed

```tsx
// components/dashboard/activity-feed.tsx
"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ActivityItem } from "./activity-item";
import { ActivityFeedData } from "@/types/dashboard";
import { Activity, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ActivityFeedProps {
  initialData?: ActivityFeedData;
  autoRefresh?: boolean;
  refreshInterval?: number;
  limit?: number;
}

export function ActivityFeed({
  initialData,
  autoRefresh = true,
  refreshInterval = 30000,
  limit = 10,
}: ActivityFeedProps) {
  const [data, setData] = useState<ActivityFeedData | null>(initialData || null);
  const [loading, setLoading] = useState(!initialData);

  const fetchActivity = async () => {
    try {
      const res = await fetch(`/api/dashboard/activity?limit=${limit}`);
      const json = await res.json();
      if (res.ok) {
        setData(json);
      }
    } catch (error) {
      console.error("Error fetching activity:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initialData) {
      fetchActivity();
    }

    if (autoRefresh) {
      const interval = setInterval(fetchActivity, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [initialData, autoRefresh, refreshInterval, limit]);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
          <Activity className="h-4 w-4" />
          Atividade Recente
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        ) : data?.events.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Activity className="h-8 w-8 mx-auto mb-2 text-gray-300" />
            <p>Nenhuma atividade recente</p>
          </div>
        ) : (
          <div className="divide-y">
            {data?.events.map((event) => (
              <ActivityItem key={event.id} event={event} />
            ))}
          </div>
        )}

        {data?.hasMore && (
          <div className="pt-4 border-t mt-4">
            <Button variant="ghost" size="sm" className="w-full">
              Ver mais
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

### Codigo Base - API

```typescript
// app/api/dashboard/activity/route.ts
import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient();
    const limit = parseInt(request.nextUrl.searchParams.get("limit") || "10");

    const events: Array<{
      id: string;
      type: string;
      message: string;
      chipName?: string;
      timestamp: string;
    }> = [];

    // 1. Buscar fechamentos recentes
    const { data: fechamentos } = await supabase
      .from("conversas")
      .select(`
        id,
        updated_at,
        chips (instance_name),
        clientes (primeiro_nome, sobrenome),
        vagas (valor)
      `)
      .eq("status", "fechado")
      .order("updated_at", { ascending: false })
      .limit(5);

    fechamentos?.forEach((f) => {
      const nome = f.clientes
        ? `${f.clientes.primeiro_nome || ""} ${f.clientes.sobrenome || ""}`.trim()
        : "medico";
      const valor = f.vagas?.valor
        ? `(R$ ${f.vagas.valor.toLocaleString("pt-BR")})`
        : "";

      events.push({
        id: `fechamento-${f.id}`,
        type: "fechamento",
        message: `fechou plantao com ${nome} ${valor}`,
        chipName: f.chips?.instance_name,
        timestamp: f.updated_at,
      });
    });

    // 2. Buscar handoffs recentes
    const { data: handoffs } = await supabase
      .from("handoffs")
      .select(`
        id,
        created_at,
        motivo,
        conversas (
          chips (instance_name),
          clientes (primeiro_nome, sobrenome)
        )
      `)
      .order("created_at", { ascending: false })
      .limit(5);

    handoffs?.forEach((h) => {
      const nome = h.conversas?.clientes
        ? `${h.conversas.clientes.primeiro_nome || ""} ${h.conversas.clientes.sobrenome || ""}`.trim()
        : "Medico";

      events.push({
        id: `handoff-${h.id}`,
        type: "handoff",
        message: `handoff: ${nome} ${h.motivo || "pediu humano"}`,
        chipName: h.conversas?.chips?.instance_name,
        timestamp: h.created_at,
      });
    });

    // 3. Buscar execucoes de campanha
    const { data: campanhas } = await supabase
      .from("execucoes_campanhas")
      .select(`
        id,
        created_at,
        total_enviados,
        campanhas (nome)
      `)
      .order("created_at", { ascending: false })
      .limit(5);

    campanhas?.forEach((c) => {
      events.push({
        id: `campanha-${c.id}`,
        type: "campanha",
        message: `Campanha "${c.campanhas?.nome}" enviou ${c.total_enviados} mensagens`,
        timestamp: c.created_at,
      });
    });

    // 4. Buscar transicoes de chip (graduacao, trust change)
    const { data: transitions } = await supabase
      .from("chip_transitions")
      .select(`
        id,
        created_at,
        from_status,
        to_status,
        from_trust_score,
        to_trust_score,
        chips (instance_name)
      `)
      .order("created_at", { ascending: false })
      .limit(5);

    transitions?.forEach((t) => {
      let type: string = "chip";
      let message: string;

      if (t.to_status === "ready" && t.from_status === "warming") {
        message = `graduou do warming (trust: ${t.to_trust_score})`;
      } else if (t.to_trust_score && t.from_trust_score) {
        const diff = t.to_trust_score - t.from_trust_score;
        if (Math.abs(diff) >= 5) {
          type = diff < 0 ? "alerta" : "chip";
          message = `trust ${diff > 0 ? "subiu" : "caiu"} ${Math.abs(diff)} pontos (${t.from_trust_score} → ${t.to_trust_score})`;
        } else {
          return; // Skip small changes
        }
      } else {
        message = `status mudou de ${t.from_status} para ${t.to_status}`;
      }

      events.push({
        id: `transition-${t.id}`,
        type,
        message,
        chipName: t.chips?.instance_name,
        timestamp: t.created_at,
      });
    });

    // Ordenar por timestamp (mais recente primeiro) e limitar
    events.sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
    const limitedEvents = events.slice(0, limit);

    return NextResponse.json({
      events: limitedEvents,
      hasMore: events.length > limit,
    });
  } catch (error) {
    console.error("Error fetching activity:", error);
    return NextResponse.json(
      { error: "Failed to fetch activity" },
      { status: 500 }
    );
  }
}
```

## Criterios de Aceite

- [ ] Feed exibe eventos em ordem cronologica (mais recente primeiro)
- [ ] Cada evento tem icone colorido baseado no tipo
- [ ] Timestamp no formato HH:mm
- [ ] Nome do chip aparece quando aplicavel
- [ ] Diferentes tipos de eventos tem icones/cores distintas
- [ ] Auto-refresh a cada 30 segundos
- [ ] Loading state enquanto carrega
- [ ] Empty state quando nao ha eventos
- [ ] Botao "Ver mais" quando ha mais eventos

## Definition of Done (DoD)

- [ ] Arquivo `components/dashboard/activity-feed.tsx` criado
- [ ] Arquivo `components/dashboard/activity-item.tsx` criado
- [ ] Arquivo `app/api/dashboard/activity/route.ts` criado
- [ ] Tipos adicionados em `types/dashboard.ts`
- [ ] Componente integrado na pagina do dashboard
- [ ] Auto-refresh funcionando
- [ ] Diferentes tipos de eventos renderizam corretamente
- [ ] Sem erros de TypeScript
- [ ] `npm run build` passa sem erros

## Dependencias

- E01 (Layout Base)

## Complexidade

**Media** - Agregacao de multiplas fontes de eventos.

## Tempo Estimado

5-6 horas

## Notas para o Desenvolvedor

1. A API agrega eventos de varias tabelas. Verificar se as tabelas existem no schema.

2. Para eventos de chips, filtrar apenas mudancas significativas (ex: trust >= 5 pontos).

3. O feed deve ser "vivo" - auto-refresh mantem atualizado.

4. Considerar limite de eventos por tipo para garantir diversidade.

5. O timestamp deve ser formatado com `date-fns`:
   ```tsx
   format(new Date(timestamp), "HH:mm")
   ```

6. Em producao, considerar websocket para eventos em tempo real.
