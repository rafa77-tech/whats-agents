# E12 - Graficos Sparkline

## Objetivo

Criar os graficos sparkline que mostram tendencias das metricas principais ao longo do periodo selecionado.

## Contexto

Sparklines sao graficos de linha compactos que mostram a evolucao de uma metrica ao longo do tempo. Eles permitem identificar rapidamente tendencias (subindo, caindo, estavel) sem ocupar muito espaco visual.

Serao exibidos na secao "Tendencias" do dashboard.

## Requisitos Funcionais

### Metricas com Sparkline

1. **Taxa de Resposta** - Evolucao diaria (%)
2. **Latencia Media** - Evolucao diaria (segundos)
3. **Deteccao Bot** - Evolucao diaria (%)
4. **Custo LLM** - Evolucao diaria ($)
5. **Trust Score Medio** - Evolucao diaria do pool de chips

### Formato

- Grafico de linha simples
- 7 pontos (um por dia no periodo de 7d)
- Valor atual exibido ao lado
- Cor indica tendencia: verde (melhora), vermelho (piora)

## Requisitos Tecnicos

### Arquivos a Criar

```
/components/dashboard/sparkline-chart.tsx
/components/dashboard/trends-section.tsx
/app/api/dashboard/trends/route.ts
```

### Dependencias

```bash
npm install recharts
```

### Interfaces

```typescript
// types/dashboard.ts (adicionar)

export interface SparklineDataPoint {
  date: string; // YYYY-MM-DD
  value: number;
}

export interface SparklineMetric {
  id: string;
  label: string;
  data: SparklineDataPoint[];
  currentValue: number;
  unit: string; // "%", "s", "$"
  trend: "up" | "down" | "stable";
  trendIsGood: boolean; // para determinar cor
}

export interface TrendsData {
  metrics: SparklineMetric[];
  period: string;
}
```

### Layout Visual

```
┌─────────────────────────────────────────────────────────────────┐
│ TENDENCIAS (7d)                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Taxa de Resposta                                                │
│ [~~~~~▔▔▔~~~] 32%  ↑                                           │
│                                                                 │
│ Latencia Media                                                  │
│ [~~~▔▔▔~~~~▁] 24s  ↓                                           │
│                                                                 │
│ Deteccao Bot                                                    │
│ [▔▔▔▁▁▁▁▁▁▁] 0.4%  ↓                                           │
│                                                                 │
│ Trust Score Medio                                               │
│ [▁▁▁▁~~~▔▔▔] 82  ↑                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Codigo Base - Sparkline Chart

```tsx
// components/dashboard/sparkline-chart.tsx
"use client";

import { LineChart, Line, ResponsiveContainer } from "recharts";
import { SparklineMetric } from "@/types/dashboard";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface SparklineChartProps {
  metric: SparklineMetric;
}

export function SparklineChart({ metric }: SparklineChartProps) {
  const { label, data, currentValue, unit, trend, trendIsGood } = metric;

  // Determinar cor da linha baseado na tendencia
  const lineColor = trend === "stable"
    ? "#9CA3AF" // gray
    : trendIsGood
    ? "#10B981" // green
    : "#EF4444"; // red

  // Icone de tendencia
  const TrendIcon = trend === "up"
    ? TrendingUp
    : trend === "down"
    ? TrendingDown
    : Minus;

  // Formatar valor
  const formattedValue = unit === "%"
    ? `${currentValue.toFixed(1)}%`
    : unit === "s"
    ? `${currentValue.toFixed(0)}s`
    : unit === "$"
    ? `$${currentValue.toFixed(2)}`
    : currentValue.toFixed(0);

  return (
    <div className="flex items-center gap-4 py-2">
      <div className="w-32 text-sm text-gray-600">{label}</div>

      <div className="flex-1 h-8">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <Line
              type="monotone"
              dataKey="value"
              stroke={lineColor}
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center gap-2 w-20 justify-end">
        <span className="font-medium">{formattedValue}</span>
        <TrendIcon
          className={`h-4 w-4 ${
            trend === "stable"
              ? "text-gray-400"
              : trendIsGood
              ? "text-green-500"
              : "text-red-500"
          }`}
        />
      </div>
    </div>
  );
}
```

### Codigo Base - Trends Section

```tsx
// components/dashboard/trends-section.tsx
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SparklineChart } from "./sparkline-chart";
import { TrendsData } from "@/types/dashboard";
import { TrendingUp } from "lucide-react";

