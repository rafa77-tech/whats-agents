# Row Level Security - Políticas de Acesso

**Última atualização:** 2026-02-09 (Sprint 57)

## Visão Geral

O sistema usa Row Level Security (RLS) para controlar acesso aos dados no PostgreSQL.
Todas as tabelas com dados sensíveis têm RLS habilitado.

## Roles

| Role | Uso | Acesso Típico |
|------|-----|---------------|
| `anon` | Clientes não autenticados | Sem acesso (bloqueado) |
| `authenticated` | Dashboard autenticado | SELECT em tabelas de leitura |
| `service_role` | Backend Python | Full access |

## Padrões de Policy

### Tabelas Backend-Only

```sql
-- Apenas service_role tem acesso
CREATE POLICY "table_service_role_all"
ON table_name FOR ALL TO service_role
USING (true) WITH CHECK (true);

CREATE POLICY "table_deny_anon"
ON table_name FOR ALL TO anon
USING (false);
```

### Tabelas Dashboard Read

```sql
-- Service role full + authenticated read
CREATE POLICY "table_service_role_all"
ON table_name FOR ALL TO service_role
USING (true) WITH CHECK (true);

CREATE POLICY "table_authenticated_read"
ON table_name FOR SELECT TO authenticated
USING (true);
```

## Inventário de Policies

### Tabelas com PII (Dados Pessoais)

| Tabela | anon | authenticated | service_role | Notas |
|--------|------|---------------|--------------|-------|
| clientes | ❌ | SELECT | ALL | Dados de médicos |
| doctor_context | ❌ | SELECT | ALL | Memórias |
| doctor_state | ❌ | SELECT | ALL | Estado do médico |
| contatos_grupo | ❌ | ❌ | ALL | Telefones |
| clientes_log | ❌ | ❌ | ALL | Histórico |

### Tabelas Operacionais

| Tabela | anon | authenticated | service_role |
|--------|------|---------------|--------------|
| chips | SELECT | SELECT | ALL |
| vagas | ❌ | SELECT | ALL |
| conversations | ❌ | SELECT+INSERT+UPDATE | ALL |
| campanhas | ❌ | SELECT+INSERT+UPDATE | ALL |
| helena_sessoes | ❌ | ❌ | ALL |
| circuit_transitions | ❌ | ❌ | ALL |
| warmup_schedule | ❌ | ❌ | ALL |
| chip_daily_snapshots | ❌ | SELECT | ALL |
| fila_mensagens_dlq | ❌ | ❌ | ALL |
| market_intelligence_daily | ❌ | SELECT | ALL |

### Tabelas de Configuração

| Tabela | anon | authenticated | service_role |
|--------|------|---------------|--------------|
| app_settings | ❌ | ❌ | ALL |
| feature_flags | ❌ | ❌ | ALL |
| prompts | ❌ | ❌ | ALL |

## Views com SECURITY DEFINER

As seguintes views usam SECURITY DEFINER intencionalmente para agregar dados do dashboard:

| View | Propósito | Documentado em |
|------|-----------|----------------|
| chips_needing_attention | Dashboard - chips que precisam atenção | Sprint 57 |
| chips_ready_for_production | Dashboard - chips prontos | Sprint 57 |
| pool_status | Dashboard - status do pool | Sprint 57 |

## Auditoria Periódica

Executar mensalmente:

```sql
-- Tabelas sem RLS
SELECT tablename FROM pg_tables
WHERE schemaname = 'public' AND NOT rowsecurity;

-- Tabelas com RLS mas sem policies
SELECT t.tablename
FROM pg_tables t
LEFT JOIN pg_policies p ON t.tablename = p.tablename
WHERE t.schemaname = 'public' AND t.rowsecurity = true
GROUP BY t.tablename
HAVING count(p.policyname) = 0;
```

## Histórico de Correções

| Data | Ação | Tabelas Afetadas |
|------|------|------------------|
| 2026-02-09 | Habilitado RLS | helena_sessoes, circuit_transitions, warmup_schedule, chip_daily_snapshots, fila_mensagens_dlq, market_intelligence_daily |
| 2026-02-09 | Removida (obsoleta) | campanhas_deprecated |

---

**Próxima auditoria:** 2026-05-09
