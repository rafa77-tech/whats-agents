# NFR Assessment - Agente Júlia

**Data:** 2026-02-09
**Tipo:** Requisitos Não-Funcionais (Segurança, Performance, Reliability, Maintainability)
**Status:** Completo

---

## Resumo Executivo

| Categoria | Score (1-5) | Status |
|-----------|-------------|--------|
| Segurança | 4 | ✅ |
| Performance | 4 | ✅ |
| Reliability | 5 | ✅ |
| Maintainability | 4 | ⚠️ |
| **Geral** | **4.25** | ✅ |

O projeto demonstra maturidade arquitetural excepcional para um sistema de produção. Os pontos identificados são melhorias incrementais, não bloqueadores.

---

## Oportunidades de Melhoria

### 1. 🔴 CRÍTICO: Índices em Foreign Keys

**Problema:** PostgreSQL não cria índices automaticamente em FKs. Encontradas 39 FKs sem índice.

**Impacto:**
- JOINs lentos
- DELETE cascading lento
- Locks prolongados em tabelas pai

**FKs prioritárias:**

| Tabela | FK Column | Referencia | Impacto |
|--------|-----------|------------|---------|
| `business_events` | `conversation_id` | conversations | 🔴 Alto |
| `business_events` | `interaction_id` | interacoes | 🔴 Alto |
| `interacoes` | `parent_id` | interacoes | 🔴 Alto |
| `fila_mensagens` | `conversa_id` | conversations | 🔴 Alto |
| `vagas` | `cliente_id` | clientes | 🟡 Médio |
| `vagas` | `setor_id`, `periodo_id`, `tipos_vaga_id` | lookup | 🟡 Médio |
| `conversations` | `campanha_id` | campanhas | 🟡 Médio |
| `policy_events` | `conversation_id`, `interaction_id` | - | 🟡 Médio |
| `contatos_grupo` | `cliente_id` | clientes | 🟡 Médio |
| `vagas_grupo` | múltiplas FKs | - | 🟡 Médio |

**Todas as 39 FKs sem índice:**

```
business_events.interaction_id → interacoes
business_events.conversation_id → conversations
conhecimento_hospitais.pedido_ajuda_id → pedidos_ajuda
contatos_grupo.cliente_id → clientes
conversation_chips.migrated_from → chips
conversation_insights.interaction_id → interacoes
conversations.execucao_campanha_id → execucoes_campanhas
conversations.campanha_id → campanhas
diretrizes.vaga_id → vagas
diretrizes_contextuais.especialidade_id → especialidades
diretrizes_contextuais.hospital_id → hospitais
doctor_context.memoria_substituta_id → doctor_context
feedbacks_gestor.conversa_id → conversations
feedbacks_gestor.interacao_id → interacoes
fila_mensagens.conversa_id → conversations
group_entry_queue.link_id → group_links
group_links.chip_id → chips
grupos_whatsapp.hospital_id → hospitais
interacoes.parent_id → interacoes
mensagens_fora_horario.conversa_id → conversations
migracao_agendada.chip_novo_id → chips
migracao_agendada.chip_antigo_id → chips
orchestrator_operations.chip_destino_id → chips
policy_events.conversation_id → conversations
policy_events.interaction_id → interacoes
prompts_historico.prompt_id → prompts
sugestoes_prompt.avaliacao_id → avaliacoes_qualidade
vagas.tipos_vaga_id → tipos_vaga
vagas.periodo_id → periodos
vagas.setor_id → setores
vagas.forma_recebimento_id → formas_recebimento
vagas.cliente_id → clientes
vagas_grupo.contato_responsavel_id → contatos_grupo
vagas_grupo.setor_id → setores
vagas_grupo.duplicada_de → vagas_grupo
vagas_grupo.forma_recebimento_id → formas_recebimento
vagas_grupo.vaga_importada_id → vagas
vagas_grupo.tipos_vaga_id → tipos_vaga
vagas_grupo_fontes.contato_id → contatos_grupo
```

**Migration sugerida (alta prioridade):**

```sql
-- Índices para FKs de alto impacto
CREATE INDEX CONCURRENTLY idx_business_events_conversation_id
    ON business_events(conversation_id);
CREATE INDEX CONCURRENTLY idx_business_events_interaction_id
    ON business_events(interaction_id);
CREATE INDEX CONCURRENTLY idx_interacoes_parent_id
    ON interacoes(parent_id);
CREATE INDEX CONCURRENTLY idx_fila_mensagens_conversa_id
    ON fila_mensagens(conversa_id);
CREATE INDEX CONCURRENTLY idx_vagas_cliente_id
    ON vagas(cliente_id);
CREATE INDEX CONCURRENTLY idx_policy_events_conversation_id
    ON policy_events(conversation_id);
CREATE INDEX CONCURRENTLY idx_policy_events_interaction_id
    ON policy_events(interaction_id);
CREATE INDEX CONCURRENTLY idx_conversations_campanha_id
    ON conversations(campanha_id);
CREATE INDEX CONCURRENTLY idx_contatos_grupo_cliente_id
    ON contatos_grupo(cliente_id);
```

