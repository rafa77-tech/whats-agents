# E07 - Pool de Chips - Lista Detalhada

## Objetivo

Criar a lista detalhada de chips com todas as informacoes relevantes de cada um, permitindo visualizacao rapida do estado individual.

## Contexto

Alem da visao agregada (E06), o gestor precisa ver detalhes de cada chip:
- Numero/nome
- Status atual
- Trust score com indicador visual
- Mensagens enviadas hoje
- Taxa de resposta
- Erros recentes
- Alertas ativos

A lista deve ter um link "Ver todos" que leva para pagina dedicada de gestao de chips.

## Requisitos Funcionais

### Tabela de Chips

Colunas:
1. **Numero** - Nome do chip (ex: "Julia-01")
2. **Status** - Badge colorido (Active, Ready, Warming, etc.)
3. **Trust** - Score numerico + indicador colorido
4. **Msgs Hoje** - Formato "X/limite"
5. **Tx Resposta** - Porcentagem
6. **Erros** - Quantidade nas ultimas 24h
7. **Alertas** - Icone se tiver alerta ativo

### Limite de Exibicao

- Mostrar no maximo 5 chips na lista resumida
- Ordenar por: alertas ativos primeiro, depois por trust (menor primeiro)
- Link "Ver todos →" no header

### Indicadores de Trust

- 75+: Badge verde
- 50-74: Badge amarelo
- 35-49: Badge laranja
- <35: Badge vermelho

## Requisitos Tecnicos

### Arquivos a Criar

```
/components/dashboard/chip-list-table.tsx
```

### Interfaces

```typescript
// types/dashboard.ts (adicionar)

export interface ChipDetail {
  id: string;
  name: string;
  telefone: string;
  status: ChipStatus;
  trustScore: number;
  trustLevel: TrustLevel;
  messagesToday: number;
  dailyLimit: number;
  responseRate: number;
  errorsLast24h: number;
  hasActiveAlert: boolean;
  alertMessage?: string;
  warmingDay?: number; // se estiver em warming
}
```

### Layout Visual

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Chips Detalhados                                            [Ver todos →]  │
├─────────────┬────────┬───────┬──────────┬──────────┬─────────┬─────────────┤
│ Numero      │ Status │ Trust │ Msgs Hoje│ Tx Resp  │ Erros   │ Alertas     │
├─────────────┼────────┼───────┼──────────┼──────────┼─────────┼─────────────┤
│ Julia-01    │ 🟢 Act │ 92 🟢 │ 47/100   │ 96.2%    │ 0       │ -           │
│ Julia-02    │ 🟢 Act │ 88 🟢 │ 52/100   │ 94.8%    │ 1       │ -           │
│ Julia-03    │ 🟡 Rdy │ 85 🟢 │ -        │ -        │ 0       │ -           │
│ Julia-04    │ 🔵 Wrm │ 72 🟡 │ 15/30    │ 91.0%    │ 0       │ Dia 14/21   │
│ Julia-05    │ 🟠 Deg │ 48 🟠 │ 8/30     │ 78.5%    │ 3       │ ⚠️ Trust    │
└─────────────┴────────┴───────┴──────────┴──────────┴─────────┴─────────────┘
```

### Codigo Base - Chip List Table

```tsx
// components/dashboard/chip-list-table.tsx
"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChipDetail, ChipStatus, TrustLevel } from "@/types/dashboard";
import { AlertTriangle, ChevronRight } from "lucide-react";
import Link from "next/link";

interface ChipListTableProps {
  chips: ChipDetail[];
  maxItems?: number;
  showViewAll?: boolean;
}

const statusConfig: Record<
  ChipStatus,
  { label: string; variant: "default" | "secondary" | "outline" | "destructive"; className: string }
