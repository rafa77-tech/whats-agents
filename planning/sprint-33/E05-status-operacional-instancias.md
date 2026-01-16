# E05 - Status Operacional e Instancias WhatsApp

## Objetivo

Criar o card de status operacional que mostra rate limits, fila de mensagens, uso de LLM e status das instancias WhatsApp.

## Contexto

Este card mostra a "saude operacional" do sistema em tempo real:
- Rate limits (evitar ban do WhatsApp)
- Fila de mensagens pendentes
- Distribuicao de uso LLM (Haiku vs Sonnet)
- Status de cada instancia WhatsApp

## Requisitos Funcionais

### Metricas a Exibir

| Metrica | Threshold | Descricao |
|---------|-----------|-----------|
| Rate Limit Hora | 20/hora | Msgs enviadas na ultima hora |
| Rate Limit Dia | 100/dia | Msgs enviadas hoje |
| Fila | 0-10 normal | Msgs aguardando envio |
| LLM Haiku | ~80% | Uso do modelo rapido |
| LLM Sonnet | ~20% | Uso do modelo complexo |

### Instancias WhatsApp

Lista de instancias mostrando:
- Nome (ex: "Julia-01")
- Status (Online/Offline)
- Mensagens enviadas hoje

## Requisitos Tecnicos

### Arquivos a Criar

```
/components/dashboard/operational-status.tsx
/components/dashboard/rate-limit-bar.tsx
/components/dashboard/instance-status-list.tsx
```

### Interfaces

```typescript
// types/dashboard.ts (adicionar)

export interface RateLimitData {
  current: number;
  max: number;
  label: string;
}

export interface LLMUsageData {
  haiku: number; // percentage
  sonnet: number; // percentage
}

export interface WhatsAppInstance {
  name: string;
  status: "online" | "offline";
  messagestoday: number;
}

export interface OperationalStatusData {
  rateLimitHour: RateLimitData;
  rateLimitDay: RateLimitData;
  queueSize: number;
  llmUsage: LLMUsageData;
  instances: WhatsAppInstance[];
}
```

### Layout Visual

```
┌─────────────────────────────────────────┐
│ STATUS OPERACIONAL                      │
├─────────────────────────────────────────┤
│ Rate Limit Hora  ████░░░░░░  8/20       │
│ Rate Limit Dia   ████████░░  78/100     │
│                                         │
│ Fila: 3 msgs     LLM: 82% Haiku / 18% S │
├─────────────────────────────────────────┤
│ INSTANCIAS WHATSAPP                     │
│ ┌─────────┬────────┬──────────────────┐ │
│ │ Julia-01│ 🟢 On  │ 47 msgs hoje     │ │
│ │ Julia-02│ 🟢 On  │ 52 msgs hoje     │ │
│ │ Julia-03│ 🔴 Off │ 0 msgs hoje      │ │
│ └─────────┴────────┴──────────────────┘ │
└─────────────────────────────────────────┘
```

### Codigo Base - Rate Limit Bar

```tsx
// components/dashboard/rate-limit-bar.tsx
"use client";

import { Progress } from "@/components/ui/progress";
import { RateLimitData } from "@/types/dashboard";

interface RateLimitBarProps {
  data: RateLimitData;
}

function getProgressColor(percentage: number): string {
  if (percentage < 50) return "bg-green-500";
  if (percentage < 80) return "bg-yellow-500";
  return "bg-red-500";
}

export function RateLimitBar({ data }: RateLimitBarProps) {
  const { current, max, label } = data;
  const percentage = (current / max) * 100;

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium">
          {current}/{max}
        </span>
      </div>
      <div className="relative">
        <Progress value={percentage} className="h-2" />
        {/* Overlay de cor baseado no percentual */}
        <div
          className={`absolute top-0 left-0 h-2 rounded-full transition-all ${getProgressColor(
            percentage
          )}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
```

### Codigo Base - Instance Status List

```tsx
// components/dashboard/instance-status-list.tsx
"use client";

import { WhatsAppInstance } from "@/types/dashboard";

interface InstanceStatusListProps {
  instances: WhatsAppInstance[];
}

