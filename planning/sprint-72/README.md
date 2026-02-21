# Sprint 72 — DDD Fase 2: Application Services (Ampliacao)

## Status: Em Progresso

**Inicio:** 2026-02-21
**Base:** Relatorio DDD (`docs/auditorias/relatorio-ddd-2026-02-21.md`)
**Referencia:** Padrao estabelecido em `app/services/campanhas/repository.py` (Sprint 35)

## Objetivo

Ampliar a Fase 2 do roadmap DDD para todos os bounded contexts que ainda possuem SQL inline em rotas. O padrao ja foi validado em campanhas (repository + types + singleton). Esta sprint replica o mesmo padrao para os contextos restantes, eliminando acesso direto a `supabase.table(...)` nas rotas.

---

## Contexto

O relatorio DDD identificou 138 violacoes de acesso direto ao Supabase em 23 arquivos de rota. A Fase 2 consiste em:

1. Criar **Repository** por contexto (encapsula queries)
2. Criar **Types** quando necessario (modelos de dominio)
3. Mover SQL das rotas para os repositories
4. Rotas ficam magras: validacao + chamada ao service/repository + resposta

### Criterio de priorizacao

| Prioridade | Criterio | Contextos |
|------------|----------|-----------|
| P0 (Critical) | Sem repository, dominio critico | incidents, supervisor_channel |
| P1 (High) | Partial service, acesso misto | policy, group_entry, campanhas (residual) |
| P2 (Medium) | Dashboard/admin, alto volume | admin, chips_dashboard, dashboard_conversations |

**Escopo desta sprint:** P0 + P1 (contextos de dominio). P2 (dashboards) fica para sprint futura.

---

## Epicos

### Epic 72.1 — Incidents Repository

**Problema:** `incidents.py` tem 5 acessos diretos a `supabase.table("health_incidents")` sem nenhum repository. Toda logica de negocio (MTTR, uptime, resolucao) esta na rota.

**Solucao:** Criar `app/services/health/incidents_repository.py` com todas as operacoes.

| # | Tarefa | Arquivo | Status |
|---|--------|---------|--------|
| T1 | Criar `IncidentsRepository` com CRUD completo | `app/services/health/incidents_repository.py` | ✅ |
| T2 | Refatorar `incidents.py` para usar repository | `app/api/routes/incidents.py` | ✅ |
| T3 | Testes do repository | `tests/services/health/test_incidents_repository.py` | ✅ |

**Metodos do repository:**
- `registrar(data) -> dict` — insert incidente
- `listar(limit, status, since) -> list` — listar com filtros
- `buscar_estatisticas(dias) -> list` — dados para calculo de metricas
- `buscar_incidente_ativo_critico() -> Optional[dict]` — buscar incidente critico nao resolvido
- `resolver(incident_id, resolved_at, duration_seconds) -> bool` — marcar como resolvido

---

### Epic 72.2 — Policy Events (Expor Repository Existente)

**Problema:** `policy.py:602` acessa `supabase.table("policy_events")` diretamente, mas ja existe `app/services/policy/events_repository.py`. O metodo necessario nao esta exposto ou nao existe.

**Solucao:** Adicionar metodo ao events_repository existente e usar na rota.

| # | Tarefa | Arquivo | Status |
|---|--------|---------|--------|
| T1 | Adicionar `listar_decisoes_por_cliente()` ao events_repository | `app/services/policy/events_repository.py` | ✅ |
| T2 | Refatorar rota debug para usar events_repository | `app/api/routes/policy.py` | ✅ |
| T3 | Teste do novo metodo | `tests/services/policy/test_events_repository_decisions.py` | ✅ |

---

### Epic 72.3 — Group Entry Repository

**Problema:** `group_entry.py` tem 4 acessos diretos: busca de link por ID, busca de invite_code, leitura de config, e atualizacao de config. Servicos parciais existem mas nao cobrem esses casos.

**Solucao:** Criar `app/services/group_entry/repository.py` para links e config.

