# E10 - Funil de Conversao Visual

## Objetivo

Criar o componente visual do funil de conversao que mostra o pipeline de vendas da Julia: Enviadas → Entregues → Respostas → Interesse → Fechadas.

## Contexto

O funil e uma das visualizacoes mais importantes do dashboard. Mostra em qual etapa os medicos estao no processo de conversao e permite identificar gargalos.

Cada etapa deve ser clicavel para drill-down (implementado no E11).

## Requisitos Funcionais

### Etapas do Funil

1. **Enviadas** - Total de mensagens enviadas
2. **Entregues** - Mensagens confirmadas como entregues
3. **Respostas** - Medicos que responderam
4. **Interesse** - Medicos que demonstraram interesse
5. **Fechadas** - Plantoes confirmados

### Informacoes por Etapa

- Quantidade absoluta
- Porcentagem em relacao ao total (enviadas)
- Comparativo com periodo anterior (%)

### Interatividade

- Hover mostra tooltip com detalhes
- Click abre modal de drill-down (E11)
- Visual de "funil" com barras decrescentes

## Requisitos Tecnicos

### Arquivos a Criar

```
/components/dashboard/conversion-funnel.tsx
/components/dashboard/funnel-stage.tsx
```

### Interfaces

```typescript
// types/dashboard.ts (adicionar)

export interface FunnelStage {
  id: string;
  label: string;
  count: number;
  previousCount: number;
  percentage: number; // em relacao ao total (primeira etapa)
}

export interface FunnelData {
  stages: FunnelStage[];
  period: string;
}
```

### Layout Visual

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FUNIL DE CONVERSAO                                          Periodo: 7 dias │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                         Enviadas: 320 (100%)                 +12% ↑│    │
│  └────────────────────────────────────────────────────────────────────┘    │
│      ┌────────────────────────────────────────────────────────────┐        │
│      │                    Entregues: 312 (97.5%)             +11% ↑│        │
│      └────────────────────────────────────────────────────────────┘        │
│          ┌────────────────────────────────────────────────┐                │
│          │              Respostas: 102 (31.9%)       +18% ↑│                │
│          └────────────────────────────────────────────────┘                │
│              ┌────────────────────────────────────────┐                    │
│              │          Interesse: 48 (15%)      +8% ↑│                    │
│              └────────────────────────────────────────┘                    │
│                  ┌────────────────────────────────┐                        │
│                  │      Fechadas: 18 (5.6%)  +20% ↑│                        │
│                  └────────────────────────────────┘                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Codigo Base - Funnel Stage

```tsx
// components/dashboard/funnel-stage.tsx
"use client";

import { FunnelStage } from "@/types/dashboard";
import { TrendingUp, TrendingDown } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface FunnelStageProps {
  stage: FunnelStage;
  maxCount: number; // para calcular largura relativa
  onClick: () => void;
  isFirst: boolean;
  isLast: boolean;
}

const stageColors: Record<string, { bg: string; border: string; text: string }> = {
  enviadas: { bg: "bg-blue-100", border: "border-blue-300", text: "text-blue-700" },
  entregues: { bg: "bg-blue-100", border: "border-blue-300", text: "text-blue-700" },
  respostas: { bg: "bg-green-100", border: "border-green-300", text: "text-green-700" },
  interesse: { bg: "bg-yellow-100", border: "border-yellow-300", text: "text-yellow-700" },
  fechadas: { bg: "bg-emerald-100", border: "border-emerald-300", text: "text-emerald-700" },
};

export function FunnelStageComponent({
  stage,
  maxCount,
  onClick,
  isFirst,
  isLast,
}: FunnelStageProps) {
  const { id, label, count, previousCount, percentage } = stage;

  // Calcular largura proporcional (minimo 30% para legibilidade)
  const widthPercent = Math.max(30, (count / maxCount) * 100);

  // Calcular variacao
  const diff = previousCount > 0
    ? ((count - previousCount) / previousCount) * 100
    : 0;
  const isPositive = diff > 0;

  const colors = stageColors[id] || stageColors.enviadas;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className="flex justify-center cursor-pointer transition-transform hover:scale-[1.02]"
            onClick={onClick}
            style={{
              paddingLeft: isFirst ? "0" : `${(100 - widthPercent) / 2}%`,
              paddingRight: isFirst ? "0" : `${(100 - widthPercent) / 2}%`,
            }}
          >
            <div
              className={`
                w-full py-3 px-4 rounded-lg border-2
                ${colors.bg} ${colors.border}
                flex items-center justify-between
              `}
            >
              <div className="flex items-center gap-2">
                <span className={`font-medium ${colors.text}`}>{label}:</span>
                <span className="font-bold text-gray-900">
                  {count.toLocaleString("pt-BR")}
                </span>
                <span className="text-gray-500 text-sm">
                  ({percentage.toFixed(1)}%)
                </span>
              </div>

              {Math.abs(diff) >= 1 && (
                <div
                  className={`flex items-center text-sm ${
                    isPositive ? "text-green-600" : "text-red-600"
                  }`}
                >
                  {isPositive ? (
                    <TrendingUp className="h-4 w-4 mr-1" />
                  ) : (
                    <TrendingDown className="h-4 w-4 mr-1" />
                  )}
                  {isPositive ? "+" : ""}
                  {diff.toFixed(0)}%
                </div>
              )}
            </div>
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p>Clique para ver detalhes de {label.toLowerCase()}</p>
          <p className="text-xs text-gray-400">
            Periodo anterior: {previousCount.toLocaleString("pt-BR")}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
```

