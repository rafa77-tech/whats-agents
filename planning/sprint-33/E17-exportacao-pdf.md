# E17 - Exportacao PDF

## Objetivo

Implementar a funcionalidade de exportar os dados do dashboard em formato PDF, gerando um relatorio visual profissional.

## Contexto

O PDF e util para:
- Compartilhar com stakeholders que nao tem acesso ao dashboard
- Arquivar relatorios periodicos
- Apresentacoes e reunioes

O PDF deve ser visualmente similar ao dashboard, com graficos e formatacao profissional.

## Requisitos Funcionais

### Conteudo do PDF

1. **Capa**
   - Logo/Titulo: "Relatorio Dashboard Julia"
   - Periodo do relatorio
   - Data de geracao

2. **Resumo Executivo**
   - Metricas principais vs metas
   - Status geral (verde/amarelo/vermelho)

3. **Metricas Detalhadas**
   - Cards de metricas com comparativos
   - Qualidade da persona

4. **Pool de Chips**
   - Tabela de chips
   - Distribuicao por status/trust

5. **Funil de Conversao**
   - Grafico do funil
   - Numeros por etapa

6. **Rodape**
   - "Gerado automaticamente pelo Dashboard Julia"
   - Numero da pagina

## Requisitos Tecnicos

### Dependencias

```bash
npm install @react-pdf/renderer
# ou
npm install puppeteer  # para screenshot do dashboard
```

### Abordagens Possiveis

**Opcao 1: React-PDF (Recomendado para MVP)**
- Gera PDF no servidor/client
- Layout customizado
- Mais leve

**Opcao 2: Puppeteer (Screenshot)**
- Captura screenshot do dashboard
- Visual identico
- Mais pesado (requer Chrome headless)

### Arquivos a Criar

```
/lib/dashboard/pdf-generator.tsx    # Componente React-PDF
/app/api/dashboard/export/pdf/route.ts
```

### Codigo Base - React-PDF

