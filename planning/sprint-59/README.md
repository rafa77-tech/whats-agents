# Sprint 59 — Otimizacao de Performance

## Status: Planejada

**Inicio:** 13/02/2026

## Objetivo

Eliminar desperdicio de I/O serial e recursos em todo o codebase.
A aplicacao funciona corretamente, mas faz ~57 conexoes HTTP efemeras onde poderia reutilizar,
duplica chamadas LLM e DB no hot path, e executa jobs sequencialmente sem necessidade.

## Metodologia

**Performance Profiling** — 3 agentes analisaram em paralelo:
- Padroes de queries DB (N+1, duplicatas, unbounded SELECTs)
- Padroes async e caching (serial awaits, oportunidades de gather)
- Hot paths e endpoints pesados (webhook, fila worker, health, jobs)

**Principio:** Nao otimizar prematuramente. Focar no que e mensuravel e impactante.

## Diagnostico Consolidado

### Achados P0 — Hot Path (cada mensagem)

| # | Problema | Local | Impacto |
|---|----------|-------|---------|
| 1 | 57 `httpx.AsyncClient()` efemeros — singleton existe mas ninguem usa | 16 arquivos | 50-200ms/request (TCP+TLS) |
| 2 | `analisar_situacao` chamado 2x com inputs identicos | `orchestrator.py:194` + `generation.py:207` | ~1-2s LLM duplicado |
| 3 | `load_doctor_state` duplicado (salva, invalida cache, recarrega) | `orchestrator.py:177,220` | 2 round-trips DB |
| 4 | ChipSelector N+1 — 1 COUNT por chip elegivel | `selector.py:293` | ~20 queries/envio |

### Achados P1 — Infraestrutura

| # | Problema | Local | Impacto |
|---|----------|-------|---------|
| 5 | Scheduler executa jobs sequencialmente no mesmo minuto | `scheduler.py:488-495` | Jobs atrasam uns aos outros |
| 6 | Deep health check — 12+ queries DB sequenciais | `health/deep.py:91-107` | 60-600ms no endpoint |
| 7 | Health score — 4 componentes calculados sequencialmente | `health/scoring.py:35-51` | ~200ms/request |
| 8 | Trust score job — loop sequencial N chips x 3 queries | `chips_ops.py:63` | 7.5s para 50 chips |

### Achados P2 — Jobs Background

| # | Problema | Local | Impacto |
|---|----------|-------|---------|
| 9 | Followup legacy N+1 — busca sem LIMIT x query/conversa | `followup.py:266-325` | 600+ queries/execucao |
| 10 | Temperature decay — reload individual por medico | `temperature_decay.py:52-58` | 200 queries/execucao |
| 11 | Fila mensagens — lookup conversa por mensagem | `fila_mensagens.py:77-91` | 20 queries/execucao |
| 12 | Qualidade — SELECT sem LIMIT em conversas fechadas | `qualidade.py:144-161` | Payload crescente |
| 13 | ChipSelector ramp-up — UPDATE individual por chip | `selector.py:908-938` | Baixo (poucos chips) |

### Achados P3 — Caching

| # | Problema | Local | Impacto |
|---|----------|-------|---------|
| 14 | Health endpoints sem cache — dashboard polla cada 10s | `scoring.py`, `chips.py`, `alerts.py` | Queries repetidas |
| 15 | Diretrizes nao cacheadas — query a cada mensagem | `contexto.py:217-241` | 1 query/msg |
| 16 | 3 health subsystems consultam chips independentemente | `chips.py`, `scoring.py`, `alerts.py` | 3 queries redundantes |

### Achados Positivos (ja bem feitos)

- `montar_contexto_completo()` ja usa `asyncio.gather()` + cache Redis
- `http_client.py` singleton existe com pooling + HTTP/2 (so precisa adotar)
- Redis bem usado para rate limiting, dedup, idempotencia e cache
- Webhook retorna 202 imediato com processamento background

---

## Epicos

### Epic 0: Safety Net — Testes de Performance Baseline

**Objetivo:** Medir tempos atuais antes de otimizar para ter baseline comparavel.

**Tarefas:**
- Criar testes que medem tempo de execucao dos hot paths (com mocks)
- Registrar baseline de queries por endpoint (contagem de chamadas mock)
- Verificar que testes de caracterizacao da Sprint 58 continuam passando

