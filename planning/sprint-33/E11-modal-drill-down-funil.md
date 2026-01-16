# E11 - Modal Drill-Down do Funil

## Objetivo

Criar o modal que exibe a lista de medicos em cada etapa do funil quando o usuario clica em uma etapa.

## Contexto

O drill-down permite ao gestor ver QUEM sao os medicos em cada etapa do funil. Por exemplo, ao clicar em "Interesse", o modal mostra a lista de medicos que demonstraram interesse mas ainda nao fecharam.

Isso ajuda a:
- Identificar oportunidades de follow-up
- Entender gargalos especificos
- Tomar acoes direcionadas

## Requisitos Funcionais

### Informacoes por Medico

| Campo | Descricao |
|-------|-----------|
| Nome | Nome completo do medico |
| Telefone | Numero de contato |
| Especialidade | Area de atuacao |
| Ultimo Contato | Tempo desde ultima interacao |
| Chip | Qual chip esta em contato |
| Acao | Botao para ver conversa |

### Funcionalidades

1. **Paginacao** - 10 itens por pagina
2. **Busca** - Filtrar por nome
3. **Ordenacao** - Por ultimo contato (mais recente primeiro)
4. **Acao** - Link para Chatwoot/detalhes da conversa

## Requisitos Tecnicos

### Arquivos a Criar

```
/components/dashboard/funnel-drilldown-modal.tsx
/app/api/dashboard/funnel/[stage]/route.ts
```

### Interfaces

```typescript
// types/dashboard.ts (adicionar)

export interface FunnelDrilldownItem {
  id: string;
  medicoId: string;
  nome: string;
  telefone: string;
  especialidade: string;
  ultimoContato: string; // ISO timestamp
  chipName: string;
  conversaId?: string;
  chatwootUrl?: string;
}

export interface FunnelDrilldownData {
  stage: string;
  stageLabel: string;
  items: FunnelDrilldownItem[];
  total: number;
  page: number;
  pageSize: number;
}
```

### Layout Visual

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Medicos em "Interesse" (48)                                           [X]  │
├─────────────────────────────────────────────────────────────────────────────┤
│ [🔍 Buscar por nome...]                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Nome              │ Especialidade │ Ultimo Contato │ Chip      │ Acao      │
├───────────────────┼───────────────┼────────────────┼───────────┼───────────┤
│ Dr. Carlos Silva  │ Cardiologia   │ ha 2 horas     │ Julia-01  │ [Ver]     │
│ Dra. Maria Santos │ Pediatria     │ ha 5 horas     │ Julia-02  │ [Ver]     │
│ Dr. Joao Costa    │ Clinica       │ ha 1 dia       │ Julia-01  │ [Ver]     │
│ ...               │ ...           │ ...            │ ...       │ ...       │
├─────────────────────────────────────────────────────────────────────────────┤
│                        [< Anterior] Pagina 1 de 5 [Proximo >]               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Codigo Base - API

```typescript
// app/api/dashboard/funnel/[stage]/route.ts
import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

const stageLabels: Record<string, string> = {
  enviadas: "Enviadas",
  entregues: "Entregues",
  respostas: "Respostas",
  interesse: "Interesse",
  fechadas: "Fechadas",
};

export async function GET(
  request: NextRequest,
  { params }: { params: { stage: string } }
) {
  try {
    const supabase = await createClient();
    const stage = params.stage;
    const searchParams = request.nextUrl.searchParams;

    const page = parseInt(searchParams.get("page") || "1");
    const pageSize = parseInt(searchParams.get("pageSize") || "10");
    const search = searchParams.get("search") || "";
    const period = searchParams.get("period") || "7d";

    const offset = (page - 1) * pageSize;

    // Definir filtro baseado na etapa
    let statusFilter: string[] = [];
    switch (stage) {
      case "enviadas":
        statusFilter = ["enviado", "entregue", "respondido", "interesse", "fechado"];
        break;
      case "entregues":
        statusFilter = ["entregue", "respondido", "interesse", "fechado"];
        break;
      case "respostas":
        statusFilter = ["respondido", "interesse", "fechado"];
        break;
      case "interesse":
        statusFilter = ["interesse"];
        break;
      case "fechadas":
        statusFilter = ["fechado"];
        break;
      default:
        return NextResponse.json({ error: "Invalid stage" }, { status: 400 });
    }

    // Calcular data inicio do periodo
    const days = parseInt(period) || 7;
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);

    // Query principal
    let query = supabase
      .from("conversas")
      .select(`
        id,
        cliente_id,
        status,
        updated_at,
        chip_id,
        clientes (
          primeiro_nome,
          sobrenome,
          telefone
        ),
        especialidades (
          nome
        ),
        chips (
          instance_name
        )
      `, { count: "exact" })
      .in("status", statusFilter)
      .gte("updated_at", startDate.toISOString())
      .order("updated_at", { ascending: false });

    // Filtro de busca
    if (search) {
      query = query.or(`clientes.primeiro_nome.ilike.%${search}%,clientes.sobrenome.ilike.%${search}%`);
    }

    // Paginacao
    query = query.range(offset, offset + pageSize - 1);

    const { data: conversas, count, error } = await query;

    if (error) throw error;

    // Formatar resposta
    const items = conversas?.map((c) => ({
      id: c.id,
      medicoId: c.cliente_id,
      nome: c.clientes
        ? `${c.clientes.primeiro_nome || ""} ${c.clientes.sobrenome || ""}`.trim()
        : "Desconhecido",
      telefone: c.clientes?.telefone || "",
      especialidade: c.especialidades?.nome || "Nao informada",
      ultimoContato: c.updated_at,
      chipName: c.chips?.instance_name || "N/A",
      conversaId: c.id,
      chatwootUrl: c.id ? `${process.env.CHATWOOT_URL}/conversations/${c.id}` : undefined,
    })) || [];

    return NextResponse.json({
      stage,
      stageLabel: stageLabels[stage] || stage,
      items,
      total: count || 0,
      page,
      pageSize,
    });
  } catch (error) {
    console.error("Error fetching funnel drilldown:", error);
    return NextResponse.json(
      { error: "Failed to fetch drilldown data" },
      { status: 500 }
    );
  }
}
```