```tsx
// lib/dashboard/pdf-generator.tsx
import React from "react";
import {
  Document,
  Page,
  Text,
  View,
  StyleSheet,
  Font,
} from "@react-pdf/renderer";
import { DashboardExportData } from "./csv-generator";

// Registrar fonte (opcional)
// Font.register({ family: "Inter", src: "/fonts/Inter-Regular.ttf" });

const styles = StyleSheet.create({
  page: {
    padding: 40,
    fontSize: 10,
    fontFamily: "Helvetica",
  },
  header: {
    marginBottom: 20,
    borderBottom: "1 solid #e5e7eb",
    paddingBottom: 10,
  },
  title: {
    fontSize: 20,
    fontWeight: "bold",
    color: "#111827",
  },
  subtitle: {
    fontSize: 12,
    color: "#6b7280",
    marginTop: 4,
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: "bold",
    color: "#374151",
    marginBottom: 10,
    backgroundColor: "#f3f4f6",
    padding: 8,
  },
  table: {
    display: "flex",
    flexDirection: "column",
    border: "1 solid #e5e7eb",
  },
  tableRow: {
    flexDirection: "row",
    borderBottom: "1 solid #e5e7eb",
  },
  tableHeader: {
    backgroundColor: "#f9fafb",
    fontWeight: "bold",
  },
  tableCell: {
    flex: 1,
    padding: 6,
    fontSize: 9,
  },
  metricCard: {
    flexDirection: "row",
    justifyContent: "space-between",
    padding: 10,
    marginBottom: 8,
    backgroundColor: "#f9fafb",
    borderRadius: 4,
  },
  metricValue: {
    fontSize: 18,
    fontWeight: "bold",
    color: "#111827",
  },
  metricLabel: {
    fontSize: 10,
    color: "#6b7280",
  },
  statusGreen: {
    color: "#059669",
  },
  statusRed: {
    color: "#dc2626",
  },
  statusYellow: {
    color: "#d97706",
  },
  footer: {
    position: "absolute",
    bottom: 30,
    left: 40,
    right: 40,
    textAlign: "center",
    fontSize: 8,
    color: "#9ca3af",
  },
});

interface DashboardPDFProps {
  data: DashboardExportData;
}

export function DashboardPDF({ data }: DashboardPDFProps) {
  const { period, metrics, quality, chips, funnel } = data;

  const formatDate = (iso: string) => new Date(iso).toLocaleDateString("pt-BR");

  return (
    <Document>
      {/* Pagina 1: Metricas */}
      <Page size="A4" style={styles.page}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>Relatorio Dashboard Julia</Text>
          <Text style={styles.subtitle}>
            Periodo: {formatDate(period.start)} a {formatDate(period.end)}
          </Text>
          <Text style={styles.subtitle}>
            Gerado em: {new Date().toLocaleString("pt-BR")}
          </Text>
        </View>

        {/* Metricas Principais */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Metricas Principais</Text>
          {metrics.map((m, i) => {
            const change = m.previous > 0
              ? ((m.current - m.previous) / m.previous) * 100
              : 0;
            const isGood = m.current >= m.meta;

            return (
              <View key={i} style={styles.metricCard}>
                <View>
                  <Text style={styles.metricLabel}>{m.name}</Text>
                  <Text style={styles.metricValue}>
                    {m.current}{m.unit}
                  </Text>
                </View>
                <View style={{ alignItems: "flex-end" }}>
                  <Text style={styles.metricLabel}>Meta: {m.meta}{m.unit}</Text>
                  <Text style={isGood ? styles.statusGreen : styles.statusRed}>
                    {isGood ? "Atingida" : "Abaixo"} ({change >= 0 ? "+" : ""}{change.toFixed(0)}%)
                  </Text>
                </View>
              </View>
            );
          })}
        </View>

        {/* Qualidade */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Qualidade da Persona</Text>
          {quality.map((q, i) => (
            <View key={i} style={styles.metricCard}>
              <View>
                <Text style={styles.metricLabel}>{q.name}</Text>
                <Text style={styles.metricValue}>
                  {q.current}{q.unit}
                </Text>
              </View>
              <View style={{ alignItems: "flex-end" }}>
                <Text style={styles.metricLabel}>Meta: {q.meta}</Text>
                <Text style={styles.statusGreen}>OK</Text>
              </View>
            </View>
          ))}
        </View>

        <Text style={styles.footer}>
          Gerado automaticamente pelo Dashboard Julia - Pagina 1
        </Text>
      </Page>

      {/* Pagina 2: Chips e Funil */}
      <Page size="A4" style={styles.page}>
        {/* Pool de Chips */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Pool de Chips</Text>
          <View style={styles.table}>
            <View style={[styles.tableRow, styles.tableHeader]}>
              <Text style={styles.tableCell}>Chip</Text>
              <Text style={styles.tableCell}>Status</Text>
              <Text style={styles.tableCell}>Trust</Text>
              <Text style={styles.tableCell}>Msgs Hoje</Text>
              <Text style={styles.tableCell}>Taxa Resp</Text>
              <Text style={styles.tableCell}>Erros</Text>
            </View>
            {chips.map((c, i) => (
              <View key={i} style={styles.tableRow}>
                <Text style={styles.tableCell}>{c.name}</Text>
                <Text style={styles.tableCell}>{c.status}</Text>
                <Text style={styles.tableCell}>{c.trust}</Text>
                <Text style={styles.tableCell}>{c.messagesToday}</Text>
                <Text style={styles.tableCell}>{c.responseRate.toFixed(1)}%</Text>
                <Text style={styles.tableCell}>{c.errors}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* Funil */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Funil de Conversao</Text>
          <View style={styles.table}>
            <View style={[styles.tableRow, styles.tableHeader]}>
              <Text style={styles.tableCell}>Etapa</Text>
              <Text style={styles.tableCell}>Quantidade</Text>
              <Text style={styles.tableCell}>Porcentagem</Text>
              <Text style={styles.tableCell}>Variacao</Text>
            </View>
            {funnel.map((f, i) => (
              <View key={i} style={styles.tableRow}>
                <Text style={styles.tableCell}>{f.stage}</Text>
                <Text style={styles.tableCell}>{f.count}</Text>
                <Text style={styles.tableCell}>{f.percentage.toFixed(1)}%</Text>
                <Text style={[
                  styles.tableCell,
                  f.change >= 0 ? styles.statusGreen : styles.statusRed
                ]}>
                  {f.change >= 0 ? "+" : ""}{f.change.toFixed(0)}%
                </Text>
              </View>
            ))}
          </View>
        </View>

        <Text style={styles.footer}>
          Gerado automaticamente pelo Dashboard Julia - Pagina 2
        </Text>
      </Page>
    </Document>
  );
}
```

