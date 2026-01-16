# E16 - Exportacao CSV

## Objetivo

Implementar a funcionalidade de exportar os dados do dashboard em formato CSV.

## Contexto

O gestor precisa poder baixar os dados do dashboard para analise externa (Excel, Google Sheets) ou para criar relatorios customizados.

O CSV deve conter todas as metricas principais do dashboard no periodo selecionado.

## Requisitos Funcionais

### Dados a Exportar

| Secao | Campos |
|-------|--------|
| Metricas | Taxa resposta, conversao, fechamentos (atual e anterior) |
| Qualidade | Bot detection, latencia, handoff rate |
| Operacional | Rate limits, fila, LLM usage |
| Chips | Status, trust, msgs, erros por chip |
| Funil | Contagem por etapa |

### Formato do CSV

```csv
Relatorio Dashboard Julia
Periodo: 10/01/2025 a 16/01/2025
Gerado em: 16/01/2025 15:30

METRICAS PRINCIPAIS
Metrica,Valor Atual,Valor Anterior,Variacao,Meta,Status
Taxa de Resposta,32%,28%,+14%,30%,Atingida
Taxa de Conversao,18%,20%,-10%,25%,Abaixo
Fechamentos/Semana,18,15,+20%,15,Atingida

QUALIDADE DA PERSONA
Metrica,Valor Atual,Valor Anterior,Variacao,Meta,Status
Deteccao Bot,0.4%,0.6%,-33%,<1%,Atingida
Latencia Media,24s,28s,-14%,<30s,Atingida
Taxa Handoff,3.2%,4.1%,-22%,<5%,Normal

POOL DE CHIPS
Chip,Status,Trust,Msgs Hoje,Taxa Resp,Erros 24h
Julia-01,active,92,47,96.2%,0
Julia-02,active,88,52,94.8%,1
...

FUNIL DE CONVERSAO
Etapa,Quantidade,Porcentagem,Variacao
Enviadas,320,100%,+12%
Entregues,312,97.5%,+11%
Respostas,102,31.9%,+18%
Interesse,48,15%,+8%
Fechadas,18,5.6%,+20%
```

## Requisitos Tecnicos

### Arquivos a Criar

```
/app/api/dashboard/export/route.ts
/lib/dashboard/csv-generator.ts
```

### Funcoes de Geracao

```typescript
// lib/dashboard/csv-generator.ts

export interface DashboardExportData {
  period: { start: string; end: string };
  metrics: Array<{
    name: string;
    current: number;
    previous: number;
    meta: number;
    unit: string;
  }>;
  quality: Array<{
    name: string;
    current: number;
    previous: number;
    meta: string;
    unit: string;
  }>;
  chips: Array<{
    name: string;
    status: string;
    trust: number;
    messagesToday: number;
    responseRate: number;
    errors: number;
  }>;
  funnel: Array<{
    stage: string;
    count: number;
    percentage: number;
    change: number;
  }>;
}

export function generateDashboardCSV(data: DashboardExportData): string {
  const lines: string[] = [];
  const { period, metrics, quality, chips, funnel } = data;

  // Header
  lines.push("Relatorio Dashboard Julia");
  lines.push(`Periodo: ${formatDate(period.start)} a ${formatDate(period.end)}`);
  lines.push(`Gerado em: ${formatDateTime(new Date())}`);
  lines.push("");

  // Metricas Principais
  lines.push("METRICAS PRINCIPAIS");
  lines.push("Metrica,Valor Atual,Valor Anterior,Variacao,Meta,Status");
  metrics.forEach((m) => {
    const change = calculateChange(m.current, m.previous);
    const status = getMetaStatus(m.current, m.meta, m.unit);
    lines.push(
      `${m.name},${formatValue(m.current, m.unit)},${formatValue(m.previous, m.unit)},${change},${formatValue(m.meta, m.unit)},${status}`
    );
  });
  lines.push("");

  // Qualidade
  lines.push("QUALIDADE DA PERSONA");
  lines.push("Metrica,Valor Atual,Valor Anterior,Variacao,Meta,Status");
  quality.forEach((q) => {
    const change = calculateChange(q.current, q.previous);
    lines.push(
      `${q.name},${formatValue(q.current, q.unit)},${formatValue(q.previous, q.unit)},${change},${q.meta},OK`
    );
  });
  lines.push("");

  // Chips
  lines.push("POOL DE CHIPS");
  lines.push("Chip,Status,Trust,Msgs Hoje,Taxa Resp,Erros 24h");
  chips.forEach((c) => {
    lines.push(
      `${c.name},${c.status},${c.trust},${c.messagesToday},${c.responseRate.toFixed(1)}%,${c.errors}`
    );
  });
  lines.push("");

  // Funil
  lines.push("FUNIL DE CONVERSAO");
  lines.push("Etapa,Quantidade,Porcentagem,Variacao");
  funnel.forEach((f) => {
    const change = f.change >= 0 ? `+${f.change.toFixed(0)}%` : `${f.change.toFixed(0)}%`;
    lines.push(`${f.stage},${f.count},${f.percentage.toFixed(1)}%,${change}`);
  });

  return lines.join("\n");
}

function formatDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString("pt-BR");
}

function formatDateTime(date: Date): string {
  return date.toLocaleString("pt-BR");
}

function formatValue(value: number, unit: string): string {
  if (unit === "%") return `${value.toFixed(1)}%`;
  if (unit === "s") return `${value}s`;
  return value.toString();
}

function calculateChange(current: number, previous: number): string {
  if (previous === 0) return "N/A";
  const change = ((current - previous) / previous) * 100;
  return change >= 0 ? `+${change.toFixed(0)}%` : `${change.toFixed(0)}%`;
}

function getMetaStatus(value: number, meta: number, unit: string): string {
  // Simplificado - adaptar conforme regras de negocio
  return value >= meta ? "Atingida" : "Abaixo";
}
```

