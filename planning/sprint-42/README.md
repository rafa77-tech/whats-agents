# Sprint 42 - Monitor Page e Warmup Rename

**Início:** A definir
**Duração estimada:** 3-4 dias
**Dependências:** Nenhuma (sprint independente)

---

## Objetivo

Criar a página **Monitor** no dashboard para visualização em tempo real dos 32 jobs do sistema e saúde geral, além de renomear `/chips/scheduler` para `/chips/warmup` com semântica mais clara.

### Por que agora?

1. **Observabilidade operacional**: Não há visibilidade no dashboard sobre execução dos jobs
2. **Debugging**: Quando algo falha, precisamos ir aos logs do Railway
3. **Semântica correta**: "Scheduler" é genérico; "Warmup" descreve a função real da página

### Benefícios

| Antes | Depois |
|-------|--------|
| Jobs só visíveis via logs Railway | Dashboard visual com status em tempo real |
| Sem alertas de jobs stale | Indicadores visuais de jobs atrasados |
| "Scheduler" genérico | "Warmup" específico para aquecimento |
| Sem histórico de execuções | Histórico com drill-down por job |

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                         Dashboard                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    /monitor                               │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐          │   │
│  │  │  System    │  │   Stats    │  │   Alerts   │          │   │
│  │  │  Health    │  │   Cards    │  │   Count    │          │   │
│  │  └────────────┘  └────────────┘  └────────────┘          │   │
│  │                                                           │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │              Jobs Table (32 jobs)                   │  │   │
│  │  │  - Status (running/success/error/timeout)          │  │   │
│  │  │  - Last Run / Next Expected                        │  │   │
│  │  │  - Duration / Success Rate                         │  │   │
│  │  │  - Click to expand execution history               │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  /chips/warmup (renomeado)                │   │
│  │             Atividades de warmup dos chips                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

        │                    │
        ▼                    ▼