**Criterios de aceite:**
- Baseline documentado para cada hot path
- Contagem de chamadas DB/HTTP por operacao registrada

**Risco:** Baixo

---

### Epic 1: Adotar HTTP Client Singleton

**Objetivo:** Substituir 57 instancias de `async with httpx.AsyncClient()` pelo singleton existente em `app/services/http_client.py`.

**Arquivos afetados (16):**

| Arquivo | Instancias | Servico |
|---------|-----------|---------|
| `app/services/whatsapp.py` | 6 | Evolution API |
| `app/evolution.py` | 6 | Evolution API (legado) |
| `app/services/chatwoot.py` | 6 | Chatwoot API |
| `app/services/salvy/client.py` | 5 | Salvy API |
| `app/services/chips/instance_manager.py` | 5 | Evolution instances |
| `app/services/chip_activator/client.py` | 6 | VPS activator |
| `app/services/whatsapp_providers/zapi.py` | 5 | Z-API provider |
| `app/services/whatsapp_providers/evolution.py` | 4 | Evolution provider |
| `app/services/group_entry/discovery.py` | 3 | Group discovery |
| `app/workers/scheduler.py` | 3 | Job scheduler |
| `app/services/chips/sync_evolution.py` | 2 | Chip sync |
| `app/services/slack.py` | 1 | Slack API |
| `app/services/slack_comandos.py` | 1 | Slack commands |
| `app/tools/slack/mensagens.py` | 1 | Slack tools |
| `app/api/routes/chatwoot.py` | 1 | Chatwoot webhook |
| `app/services/outbound/multi_chip.py` | 1 | Multi-chip |
| `app/services/group_entry/crawler.py` | 1 | Group crawler |

**Tecnica:** Substituir `async with httpx.AsyncClient() as client:` por:
```python
from app.services.http_client import get_http_client
client = await get_http_client()
```

**Atencao especial:**
- `chip_activator/client.py` usa `verify=False` — precisa parametro ou cliente separado
- Timeouts customizados (300s no scheduler, 5s no multi_chip) — usar `timeout=` por request
- Garantir `close_http_client()` no shutdown via `app/main.py` lifespan

**Criterios de aceite:**
- Zero `async with httpx.AsyncClient()` restantes em `app/`
- Todos os testes passando
- `close_http_client()` no lifespan shutdown

**Risco:** Baixo — substituicao mecanica, sem mudanca de logica

---

### Epic 2: Eliminar Duplicatas no Hot Path

**Objetivo:** Remover chamadas duplicadas de LLM e DB que acontecem em cada mensagem.

**Tarefa 2.1: Eliminar double `analisar_situacao`**

Arquivo: `app/services/agente/orchestrator.py:194` + `app/services/agente/generation.py:207`

O `analisar_situacao()` e chamado com inputs identicos em dois locais:
1. No orchestrator — para detectar objecoes
2. No generation — para buscar conhecimento dinamico

**Fix:** Passar `situacao` do orchestrator para `gerar_resposta_julia` via parametro.

```python
# orchestrator.py: passa situacao como parametro
resposta = await pkg.gerar_resposta_julia(
    ...,
    situacao=situacao,  # Pre-computado
)

# generation.py: recebe e usa se disponivel
async def _gerar_resposta_julia_impl(..., situacao=None):
    if situacao is None:
        situacao = await orquestrador.analisar_situacao(...)
    conhecimento_dinamico = situacao.resumo
```

**Impacto:** Elimina ~1-2s de CPU/LLM por mensagem recebida.

**Tarefa 2.2: Eliminar double `load_doctor_state`**

Arquivo: `app/services/agente/orchestrator.py:177,220`

Apos salvar updates, o state e recarregado do DB (cache Redis invalido).

**Fix:** Aplicar updates em memoria em vez de recarregar:

```python
if inbound_updates:
    await pkg.save_doctor_state_updates(medico["id"], inbound_updates)
    for key, value in inbound_updates.items():
        if hasattr(state, key):
            setattr(state, key, value)
# Remover: state = await pkg.load_doctor_state(medico["id"])
```

**Impacto:** Elimina 2 round-trips DB (cache delete + SELECT) por mensagem.

**Tarefa 2.3: ChipSelector batch query**

Arquivo: `app/services/chips/selector.py:293,362-375`

