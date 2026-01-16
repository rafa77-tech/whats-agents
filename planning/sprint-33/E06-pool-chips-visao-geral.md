# E06 - Pool de Chips - Visao Geral

## Objetivo

Criar a secao de visao geral do pool de chips mostrando distribuicao por status, distribuicao por trust level e metricas agregadas.

## Contexto

Os chips (numeros virtuais) sao a infraestrutura critica da Julia. Cada chip tem:
- **Status:** provisioned, pending, warming, ready, active, degraded, paused, banned, cancelled
- **Trust Score:** 0-100 que determina o que o chip pode fazer
- **Trust Level:** Verde (75+), Amarelo (50-74), Laranja (35-49), Vermelho (<35)

O gestor precisa ver rapidamente:
- Quantos chips em cada status
- Saude geral do pool (trust levels)
- Metricas agregadas (msgs enviadas, taxa resposta, etc.)

## Requisitos Funcionais

### Status do Pool

Exibir contagem de chips por status principal:
- Active (em producao)
- Ready (prontos para ativar)
- Warming (aquecendo)
- Degraded (problematicos)

### Distribuicao por Trust Level

Barra horizontal mostrando:
- Verde (75+): Chips saudaveis
- Amarelo (50-74): Atencao
- Laranja (35-49): Problematicos
- Vermelho (<35): Criticos

### Metricas Agregadas do Pool

- Total msgs enviadas (periodo)
- Taxa de resposta media
- Taxa de block media
- Total de erros

## Requisitos Tecnicos

### Arquivos a Criar

```
/components/dashboard/chip-pool-overview.tsx
/components/dashboard/chip-status-counters.tsx
/components/dashboard/chip-trust-distribution.tsx
/components/dashboard/chip-pool-metrics.tsx
```

### Interfaces

```typescript
// types/dashboard.ts (adicionar)

export type ChipStatus =
  | "provisioned"
  | "pending"
  | "warming"
  | "ready"
  | "active"
  | "degraded"
  | "paused"
  | "banned"
  | "cancelled";

export type TrustLevel = "verde" | "amarelo" | "laranja" | "vermelho";

export interface ChipStatusCount {
  status: ChipStatus;
  count: number;
}

export interface TrustDistribution {
  level: TrustLevel;
  count: number;
  percentage: number;
}

export interface ChipPoolMetrics {
  totalMessagesSent: number;
  avgResponseRate: number;
  avgBlockRate: number;
  totalErrors: number;
  // Comparativos
  previousMessagesSent: number;
  previousResponseRate: number;
  previousBlockRate: number;
  previousErrors: number;
}

export interface ChipPoolOverviewData {
  statusCounts: ChipStatusCount[];
  trustDistribution: TrustDistribution[];
  metrics: ChipPoolMetrics;
}
```

### Layout Visual

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ POOL DE CHIPS                                                               │
├─────────────────────────────────┬───────────────────────────────────────────┤
│ Status do Pool                  │ Distribuicao por Trust                    │
│ ┌────────┬────────┬────────┬───┴┐ ┌──────────────────────────────────────┐  │
│ │ Active │ Ready  │Warming │Deg │ │ 🟢 Verde (75+)    ████████  6        │  │
│ │   5    │   3    │   4    │ 1  │ │ 🟡 Amarelo        ███      2         │  │
│ └────────┴────────┴────────┴────┘ │ 🟠 Laranja        █        1         │  │
│                                   │ 🔴 Vermelho       ░        0         │  │
│                                   └──────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────────┤
│ Metricas Agregadas (7d)                                                     │
│ ┌──────────────┬──────────────┬──────────────┬──────────────┐               │
│ │ Msgs Enviadas│ Taxa Resposta│ Taxa Block   │ Erros Pool   │               │
│ │    2.847     │    94.2%     │    1.8%      │     12       │               │
│ │   +15% ↑     │   +2.1% ↑    │   -0.5% ↓    │   -25% ↓     │               │
│ └──────────────┴──────────────┴──────────────┴──────────────┘               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Codigo Base - Status Counters