┌───────────────┐    ┌───────────────┐
│  API Routes   │    │   Supabase    │
│  /api/monitor │───►│ job_executions│
└───────────────┘    └───────────────┘
```

---

## Dados Disponíveis

### Tabela `job_executions` (já existe)

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | UUID | Identificador único |
| job_name | TEXT | Nome do job (heartbeat, processar_mensagens_agendadas, etc.) |
| started_at | TIMESTAMPTZ | Início da execução |
| finished_at | TIMESTAMPTZ | Fim da execução (null se running) |
| status | TEXT | running, success, error, timeout |
| duration_ms | INTEGER | Duração em milissegundos |
| response_code | INTEGER | Código HTTP (opcional) |
| error | TEXT | Mensagem de erro (truncada 500 chars) |
| items_processed | INTEGER | Itens processados (opcional) |

### Jobs do Sistema (32 total)

| Categoria | Jobs | Schedule | SLA |
|-----------|------|----------|-----|
| **Critical** | heartbeat, processar_mensagens_agendadas, processar_campanhas_agendadas, processar_grupos | * * * * * | 3 min |
| **Frequent** | verificar_whatsapp, sincronizar_chips, validar_telefones, atualizar_trust_scores, verificar_alertas, processar_handoffs | */5-15 min | 15-45 min |
| **Hourly** | sincronizar_briefing, processar_confirmacao_plantao, oferta_autonoma | 0 * * * * | 2h |
| **Daily** | processar_followups, processar_pausas_expiradas, report_manha, report_fim_dia, discovery_autonomo, feedback_autonomo, etc. | Vários | 25h |
| **Weekly** | report_semanal, atualizar_prompt_feedback, reativacao_autonoma, doctor_state_manutencao_semanal | Semanal | 8d |

### Endpoint Existente: `/health/jobs`

O backend já tem endpoint que retorna dados agregados dos jobs. Será adaptado para uso pelo dashboard.

---

## Decisões Técnicas

### 1. Estrutura de Componentes

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Client/Server | Client Component | Precisa de refresh, filtros, modais |
| Fetching | useCallback + useEffect | Padrão do dashboard existente |
| Auto-refresh | 30 segundos | Balance entre atualização e requests |
| Paginação jobs | Não | São apenas 32 jobs, cabe em uma tela |
| Paginação executions | Sim (20 por página) | Histórico pode ser extenso |

### 2. Organização de Arquivos

```
dashboard/
├── app/(dashboard)/monitor/page.tsx
├── app/api/dashboard/monitor/
│   ├── route.ts              # Overview + stats
│   ├── jobs/route.ts         # Lista de jobs
│   └── job/[name]/executions/route.ts
├── components/monitor/
│   ├── monitor-page-content.tsx
│   ├── system-health-card.tsx
│   ├── jobs-stats-cards.tsx
│   ├── jobs-table.tsx
│   ├── job-detail-modal.tsx
│   └── jobs-filters.tsx
└── types/monitor.ts
```

### 3. Rename Warmup

Renomear arquivos e atualizar referências:
- `/chips/scheduler` → `/chips/warmup`
- Componentes e APIs correspondentes
- Links de navegação

---

## Épicos

| # | Épico | Descrição | Estimativa |
|---|-------|-----------|------------|
| E01 | Rename Scheduler → Warmup | Renomear rotas, componentes, APIs | 1h |
| E02 | Types Monitor | Definir tipos TypeScript | 0.5h |
| E03 | API Routes Monitor | 3 endpoints (/monitor, /jobs, /executions) | 2h |
| E04 | Components Monitor | 6 componentes React | 4h |
| E05 | Page Monitor | Página principal com layout | 1h |
| E06 | Sidebar Navigation | Adicionar entrada "Monitor" | 0.5h |
| E07 | Tests & Validation | Testes E2E, build, verificação | 1h |

**Total estimado:** ~10 horas (1-2 dias de trabalho)

---

## Fluxo de Dados

### Carregamento Inicial

```
1. Usuário acessa /monitor
2. Page carrega → MonitorPageContent renderiza
3. useEffect dispara fetchOverview() e fetchJobs() em paralelo
4. APIs consultam job_executions (últimas 24h)
5. Componentes renderizam com dados
6. setInterval(30s) inicia auto-refresh
```

### Drill-down de Job

```
1. Usuário clica em um job na tabela
2. Modal abre com jobName selecionado
3. API /monitor/job/[name]/executions é chamada
4. Histórico paginado é exibido
5. Usuário pode navegar páginas
```

### Filtros

```
1. Usuário muda filtro (status, timeRange, search)
2. Estado filters é atualizado
3. useEffect detecta mudança em filters
4. fetchJobs() é chamado com novos params
5. Tabela atualiza com dados filtrados
```

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| job_executions não existe | Baixa | Alto | Verificar com MCP antes de implementar |
| Muitos registros (performance) | Média | Médio | Limitar a 24h, índices corretos |
| Conflito de nomes no rename | Baixa | Baixo | Grep completo antes de renomear |
| Auto-refresh sobrecarrega API | Baixa | Baixo | 30s é conservador |

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Build sem erros | 100% |
| Testes E2E passando | 100% |
| Página /monitor carregando | < 2s |
| Auto-refresh funcionando | 30s |
| Jobs visíveis | 32/32 |
| Histórico acessível | Via modal |

---

## Checklist Final

### Pré-requisitos
- [ ] Tabela job_executions existe e tem dados
- [ ] Endpoint /health/jobs funciona

### Entregas
- [ ] E01 - /chips/warmup funcionando
- [ ] E02 - types/monitor.ts criado
- [ ] E03 - 3 APIs implementadas
- [ ] E04 - 6 componentes criados
- [ ] E05 - Página /monitor funcionando
- [ ] E06 - Sidebar atualizado
- [ ] E07 - Testes passando, build OK

### Validação
- [ ] Navegação /monitor funciona
- [ ] /chips/scheduler redireciona ou 404
- [ ] /chips/warmup funciona
- [ ] Jobs aparecem com status correto
- [ ] Drill-down mostra histórico
- [ ] Auto-refresh atualiza dados
- [ ] Mobile responsivo
