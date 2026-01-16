# E03 - Cards de Metricas vs Meta

## Objetivo

Criar os cards de metricas principais que mostram performance atual vs metas definidas, com indicador visual de atingimento e comparativo com periodo anterior.

## Contexto

Estes cards mostram as metricas mais importantes para avaliar se Julia esta performando conforme esperado. Cada card mostra:
- Valor atual
- Meta definida
- Indicador de atingimento (check verde, warning amarelo)
- Comparativo com semana anterior (ex: +14% ↑)

## Requisitos Funcionais

### Metricas a Exibir

| Metrica | Meta | Fonte |
|---------|------|-------|
| Taxa de Resposta | > 30% | respostas / enviadas |
| Taxa de Conversao | > 25% | fechamentos / respostas |
| Fechamentos/Semana | > 15 | contagem de fechamentos |

### Regras de Exibicao

1. **Atingiu meta:** Badge verde com check
2. **Abaixo da meta (< 20% diferenca):** Badge amarelo com warning
3. **Muito abaixo da meta (>= 20% diferenca):** Badge vermelho com X

### Comparativo

- Se valor atual > anterior: seta verde para cima com porcentagem
- Se valor atual < anterior: seta vermelha para baixo com porcentagem
- Se igual: traço cinza

## Requisitos Tecnicos

### Arquivos a Criar

```
/components/dashboard/metric-card.tsx
/components/dashboard/comparison-badge.tsx
/components/dashboard/metrics-section.tsx
```

### Interfaces

```typescript
// types/dashboard.ts (adicionar)

export interface MetricData {
  label: string;
  value: number;
  unit: "percent" | "number" | "currency";
  meta: number;
  previousValue: number;
  metaOperator: "gt" | "lt" | "eq"; // greater than, less than, equal
}

export interface ComparisonData {
  currentValue: number;
  previousValue: number;
}
```

### Layout Visual

```
┌─────────────────────────────────┐
│ Taxa de Resposta                │
│                                 │
│     32%            Meta: 30%    │
│   ██████████░░     ✅           │
│                                 │
│   vs sem. ant: 28%    +14% ↑    │
└─────────────────────────────────┘
```

### Codigo Base - Metric Card

```tsx
// components/dashboard/metric-card.tsx
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Check, AlertTriangle, X, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { MetricData } from "@/types/dashboard";

interface MetricCardProps {
  data: MetricData;
}

function formatValue(value: number, unit: MetricData["unit"]): string {
  switch (unit) {
    case "percent":
      return `${value.toFixed(1)}%`;
    case "currency":
      return `R$ ${value.toLocaleString("pt-BR")}`;
    case "number":
    default:
      return value.toLocaleString("pt-BR");
  }
}

function getMetaStatus(
  value: number,
  meta: number,
  operator: MetricData["metaOperator"]
): "success" | "warning" | "error" {
  const meetsTarget =
    operator === "gt" ? value >= meta :
    operator === "lt" ? value <= meta :
    value === meta;

  if (meetsTarget) return "success";

  const diff = Math.abs((value - meta) / meta);
  return diff < 0.2 ? "warning" : "error";
}

function MetaIndicator({ status }: { status: "success" | "warning" | "error" }) {
  if (status === "success") {
    return (
      <Badge className="bg-green-100 text-green-700 border-green-200">
        <Check className="h-3 w-3 mr-1" />
        Meta
      </Badge>
    );
  }
  if (status === "warning") {
    return (
      <Badge className="bg-yellow-100 text-yellow-700 border-yellow-200">
        <AlertTriangle className="h-3 w-3 mr-1" />
        Atencao
      </Badge>
    );
  }
  return (
    <Badge className="bg-red-100 text-red-700 border-red-200">
      <X className="h-3 w-3 mr-1" />
      Abaixo
    </Badge>
  );
}

function ComparisonBadge({
  current,
  previous,
  unit,
}: {
  current: number;
  previous: number;
  unit: MetricData["unit"];
}) {
  if (previous === 0) return null;

  const diff = ((current - previous) / previous) * 100;
  const isPositive = diff > 0;
  const isNeutral = Math.abs(diff) < 1;

  if (isNeutral) {
    return (
      <span className="flex items-center text-gray-500 text-sm">
        <Minus className="h-3 w-3 mr-1" />
        Estavel
      </span>
    );
  }

  return (
    <span
      className={`flex items-center text-sm ${
        isPositive ? "text-green-600" : "text-red-600"
      }`}
    >
      {isPositive ? (
        <TrendingUp className="h-3 w-3 mr-1" />
      ) : (
        <TrendingDown className="h-3 w-3 mr-1" />
      )}
      {isPositive ? "+" : ""}
      {diff.toFixed(0)}%
    </span>
  );
}

export function MetricCard({ data }: MetricCardProps) {
  const { label, value, unit, meta, previousValue, metaOperator } = data;
  const status = getMetaStatus(value, meta, metaOperator);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-gray-500">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-end justify-between">
          <div>
            <div className="text-3xl font-bold">{formatValue(value, unit)}</div>
            <div className="text-sm text-gray-500 mt-1">
              Meta: {formatValue(meta, unit)}
            </div>
          </div>
          <MetaIndicator status={status} />
        </div>

        <div className="mt-4 pt-4 border-t flex items-center justify-between">
          <span className="text-sm text-gray-500">
            vs sem. ant: {formatValue(previousValue, unit)}
          </span>
          <ComparisonBadge
            current={value}
            previous={previousValue}
            unit={unit}
          />
        </div>
      </CardContent>
    </Card>
  );
}
```