**Esforço:** Baixo (1-2h) | **Impacto:** Alto | **Prioridade:** P0

---

### 2. 🔴 CRÍTICO: Monitoramento e Alertas

**Problema:** Sistema de monitoramento planejado (Epic 12.4) mas não implementado.

**Status atual:**
- Prometheus: 🔴 Não configurado
- Grafana: 🔴 Não configurado
- Alertmanager: 🔴 Não configurado
- Alertas Slack: 🔴 Não configurado

**Documentação existente:** `planning/sprint-12/epic-04-monitoramento.md`

**O que está planejado:**
- Prometheus + Node Exporter para coleta de métricas
- cAdvisor para métricas de containers
- Grafana com dashboards customizados
- Alertmanager com notificações Slack

**Alertas planejados:**
- ContainerDown (container não responde)
- HighCpuUsage (CPU > 80% por 5min)
- HighMemoryUsage (Memória > 85% por 5min)
- DiskSpaceLow (Disco > 85%)
- JuliaApiDown (API não responde)
- JuliaApiHighLatency (p95 > 5s)
- ContainerRestarting (> 3 restarts/hora)

**Esforço:** ~2.5h | **Impacto:** Alto | **Prioridade:** P0

---

### 3. 🟡 IMPORTANTE: Potenciais N+1 Queries

**Problema:** 81 arquivos com padrão `for ... await supabase` que podem causar N+1 queries.

**Arquivos prioritários:**

| Arquivo | Loops | Criticidade |
|---------|-------|-------------|
| `campanhas/executor.py` | 1 | 🔴 Alta |
| `warmer/pairing_engine.py` | 9 | 🔴 Alta |
| `chips/health_monitor.py` | 6 | 🟡 Média |
| `briefing_analyzer.py` | 14 | 🟡 Média |
| `warmer/scheduler.py` | 9 | 🟡 Média |
| `grupos/extrator_v2/extrator_valores.py` | 8 | 🟡 Média |
| `grupos/extrator_v2/extrator_hospitais.py` | 7 | 🟡 Média |
| `business_events/metrics.py` | 7 | 🟡 Média |
| `feedback.py` | 7 | 🟡 Média |

**Exemplo crítico (`campanhas/executor.py:93-99`):**

```python
# ❌ Atual (N+1)
for dest in destinatarios:
    try:
        sucesso = await self._criar_envio(campanha, dest)
        if sucesso:
            enviados += 1
```

**Padrão recomendado:**

```python
# ✅ Recomendado (batch)
envios = [preparar_envio(campanha, dest) for dest in destinatarios]
await supabase.table("envios").insert(envios).execute()
```

**Esforço:** Médio-Alto | **Impacto:** Alto | **Prioridade:** P1

---

### 4. 🟢 MENOR: Índices Não Utilizados

**Problema:** 20 índices com 0 scans identificados.

**Candidatos a remoção (~12MB):**

| Tabela | Índice | Tamanho | Recomendação |
|--------|--------|---------|--------------|
| `clientes` | `idx_clientes_email` | 1.4 MB | ⚠️ Verificar |
| `clientes` | `idx_clientes_crm` | 264 KB | ⚠️ Verificar |
| `clientes` | `idx_clientes_estado` | 272 KB | 🔴 Remover |
| `clientes` | `idx_clientes_opted_out` | 256 KB | ⚠️ Verificar |
| `clientes` | `idx_clientes_ultima_abertura` | 360 KB | 🔴 Remover |
| `mensagens_grupo` | `idx_mensagens_grupo_timestamp` | 1.3 MB | ⚠️ Verificar |
| `mensagens_grupo` | `idx_mensagens_grupo_ofertas` | 840 KB | ⚠️ Verificar |
| `vagas_grupo` | `idx_vagas_grupo_hospital` | 1.4 MB | ⚠️ Verificar |
| `mensagens_grupo` | `mensagens_grupo_message_id_key` | 2.1 MB | ⚠️ UNIQUE |
| `vagas_grupo_fontes` | `vagas_grupo_fontes_pkey` | 1.5 MB | ❌ PK |

**Nota:** Antes de remover, verificar com `EXPLAIN ANALYZE` em queries do código.

**Esforço:** Médio | **Impacto:** Baixo | **Prioridade:** P2

---

### 5. 🟢 MENOR: Tabelas Sem RLS

**Status:** 7 tabelas sem RLS, mas todas são de baixo risco.

| Tabela | Classificação | Status |
|--------|---------------|--------|
| `campanhas_deprecated` | Deprecated | ✅ OK (dropar) |
| `chip_daily_snapshots` | Métricas | ✅ OK |
| `circuit_transitions` | Logs internos | ✅ OK |
| `fila_mensagens_dlq` | Operacional | ⚠️ Avaliar |
| `helena_sessoes` | Sessões Slack | ✅ OK |
| `market_intelligence_daily` | Analytics | ✅ OK |
| `warmup_schedule` | Config | ✅ OK |