### Codigo Base - Conversion Funnel

```tsx
// components/dashboard/conversion-funnel.tsx
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FunnelStageComponent } from "./funnel-stage";
import { FunnelData } from "@/types/dashboard";
import { Filter } from "lucide-react";

interface ConversionFunnelProps {
  data: FunnelData;
  onStageClick: (stageId: string) => void;
}

export function ConversionFunnel({ data, onStageClick }: ConversionFunnelProps) {
  const { stages, period } = data;
  const maxCount = stages[0]?.count || 1;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Funil de Conversao
          </CardTitle>
          <span className="text-sm text-gray-400">Periodo: {period}</span>
        </div>
      </CardHeader>
      <CardContent className="space-y-2 py-4">
        {stages.map((stage, index) => (
          <FunnelStageComponent
            key={stage.id}
            stage={stage}
            maxCount={maxCount}
            onClick={() => onStageClick(stage.id)}
            isFirst={index === 0}
            isLast={index === stages.length - 1}
          />
        ))}
      </CardContent>
    </Card>
  );
}
```

### Dados Mock

```typescript
// lib/mock/dashboard-data.ts (adicionar)

export const mockFunnelData: FunnelData = {
  stages: [
    {
      id: "enviadas",
      label: "Enviadas",
      count: 320,
      previousCount: 286,
      percentage: 100,
    },
    {
      id: "entregues",
      label: "Entregues",
      count: 312,
      previousCount: 281,
      percentage: 97.5,
    },
    {
      id: "respostas",
      label: "Respostas",
      count: 102,
      previousCount: 86,
      percentage: 31.9,
    },
    {
      id: "interesse",
      label: "Interesse",
      count: 48,
      previousCount: 44,
      percentage: 15,
    },
    {
      id: "fechadas",
      label: "Fechadas",
      count: 18,
      previousCount: 15,
      percentage: 5.6,
    },
  ],
  period: "7 dias",
};
```

## Criterios de Aceite

- [ ] Funil exibe 5 etapas em formato de funil visual
- [ ] Cada etapa mostra: label, count, percentage, comparativo
- [ ] Barras tem largura proporcional ao count (minimo 30%)
- [ ] Cores distintas por etapa
- [ ] Hover mostra tooltip com informacoes adicionais
- [ ] Click dispara callback `onStageClick` com o id da etapa
- [ ] Comparativo mostra seta verde para crescimento, vermelha para queda
- [ ] Layout responsivo (funil centralizado)

## Definition of Done (DoD)

- [ ] Arquivo `components/dashboard/conversion-funnel.tsx` criado
- [ ] Arquivo `components/dashboard/funnel-stage.tsx` criado
- [ ] Tipos `FunnelStage` e `FunnelData` adicionados em `types/dashboard.ts`
- [ ] Mocks adicionados em `lib/mock/dashboard-data.ts`
- [ ] Componente integrado na pagina do dashboard
- [ ] Callback `onStageClick` conectado (pode ser console.log por enquanto)
- [ ] Tooltip funcionando no hover
- [ ] Sem erros de TypeScript
- [ ] `npm run build` passa sem erros

## Dependencias

- E01 (Layout Base)
- E08 (API de funil para dados reais)

## Complexidade

**Media** - Visual de funil com calculos de largura.

## Tempo Estimado

5-6 horas

## Notas para o Desenvolvedor

1. O efeito de "funil" e criado usando padding lateral progressivo. A primeira barra ocupa 100% da largura, a ultima pode ocupar apenas 30%.

2. A porcentagem sempre e calculada em relacao ao TOTAL (primeira etapa), nao em relacao a etapa anterior.

3. Para o visual de funil, considere usar:
   ```css
   padding-left: calc((100% - widthPercent) / 2);
   padding-right: calc((100% - widthPercent) / 2);
   ```

4. O drill-down (E11) sera acionado pelo `onStageClick`. Por enquanto, implemente como `console.log`.

5. Cores sugeridas (todas tons pasteis):
   - Enviadas/Entregues: Azul
   - Respostas: Verde
   - Interesse: Amarelo
   - Fechadas: Verde escuro (emerald)