export function InstanceStatusList({ instances }: InstanceStatusListProps) {
  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium text-gray-700">Instancias WhatsApp</h4>
      <div className="space-y-1">
        {instances.map((instance) => (
          <div
            key={instance.name}
            className="flex items-center justify-between py-1.5 px-2 bg-gray-50 rounded"
          >
            <div className="flex items-center gap-2">
              <span
                className={`h-2 w-2 rounded-full ${
                  instance.status === "online" ? "bg-green-500" : "bg-red-500"
                }`}
              />
              <span className="text-sm font-medium">{instance.name}</span>
            </div>
            <span className="text-sm text-gray-500">
              {instance.messagestoday} msgs
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Codigo Base - Operational Status

```tsx
// components/dashboard/operational-status.tsx
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RateLimitBar } from "./rate-limit-bar";
import { InstanceStatusList } from "./instance-status-list";
import { OperationalStatusData } from "@/types/dashboard";
import { Activity, Cpu, MessageSquare } from "lucide-react";

interface OperationalStatusProps {
  data: OperationalStatusData;
}

export function OperationalStatus({ data }: OperationalStatusProps) {
  const { rateLimitHour, rateLimitDay, queueSize, llmUsage, instances } = data;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
          <Activity className="h-4 w-4" />
          Status Operacional
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Rate Limits */}
        <div className="space-y-3">
          <RateLimitBar data={rateLimitHour} />
          <RateLimitBar data={rateLimitDay} />
        </div>

        {/* Fila e LLM */}
        <div className="flex items-center justify-between pt-2 border-t">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-gray-400" />
            <span className="text-sm text-gray-600">
              Fila: <span className="font-medium">{queueSize} msgs</span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-gray-400" />
            <span className="text-sm text-gray-600">
              <span className="font-medium">{llmUsage.haiku}%</span> Haiku /{" "}
              <span className="font-medium">{llmUsage.sonnet}%</span> Sonnet
            </span>
          </div>
        </div>

        {/* Instancias */}
        <div className="pt-2 border-t">
          <InstanceStatusList instances={instances} />
        </div>
      </CardContent>
    </Card>
  );
}
```

### Dados Mock

```typescript
// lib/mock/dashboard-data.ts (adicionar)

export const mockOperationalStatus: OperationalStatusData = {
  rateLimitHour: {
    current: 8,
    max: 20,
    label: "Rate Limit Hora",
  },
  rateLimitDay: {
    current: 78,
    max: 100,
    label: "Rate Limit Dia",
  },
  queueSize: 3,
  llmUsage: {
    haiku: 82,
    sonnet: 18,
  },
  instances: [
    { name: "Julia-01", status: "online", messagestoday: 47 },
    { name: "Julia-02", status: "online", messagestoday: 52 },
    { name: "Julia-03", status: "offline", messagestoday: 0 },
  ],
};
```

## Criterios de Aceite

- [ ] Card exibe rate limit hora e dia com barras de progresso
- [ ] Barra verde < 50%, amarela 50-80%, vermelha > 80%
- [ ] Fila mostra quantidade de mensagens pendentes
- [ ] LLM mostra split Haiku/Sonnet em porcentagem
- [ ] Lista de instancias mostra nome, status (indicador colorido), msgs hoje
- [ ] Instancia online = bolinha verde, offline = bolinha vermelha
- [ ] Layout compacto que cabe na coluna do grid

## Definition of Done (DoD)

- [ ] Arquivo `components/dashboard/operational-status.tsx` criado
- [ ] Arquivo `components/dashboard/rate-limit-bar.tsx` criado
- [ ] Arquivo `components/dashboard/instance-status-list.tsx` criado
- [ ] Tipos adicionados em `types/dashboard.ts`
- [ ] Mocks adicionados em `lib/mock/dashboard-data.ts`
- [ ] Progress instalado: `npx shadcn-ui@latest add progress`
- [ ] Componente integrado na pagina do dashboard
- [ ] Cores das barras mudam corretamente com diferentes valores
- [ ] Sem erros de TypeScript
- [ ] `npm run build` passa sem erros

## Dependencias

- E01 (Layout Base)

## Complexidade

**Media** - Varios sub-componentes com logica de cores.

## Tempo Estimado

4-5 horas

## Notas para o Desenvolvedor

1. Instalar Progress se nao existir:
   ```bash
   npx shadcn-ui@latest add progress
   ```

2. A barra de progresso do shadcn/ui pode precisar de customizacao para mudar cor dinamicamente. Uma alternativa e usar div com width dinamico:
   ```tsx
   <div className="h-2 bg-gray-200 rounded-full">
     <div
       className={`h-full rounded-full ${getProgressColor(percentage)}`}
       style={{ width: `${percentage}%` }}
     />
   </div>
   ```

3. Os rate limits vem do CLAUDE.md:
   - 20 msgs/hora
   - 100 msgs/dia

4. Os dados de instancias virao da tabela `whatsapp_instances` (via API no E08).