| # | Tarefa | Arquivo | Status |
|---|--------|---------|--------|
| T1 | Criar `GroupEntryRepository` | `app/services/group_entry/repository.py` | ✅ |
| T2 | Refatorar `group_entry.py` para usar repository | `app/api/routes/group_entry.py` | ✅ |
| T3 | Testes do repository | `tests/services/group_entry/test_repository.py` | ✅ |

**Metodos do repository:**
- `buscar_link_por_id(link_id) -> Optional[dict]` — busca link completo
- `buscar_invite_code(link_id) -> Optional[str]` — busca apenas invite_code
- `buscar_config() -> Optional[dict]` — configuracao atual
- `atualizar_config(update_data) -> bool` — atualizar configuracao

---

### Epic 72.4 — Campanhas Repository (Metodos Residuais)

**Problema:** `campanhas.py` tem 2 acessos diretos residuais: listagem com filtros (linha 259) e stats de fila (linha 208). O repository existe mas nao tem esses metodos.

**Solucao:** Adicionar metodos ao `CampanhaRepository` existente.

| # | Tarefa | Arquivo | Status |
|---|--------|---------|--------|
| T1 | Adicionar `listar(status, tipo, limit)` e `buscar_stats_fila(campanha_id)` ao repository | `app/services/campanhas/repository.py` | ✅ |
| T2 | Refatorar rotas para usar novos metodos | `app/api/routes/campanhas.py` | ✅ |
| T3 | Testes dos novos metodos | `tests/services/campanhas/test_repository_list.py` | ✅ |

---

## Ordem de Execucao

```
Epic 72.1 (Incidents) ──→ Epic 72.2 (Policy Events) ──→ Epic 72.3 (Group Entry)
                                                              │
Epic 72.4 (Campanhas Residual) ────────────────────────── [paralelo com 72.3]
```

1. **Epic 72.1** primeiro — contexto mais isolado, bom para validar padrao
2. **Epic 72.2** menor escopo — apenas expor metodo em repository existente
3. **Epic 72.3** e **72.4** podem ser paralelos — contextos independentes

---

## Padrao de Implementacao (Referencia)

Baseado no padrao `campanhas/repository.py`:

```python
# 1. Repository com TABLE constante e singleton
class NomeRepository:
    TABLE = "nome_tabela"

    async def buscar_por_id(self, id: str) -> Optional[dict]:
        try:
            response = (
                supabase.table(self.TABLE)
                .select("*")
                .eq("id", id)
                .single()
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Erro ao buscar {id}: {e}")
            return None

# Singleton
nome_repository = NomeRepository()
```

```python
# 2. Rota magra
@router.get("/items/{item_id}")
async def buscar_item(item_id: str):
    result = await nome_repository.buscar_por_id(item_id)
    if not result:
        raise HTTPException(404, "Item nao encontrado")
    return result
```

---

## Criterios de Aceite

- [x] Zero acessos `supabase.table(...)` em `incidents.py`
- [x] Zero acessos `supabase.table(...)` em `policy.py` (debug endpoint)
- [x] Zero acessos `supabase.table(...)` em `group_entry.py`
- [x] Zero acessos `supabase.table("campanhas")` residuais em `campanhas.py`
- [x] Zero acessos `supabase.table("fila_mensagens")` em `campanhas.py`
- [x] Todos os repositories com testes unitarios
- [x] Testes existentes continuam passando (zero regressao)
- [x] Rotas usam apenas repository/service, nunca supabase direto

---

## Escopo Futuro (Sprint 73+)

Contextos P2 que ficam para proxima sprint:

| Contexto | Violacoes | Motivo do adiamento |
|----------|-----------|---------------------|
| `admin.py` | 11 | Multiplas tabelas, requer varios repositories |
| `chips_dashboard.py` | 17 | Alto volume, requer consolidacao no orchestrator |
| `dashboard_conversations.py` | 14 | Misto, requer conversation_operations_repository |
| `webhook_zapi.py` | 13 | Chip operations, requer chip_operation_repository |
| `webhook_router.py` | 10 | Idem webhook_zapi |
| `supervisor_channel.py` | 6 | Requer conversation_context_service |
