# E13 - Sistema de Alertas

## Objetivo

Criar o componente de lista de alertas que mostra notificacoes criticas e warnings do sistema, unificando alertas de Julia, chips e operacionais.

## Contexto

Os alertas sao a forma de chamar atencao do gestor para problemas que precisam de acao imediata. Devem ser visiveis, claros e acionaveis.

Tipos de alerta:
- **Critico (vermelho):** Requer acao imediata
- **Warning (amarelo):** Atencao necessaria
- **Info (azul):** Informativo

## Requisitos Funcionais

### Categorias de Alertas

| Categoria | Exemplos |
|-----------|----------|
| Julia | Medico irritado, handoff necessario |
| Chips | Trust critico, chip desconectado, muitos erros |
| Operacional | Rate limit alto, instancia offline, fila grande |
| Vagas | Vaga expirando sem medico |

### Informacoes por Alerta

- Severidade (icone colorido)
- Mensagem curta
- Tempo (ha quanto tempo)
- Acao (link ou botao)

### Funcionalidades

- Ordenar por severidade (critico primeiro)
- Limitar a 5-10 alertas mais recentes
- Auto-refresh a cada 30 segundos

## Requisitos Tecnicos

### Arquivos a Criar

```
/components/dashboard/alerts-list.tsx
/components/dashboard/alert-item.tsx
/app/api/dashboard/alerts/route.ts
```

### Interfaces

```typescript
// types/dashboard.ts (adicionar)

export type AlertSeverity = "critical" | "warning" | "info";
export type AlertCategory = "julia" | "chip" | "operational" | "vaga";

export interface DashboardAlert {
  id: string;
  severity: AlertSeverity;
  category: AlertCategory;
  title: string;
  message: string;
  createdAt: string; // ISO timestamp
  actionLabel?: string;
  actionUrl?: string;
  metadata?: Record<string, unknown>;
}

export interface AlertsData {
  alerts: DashboardAlert[];
  totalCritical: number;
  totalWarning: number;
}
```

### Layout Visual

```
┌─────────────────────────────────────────────────────────────────┐
│ ALERTAS CRITICOS                                    3 criticos  │
├─────────────────────────────────────────────────────────────────┤
│ 🔴 Dr. Joao - irritado ha 2h                                    │
│    "isso e um absurdo"                          [Ver conversa]  │
├─────────────────────────────────────────────────────────────────┤
│ 🔴 Julia-05 trust critico (48)                                  │
│    Queda de 15 pts em 24h                       [Ver chip]      │
├─────────────────────────────────────────────────────────────────┤
│ 🟡 Rate limit hora em 85%                                       │
│    Reseta em 12 minutos                                         │
├─────────────────────────────────────────────────────────────────┤
│ 🟡 5 vagas expiram em 24h                                       │
│    Sem medico confirmado                        [Ver vagas]     │
└─────────────────────────────────────────────────────────────────┘
```

### Codigo Base - Alert Item

```tsx
// components/dashboard/alert-item.tsx
"use client";

import { DashboardAlert } from "@/types/dashboard";
import { Button } from "@/components/ui/button";
import {
  AlertCircle,
  AlertTriangle,
  Info,
  ExternalLink,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";

interface AlertItemProps {
  alert: DashboardAlert;
}

const severityConfig = {
  critical: {
    icon: AlertCircle,
    bgColor: "bg-red-50",
    borderColor: "border-red-200",
    iconColor: "text-red-500",
    textColor: "text-red-800",
  },
  warning: {
    icon: AlertTriangle,
    bgColor: "bg-yellow-50",
    borderColor: "border-yellow-200",
    iconColor: "text-yellow-500",
    textColor: "text-yellow-800",
  },
  info: {
    icon: Info,
    bgColor: "bg-blue-50",
    borderColor: "border-blue-200",
    iconColor: "text-blue-500",
    textColor: "text-blue-800",
  },
};

export function AlertItem({ alert }: AlertItemProps) {
  const { severity, title, message, createdAt, actionLabel, actionUrl } = alert;
  const config = severityConfig[severity];
  const Icon = config.icon;

  return (
    <div
      className={`
        p-3 rounded-lg border
        ${config.bgColor} ${config.borderColor}
      `}
    >
      <div className="flex items-start gap-3">
        <Icon className={`h-5 w-5 mt-0.5 ${config.iconColor}`} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h4 className={`font-medium text-sm ${config.textColor}`}>
              {title}
            </h4>
            <span className="text-xs text-gray-500 whitespace-nowrap">
              {formatDistanceToNow(new Date(createdAt), {
                addSuffix: true,
                locale: ptBR,
              })}
            </span>
          </div>

          <p className="text-sm text-gray-600 mt-0.5">{message}</p>

          {actionUrl && (
            <Button
              variant="ghost"
              size="sm"
              className="mt-2 h-7 px-2 text-xs"
              asChild
            >
              <a href={actionUrl} target="_blank" rel="noopener noreferrer">
                {actionLabel || "Ver detalhes"}
                <ExternalLink className="h-3 w-3 ml-1" />
              </a>
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
```

