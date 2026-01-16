# Sprint 33 - Dashboard de Performance Julia

## Visao Geral

**Objetivo:** Implementar o dashboard principal do sistema Julia, permitindo monitoramento completo de performance, qualidade de persona, saude dos chips e funil de conversao.

**Inicio:** 17/01/2026
**Duracao Estimada:** 2-3 semanas
**Responsavel:** Dev Junior (com supervisao)

---

## Contexto de Negocio

Julia e uma escalista virtual autonoma que prospecta medicos via WhatsApp. O dashboard deve permitir:

1. **Monitorar performance** - Julia esta atingindo as metas?
2. **Garantir qualidade** - Julia parece humana? Taxa de deteccao como bot?
3. **Saude dos chips** - Os numeros virtuais estao saudaveis?
4. **Visao do funil** - Quantos medicos em cada etapa?
5. **Alertas proativos** - Problemas criticos precisam atencao imediata

---

## Metas de Referencia (CLAUDE.md)

| Metrica | Meta | Prioridade |
|---------|------|------------|
| Taxa de resposta | > 30% | Alta |
| Latencia de resposta | < 30s | Alta |
| Deteccao como bot | < 1% | Critica |
| Uptime | > 99% | Alta |

---

## Arquitetura do Dashboard

```
/app/(dashboard)/page.tsx          <- Pagina principal do dashboard
/app/api/dashboard/                <- APIs do dashboard
  ├── metrics/route.ts             <- Metricas gerais
  ├── funnel/route.ts              <- Dados do funil
  ├── funnel/[stage]/route.ts      <- Drill-down por etapa
  ├── chips/route.ts               <- Pool de chips
  ├── chips/[id]/route.ts          <- Detalhes de chip
  ├── alerts/route.ts              <- Alertas
  ├── activity/route.ts            <- Feed de atividades
  └── export/route.ts              <- Exportacao CSV/PDF
/components/dashboard/
  ├── header.tsx                   <- Header com status
  ├── period-selector.tsx          <- Seletor de periodo
  ├── metric-card.tsx              <- Card de metrica
  ├── comparison-badge.tsx         <- Badge de comparativo
  ├── chip-pool-status.tsx         <- Status do pool
  ├── chip-list.tsx                <- Lista de chips
  ├── conversion-funnel.tsx        <- Funil de conversao
  ├── funnel-drilldown-modal.tsx   <- Modal drill-down
  ├── sparkline-chart.tsx          <- Grafico sparkline
  ├── alerts-list.tsx              <- Lista de alertas
  ├── activity-feed.tsx            <- Feed de atividades
  └── export-menu.tsx              <- Menu de exportacao
```

---

## Epicos da Sprint

### Fase 1: Estrutura Base (E01-E02)

| Epico | Titulo | Complexidade | Dependencias |
|-------|--------|--------------|--------------|
| E01 | Layout Base e Grid | Baixa | - |
| E02 | Header com Status e Controles | Baixa | E01 |

### Fase 2: Cards de Metricas (E03-E05)

| Epico | Titulo | Complexidade | Dependencias |
|-------|--------|--------------|--------------|
| E03 | Cards de Metricas vs Meta | Media | E01 |
| E04 | Cards de Qualidade Persona | Media | E03 |
| E05 | Status Operacional e Instancias | Media | E03 |

### Fase 3: Pool de Chips (E06-E07)

| Epico | Titulo | Complexidade | Dependencias |
|-------|--------|--------------|--------------|
| E06 | Pool de Chips - Visao Geral | Media | E01 |
| E07 | Pool de Chips - Lista Detalhada | Media | E06 |

### Fase 4: APIs Backend (E08-E09)

| Epico | Titulo | Complexidade | Dependencias |
|-------|--------|--------------|--------------|
| E08 | APIs de Metricas Gerais | Media | - |
| E09 | APIs de Chips | Media | E08 |

### Fase 5: Funil de Conversao (E10-E11)

| Epico | Titulo | Complexidade | Dependencias |
|-------|--------|--------------|--------------|
| E10 | Funil de Conversao Visual | Media | E08 |
| E11 | Modal Drill-Down do Funil | Alta | E10 |

### Fase 6: Graficos e Tendencias (E12)

| Epico | Titulo | Complexidade | Dependencias |
|-------|--------|--------------|--------------|
| E12 | Graficos Sparkline | Media | E08 |

### Fase 7: Alertas e Feed (E13-E14)

| Epico | Titulo | Complexidade | Dependencias |
|-------|--------|--------------|--------------|
| E13 | Sistema de Alertas | Media | E08, E09 |
| E14 | Activity Feed | Media | E08 |

### Fase 8: Comparativos e Exportacao (E15-E17)

| Epico | Titulo | Complexidade | Dependencias |
|-------|--------|--------------|--------------|
| E15 | Comparativos vs Semana Anterior | Media | E08 |
| E16 | Exportacao CSV | Media | E08 |
| E17 | Exportacao PDF | Media | E16 |

---

## Definition of Done (DoD) Global

Todos os epicos devem atender:

- [ ] Codigo escrito em TypeScript strict (sem `any`)
- [ ] Componentes React funcionais com hooks
- [ ] Responsivo desktop-first (min-width: 1024px)
- [ ] Tratamento de loading states
- [ ] Tratamento de error states
- [ ] Testes unitarios para logica de negocio
- [ ] Codigo revisado (code review)
- [ ] Build sem erros (`npm run build`)
- [ ] Lint sem erros (`npm run lint`)
- [ ] Documentacao inline quando necessario

---

## Stack Tecnica

| Tecnologia | Uso |
|------------|-----|
| Next.js 14 | App Router, Server Components |
| TypeScript | Strict mode |
| Tailwind CSS | Estilizacao |
| shadcn/ui | Componentes base |
| Recharts | Graficos (sparklines) |
| date-fns | Formatacao de datas |
| Supabase | Banco de dados |

---

## Dados de Teste

Para desenvolvimento, usar o ambiente DEV do Supabase:
- Project: `ofpnronthwcsybfxnxgj`
- URL: `https://ofpnronthwcsybfxnxgj.supabase.co`

Se precisar de dados mock, criar em `/lib/mock/dashboard-data.ts`.

---

## Checklist de Entrega da Sprint

- [ ] E01 - Layout Base e Grid
- [ ] E02 - Header com Status e Controles
- [ ] E03 - Cards de Metricas vs Meta
- [ ] E04 - Cards de Qualidade Persona
- [ ] E05 - Status Operacional e Instancias
- [ ] E06 - Pool de Chips - Visao Geral
- [ ] E07 - Pool de Chips - Lista Detalhada
- [ ] E08 - APIs de Metricas Gerais
- [ ] E09 - APIs de Chips
- [ ] E10 - Funil de Conversao Visual
- [ ] E11 - Modal Drill-Down do Funil
- [ ] E12 - Graficos Sparkline
- [ ] E13 - Sistema de Alertas
- [ ] E14 - Activity Feed
- [ ] E15 - Comparativos vs Semana Anterior
- [ ] E16 - Exportacao CSV
- [ ] E17 - Exportacao PDF

---

## Referencias

- Especificacao original: Sprint 28 E05
- Persona Julia: `CLAUDE.md`
- Convencoes: `app/CONVENTIONS.md`
- Regras Next.js: `docs/best-practices/nextjs-typescript-rules.md`