```tsx
// components/dashboard/chip-status-counters.tsx
"use client";

import { ChipStatusCount } from "@/types/dashboard";

interface ChipStatusCountersProps {
  counts: ChipStatusCount[];
}

const statusConfig: Record<
  string,
  { label: string; bgColor: string; textColor: string }
> = {
  active: { label: "Active", bgColor: "bg-green-100", textColor: "text-green-700" },
  ready: { label: "Ready", bgColor: "bg-blue-100", textColor: "text-blue-700" },
  warming: { label: "Warming", bgColor: "bg-yellow-100", textColor: "text-yellow-700" },
  degraded: { label: "Degraded", bgColor: "bg-orange-100", textColor: "text-orange-700" },
  banned: { label: "Banned", bgColor: "bg-red-100", textColor: "text-red-700" },
};

export function ChipStatusCounters({ counts }: ChipStatusCountersProps) {
  // Filtrar apenas status relevantes
  const relevantStatuses = ["active", "ready", "warming", "degraded"];
  const filteredCounts = counts.filter((c) =>
    relevantStatuses.includes(c.status)
  );

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium text-gray-700">Status do Pool</h4>
      <div className="grid grid-cols-4 gap-2">
        {filteredCounts.map((item) => {
          const config = statusConfig[item.status] || {
            label: item.status,
            bgColor: "bg-gray-100",
            textColor: "text-gray-700",
          };
          return (
            <div
              key={item.status}
              className={`${config.bgColor} rounded-lg p-3 text-center`}
            >
              <div className={`text-2xl font-bold ${config.textColor}`}>
                {item.count}
              </div>
              <div className={`text-xs ${config.textColor}`}>{config.label}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

### Codigo Base - Trust Distribution

```tsx
// components/dashboard/chip-trust-distribution.tsx
"use client";

import { TrustDistribution, TrustLevel } from "@/types/dashboard";

interface ChipTrustDistributionProps {
  distribution: TrustDistribution[];
}

const trustConfig: Record<
  TrustLevel,
  { label: string; range: string; color: string; bgColor: string }
> = {
  verde: { label: "Verde", range: "75+", color: "bg-green-500", bgColor: "bg-green-100" },
  amarelo: { label: "Amarelo", range: "50-74", color: "bg-yellow-500", bgColor: "bg-yellow-100" },
  laranja: { label: "Laranja", range: "35-49", color: "bg-orange-500", bgColor: "bg-orange-100" },
  vermelho: { label: "Vermelho", range: "<35", color: "bg-red-500", bgColor: "bg-red-100" },
};

