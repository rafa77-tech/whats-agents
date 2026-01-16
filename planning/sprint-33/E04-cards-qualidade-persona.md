# E04 - Cards de Qualidade Persona

## Objetivo

Criar os cards de metricas de qualidade da persona Julia, focados em garantir que ela parece humana e responde adequadamente.

## Contexto

A qualidade da persona e CRITICA para o sucesso do projeto. Se medicos percebem que estao falando com um bot, a taxa de conversao despenca e podem ocorrer bloqueios.

Estas metricas respondem a pergunta: "Julia esta parecendo humana?"

## Requisitos Funcionais

### Metricas a Exibir

| Metrica | Meta | Descricao |
|---------|------|-----------|
| Deteccao como Bot | < 1% | Taxa de conversas detectadas como bot |
| Latencia Media | < 30s | Tempo medio para responder |
| Taxa de Handoff | Informativo | % de conversas passadas para humano |

### Regras de Exibicao

1. **Deteccao Bot:**
   - < 1%: Verde (otimo)
   - 1-3%: Amarelo (atencao)
   - > 3%: Vermelho (critico)

2. **Latencia:**
   - < 30s: Verde
   - 30-60s: Amarelo
   - > 60s: Vermelho

3. **Handoff:**
   - < 5%: Informativo (normal)
   - 5-10%: Amarelo (verificar)
   - > 10%: Vermelho (problema)

## Requisitos Tecnicos

### Arquivos a Modificar/Criar

```
/components/dashboard/quality-metrics-section.tsx
/types/dashboard.ts (adicionar tipos)
/lib/mock/dashboard-data.ts (adicionar mocks)
```

### Interfaces Adicionais

```typescript
// types/dashboard.ts (adicionar)

export interface QualityMetricData {
  label: string;
  value: number;
  unit: "percent" | "seconds";
  threshold: {
    good: number;
    warning: number;
  };
  operator: "lt" | "gt"; // less than or greater than for "good"
  previousValue: number;
  tooltip?: string;
}
```

### Layout Visual

```
┌─────────────────────────────────┐
│ Deteccao como Bot               │
│                                 │
│     0.4%           Meta: <1%    │
│                    ✅ Otimo     │
│                                 │
│   vs sem. ant: 0.6%    -33% ↓   │
└─────────────────────────────────┘
```

### Codigo Base - Quality Metric Card

```tsx
// components/dashboard/quality-metric-card.tsx
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Check,
  AlertTriangle,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Info,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { QualityMetricData } from "@/types/dashboard";

interface QualityMetricCardProps {
  data: QualityMetricData;
}

function formatValue(value: number, unit: QualityMetricData["unit"]): string {
  if (unit === "percent") {
    return `${value.toFixed(1)}%`;
  }
  return `${value.toFixed(0)}s`;
}

function getQualityStatus(
  value: number,
  threshold: QualityMetricData["threshold"],
  operator: QualityMetricData["operator"]
): "good" | "warning" | "critical" {
  const isGood =
    operator === "lt" ? value < threshold.good : value > threshold.good;
  const isWarning =
    operator === "lt" ? value < threshold.warning : value > threshold.warning;

  if (isGood) return "good";
  if (isWarning) return "warning";
  return "critical";
}

function StatusBadge({ status }: { status: "good" | "warning" | "critical" }) {
  const config = {
    good: {
      className: "bg-green-100 text-green-700 border-green-200",
      icon: Check,
      label: "Otimo",
    },
    warning: {
      className: "bg-yellow-100 text-yellow-700 border-yellow-200",
      icon: AlertTriangle,
      label: "Atencao",
    },
    critical: {
      className: "bg-red-100 text-red-700 border-red-200",
      icon: AlertCircle,
      label: "Critico",
    },
  };

  const { className, icon: Icon, label } = config[status];

  return (
    <Badge className={className}>
      <Icon className="h-3 w-3 mr-1" />
      {label}
    </Badge>
  );
}

export function QualityMetricCard({ data }: QualityMetricCardProps) {
  const { label, value, unit, threshold, operator, previousValue, tooltip } =
    data;
  const status = getQualityStatus(value, threshold, operator);

  // Para comparativo, inversao de logica para "menos e melhor"
  const diff =
    previousValue !== 0 ? ((value - previousValue) / previousValue) * 100 : 0;

  // Se operator e "lt", queda e positiva (melhor)
  const isImprovement = operator === "lt" ? diff < 0 : diff > 0;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <CardTitle className="text-sm font-medium text-gray-500">
            {label}
          </CardTitle>
          {tooltip && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Info className="h-4 w-4 text-gray-400" />
                </TooltipTrigger>
                <TooltipContent>
                  <p className="max-w-xs">{tooltip}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-end justify-between">
          <div>
            <div className="text-3xl font-bold">{formatValue(value, unit)}</div>
            <div className="text-sm text-gray-500 mt-1">
              Meta: {operator === "lt" ? "<" : ">"} {formatValue(threshold.good, unit)}
            </div>
          </div>
          <StatusBadge status={status} />
        </div>

        <div className="mt-4 pt-4 border-t flex items-center justify-between">
          <span className="text-sm text-gray-500">
            vs sem. ant: {formatValue(previousValue, unit)}
          </span>
          {Math.abs(diff) >= 1 && (
            <span
              className={`flex items-center text-sm ${
                isImprovement ? "text-green-600" : "text-red-600"
              }`}
            >
              {isImprovement ? (
                <TrendingDown className="h-3 w-3 mr-1" />
              ) : (
                <TrendingUp className="h-3 w-3 mr-1" />
              )}
              {diff > 0 ? "+" : ""}
              {diff.toFixed(0)}%
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
```