### Codigo Base - API

```typescript
// app/api/dashboard/export/route.ts
import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { generateDashboardCSV, DashboardExportData } from "@/lib/dashboard/csv-generator";
import { getPeriodDates } from "@/lib/dashboard/calculations";

export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient();
    const searchParams = request.nextUrl.searchParams;
    const format = searchParams.get("format") || "csv";
    const period = searchParams.get("period") || "7d";

    if (format !== "csv") {
      return NextResponse.json({ error: "Format not supported" }, { status: 400 });
    }

    const { currentStart, currentEnd, previousStart, previousEnd } = getPeriodDates(period);

    // Coletar todos os dados necessarios
    // (Reutilizar logica das APIs existentes ou fazer queries diretas)

    // Exemplo simplificado:
    const exportData: DashboardExportData = {
      period: { start: currentStart, end: currentEnd },
      metrics: [
        { name: "Taxa de Resposta", current: 32, previous: 28, meta: 30, unit: "%" },
        { name: "Taxa de Conversao", current: 18, previous: 20, meta: 25, unit: "%" },
        { name: "Fechamentos/Semana", current: 18, previous: 15, meta: 15, unit: "" },
      ],
      quality: [
        { name: "Deteccao Bot", current: 0.4, previous: 0.6, meta: "<1%", unit: "%" },
        { name: "Latencia Media", current: 24, previous: 28, meta: "<30s", unit: "s" },
        { name: "Taxa Handoff", current: 3.2, previous: 4.1, meta: "<5%", unit: "%" },
      ],
      chips: [], // Buscar da API de chips
      funnel: [
        { stage: "Enviadas", count: 320, percentage: 100, change: 12 },
        { stage: "Entregues", count: 312, percentage: 97.5, change: 11 },
        { stage: "Respostas", count: 102, percentage: 31.9, change: 18 },
        { stage: "Interesse", count: 48, percentage: 15, change: 8 },
        { stage: "Fechadas", count: 18, percentage: 5.6, change: 20 },
      ],
    };

    // Buscar chips
    const { data: chips } = await supabase
      .from("chips")
      .select("instance_name, status, trust_score, msgs_enviadas_hoje, taxa_resposta, erros_ultimas_24h")
      .in("status", ["active", "ready", "warming", "degraded"]);

    exportData.chips = chips?.map((c) => ({
      name: c.instance_name || "Chip",
      status: c.status,
      trust: c.trust_score || 0,
      messagesToday: c.msgs_enviadas_hoje || 0,
      responseRate: (c.taxa_resposta || 0) * 100,
      errors: c.erros_ultimas_24h || 0,
    })) || [];

    // Gerar CSV
    const csv = generateDashboardCSV(exportData);

    // Retornar como download
    const filename = `dashboard-julia-${period}-${new Date().toISOString().split("T")[0]}.csv`;

    return new NextResponse(csv, {
      headers: {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": `attachment; filename="${filename}"`,
      },
    });
  } catch (error) {
    console.error("Error exporting dashboard:", error);
    return NextResponse.json({ error: "Failed to export" }, { status: 500 });
  }
}
```

### Integracao com Export Menu

```tsx
// Atualizar components/dashboard/export-menu.tsx

const handleExport = async (format: "csv" | "pdf") => {
  if (format === "csv") {
    // Trigger download
    window.location.href = `/api/dashboard/export?format=csv&period=${period}`;
  } else {
    // PDF sera implementado no E17
    onExport(format);
  }
};
```

## Criterios de Aceite

- [ ] Botao "Exportar CSV" baixa arquivo .csv
- [ ] CSV contem todas as secoes: metricas, qualidade, chips, funil
- [ ] Dados correspondem ao periodo selecionado
- [ ] Formato legivel (separadores, headers)
- [ ] Filename inclui periodo e data
- [ ] Encoding UTF-8 (acentos funcionam)

## Definition of Done (DoD)

- [ ] Arquivo `lib/dashboard/csv-generator.ts` criado
- [ ] Arquivo `app/api/dashboard/export/route.ts` criado
- [ ] Export Menu atualizado para chamar API
- [ ] CSV gerado corretamente com todos os dados
- [ ] Download funciona no navegador
- [ ] Acentuacao correta (UTF-8)
- [ ] Sem erros de TypeScript
- [ ] `npm run build` passa sem erros

## Dependencias

- E02 (Export Menu)
- E08, E09 (APIs de dados)

## Complexidade

**Media** - Geracao de arquivo e download.

## Tempo Estimado

4-5 horas

## Notas para o Desenvolvedor

1. O CSV deve ser em UTF-8 para suportar acentos corretamente.

2. Para o download funcionar, a API retorna o arquivo diretamente:
   ```typescript
   return new NextResponse(csv, {
     headers: {
       "Content-Type": "text/csv; charset=utf-8",
       "Content-Disposition": `attachment; filename="${filename}"`,
     },
   });
   ```

3. No client, o download pode ser iniciado com:
   ```typescript
   window.location.href = `/api/dashboard/export?format=csv&period=${period}`;
   ```
   Ou criando um link temporario:
   ```typescript
   const link = document.createElement("a");
   link.href = `/api/dashboard/export?format=csv&period=${period}`;
   link.download = "dashboard.csv";
   link.click();
   ```

4. Idealmente, os dados devem vir das mesmas fontes que alimentam o dashboard para garantir consistencia.

5. Considerar adicionar BOM para Excel reconhecer UTF-8:
   ```typescript
   const bom = "\uFEFF";
   const csv = bom + generateDashboardCSV(data);
   ```