> = {
  active: { label: "Active", variant: "default", className: "bg-green-100 text-green-700 border-green-200" },
  ready: { label: "Ready", variant: "secondary", className: "bg-blue-100 text-blue-700 border-blue-200" },
  warming: { label: "Warming", variant: "secondary", className: "bg-yellow-100 text-yellow-700 border-yellow-200" },
  degraded: { label: "Degraded", variant: "outline", className: "bg-orange-100 text-orange-700 border-orange-200" },
  paused: { label: "Paused", variant: "outline", className: "bg-gray-100 text-gray-700 border-gray-200" },
  banned: { label: "Banned", variant: "destructive", className: "bg-red-100 text-red-700 border-red-200" },
  provisioned: { label: "Prov.", variant: "outline", className: "bg-gray-100 text-gray-600 border-gray-200" },
  pending: { label: "Pending", variant: "outline", className: "bg-gray-100 text-gray-600 border-gray-200" },
  cancelled: { label: "Cancelled", variant: "outline", className: "bg-gray-100 text-gray-400 border-gray-200" },
};

const trustColors: Record<TrustLevel, string> = {
  verde: "text-green-600 bg-green-100",
  amarelo: "text-yellow-600 bg-yellow-100",
  laranja: "text-orange-600 bg-orange-100",
  vermelho: "text-red-600 bg-red-100",
};