### Codigo Base - Quality Metrics Section

```tsx
// components/dashboard/quality-metrics-section.tsx
"use client";

import { QualityMetricCard } from "./quality-metric-card";
import { QualityMetricData } from "@/types/dashboard";

interface QualityMetricsSectionProps {
  metrics: QualityMetricData[];
}

export function QualityMetricsSection({ metrics }: QualityMetricsSectionProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {metrics.map((metric, index) => (
        <QualityMetricCard key={index} data={metric} />
      ))}
    </div>
  );
}
```

### Dados Mock

```typescript
// lib/mock/dashboard-data.ts (adicionar)

export const mockQualityMetrics: QualityMetricData[] = [
  {
    label: "Deteccao como Bot",
    value: 0.4,
    unit: "percent",
    threshold: { good: 1, warning: 3 },
    operator: "lt",
    previousValue: 0.6,
    tooltip: "Porcentagem de conversas onde o medico detectou que estava falando com um bot",
  },
  {
    label: "Latencia Media",
    value: 24,
    unit: "seconds",
    threshold: { good: 30, warning: 60 },
    operator: "lt",
    previousValue: 28,
    tooltip: "Tempo medio que Julia leva para responder uma mensagem",
  },
  {
    label: "Taxa de Handoff",
    value: 3.2,
    unit: "percent",
    threshold: { good: 5, warning: 10 },
    operator: "lt",
    previousValue: 4.1,
    tooltip: "Porcentagem de conversas transferidas para atendimento humano",
  },
];
```

## Criterios de Aceite

- [ ] Card exibe label, valor, meta e status
- [ ] Deteccao Bot: verde < 1%, amarelo 1-3%, vermelho > 3%
- [ ] Latencia: verde < 30s, amarelo 30-60s, vermelho > 60s
- [ ] Handoff: verde < 5%, amarelo 5-10%, vermelho > 10%
- [ ] Comparativo mostra se melhorou ou piorou
- [ ] Para metricas "quanto menor melhor", queda e verde
- [ ] Tooltip exibe explicacao da metrica ao hover no icone (i)
- [ ] 3 cards renderizam lado a lado em desktop

## Definition of Done (DoD)

- [ ] Arquivo `components/dashboard/quality-metric-card.tsx` criado
- [ ] Arquivo `components/dashboard/quality-metrics-section.tsx` criado
- [ ] Tipos `QualityMetricData` adicionados em `types/dashboard.ts`
- [ ] Mocks adicionados em `lib/mock/dashboard-data.ts`
- [ ] Componente integrado na pagina do dashboard
- [ ] Tooltip instalado: `npx shadcn-ui@latest add tooltip`
- [ ] Logica de status testada com valores limites
- [ ] Sem erros de TypeScript
- [ ] `npm run build` passa sem erros

## Dependencias

- E01 (Layout Base)
- E03 (Reutiliza padrao de cards)

## Complexidade

**Media** - Logica invertida para "menos e melhor".

## Tempo Estimado

3-4 horas

## Notas para o Desenvolvedor

1. ATENCAO: A logica de "melhor" e invertida para estas metricas:
   - Deteccao Bot: MENOS e melhor (queda = verde)
   - Latencia: MENOS e melhor (queda = verde)
   - Handoff: MENOS e melhor (queda = verde)

2. O comparativo deve mostrar seta VERDE quando o valor CAI (porque cair e bom).

3. Instalar tooltip se nao existir:
   ```bash
   npx shadcn-ui@latest add tooltip
   ```

4. Os thresholds sao fixos e vem do CLAUDE.md:
   - Bot detection: < 1% (meta critica)
   - Latencia: < 30s