### Codigo Base - Modal

```tsx
// components/dashboard/funnel-drilldown-modal.tsx
"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { FunnelDrilldownData, FunnelDrilldownItem } from "@/types/dashboard";
import { Search, ExternalLink, Loader2, ChevronLeft, ChevronRight } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";

interface FunnelDrilldownModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  stage: string | null;
  period: string;
}

export function FunnelDrilldownModal({
  open,
  onOpenChange,
  stage,
  period,
}: FunnelDrilldownModalProps) {
  const [data, setData] = useState<FunnelDrilldownData | null>(null);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (open && stage) {
      fetchData();
    }
  }, [open, stage, page, search, period]);

  const fetchData = async () => {
    if (!stage) return;

    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        pageSize: "10",
        search,
        period,
      });

      const res = await fetch(`/api/dashboard/funnel/${stage}?${params}`);
      const json = await res.json();

      if (res.ok) {
        setData(json);
      }
    } catch (error) {
      console.error("Error fetching drilldown:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setPage(1); // Reset page on search
  };

  const totalPages = data ? Math.ceil(data.total / data.pageSize) : 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>
            Medicos em "{data?.stageLabel || stage}" ({data?.total || 0})
          </DialogTitle>
        </DialogHeader>

        {/* Busca */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Buscar por nome..."
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* Tabela */}
        <div className="flex-1 overflow-auto border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Especialidade</TableHead>
                <TableHead>Ultimo Contato</TableHead>
                <TableHead>Chip</TableHead>
                <TableHead className="w-[80px]">Acao</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                  </TableCell>
                </TableRow>
              ) : data?.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8 text-gray-500">
                    Nenhum medico encontrado
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-medium">{item.nome}</TableCell>
                    <TableCell className="text-gray-600">
                      {item.especialidade}
                    </TableCell>
                    <TableCell className="text-gray-500">
                      {formatDistanceToNow(new Date(item.ultimoContato), {
                        addSuffix: true,
                        locale: ptBR,
                      })}
                    </TableCell>
                    <TableCell className="text-gray-600">{item.chipName}</TableCell>
                    <TableCell>
                      {item.chatwootUrl && (
                        <Button
                          variant="ghost"
                          size="sm"
                          asChild
                        >
                          <a
                            href={item.chatwootUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <ExternalLink className="h-4 w-4" />
                          </a>
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        {/* Paginacao */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between pt-4 border-t">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1 || loading}
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Anterior
            </Button>
            <span className="text-sm text-gray-500">
              Pagina {page} de {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages || loading}
            >
              Proximo
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
```

## Criterios de Aceite

- [ ] Modal abre ao clicar em etapa do funil
- [ ] Titulo mostra nome da etapa e total de itens
- [ ] Campo de busca filtra por nome
- [ ] Tabela exibe: nome, especialidade, ultimo contato, chip, acao
- [ ] Ultimo contato em formato relativo ("ha 2 horas")
- [ ] Botao "Ver" abre link externo para Chatwoot
- [ ] Paginacao funciona (10 itens por pagina)
- [ ] Loading state enquanto carrega
- [ ] Empty state quando nao ha resultados
- [ ] Modal fecha ao clicar fora ou no X

## Definition of Done (DoD)

- [ ] Arquivo `components/dashboard/funnel-drilldown-modal.tsx` criado
- [ ] Arquivo `app/api/dashboard/funnel/[stage]/route.ts` criado
- [ ] Tipos `FunnelDrilldownItem` e `FunnelDrilldownData` em `types/dashboard.ts`
- [ ] Dialog instalado: `npx shadcn-ui@latest add dialog`
- [ ] Modal integrado na pagina do dashboard
- [ ] Conectado ao callback `onStageClick` do funil
- [ ] Busca funcionando
- [ ] Paginacao funcionando
- [ ] Sem erros de TypeScript
- [ ] `npm run build` passa sem erros

## Dependencias

- E10 (Funil de Conversao Visual)
- E08 (APIs)

## Complexidade

**Alta** - Modal com estado, paginacao, busca e API.

## Tempo Estimado

6-8 horas

## Notas para o Desenvolvedor

1. Instalar Dialog se nao existir:
   ```bash
   npx shadcn-ui@latest add dialog
   ```

2. A query do Supabase usa relacionamentos. Verificar se as foreign keys existem:
   - `conversas.cliente_id` → `clientes.id`
   - `conversas.chip_id` → `chips.id`
   - `clientes.especialidade_id` → `especialidades.id` (ou campo diferente)

3. O filtro de status por etapa e simplificado. Adaptar conforme a logica real do sistema.

4. A URL do Chatwoot vem da env `CHATWOOT_URL`. Se nao existir, o botao nao aparece.

5. Considerar debounce no campo de busca para evitar muitas requisicoes.

6. O modal deve resetar o estado (page, search) ao fechar.