### Codigo Base - Alerts List

```tsx
// components/dashboard/alerts-list.tsx
"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertItem } from "./alert-item";
import { AlertsData, DashboardAlert } from "@/types/dashboard";
import { Bell, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface AlertsListProps {
  initialData?: AlertsData;
  autoRefresh?: boolean;
  refreshInterval?: number; // em ms
}

export function AlertsList({
  initialData,
  autoRefresh = true,
  refreshInterval = 30000,
}: AlertsListProps) {
  const [data, setData] = useState<AlertsData | null>(initialData || null);
  const [loading, setLoading] = useState(!initialData);

  const fetchAlerts = async () => {
    try {
      const res = await fetch("/api/dashboard/alerts");
      const json = await res.json();
      if (res.ok) {
        setData(json);
      }
    } catch (error) {
      console.error("Error fetching alerts:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initialData) {
      fetchAlerts();
    }

    if (autoRefresh) {
      const interval = setInterval(fetchAlerts, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [initialData, autoRefresh, refreshInterval]);

  // Ordenar alertas: critico > warning > info
  const sortedAlerts = data?.alerts.sort((a, b) => {
    const order = { critical: 0, warning: 1, info: 2 };
    return order[a.severity] - order[b.severity];
  });

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
            <Bell className="h-4 w-4" />
            Alertas
          </CardTitle>
          {data && data.totalCritical > 0 && (
            <Badge variant="destructive" className="text-xs">
              {data.totalCritical} critico{data.totalCritical > 1 ? "s" : ""}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        ) : sortedAlerts?.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Bell className="h-8 w-8 mx-auto mb-2 text-gray-300" />
            <p>Nenhum alerta no momento</p>
          </div>
        ) : (
          sortedAlerts?.map((alert) => (
            <AlertItem key={alert.id} alert={alert} />
          ))
        )}
      </CardContent>
    </Card>
  );
}
```

### Codigo Base - API

