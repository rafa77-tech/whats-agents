# E02 - Header com Status e Controles

## Objetivo

Criar o header do dashboard com status da Julia, uptime, seletor de periodo e botao de exportacao.

## Contexto

O header e a primeira linha do dashboard e mostra informacoes criticas de status alem de controles globais que afetam toda a pagina.

## Requisitos Funcionais

1. Exibir status da Julia (Online/Offline) com indicador visual
2. Exibir uptime dos ultimos 30 dias
3. Seletor de periodo (7 dias, 14 dias, 30 dias)
4. Botao de exportar com dropdown (CSV, PDF)
5. Ultimo heartbeat (tempo relativo)

## Requisitos Tecnicos

### Arquivos a Criar

```
/components/dashboard/dashboard-header.tsx
/components/dashboard/period-selector.tsx
/components/dashboard/export-menu.tsx
```

### Interface de Props

```typescript
// types/dashboard.ts
export type DashboardPeriod = "7d" | "14d" | "30d";

export interface DashboardHeaderProps {
  juliaStatus: "online" | "offline";
  lastHeartbeat: Date | null;
  uptime30d: number; // 0-100
  selectedPeriod: DashboardPeriod;
  onPeriodChange: (period: DashboardPeriod) => void;
  onExport: (format: "csv" | "pdf") => void;
}
```

### Layout Visual

```
┌────────────────────────────────────────────────────────────────────────────┐
│ 🟢 Julia Online │ Ultimo: ha 2min │ Uptime: 99.8% │ [7 dias ▼] │ [Exportar]│
└────────────────────────────────────────────────────────────────────────────┘
```

### Codigo Base - Header

```tsx
// components/dashboard/dashboard-header.tsx
"use client";

import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import { PeriodSelector } from "./period-selector";
import { ExportMenu } from "./export-menu";
import { DashboardPeriod } from "@/types/dashboard";

interface DashboardHeaderProps {
  juliaStatus: "online" | "offline";
  lastHeartbeat: Date | null;
  uptime30d: number;
  selectedPeriod: DashboardPeriod;
  onPeriodChange: (period: DashboardPeriod) => void;
  onExport: (format: "csv" | "pdf") => void;
}

export function DashboardHeader({
  juliaStatus,
  lastHeartbeat,
  uptime30d,
  selectedPeriod,
  onPeriodChange,
  onExport,
}: DashboardHeaderProps) {
  const isOnline = juliaStatus === "online";

  return (
    <div className="flex items-center justify-between bg-white rounded-lg border px-6 py-4">
      <div className="flex items-center gap-6">
        {/* Status Julia */}
        <div className="flex items-center gap-2">
          <span
            className={`h-3 w-3 rounded-full ${
              isOnline ? "bg-green-500" : "bg-red-500"
            }`}
          />
          <span className="font-medium">
            Julia {isOnline ? "Online" : "Offline"}
          </span>
        </div>

        {/* Ultimo Heartbeat */}
        {lastHeartbeat && (
          <div className="text-sm text-gray-500">
            Ultimo:{" "}
            {formatDistanceToNow(lastHeartbeat, {
              addSuffix: true,
              locale: ptBR,
            })}
          </div>
        )}

        {/* Uptime */}
        <div className="text-sm text-gray-500">
          Uptime: <span className="font-medium">{uptime30d.toFixed(1)}%</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <PeriodSelector
          value={selectedPeriod}
          onChange={onPeriodChange}
        />
        <ExportMenu onExport={onExport} />
      </div>
    </div>
  );
}
```

### Codigo Base - Period Selector

```tsx
// components/dashboard/period-selector.tsx
"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DashboardPeriod } from "@/types/dashboard";

interface PeriodSelectorProps {
  value: DashboardPeriod;
  onChange: (value: DashboardPeriod) => void;
}

const periodLabels: Record<DashboardPeriod, string> = {
  "7d": "7 dias",
  "14d": "14 dias",
  "30d": "30 dias",
};

export function PeriodSelector({ value, onChange }: PeriodSelectorProps) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="w-[120px]">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="7d">{periodLabels["7d"]}</SelectItem>
        <SelectItem value="14d">{periodLabels["14d"]}</SelectItem>
        <SelectItem value="30d">{periodLabels["30d"]}</SelectItem>
      </SelectContent>
    </Select>
  );
}
```

### Codigo Base - Export Menu

```tsx
// components/dashboard/export-menu.tsx
"use client";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Download, FileSpreadsheet, FileText } from "lucide-react";

interface ExportMenuProps {
  onExport: (format: "csv" | "pdf") => void;
  disabled?: boolean;
}

export function ExportMenu({ onExport, disabled }: ExportMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" disabled={disabled}>
          <Download className="h-4 w-4 mr-2" />
          Exportar
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => onExport("csv")}>
          <FileSpreadsheet className="h-4 w-4 mr-2" />
          Exportar CSV
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => onExport("pdf")}>
          <FileText className="h-4 w-4 mr-2" />
          Exportar PDF
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

## Criterios de Aceite

- [ ] Header renderiza com todos os elementos visuais
- [ ] Indicador de status mostra verde para online, vermelho para offline
- [ ] Ultimo heartbeat exibe tempo relativo em portugues ("ha 2 minutos")
- [ ] Uptime exibe porcentagem com 1 casa decimal
- [ ] Seletor de periodo muda entre 7d, 14d, 30d
- [ ] Menu de exportar abre dropdown com opcoes CSV e PDF
- [ ] Layout responsivo (elementos nao quebram em 1024px)

## Definition of Done (DoD)

- [ ] Arquivo `components/dashboard/dashboard-header.tsx` criado
- [ ] Arquivo `components/dashboard/period-selector.tsx` criado
- [ ] Arquivo `components/dashboard/export-menu.tsx` criado
- [ ] Arquivo `types/dashboard.ts` criado com tipos
- [ ] Header integrado na pagina `/app/(dashboard)/page.tsx`
- [ ] Callbacks `onPeriodChange` e `onExport` funcionam (podem ser console.log por enquanto)
- [ ] Sem erros de TypeScript
- [ ] `npm run build` passa sem erros
- [ ] `npm run lint` passa sem erros

## Dependencias

- E01 (Layout Base)

## Complexidade

**Baixa** - Componentes de UI com props simples.

## Tempo Estimado

3-4 horas

## Notas para o Desenvolvedor

1. Os componentes `Select` e `DropdownMenu` vem do shadcn/ui. Verifique se estao instalados:
   ```bash
   npx shadcn-ui@latest add select dropdown-menu
   ```

2. Por enquanto, use dados mockados para `juliaStatus`, `lastHeartbeat`, `uptime30d`. A integracao com API vira no E08.

3. O estado do periodo (`selectedPeriod`) deve ser gerenciado na pagina pai (`page.tsx`) e passado como prop.

4. Os callbacks de export podem ser `console.log` por enquanto - serao implementados em E16/E17.
