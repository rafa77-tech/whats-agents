# E15 - Comparativos vs Semana Anterior

## Objetivo

Implementar a logica de comparativo que mostra a diferenca entre o periodo atual e o periodo anterior em todos os componentes relevantes.

## Contexto

Todos os componentes de metricas ja tem placeholders para comparativos (props como `previousValue`). Este epico consolida a logica de calculo e garante consistencia em toda a aplicacao.

O comparativo ajuda a responder: "Estamos melhorando ou piorando?"

## Requisitos Funcionais

### Metricas com Comparativo

| Componente | Metricas |
|------------|----------|
| Cards de Meta | Taxa resposta, conversao, fechamentos |
| Qualidade | Bot detection, latencia, handoff rate |
| Pool de Chips | Msgs enviadas, taxa resposta, taxa block, erros |
| Funil | Todas as etapas |

### Regras de Calculo

1. **Periodo atual:** Ultimos N dias (7d, 14d, 30d)
2. **Periodo anterior:** N dias antes do periodo atual
3. **Formula:** `((atual - anterior) / anterior) * 100`
4. **Caso especial:** Se anterior = 0, nao mostrar comparativo

### Regras de Cor

- **Melhoria:** Verde ↑ ou ↓ (depende da metrica)
- **Piora:** Vermelho ↑ ou ↓ (depende da metrica)
- **Estavel (< 1%):** Cinza —

### Metricas onde "Menos e Melhor"

- Bot detection
- Latencia
- Taxa de block
- Erros
- Taxa de handoff

## Requisitos Tecnicos

### Arquivos a Criar/Modificar

```
/lib/dashboard/calculations.ts     # Funcoes de calculo (adicionar)
/components/dashboard/comparison-indicator.tsx  # Componente reutilizavel
```

### Funcoes Utilitarias

```typescript
// lib/dashboard/calculations.ts

/**
 * Calcula a diferenca percentual entre dois valores
 */
export function calculatePercentageChange(
  current: number,
  previous: number
): number | null {
  if (previous === 0) return null;
  return ((current - previous) / previous) * 100;
}

/**
 * Determina se a tendencia e positiva baseado no tipo de metrica
 * @param change - Variacao percentual
 * @param lesserIsBetter - Se menor valor e melhor (ex: latencia)
 */
export function isTrendPositive(
  change: number,
  lesserIsBetter: boolean = false
): boolean {
  if (lesserIsBetter) {
    return change < 0; // queda e positiva
  }
  return change > 0; // subida e positiva
}

/**
 * Formata a variacao para exibicao
 */
export function formatChange(change: number | null): string {
  if (change === null) return "N/A";
  const prefix = change > 0 ? "+" : "";
  return `${prefix}${change.toFixed(0)}%`;
}

/**
 * Determina o status da tendencia
 */
export function getTrendStatus(
  change: number | null,
  lesserIsBetter: boolean = false
): "positive" | "negative" | "neutral" {
  if (change === null || Math.abs(change) < 1) return "neutral";
  const isPositive = isTrendPositive(change, lesserIsBetter);
  return isPositive ? "positive" : "negative";
}
```

### Codigo Base - Comparison Indicator

```tsx
// components/dashboard/comparison-indicator.tsx
"use client";

import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import {
  calculatePercentageChange,
  getTrendStatus,
  formatChange,
} from "@/lib/dashboard/calculations";

interface ComparisonIndicatorProps {
  current: number;
  previous: number;
  lesserIsBetter?: boolean;
  showValue?: boolean;
  size?: "sm" | "md";
}

export function ComparisonIndicator({
  current,
  previous,
  lesserIsBetter = false,
  showValue = true,
  size = "md",
}: ComparisonIndicatorProps) {
  const change = calculatePercentageChange(current, previous);
  const status = getTrendStatus(change, lesserIsBetter);

  const iconSize = size === "sm" ? "h-3 w-3" : "h-4 w-4";
  const textSize = size === "sm" ? "text-xs" : "text-sm";

  const statusConfig = {
    positive: {
      color: "text-green-600",
      Icon: change && change > 0 ? TrendingUp : TrendingDown,
    },
    negative: {
      color: "text-red-600",
      Icon: change && change > 0 ? TrendingUp : TrendingDown,
    },
    neutral: {
      color: "text-gray-400",
      Icon: Minus,
    },
  };

  const config = statusConfig[status];
  const Icon = config.Icon;

  if (change === null) {
    return null;
  }

  return (
    <span className={`flex items-center gap-1 ${config.color} ${textSize}`}>
      <Icon className={iconSize} />
      {showValue && formatChange(change)}
    </span>
  );
}
```

### Exemplo de Uso nos Componentes

```tsx
// Em metric-card.tsx, substituir a logica de comparativo:

import { ComparisonIndicator } from "./comparison-indicator";

// No JSX:
<ComparisonIndicator
  current={value}
  previous={previousValue}
  lesserIsBetter={false} // ou true para latencia, bot detection, etc.
/>
```

### Atualizacoes Necessarias

1. **metric-card.tsx** - Usar ComparisonIndicator
2. **quality-metric-card.tsx** - Usar ComparisonIndicator com `lesserIsBetter={true}`
3. **chip-pool-metrics.tsx** - Usar ComparisonIndicator
4. **funnel-stage.tsx** - Usar ComparisonIndicator

## Criterios de Aceite

- [ ] Funcoes de calculo exportadas de `lib/dashboard/calculations.ts`
- [ ] ComparisonIndicator renderiza corretamente para todos os cenarios
- [ ] Verde quando melhoria, vermelho quando piora, cinza quando estavel
- [ ] Para metricas "menos e melhor", queda = verde
- [ ] Nao mostra indicador quando previous = 0
- [ ] Formato consistente em todos os componentes

## Definition of Done (DoD)

- [ ] Arquivo `lib/dashboard/calculations.ts` com funcoes de calculo
- [ ] Arquivo `components/dashboard/comparison-indicator.tsx` criado
- [ ] Todos os componentes de metricas usando ComparisonIndicator
- [ ] Logica de `lesserIsBetter` aplicada corretamente
- [ ] Testes unitarios para funcoes de calculo
- [ ] Sem erros de TypeScript
- [ ] `npm run build` passa sem erros

## Dependencias

- E03, E04, E06, E10 (componentes que usam comparativos)

## Complexidade

**Media** - Refatoracao de varios componentes.

## Tempo Estimado

4-5 horas

## Notas para o Desenvolvedor

1. Este epico e de REFATORACAO. Os componentes ja existem, voce vai padronizar a logica.

2. A chave e identificar quais metricas sao "lesserIsBetter":
   - Bot detection: SIM
   - Latencia: SIM
   - Handoff rate: SIM
   - Taxa de block: SIM
   - Erros: SIM
   - Taxa de resposta: NAO
   - Conversao: NAO
   - Fechamentos: NAO

3. O componente ComparisonIndicator deve ser REUTILIZAVEL em qualquer lugar.

4. Adicionar testes unitarios para as funcoes de calculo:
   ```typescript
   describe("calculatePercentageChange", () => {
     it("returns positive change", () => {
       expect(calculatePercentageChange(32, 28)).toBeCloseTo(14.29);
     });
     it("returns negative change", () => {
       expect(calculatePercentageChange(28, 32)).toBeCloseTo(-12.5);
     });
     it("returns null when previous is 0", () => {
       expect(calculatePercentageChange(10, 0)).toBeNull();
     });
   });
   ```

5. Considerar threshold para "estavel" (ex: < 1% = neutro).