function TrustBadge({ score, level }: { score: number; level: TrustLevel }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-sm font-medium ${trustColors[level]}`}
    >
      {score}
    </span>
  );
}

function StatusBadge({ status }: { status: ChipStatus }) {
  const config = statusConfig[status];
  return (
    <Badge variant="outline" className={config.className}>
      {config.label}
    </Badge>
  );
}

export function ChipListTable({
  chips,
  maxItems = 5,
  showViewAll = true,
}: ChipListTableProps) {
  // Ordenar: alertas primeiro, depois por trust (menor primeiro)
  const sortedChips = [...chips].sort((a, b) => {
    if (a.hasActiveAlert && !b.hasActiveAlert) return -1;
    if (!a.hasActiveAlert && b.hasActiveAlert) return 1;
    return a.trustScore - b.trustScore;
  });

  const displayedChips = sortedChips.slice(0, maxItems);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-gray-700">Chips Detalhados</h4>
        {showViewAll && (
          <Link href="/chips">
            <Button variant="ghost" size="sm" className="text-sm">
              Ver todos
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </Link>
        )}
      </div>

      <div className="border rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-gray-50">
              <TableHead className="w-[120px]">Numero</TableHead>
              <TableHead className="w-[90px]">Status</TableHead>
              <TableHead className="w-[70px]">Trust</TableHead>
              <TableHead className="w-[90px]">Msgs Hoje</TableHead>
              <TableHead className="w-[80px]">Tx Resp</TableHead>
              <TableHead className="w-[60px]">Erros</TableHead>
              <TableHead>Alertas</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {displayedChips.map((chip) => (
              <TableRow
                key={chip.id}
                className={chip.hasActiveAlert ? "bg-red-50" : ""}
              >
                <TableCell className="font-medium">{chip.name}</TableCell>
                <TableCell>
                  <StatusBadge status={chip.status} />
                </TableCell>
                <TableCell>
                  <TrustBadge score={chip.trustScore} level={chip.trustLevel} />
                </TableCell>
                <TableCell>
                  {chip.status === "active" || chip.status === "warming" ? (
                    <span className="text-gray-600">
                      {chip.messagesToday}/{chip.dailyLimit}
                    </span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </TableCell>
                <TableCell>
                  {chip.responseRate > 0 ? (
                    <span
                      className={
                        chip.responseRate >= 90
                          ? "text-green-600"
                          : chip.responseRate >= 80
                          ? "text-yellow-600"
                          : "text-red-600"
                      }
                    >
                      {chip.responseRate.toFixed(1)}%
                    </span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </TableCell>
                <TableCell>
                  <span
                    className={
                      chip.errorsLast24h > 0 ? "text-red-600 font-medium" : "text-gray-400"
                    }
                  >
                    {chip.errorsLast24h}
                  </span>
                </TableCell>
                <TableCell>
                  {chip.hasActiveAlert ? (
                    <div className="flex items-center gap-1 text-orange-600">
                      <AlertTriangle className="h-4 w-4" />
                      <span className="text-xs">{chip.alertMessage}</span>
                    </div>
                  ) : chip.warmingDay ? (
                    <span className="text-xs text-blue-600">
                      Dia {chip.warmingDay}/21
                    </span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
```

### Dados Mock

```typescript
// lib/mock/dashboard-data.ts (adicionar)

export const mockChipsList: ChipDetail[] = [
  {
    id: "1",
    name: "Julia-01",
    telefone: "+5511999990001",
    status: "active",
    trustScore: 92,
    trustLevel: "verde",
    messagesToday: 47,
    dailyLimit: 100,
    responseRate: 96.2,
    errorsLast24h: 0,
    hasActiveAlert: false,
  },
  {
    id: "2",
    name: "Julia-02",
    telefone: "+5511999990002",
    status: "active",
    trustScore: 88,
    trustLevel: "verde",
    messagesToday: 52,
    dailyLimit: 100,
    responseRate: 94.8,
    errorsLast24h: 1,
    hasActiveAlert: false,
  },
  {
    id: "3",
    name: "Julia-03",
    telefone: "+5511999990003",
    status: "ready",
    trustScore: 85,
    trustLevel: "verde",
    messagesToday: 0,
    dailyLimit: 100,
    responseRate: 0,
    errorsLast24h: 0,
    hasActiveAlert: false,
  },
  {
    id: "4",
    name: "Julia-04",
    telefone: "+5511999990004",
    status: "warming",
    trustScore: 72,
    trustLevel: "amarelo",
    messagesToday: 15,
    dailyLimit: 30,
    responseRate: 91.0,
    errorsLast24h: 0,
    hasActiveAlert: false,
    warmingDay: 14,
  },
  {
    id: "5",
    name: "Julia-05",
    telefone: "+5511999990005",
    status: "degraded",
    trustScore: 48,
    trustLevel: "laranja",
    messagesToday: 8,
    dailyLimit: 30,
    responseRate: 78.5,
    errorsLast24h: 3,
    hasActiveAlert: true,
    alertMessage: "Trust baixo",
  },
];
```

## Criterios de Aceite

- [ ] Tabela exibe todas as colunas especificadas
- [ ] Status tem badge colorido correto para cada tipo
- [ ] Trust score tem cor de fundo baseada no level
- [ ] Msgs Hoje mostra "X/limite" para chips ativos/warming, "-" para outros
- [ ] Taxa Resposta tem cor: verde >= 90%, amarelo >= 80%, vermelho < 80%
- [ ] Erros em vermelho se > 0, cinza se 0
- [ ] Alertas mostram icone e mensagem, ou "Dia X/21" para warming
- [ ] Chips com alerta ativo tem background vermelho claro na linha
- [ ] Ordenacao: alertas primeiro, depois trust menor primeiro
- [ ] Maximo 5 chips exibidos por padrao
- [ ] Link "Ver todos" redireciona para /chips

## Definition of Done (DoD)

- [ ] Arquivo `components/dashboard/chip-list-table.tsx` criado
- [ ] Tipo `ChipDetail` adicionado em `types/dashboard.ts`
- [ ] Mocks adicionados em `lib/mock/dashboard-data.ts`
- [ ] Table instalado: `npx shadcn-ui@latest add table`
- [ ] Componente integrado na secao de chips do dashboard
- [ ] Ordenacao funcionando corretamente
- [ ] Cores e badges corretos para cada estado
- [ ] Link "Ver todos" funcional (pode levar para 404 por enquanto)
- [ ] Sem erros de TypeScript
- [ ] `npm run build` passa sem erros

## Dependencias

- E01 (Layout Base)
- E06 (Pool de Chips - Visao Geral)

## Complexidade

**Media** - Tabela com muita logica de formatacao condicional.

## Tempo Estimado

4-5 horas

## Notas para o Desenvolvedor

1. Instalar Table se nao existir:
   ```bash
   npx shadcn-ui@latest add table
   ```

2. A ordenacao e importante:
   - Primeiro: chips com `hasActiveAlert: true`
   - Segundo: chips ordenados por `trustScore` crescente (menor = mais problematico)

3. A pagina `/chips` nao existe ainda. O link pode levar para 404 por enquanto ou criar uma pagina placeholder.

4. O limite diario (`dailyLimit`) varia conforme o status:
   - active: 100
   - warming: 30 (varia por fase)
   - degraded: 30

5. Para chips em warming, mostrar "Dia X/21" na coluna de alertas se nao tiver alerta ativo.

6. A linha do chip deve ter `bg-red-50` se `hasActiveAlert: true` para destacar visualmente.