interface TrendsSectionProps {
  data: TrendsData;
}

export function TrendsSection({ data }: TrendsSectionProps) {
  const { metrics, period } = data;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
          <TrendingUp className="h-4 w-4" />
          Tendencias ({period})
        </CardTitle>
      </CardHeader>
      <CardContent className="divide-y">
        {metrics.map((metric) => (
          <SparklineChart key={metric.id} metric={metric} />
        ))}
      </CardContent>
    </Card>
  );
}
```

### Codigo Base - API

```typescript
// app/api/dashboard/trends/route.ts
import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient();
    const period = request.nextUrl.searchParams.get("period") || "7d";
    const days = parseInt(period) || 7;

    // Gerar array de datas
    const dates: string[] = [];
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      dates.push(date.toISOString().split("T")[0]);
    }

    // Buscar metricas por dia
    // NOTA: Isso requer tabelas de metricas agregadas por dia
    // Implementacao simplificada com dados simulados

    const generateTrendData = (
      baseValue: number,
      variance: number,
      trend: "up" | "down" | "stable"
    ) => {
      return dates.map((date, i) => {
        const progress = i / (dates.length - 1);
        const trendOffset =
          trend === "up"
            ? progress * variance
            : trend === "down"
            ? -progress * variance
            : 0;
        const randomOffset = (Math.random() - 0.5) * variance * 0.5;
        return {
          date,
          value: baseValue + trendOffset + randomOffset,
        };
      });
    };

    const responseRateData = generateTrendData(30, 5, "up");
    const latencyData = generateTrendData(28, 6, "down");
    const botDetectionData = generateTrendData(0.6, 0.3, "down");
    const trustScoreData = generateTrendData(80, 5, "up");

    const metrics = [
      {
        id: "responseRate",
        label: "Taxa de Resposta",
        data: responseRateData,
        currentValue: responseRateData[responseRateData.length - 1].value,
        unit: "%",
        trend: "up" as const,
        trendIsGood: true,
      },
      {
        id: "latency",
        label: "Latencia Media",
        data: latencyData,
        currentValue: latencyData[latencyData.length - 1].value,
        unit: "s",
        trend: "down" as const,
        trendIsGood: true, // menor e melhor
      },
      {
        id: "botDetection",
        label: "Deteccao Bot",
        data: botDetectionData,
        currentValue: botDetectionData[botDetectionData.length - 1].value,
        unit: "%",
        trend: "down" as const,
        trendIsGood: true, // menor e melhor
      },
      {
        id: "trustScore",
        label: "Trust Score Medio",
        data: trustScoreData,
        currentValue: trustScoreData[trustScoreData.length - 1].value,
        unit: "",
        trend: "up" as const,
        trendIsGood: true,
      },
    ];

    return NextResponse.json({
      metrics,
      period: `${days}d`,
    });
  } catch (error) {
    console.error("Error fetching trends:", error);
    return NextResponse.json(
      { error: "Failed to fetch trends" },
      { status: 500 }
    );
  }
}
```

### Dados Mock

```typescript
// lib/mock/dashboard-data.ts (adicionar)