O `_contar_msgs_ultima_hora()` faz 1 COUNT query por chip. Com 20 chips, sao 20 queries por envio.

**Fix:** Batch query com GROUP BY via RPC, ou usar contadores Redis existentes.

```python
# Antes: 20 queries
for chip in result.data:
    uso_hora = await self._contar_msgs_ultima_hora(chip["id"])

# Depois: 1 query
uso_por_chip = await self._contar_msgs_ultima_hora_batch(
    [c["id"] for c in result.data]
)
```

**Impacto:** Reduz de N queries para 1 por envio outbound.

**Criterios de aceite:**
- `analisar_situacao` chamado exatamente 1x por mensagem (verificavel via mock count)
- `load_doctor_state` chamado exatamente 1x por mensagem
- `_contar_msgs_ultima_hora` nao mais chamado em loop
- Todos os testes passando

**Risco:** Medio — altera hot path do agente, requer cuidado com assinaturas

---

### Epic 3: Paralelizar Scheduler e Jobs

**Objetivo:** Jobs do mesmo minuto rodam em paralelo. Trust score e health check usam asyncio.gather.

**Tarefa 3.1: Scheduler paralelo**

Arquivo: `app/workers/scheduler.py:488-495`

```python
# Antes: sequencial
for job in JOBS:
    if should_run(job["schedule"], now):
        await execute_job(job)

# Depois: paralelo
triggered = [job for job in JOBS if should_run(job["schedule"], now)]
if triggered:
    await asyncio.gather(
        *[execute_job(job) for job in triggered],
        return_exceptions=True,
    )
```

**Tarefa 3.2: Trust score com semaphore**

Arquivo: `app/api/routes/jobs/chips_ops.py:63-76`

```python
semaphore = asyncio.Semaphore(5)
async def _calc(chip):
    async with semaphore:
        return await calcular_trust_score(chip["id"])

results = await asyncio.gather(
    *[_calc(chip) for chip in chips.data],
    return_exceptions=True,
)
```

**Tarefa 3.3: Deep health check paralelo**

Arquivo: `app/services/health/deep.py:91-107`

Wrappear checks independentes em `asyncio.gather()`. Checks de tabelas/views individiuais tambem paralelizados.

**Tarefa 3.4: Health score paralelo**

Arquivo: `app/services/health/scoring.py:35-51`

```python
connectivity_score, fila_score = await asyncio.gather(
    _calcular_score_conectividade(),
    _calcular_score_fila(),
)
```

Dentro de `_calcular_score_conectividade`, paralelizar Redis + Evolution:
```python
redis_ok, evolution_status = await asyncio.gather(
    verificar_conexao_redis(),
    evolution.verificar_conexao(),
    return_exceptions=True,
)
```

**Criterios de aceite:**
- Jobs do mesmo minuto iniciam simultaneamente (verificavel via logs)
- Trust score de 50 chips completa em <3s (era ~7.5s)
- `/health/deep` responde em <200ms (era 60-600ms)
- `/health/score` responde em <100ms
- Todos os testes passando

**Risco:** Baixo-Medio — scheduler precisa tratar exceptions por job independentemente

---

### Epic 4: Corrigir N+1 em Jobs Background

**Objetivo:** Eliminar queries desnecessarias em jobs que rodam periodicamente.

**Tarefa 4.1: Followup legacy — substituir por path moderno**

Arquivo: `app/services/followup.py:266-325`

O `verificar_followups_pendentes()` faz N+1 triplo. O path moderno `processar_followups_pendentes()` ja existe e e mais eficiente. Remover path legacy ou adicionar LIMIT + JOIN.

**Tarefa 4.2: Temperature decay — batch SELECT e UPDATE**

Arquivo: `app/workers/temperature_decay.py:52-58`

Alterar `buscar_states_para_decay()` para `SELECT *` e converter diretamente para DoctorState, evitando `load_doctor_state()` por medico. Batch os UPDATEs.

**Tarefa 4.3: Fila mensagens — JOIN na query inicial**

Arquivo: `app/services/fila_mensagens.py:77-91` (ou `app/services/jobs/fila_mensagens.py`)

Alterar query inicial para incluir JOIN:
```python
supabase.table("fila_mensagens")
    .select("*, conversations(*, clientes(*))")
    .eq("status", "pendente")
    .limit(50)
    .execute()
```