```typescript
// app/api/dashboard/alerts/route.ts
import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET() {
  try {
    const supabase = await createClient();
    const alerts: Array<{
      id: string;
      severity: "critical" | "warning" | "info";
      category: string;
      title: string;
      message: string;
      createdAt: string;
      actionLabel?: string;
      actionUrl?: string;
    }> = [];

    // 1. Alertas de chips (trust critico, desconectado)
    const { data: chipAlerts } = await supabase
      .from("chip_alerts")
      .select("id, chip_id, severity, tipo, message, created_at, chips(instance_name)")
      .eq("resolved", false)
      .order("created_at", { ascending: false })
      .limit(5);

    chipAlerts?.forEach((ca) => {
      alerts.push({
        id: `chip-${ca.id}`,
        severity: ca.severity === "critical" ? "critical" : "warning",
        category: "chip",
        title: `${ca.chips?.instance_name || "Chip"} - ${ca.tipo}`,
        message: ca.message,
        createdAt: ca.created_at,
        actionLabel: "Ver chip",
        actionUrl: `/chips/${ca.chip_id}`,
      });
    });

    // 2. Alertas de handoff (medico irritado)
    const { data: handoffs } = await supabase
      .from("handoffs")
      .select(`
        id,
        motivo,
        created_at,
        conversa_id,
        conversas (
          clientes (primeiro_nome, sobrenome)
        )
      `)
      .eq("status", "pendente")
      .order("created_at", { ascending: false })
      .limit(3);

    handoffs?.forEach((h) => {
      const nome = h.conversas?.clientes
        ? `${h.conversas.clientes.primeiro_nome || ""} ${h.conversas.clientes.sobrenome || ""}`.trim()
        : "Medico";
      alerts.push({
        id: `handoff-${h.id}`,
        severity: "critical",
        category: "julia",
        title: `${nome} - aguardando atendimento`,
        message: h.motivo || "Handoff solicitado",
        createdAt: h.created_at,
        actionLabel: "Ver conversa",
        actionUrl: `${process.env.CHATWOOT_URL}/conversations/${h.conversa_id}`,
      });
    });

    // 3. Alertas de vagas expirando
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);

    const { data: vagasExpirando, count: vagasCount } = await supabase
      .from("vagas")
      .select("id", { count: "exact", head: true })
      .lte("data", tomorrow.toISOString())
      .is("medico_confirmado_id", null)
      .eq("status", "aberta");

    if (vagasCount && vagasCount > 0) {
      alerts.push({
        id: "vagas-expirando",
        severity: "warning",
        category: "vaga",
        title: `${vagasCount} vaga${vagasCount > 1 ? "s" : ""} expirando em 24h`,
        message: "Sem medico confirmado",
        createdAt: new Date().toISOString(),
        actionLabel: "Ver vagas",
        actionUrl: "/vagas?status=urgente",
      });
    }

    // 4. Rate limit (verificar uso atual)
    // NOTA: Requer logica de rate limit implementada
    // Placeholder por enquanto

    // Contar por severidade
    const totalCritical = alerts.filter((a) => a.severity === "critical").length;
    const totalWarning = alerts.filter((a) => a.severity === "warning").length;

    return NextResponse.json({
      alerts,
      totalCritical,
      totalWarning,
    });
  } catch (error) {
    console.error("Error fetching alerts:", error);
    return NextResponse.json(
      { error: "Failed to fetch alerts" },
      { status: 500 }
    );
  }
}
```

## Criterios de Aceite

- [ ] Lista exibe alertas ordenados por severidade
- [ ] Alertas criticos tem background vermelho, icone vermelho
- [ ] Alertas warning tem background amarelo, icone amarelo
- [ ] Alertas info tem background azul, icone azul
- [ ] Cada alerta mostra: titulo, mensagem, tempo, acao (opcional)
- [ ] Badge mostra quantidade de criticos no header
- [ ] Auto-refresh a cada 30 segundos
- [ ] Empty state quando nao ha alertas
- [ ] Loading state enquanto carrega

## Definition of Done (DoD)

- [ ] Arquivo `components/dashboard/alerts-list.tsx` criado
- [ ] Arquivo `components/dashboard/alert-item.tsx` criado
- [ ] Arquivo `app/api/dashboard/alerts/route.ts` criado
- [ ] Tipos adicionados em `types/dashboard.ts`
- [ ] Componente integrado na pagina do dashboard
- [ ] Auto-refresh funcionando
- [ ] Ordenacao por severidade funcionando
- [ ] Sem erros de TypeScript
- [ ] `npm run build` passa sem erros

## Dependencias

- E01 (Layout Base)
- E09 (APIs de chips para alertas de chips)

## Complexidade

**Media** - Agregacao de multiplas fontes de alertas.

## Tempo Estimado

5-6 horas

## Notas para o Desenvolvedor

1. A API agrega alertas de varias fontes:
   - `chip_alerts` - alertas de chips
   - `handoffs` - medicos aguardando humano
   - `vagas` - vagas expirando
   - Logica de rate limit (se implementada)

2. Os alertas devem ser VISIVEIS e ACIONAVEIS. Cada alerta deve ter um proximo passo claro.

3. Considerar websocket para alertas em tempo real no futuro.

4. O auto-refresh usa `setInterval`. Limpar intervalo no cleanup do useEffect.

5. Limitar a quantidade de alertas (ex: max 10) para nao sobrecarregar a interface.

6. A URL do Chatwoot vem da env `CHATWOOT_URL`.