export const mockTrendsData: TrendsData = {
  metrics: [
    {
      id: "responseRate",
      label: "Taxa de Resposta",
      data: [
        { date: "2025-01-10", value: 28 },
        { date: "2025-01-11", value: 29 },
        { date: "2025-01-12", value: 27 },
        { date: "2025-01-13", value: 30 },
        { date: "2025-01-14", value: 31 },
        { date: "2025-01-15", value: 30 },
        { date: "2025-01-16", value: 32 },
      ],
      currentValue: 32,
      unit: "%",
      trend: "up",
      trendIsGood: true,
    },
    {
      id: "latency",
      label: "Latencia Media",
      data: [
        { date: "2025-01-10", value: 30 },
        { date: "2025-01-11", value: 28 },
        { date: "2025-01-12", value: 32 },
        { date: "2025-01-13", value: 26 },
        { date: "2025-01-14", value: 25 },
        { date: "2025-01-15", value: 24 },
        { date: "2025-01-16", value: 24 },
      ],
      currentValue: 24,
      unit: "s",
      trend: "down",
      trendIsGood: true,
    },
    {
      id: "botDetection",
      label: "Deteccao Bot",
      data: [
        { date: "2025-01-10", value: 0.8 },
        { date: "2025-01-11", value: 0.6 },
        { date: "2025-01-12", value: 0.7 },
        { date: "2025-01-13", value: 0.5 },
        { date: "2025-01-14", value: 0.5 },
        { date: "2025-01-15", value: 0.4 },
        { date: "2025-01-16", value: 0.4 },
      ],
      currentValue: 0.4,
      unit: "%",
      trend: "down",
      trendIsGood: true,
    },
    {
      id: "trustScore",
      label: "Trust Score Medio",
      data: [
        { date: "2025-01-10", value: 78 },
        { date: "2025-01-11", value: 79 },
        { date: "2025-01-12", value: 78 },
        { date: "2025-01-13", value: 80 },
        { date: "2025-01-14", value: 81 },
        { date: "2025-01-15", value: 82 },
        { date: "2025-01-16", value: 82 },
      ],
      currentValue: 82,
      unit: "",
      trend: "up",
      trendIsGood: true,
    },
  ],
  period: "7d",
};
```

## Criterios de Aceite

- [ ] Sparklines renderizam para cada metrica
- [ ] Linha do grafico muda de cor baseado em trend e trendIsGood
- [ ] Valor atual exibido ao lado do grafico
- [ ] Icone de seta indica direcao da tendencia
- [ ] Verde para tendencia positiva, vermelho para negativa, cinza para estavel
- [ ] Para metricas onde "menos e melhor" (latencia, bot detection), queda = verde
- [ ] Graficos responsivos dentro do card

## Definition of Done (DoD)

- [ ] Arquivo `components/dashboard/sparkline-chart.tsx` criado
- [ ] Arquivo `components/dashboard/trends-section.tsx` criado
- [ ] Arquivo `app/api/dashboard/trends/route.ts` criado
- [ ] Recharts instalado: `npm install recharts`
- [ ] Tipos adicionados em `types/dashboard.ts`
- [ ] Mocks adicionados em `lib/mock/dashboard-data.ts`
- [ ] Componente integrado na pagina do dashboard
- [ ] Cores corretas para cada tipo de tendencia
- [ ] Sem erros de TypeScript
- [ ] `npm run build` passa sem erros

## Dependencias

- E01 (Layout Base)
- E08 (APIs)

## Complexidade

**Media** - Uso de biblioteca de graficos.

## Tempo Estimado

4-5 horas

## Notas para o Desenvolvedor

1. Instalar Recharts:
   ```bash
   npm install recharts
   ```

2. Recharts precisa de `ResponsiveContainer` para funcionar bem em layouts flexiveis.

3. A logica de `trendIsGood` e importante:
   - Taxa Resposta: subir e bom → trend="up" + trendIsGood=true
   - Latencia: descer e bom → trend="down" + trendIsGood=true
   - Bot Detection: descer e bom → trend="down" + trendIsGood=true

4. Para dados reais, seria necessario uma tabela de metricas agregadas por dia. A API atual usa dados simulados.

5. O sparkline deve ser minimalista - sem eixos, sem labels, apenas a linha.

6. Considerar adicionar tooltip no hover mostrando o valor do ponto.