**Tarefa 4.4: Qualidade — adicionar LIMIT**

Arquivo: `app/services/qualidade.py:144-161`

- Adicionar `.limit(50)` na busca de conversas fechadas
- Adicionar `.limit(100)` na busca de interacoes por conversa
- Usar RPC com NOT IN para excluir ja avaliadas

**Tarefa 4.5: ChipSelector ramp-up — batch UPDATE**

Arquivo: `app/services/chips/selector.py:908-938`

Agrupar chips por nova fase e fazer 1 UPDATE por grupo.

**Criterios de aceite:**
- Followup job faz <10 queries (era 600+)
- Temperature decay faz <5 queries (era 200)
- Fila mensagens faz 1 query com JOIN (era N+1)
- Qualidade tem LIMIT em todas as queries
- Todos os testes passando

**Risco:** Medio — alteracoes em queries podem mudar comportamento sutil

---

### Epic 5: Caching Layer para Endpoints Frequentes

**Objetivo:** Cache Redis com TTL curto para endpoints pollados frequentemente.

**Tarefa 5.1: Cache health endpoints**

Arquivos: `app/services/health/scoring.py`, `chips.py`, `alerts.py`

Cache Redis de 15-30s para:
- `/health/score` → `health:score` TTL 15s
- `/health/chips` → `health:chips` TTL 30s
- `/health/alerts` → `health:alerts` TTL 15s

**Tarefa 5.2: Cache diretrizes**

Arquivo: `app/services/contexto.py:217-241`

Cache Redis de 5min para `carregar_diretrizes_ativas()`:
```python
cached = await cache_get_json("diretrizes:ativas")
if cached:
    return cached
# ... fetch from DB ...
await cache_set_json("diretrizes:ativas", result, ttl=300)
```

**Tarefa 5.3: Cache compartilhado de chips ativos**

Arquivos: `app/services/health/chips.py`, `scoring.py`, `alerts.py`

Criar `obter_chips_ativos_cached()` que retorna dados de chips com TTL 30s, usado por todos os health subsystems.

**Criterios de aceite:**
- Dashboard pollando 3 endpoints a cada 10s gera no maximo 6 queries/minuto (era ~18/minuto)
- Diretrizes buscam do DB no maximo 1x a cada 5 minutos
- Cache invalidado corretamente quando dados mudam
- Todos os testes passando

**Risco:** Baixo — cache com TTL curto, dados nao criticos

---

## Ordem de Execucao

```
Epic 0 (baseline)           [PRIMEIRO]
    |
    +---> Epic 1 (httpx singleton)  [independente, maior impacto]
    +---> Epic 5 (caching)          [independente]
    |
    +---> Epic 2 (hot path dupes)   [independente]
    +---> Epic 3 (parallelization)  [independente]
    |
    +---> Epic 4 (N+1 fixes)        [independente]
```

Epics 1-5 sao todos independentes entre si. Epic 1 e o maior bang-for-buck.

---

## Definition of Done

- [ ] Zero `async with httpx.AsyncClient()` em `app/`
- [ ] `analisar_situacao` chamado 1x por mensagem (era 2x)
- [ ] `load_doctor_state` chamado 1x por mensagem (era 2x)
- [ ] Scheduler executa jobs em paralelo
- [ ] Health endpoints cacheados com TTL
- [ ] N+1 corrigidos em followup, temperature decay, fila mensagens
- [ ] `uv run pytest` limpo
- [ ] Testes de caracterizacao (Sprint 58) passando
- [ ] Baseline de performance documentado com melhoria mensuravel

## Verificacao

```bash
# Apos cada epic:
uv run pytest --no-cov                                      # Todos os testes
uv run pytest tests/characterization/ --no-cov               # Sprint 58 safety net
grep -rn "async with httpx.AsyncClient" app/ | wc -l        # Deve ser 0 apos Epic 1
```

## Rollback

- Epic 1: Reverter para httpx efemero (funcional, so perde performance)
- Epic 2: Reverter parametro `situacao` e reload de state
- Epic 3: Reverter para for/await sequencial
- Epic 4: Reverter queries para formato original
- Epic 5: Remover cache (fallback para query direta)

Todas as mudancas sao backward-compatible. Nenhuma altera contratos de API.