### Codigo Base - API

```typescript
// app/api/dashboard/export/pdf/route.ts
import { NextRequest, NextResponse } from "next/server";
import { renderToBuffer } from "@react-pdf/renderer";
import { DashboardPDF } from "@/lib/dashboard/pdf-generator";
import { DashboardExportData } from "@/lib/dashboard/csv-generator";
import { createClient } from "@/lib/supabase/server";
import { getPeriodDates } from "@/lib/dashboard/calculations";

export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient();
    const period = request.nextUrl.searchParams.get("period") || "7d";
    const { currentStart, currentEnd } = getPeriodDates(period);

    // Coletar dados (similar ao CSV)
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
      chips: [],
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

    // Gerar PDF
    const pdfBuffer = await renderToBuffer(<DashboardPDF data={exportData} />);

    // Retornar como download
    const filename = `dashboard-julia-${period}-${new Date().toISOString().split("T")[0]}.pdf`;

    return new NextResponse(pdfBuffer, {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="${filename}"`,
      },
    });
  } catch (error) {
    console.error("Error generating PDF:", error);
    return NextResponse.json({ error: "Failed to generate PDF" }, { status: 500 });
  }
}
```

### Integracao com Export Menu

```tsx
// Atualizar components/dashboard/export-menu.tsx

const handleExport = async (format: "csv" | "pdf") => {
  const endpoint = format === "csv"
    ? `/api/dashboard/export?format=csv&period=${period}`
    : `/api/dashboard/export/pdf?period=${period}`;

  window.location.href = endpoint;
};
```

## Criterios de Aceite

- [ ] Botao "Exportar PDF" baixa arquivo .pdf
- [ ] PDF contem capa com titulo e periodo
- [ ] PDF contem metricas principais com status
- [ ] PDF contem tabela de chips
- [ ] PDF contem funil de conversao
- [ ] Layout profissional e legivel
- [ ] Filename inclui periodo e data

## Definition of Done (DoD)

- [ ] Dependencia instalada: `npm install @react-pdf/renderer`
- [ ] Arquivo `lib/dashboard/pdf-generator.tsx` criado
- [ ] Arquivo `app/api/dashboard/export/pdf/route.ts` criado
- [ ] Export Menu atualizado para chamar API de PDF
- [ ] PDF gerado corretamente com layout profissional
- [ ] Download funciona no navegador
- [ ] Sem erros de TypeScript
- [ ] `npm run build` passa sem erros

## Dependencias

- E16 (Exportacao CSV - compartilha estrutura de dados)
- E02 (Export Menu)

## Complexidade

**Media-Alta** - Uso de biblioteca de PDF.

## Tempo Estimado

6-8 horas

## Notas para o Desenvolvedor

1. Instalar react-pdf:
   ```bash
   npm install @react-pdf/renderer
   ```

2. React-PDF tem limitacoes:
   - Nao suporta todos os estilos CSS
   - Fontes customizadas precisam ser registradas
   - Graficos precisam ser desenhados manualmente ou usar SVG

3. Se precisar de graficos complexos, considerar:
   - Usar Puppeteer para capturar screenshot do dashboard
   - Ou gerar graficos como SVG e incluir no PDF

4. Para deploy em serverless (Vercel), react-pdf funciona bem.

5. O buffer do PDF pode ser grande. Considerar streaming para arquivos muito grandes.

6. Testar em diferentes navegadores - alguns podem abrir o PDF em vez de baixar.

7. Alternativa mais simples: usar servico externo como html2pdf ou similar.