**Tabelas sensíveis com RLS ativado (confirmado):**
- ✅ `clientes`
- ✅ `doctor_context`
- ✅ `doctor_state`
- ✅ `contatos_grupo`
- ✅ `dashboard_users`
- ✅ `conversations`
- ✅ `interacoes`
- ✅ `medico_chip_affinity`

**Esforço:** Baixo | **Impacto:** Baixo | **Prioridade:** P2

---

### 6. 🟢 MENOR: Manutenção do Banco

**Tabelas sem VACUUM/ANALYZE recente:**

| Tabela | Rows | Dead Rows | Tamanho | Ação |
|--------|------|-----------|---------|------|
| `job_executions` | 222k | 14k | 53 MB | VACUUM |
| `mensagens_grupo` | 30k | 6k | 35 MB | VACUUM |
| `vagas_grupo` | 64k | 3k | 35 MB | VACUUM |
| `clientes_log` | 30k | 3 | 43 MB | OK |

**Comandos:**

```sql
-- Verificar configuração de autovacuum
SHOW autovacuum;

-- Forçar ANALYZE para atualizar estatísticas
ANALYZE job_executions;
ANALYZE mensagens_grupo;
ANALYZE vagas_grupo;
```

**Esforço:** Baixo | **Impacto:** Baixo | **Prioridade:** P2

---

### 7. 🟢 MENOR: Documentação de Secrets Rotation

**Problema:** Processo de rotação de secrets não documentado.

**Recomendação:** Adicionar ao runbook:

```markdown
## Rotação de Secrets

### API Keys para rotacionar periodicamente
| Secret | Frequência | Provider |
|--------|------------|----------|
| ANTHROPIC_API_KEY | 90 dias | console.anthropic.com |
| EVOLUTION_API_KEY | 90 dias | Evolution self-hosted |
| SUPABASE_SERVICE_KEY | 90 dias | supabase.com |
| SLACK_BOT_TOKEN | Quando comprometido | api.slack.com |
| VOYAGE_API_KEY | 90 dias | voyage.ai |

### Processo de Rotação
1. Gerar nova key no provider
2. Atualizar em Railway (variáveis de ambiente)
3. Deploy automático acontece
4. Testar endpoint de saúde: `GET /health`
5. Verificar logs por erros de autenticação
6. Revogar key antiga após 24h de funcionamento
```

**Esforço:** Baixo | **Impacto:** Baixo | **Prioridade:** P3

---

## Plano de Ação

| # | Item | Esforço | Impacto | Prioridade | Sprint |
|---|------|---------|---------|------------|--------|
| 1 | Criar índices em FKs críticas | Baixo | Alto | P0 | Próxima |
| 2 | Implementar monitoramento (Epic 12.4) | Médio | Alto | P0 | Próxima |
| 3 | Refatorar N+1 em campanhas/executor | Médio | Alto | P1 | Backlog |
| 4 | Refatorar N+1 em warmer/pairing_engine | Médio | Alto | P1 | Backlog |
| 5 | Revisar índices não utilizados | Médio | Baixo | P2 | Backlog |
| 6 | VACUUM/ANALYZE em tabelas grandes | Baixo | Baixo | P2 | Backlog |
| 7 | Documentar secrets rotation | Baixo | Baixo | P3 | Backlog |
| 8 | Dropar `campanhas_deprecated` | Baixo | Baixo | P3 | Backlog |
| 9 | Avaliar RLS em `fila_mensagens_dlq` | Baixo | Baixo | P3 | Backlog |

---

## Destaques Positivos

O projeto apresenta excelentes práticas em:

1. **Reliability** - Circuit breaker distribuído, fallbacks, dedup atômica
2. **Pipeline modular** - Extensibilidade sem afetar core
3. **Guards DEV/PROD** - Previne erros catastróficos
4. **Logging estruturado** - Trace IDs habilitam debugging efetivo
5. **Cobertura de testes** - ~2550 testes
6. **RLS em tabelas sensíveis** - PII protegido
7. **Rate limiting robusto** - Redis + Supabase fallback, FAIL-CLOSED

---

## Queries de Diagnóstico

### Verificar FKs sem índice

```sql
SELECT
    tc.table_name,
    kcu.column_name as fk_column,
    ccu.table_name AS referenced_table
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu
    ON ccu.constraint_name = tc.constraint_name
LEFT JOIN pg_indexes i
    ON i.tablename = tc.table_name
    AND i.indexdef LIKE '%' || kcu.column_name || '%'
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema = 'public'
    AND i.indexname IS NULL
ORDER BY tc.table_name;
```

### Verificar índices não utilizados

```sql
SELECT
    relname as table_name,
    indexrelname as index_name,
    idx_scan as times_used,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Verificar tabelas sem RLS

```sql
SELECT tablename, rowsecurity as rls_enabled
FROM pg_tables
WHERE schemaname = 'public' AND NOT rowsecurity;
```

### Verificar tabelas que precisam VACUUM

```sql
SELECT
    relname as table_name,
    n_live_tup as rows,
    n_dead_tup as dead_rows,
    last_vacuum,
    last_analyze
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;
```

---

*Documento gerado automaticamente via test-architect skill*