### Codigo Base - Metrics Section

```tsx
// components/dashboard/metrics-section.tsx
"use client";

import { MetricCard } from "./metric-card";
import { MetricData } from "@/types/dashboard";

interface MetricsSectionProps {
  metrics: MetricData[];
}

export function MetricsSection({ metrics }: MetricsSectionProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {metrics.map((metric, index) => (
        <MetricCard key={index} data={metric} />
      ))}
    </div>
  );
}
```

### Dados Mock para Teste

```typescript
// lib/mock/dashboard-data.ts
import { MetricData } from "@/types/dashboard";

export const mockMetricsVsMeta: MetricData[] = [
  {
    label: "Taxa de Resposta",
    value: 32,
    unit: "percent",
    meta: 30,
    previousValue: 28,
    metaOperator: "gt",
  },
  {
    label: "Taxa de Conversao",
    value: 18,
    unit: "percent",
    meta: 25,
    previousValue: 20,
    metaOperator: "gt",
  },
  {
    label: "Fechamentos/Semana",
    value: 18,
    unit: "number",
    meta: 15,
    previousValue: 15,
    metaOperator: "gt",
  },
];
```

## Criterios de Aceite

- [ ] Card exibe label, valor atual, meta e indicador de status
- [ ] Valores formatados corretamente (% para porcentagem, numero com separador)
- [ ] Badge verde quando meta atingida
- [ ] Badge amarelo quando abaixo da meta (< 20% diferenca)
- [ ] Badge vermelho quando muito abaixo (>= 20% diferenca)
- [ ] Comparativo mostra diferenca percentual com seta
- [ ] Seta verde para crescimento, vermelha para queda
- [ ] 3 cards renderizam lado a lado em desktop

## Definition of Done (DoD)

- [ ] Arquivo `components/dashboard/metric-card.tsx` criado
- [ ] Arquivo `components/dashboard/metrics-section.tsx` criado
- [ ] Tipos adicionados em `types/dashboard.ts`
- [ ] Dados mock criados em `lib/mock/dashboard-data.ts`
- [ ] Componente integrado na pagina do dashboard
- [ ] Logica de `getMetaStatus` testada com diferentes valores
- [ ] Sem erros de TypeScript (nenhum `any`)
- [ ] `npm run build` passa sem erros
- [ ] `npm run lint` passa sem erros

## Dependencias

- E01 (Layout Base)

## Complexidade

**Media** - Logica de calculo de status e formatacao.

## Tempo Estimado

4-5 horas

## Notas para o Desenvolvedor

1. O componente `Card` vem do shadcn/ui:
   ```bash
   npx shadcn-ui@latest add card badge
   ```

2. A funcao `getMetaStatus` e critica - teste com varios cenarios:
   - value=32, meta=30, operator=gt → success
   - value=27, meta=30, operator=gt → warning (10% abaixo)
   - value=20, meta=30, operator=gt → error (33% abaixo)

3. O comparativo usa o `previousValue` que sera o valor da semana anterior. Por enquanto use mock.

4. Cuidado com divisao por zero no `ComparisonBadge` quando `previous === 0`.