export function ChipTrustDistribution({
  distribution,
}: ChipTrustDistributionProps) {
  const maxCount = Math.max(...distribution.map((d) => d.count), 1);

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium text-gray-700">Trust Level</h4>
      <div className="space-y-2">
        {distribution.map((item) => {
          const config = trustConfig[item.level];
          const barWidth = (item.count / maxCount) * 100;

          return (
            <div key={item.level} className="flex items-center gap-3">
              <div className="w-20 text-sm text-gray-600">
                {config.label} ({config.range})
              </div>
              <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full ${config.color} rounded-full transition-all`}
                  style={{ width: `${barWidth}%` }}
                />
              </div>
              <div className="w-8 text-sm font-medium text-right">
                {item.count}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

### Codigo Base - Pool Metrics

```tsx
// components/dashboard/chip-pool-metrics.tsx
"use client";

import { ChipPoolMetrics } from "@/types/dashboard";
import { TrendingUp, TrendingDown } from "lucide-react";

interface ChipPoolMetricsProps {
  metrics: ChipPoolMetrics;
}

function MetricItem({
  label,
  value,
  previousValue,
  format,
  invertTrend = false,
}: {
  label: string;
  value: number;
  previousValue: number;
  format: "number" | "percent";
  invertTrend?: boolean;
}) {
  const diff =
    previousValue !== 0 ? ((value - previousValue) / previousValue) * 100 : 0;
  const isPositive = diff > 0;
  // Para taxa block e erros, queda e bom
  const isGood = invertTrend ? !isPositive : isPositive;

  const formattedValue =
    format === "percent"
      ? `${value.toFixed(1)}%`
      : value.toLocaleString("pt-BR");

  return (
    <div className="bg-gray-50 rounded-lg p-3 text-center">
      <div className="text-lg font-bold text-gray-900">{formattedValue}</div>
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      {Math.abs(diff) >= 1 && (
        <div
          className={`flex items-center justify-center text-xs ${
            isGood ? "text-green-600" : "text-red-600"
          }`}
        >
          {isPositive ? (
            <TrendingUp className="h-3 w-3 mr-0.5" />
          ) : (
            <TrendingDown className="h-3 w-3 mr-0.5" />
          )}
          {isPositive ? "+" : ""}
          {diff.toFixed(0)}%
        </div>
      )}
    </div>
  );
}

export function ChipPoolMetricsComponent({ metrics }: ChipPoolMetricsProps) {
  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium text-gray-700">
        Metricas Agregadas (periodo)
      </h4>
      <div className="grid grid-cols-4 gap-3">
        <MetricItem
          label="Msgs Enviadas"
          value={metrics.totalMessagesSent}
          previousValue={metrics.previousMessagesSent}
          format="number"
        />
        <MetricItem
          label="Taxa Resposta"
          value={metrics.avgResponseRate}
          previousValue={metrics.previousResponseRate}
          format="percent"
        />
        <MetricItem
          label="Taxa Block"
          value={metrics.avgBlockRate}
          previousValue={metrics.previousBlockRate}
          format="percent"
          invertTrend
        />
        <MetricItem
          label="Erros"
          value={metrics.totalErrors}
          previousValue={metrics.previousErrors}
          format="number"
          invertTrend
        />
      </div>
    </div>
  );
}
```

### Codigo Base - Chip Pool Overview (Container)

```tsx
// components/dashboard/chip-pool-overview.tsx
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChipStatusCounters } from "./chip-status-counters";
import { ChipTrustDistribution } from "./chip-trust-distribution";
import { ChipPoolMetricsComponent } from "./chip-pool-metrics";
import { ChipPoolOverviewData } from "@/types/dashboard";
import { Smartphone } from "lucide-react";

interface ChipPoolOverviewProps {
  data: ChipPoolOverviewData;
}

export function ChipPoolOverview({ data }: ChipPoolOverviewProps) {
  const { statusCounts, trustDistribution, metrics } = data;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
          <Smartphone className="h-4 w-4" />
          Pool de Chips
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Linha 1: Status + Trust */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ChipStatusCounters counts={statusCounts} />
          <ChipTrustDistribution distribution={trustDistribution} />
        </div>

        {/* Linha 2: Metricas */}
        <div className="pt-4 border-t">
          <ChipPoolMetricsComponent metrics={metrics} />
        </div>
      </CardContent>
    </Card>
  );
}
```

### Dados Mock

```typescript
// lib/mock/dashboard-data.ts (adicionar)

export const mockChipPoolOverview: ChipPoolOverviewData = {
  statusCounts: [
    { status: "active", count: 5 },
    { status: "ready", count: 3 },
    { status: "warming", count: 4 },
    { status: "degraded", count: 1 },
    { status: "banned", count: 0 },
  ],
  trustDistribution: [
    { level: "verde", count: 6, percentage: 46 },
    { level: "amarelo", count: 2, percentage: 15 },
    { level: "laranja", count: 1, percentage: 8 },
    { level: "vermelho", count: 0, percentage: 0 },
  ],
  metrics: {
    totalMessagesSent: 2847,
    avgResponseRate: 94.2,
    avgBlockRate: 1.8,
    totalErrors: 12,
    previousMessagesSent: 2475,
    previousResponseRate: 92.1,
    previousBlockRate: 2.3,
    previousErrors: 16,
  },
};
```

## Criterios de Aceite

- [ ] Card exibe titulo "Pool de Chips" com icone
- [ ] Status counters mostram Active, Ready, Warming, Degraded com cores distintas
- [ ] Trust distribution mostra barras horizontais com cores corretas
- [ ] Metricas agregadas mostram valor atual e comparativo
- [ ] Taxa Block e Erros: queda = verde (invertTrend)
- [ ] Layout responsivo (2 colunas em desktop, 1 em mobile)
- [ ] Componente cabe na secao full-width do grid

## Definition of Done (DoD)

- [ ] Arquivo `components/dashboard/chip-pool-overview.tsx` criado
- [ ] Arquivo `components/dashboard/chip-status-counters.tsx` criado
- [ ] Arquivo `components/dashboard/chip-trust-distribution.tsx` criado
- [ ] Arquivo `components/dashboard/chip-pool-metrics.tsx` criado
- [ ] Tipos adicionados em `types/dashboard.ts`
- [ ] Mocks adicionados em `lib/mock/dashboard-data.ts`
- [ ] Componente integrado na pagina do dashboard
- [ ] Cores corretas para cada status e trust level
- [ ] Sem erros de TypeScript
- [ ] `npm run build` passa sem erros

## Dependencias

- E01 (Layout Base)

## Complexidade

**Media** - Varios sub-componentes, logica de cores.

## Tempo Estimado

5-6 horas

## Notas para o Desenvolvedor

1. Os status de chip vem da tabela `chips` no Supabase. Os principais para exibir sao:
   - active: Em uso pela Julia
   - ready: Prontos para serem ativados
   - warming: Fase de aquecimento (21 dias)
   - degraded: Com problemas, uso restrito

2. Trust levels e suas cores:
   - Verde (75+): `bg-green-500` / `bg-green-100`
   - Amarelo (50-74): `bg-yellow-500` / `bg-yellow-100`
   - Laranja (35-49): `bg-orange-500` / `bg-orange-100`
   - Vermelho (<35): `bg-red-500` / `bg-red-100`

3. Para metricas como "Taxa Block" e "Erros", uma QUEDA e positiva (verde), entao use `invertTrend={true}`.

4. A barra de trust distribution deve ter largura proporcional ao maior valor, nao a 100%.
