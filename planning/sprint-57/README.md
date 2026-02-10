# Sprint 57: Database Security & Performance

## Objetivo

Corrigir vulnerabilidades críticas de segurança no banco de dados, otimizar performance com índices faltantes, e estabelecer padrões de governança para futuras mudanças no schema.

**Origem:** Database Review profundo realizado em 2026-02-09 (ver `docs/auditorias/db-review-2026-02-09.md`)

---

## Épicos

| # | Épico | Prioridade | Estimativa | Risco |
|---|-------|------------|------------|-------|
| 1 | [Segurança RLS Crítica](epic-01-rls-critico.md) | P0 | 4h | Alto |
| 2 | [Functions & Search Path](epic-02-functions-security.md) | P0 | 3h | Alto |
| 3 | [Índices em Foreign Keys](epic-03-indices-fk.md) | P1 | 2h | Médio |
| 4 | [Limpeza de Índices](epic-04-indices-cleanup.md) | P2 | 2h | Baixo |
| 5 | [Cleanup & Governança](epic-05-cleanup-governanca.md) | P2 | 2h | Baixo |

**Total estimado:** 13 horas

---

## Critérios de Sucesso

- [ ] Zero tabelas públicas sem RLS habilitado
- [ ] Zero policies com `USING (true)` em tabelas com PII
- [ ] 100% das FKs em tabelas >10k rows com índice
- [ ] Todas as functions SECURITY DEFINER com search_path fixo
- [ ] Supabase Advisor: zero findings críticos (ERROR)
- [ ] Documentação de políticas de acesso atualizada

---

## Riscos

| Risco | Impacto | Probabilidade | Mitigação |
|-------|---------|---------------|-----------|
| Migrations quebram aplicação | Alto | Média | Testar em branch Supabase antes de prod |
| Índices novos causam locks | Médio | Baixa | Usar CREATE INDEX CONCURRENTLY |
| Policies restritivas demais bloqueiam funcionalidades | Alto | Média | Testar fluxos críticos após cada policy |
| Remover índice que é usado em reports | Médio | Média | Análise de 30 dias + backup do DDL |

---

## Dependências

| Épico | Depende de | Status |
|-------|-----------|--------|
| Épico 2 | - | Independente |
| Épico 1 | - | Independente |
| Épico 3 | - | Independente |
| Épico 4 | Épico 3 (validar antes de remover) | Sequencial |
| Épico 5 | Épicos 1-4 | Após validação |

---

## Ordem de Execução Recomendada

```
Dia 1 (Crítico):
├── Épico 1: RLS Crítico (4h)
│   ├── Habilitar RLS em 7 tabelas
│   ├── Criar policies service_role
│   └── Testar fluxos
│
└── Épico 2: Functions Security (3h)
    ├── Corrigir execute_readonly_query
    ├── Adicionar search_path em 37 functions
    └── Testar functions

Dia 2 (Performance):
├── Épico 3: Índices FK (2h)
│   ├── Criar 31 índices CONCURRENTLY
│   └── Validar performance
│
└── Épico 4: Cleanup Índices (2h)
    ├── Analisar usage últimos 30 dias
    ├── Backup DDL
    └── Remover candidatos seguros

Dia 3 (Governança):
└── Épico 5: Cleanup & Docs (2h)
    ├── Remover campanhas_deprecated
    ├── Documentar policies
    └── Criar checklist para futuras tabelas
```

---

## Métricas de Acompanhamento

### Antes da Sprint (Baseline)
- Tabelas sem RLS: **7**
- FKs sem índice: **31**
- Índices não utilizados: **30** (~15 MB)
- Functions sem search_path: **37**
- Supabase Advisor ERRORs: **10**
- Supabase Advisor WARNs: **80+**

### Depois da Sprint (Target)
- Tabelas sem RLS: **0**
- FKs sem índice: **0** (em tabelas >1k rows)
- Índices não utilizados: **<10** (após análise)
- Functions sem search_path: **0**
- Supabase Advisor ERRORs: **0**
- Supabase Advisor WARNs: **<30**

---

## Checklist de Validação Final

- [ ] `mcp__supabase__get_advisors(type='security')` sem ERRORs
- [ ] `mcp__supabase__get_advisors(type='performance')` revisado
- [ ] Queries de auditoria confirmam FKs indexadas
- [ ] Fluxos críticos testados manualmente:
  - [ ] Login/auth no dashboard
  - [ ] Webhook de mensagem recebida
  - [ ] Criação de conversa
  - [ ] Busca de vagas
  - [ ] Helena analytics query
- [ ] Documentação atualizada em `docs/arquitetura/banco-de-dados.md`

---

## Rollback Plan

Cada migration deve ter script de rollback. Em caso de problema:

1. **Identificar migration problemática** via logs
2. **Executar rollback específico** (cada épico tem seu rollback)
3. **Notificar equipe** no Slack #ops
4. **Documentar** o que aconteceu para próxima tentativa

---

## Referências

- [Database Review 2026-02-09](../../docs/auditorias/db-review-2026-02-09.md)
- [Supabase RLS Docs](https://supabase.com/docs/guides/auth/row-level-security)
- [PostgreSQL Index Best Practices](https://www.postgresql.org/docs/current/indexes.html)
- [app/CONVENTIONS.md](../../app/CONVENTIONS.md) - Padrões de código
