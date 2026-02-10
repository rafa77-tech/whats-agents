# Functions com SECURITY DEFINER

**Última atualização:** 2026-02-09 (Sprint 57)

## O que é SECURITY DEFINER?

Functions com SECURITY DEFINER executam com os privilégios do usuário que **CRIOU** a function (geralmente postgres/supabase_admin), não do usuário que **EXECUTA**.

## Quando usar?

- Function precisa acessar dados que o caller não tem permissão
- Function precisa bypassar RLS intencionalmente
- Function é chamada apenas pelo backend (service_role)

## Riscos

1. **SQL Injection**: Se a function aceita input dinâmico
2. **Search Path**: Atacante pode criar objetos maliciosos em outro schema
3. **Privilege Escalation**: Caller ganha privilégios temporários

## Mitigações Obrigatórias

1. `SET search_path = public` em **TODA** function SECURITY DEFINER
2. Validar inputs antes de usar em SQL dinâmico
3. Usar `quote_ident()` e `quote_literal()` para interpolação
4. Limitar escopo ao mínimo necessário

## Inventário de Functions SECURITY DEFINER

### Críticas (SQL Dinâmico)

| Function | Propósito | Mitigações | Revisado |
|----------|-----------|------------|----------|
| `execute_readonly_query` | Helena SQL | search_path, SELECT only, block schemas, LIMIT | 2026-02-09 |

### Chips & Métricas

| Function | Propósito | Revisado |
|----------|-----------|----------|
| `chip_calcular_taxa_delivery` | Calcula taxa de delivery | 2026-02-09 |
| `chip_calcular_taxa_resposta` | Calcula taxa de resposta | 2026-02-09 |
| `chip_criar_snapshot_diario` | Snapshot diário | 2026-02-09 |
| `chip_criar_snapshots_todos` | Snapshots de todos os chips | 2026-02-09 |
| `chip_registrar_envio_erro` | Registra erro de envio | 2026-02-09 |
| `chip_registrar_envio_sucesso` | Registra envio OK | 2026-02-09 |
| `chip_registrar_resposta` | Registra resposta recebida | 2026-02-09 |
| `chip_resetar_contadores_diarios` | Reset diário | 2026-02-09 |
| `chip_resetar_erros_24h` | Recalcula erros 24h | 2026-02-09 |
| `chip_resetar_msgs_hoje` | Reset msgs hoje | 2026-02-09 |

### Auditoria & Reconciliação

| Function | Propósito | Revisado |
|----------|-----------|----------|
| `audit_outbound_coverage` | Cobertura outbound | 2026-02-09 |
| `audit_pipeline_inbound_coverage` | Cobertura inbound | 2026-02-09 |
| `audit_status_transition_coverage` | Cobertura transições | 2026-02-09 |
| `reconcile_all` | Reconciliação geral | 2026-02-09 |
| `reconcile_db_to_events` | DB → Events | 2026-02-09 |
| `reconcile_events_to_db` | Events → DB | 2026-02-09 |
| `buscar_candidatos_touch_reconciliation` | Touch reconciliation | 2026-02-09 |

### Dashboard & Métricas

| Function | Propósito | Revisado |
|----------|-----------|----------|
| `get_conversion_rates` | Taxas de conversão | 2026-02-09 |
| `get_fila_stats` | Stats da fila | 2026-02-09 |
| `get_funnel_invariant_violations` | Violações de funil | 2026-02-09 |
| `get_health_score_components` | Componentes health score | 2026-02-09 |
| `get_last_job_executions` | Últimas execuções jobs | 2026-02-09 |
| `get_table_columns_for_fingerprint` | Colunas para fingerprint | 2026-02-09 |
| `get_time_to_fill_breakdown` | Breakdown time-to-fill | 2026-02-09 |

### Operacionais

| Function | Propósito | Revisado |
|----------|-----------|----------|
| `incrementar_mensagens_contato` | Contador de msgs contato | 2026-02-09 |
| `incrementar_mensagens_grupo` | Contador de msgs grupo | 2026-02-09 |
| `interacao_atualizar_delivery_status` | Atualiza delivery status | 2026-02-09 |
| `limpar_circuit_transitions_antigas` | Cleanup circuit transitions | 2026-02-09 |
| `registrar_primeira_mensagem_grupo` | Primeira msg grupo | 2026-02-09 |
| `sync_cliente_to_bitrix` | Sync Bitrix | 2026-02-09 |

## Verificação

```sql
-- Functions SECURITY DEFINER sem search_path
SELECT proname
FROM pg_proc
WHERE pronamespace = 'public'::regnamespace
AND prosecdef = true
AND NOT (proconfig @> ARRAY['search_path=public']);
-- Deve retornar vazio
```

## Histórico de Correções

| Data | Ação | Functions Afetadas |
|------|------|-------------------|
| 2026-02-09 | Adicionado search_path | 14 functions (chip_*, get_fila_stats, etc.) |
| 2026-02-09 | Validações reforçadas | execute_readonly_query |

---

**Próxima auditoria:** 2026-05-09
