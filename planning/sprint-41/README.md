# Sprint 41 - NotificationHub: Sistema Centralizado de Notificacoes

**Branch:** `feature/sprint-41-notification-hub`
**Criacao:** 2026-01-27
**Status:** 📋 Planejado

---

## Sumario Executivo

### Problema

O sistema atual de notificacoes Slack esta fragmentado em 19 arquivos com 36 pontos de envio independentes, causando:

1. **Excesso de notificacoes** - Um problema raiz (ex: WhatsApp offline) dispara multiplos alertas de sistemas diferentes
2. **Cooldowns isolados** - 3 sistemas de cooldown que nao se comunicam (`alertas.py`, `business_events/alerts.py`, `monitor_whatsapp.py`)
3. **Sem correlacao** - Alertas relacionados nao sao agrupados
4. **Dificil manutencao** - Logica de notificacao espalhada por todo o codebase

### Impacto Atual

- **36 call sites** em 19 arquivos diferentes
- **3 sistemas de cooldown** independentes
- Quando WhatsApp cai, pode disparar 4+ notificacoes simultaneas
- Equipe sobrecarregada com alertas redundantes

### Solucao

Criar um **NotificationHub** centralizado que:
1. Centraliza todos os envios de notificacao em um unico ponto
2. Agrupa alertas relacionados (correlacao)
3. Aplica cooldown unificado e inteligente
4. Oferece modo digest para notificacoes de baixa prioridade
5. Mantem retrocompatibilidade com callers existentes

---

## Arquitetura da Solucao

### Estrutura de Modulos

```
app/services/notifications/
├── __init__.py           # Exports publicos
├── types.py              # Dataclasses e enums
├── config.py             # Configuracoes e regras
├── cooldown.py           # CooldownManager unificado
├── correlation.py        # Correlacao de alertas
├── digest.py             # DigestManager para batching
├── formatters.py         # Formatacao de mensagens Slack
├── hub.py                # NotificationHub (orquestrador)
└── repository.py         # Persistencia de metricas
```

### Fluxo do NotificationHub

```
┌─────────────────┐
│  Caller         │  (alertas.py, monitor_whatsapp.py, etc)
│  notify(...)    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  NotificationHub.notify()                               │
│                                                         │
│  1. Validar janela operacional (08-20h para non-CRIT)   │
│  2. Verificar cooldown unificado                        │
│  3. Verificar correlacao (suprimir se relacionado)      │
│  4. Rotear por categoria:                               │
│     - CRITICAL → enviar imediatamente                   │
│     - ATTENTION → enviar com cooldown                   │
│     - DIGEST → adicionar ao batch                       │
│     - INFO → enviar se nao em cooldown                  │
│  5. Formatar mensagem Slack                             │
│  6. Enviar via webhook                                  │
│  7. Registrar metricas                                  │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Slack          │
│  Webhook        │
└─────────────────┘
```

---

## Categorias de Notificacao

| Categoria | Comportamento | Cooldown | Janela | Exemplos |
|-----------|---------------|----------|--------|----------|
| **CRITICAL** | Imediato | 15min | 24/7 | WhatsApp offline, pool vazio |
| **ATTENTION** | Com cooldown | 30min | 08-20h | Handoff spike, qualidade baixa |
| **DIGEST** | Batched (1h) | N/A | 08-20h | Plantao reservado, confirmacoes |
| **INFO** | Baixa prioridade | 60min | 08-20h | Reconectado, chip ativado |

---

## Clusters de Correlacao

Quando um alerta de um cluster e enviado, os demais sao suprimidos na mesma janela:

| Cluster | Alertas Correlacionados | Janela |
|---------|-------------------------|--------|
| `whatsapp` | desconectado, criptografia, evolution_down, sem_respostas | 30min |
| `chips` | pool_vazio, pool_baixo, trust_critico, chip_desconectado | 60min |
| `funnel` | handoff_spike, recusa_spike, conversion_drop | 60min |
| `performance` | performance_critica, tempo_resposta_alto | 30min |

---

## Epicos

A sprint esta dividida em **9 epicos** que devem ser executados sequencialmente.

| Epico | Nome | Arquivo | Dependencias | Prioridade |
|-------|------|---------|--------------|------------|
| E01 | Estrutura e Tipos | [E01-estrutura-tipos.md](epicos/E01-estrutura-tipos.md) | - | Alta (fundacao) |
| E02 | Configuracoes e Regras | [E02-configuracoes-regras.md](epicos/E02-configuracoes-regras.md) | E01 | Alta |
| E03 | CooldownManager Unificado | [E03-cooldown-manager.md](epicos/E03-cooldown-manager.md) | E01, E02 | Alta |
| E04 | CorrelationManager | [E04-correlation-manager.md](epicos/E04-correlation-manager.md) | E01, E02 | Alta |
| E05 | DigestManager | [E05-digest-manager.md](epicos/E05-digest-manager.md) | E01, E02 | Media |
| E06 | Formatadores de Mensagem | [E06-formatadores.md](epicos/E06-formatadores.md) | E01, E02 | Media |
| E07 | NotificationHub Core | [E07-notification-hub.md](epicos/E07-notification-hub.md) | E01-E06 | Alta |
| E08 | Migracao de Callers | [E08-migracao-callers.md](epicos/E08-migracao-callers.md) | E07 | Alta |
| E09 | Refatoracao e Seguranca | [E09-refatoracao-seguranca.md](epicos/E09-refatoracao-seguranca.md) | E01-E08 | Obrigatorio |

---

## Definition of Done (Sprint)

A sprint e considerada **COMPLETA** quando:

1. [ ] Todos os 9 epicos marcados como completos
2. [ ] Cobertura de testes >= 90%
3. [ ] Zero erros de tipo (mypy)
4. [ ] Zero erros de lint (ruff)
5. [ ] Todos os 36 callers migrados para o hub
6. [ ] Correlacao funcionando (teste: simular WhatsApp offline = 1 notificacao)
7. [ ] Digest funcionando (teste: 5 reservas = 1 mensagem de resumo)
8. [ ] Zero testes skipped
9. [ ] Branch mergeada na main apos aprovacao

---

## Arquivos de Referencia

Estes arquivos devem ser estudados antes de iniciar:

| Arquivo | Proposito |
|---------|-----------|
| `app/services/slack.py` | Funcoes atuais de notificacao (545 linhas) |
| `app/services/alertas.py` | Sistema de cooldown atual (413 linhas) |
| `app/services/business_events/alerts.py` | Outro sistema de cooldown (676 linhas) |
| `app/services/monitor_whatsapp.py` | Outro sistema de cooldown (356 linhas) |
| `app/services/chips/health_monitor.py` | Notificacoes de chips |
| `app/services/redis.py` | Cache Redis |

---

## Metricas de Sucesso

| Metrica | Atual | Meta |
|---------|-------|------|
| Notificacoes por problema unico | 3-5 | 1 |
| Sistemas de cooldown | 3 | 1 unificado |
| Arquivos com logica de cooldown | 4 | 1 |
| Alertas digest/hora | 5-10 individuais | 1 resumo |

---

## Comandos de Teste

```bash
# Rodar todos os testes da sprint
uv run pytest tests/services/notifications/ -v

# Verificar cobertura
uv run pytest tests/services/notifications/ --cov=app/services/notifications --cov-report=term-missing

# Verificar tipos
uv run mypy app/services/notifications/

# Verificar lint
uv run ruff check app/services/notifications/
```

---

## Arquivos a Criar

### Novos Arquivos (Modulo)
- `app/services/notifications/__init__.py`
- `app/services/notifications/types.py`
- `app/services/notifications/exceptions.py`
- `app/services/notifications/config.py`
- `app/services/notifications/cooldown.py`
- `app/services/notifications/correlation.py`
- `app/services/notifications/digest.py`
- `app/services/notifications/formatters.py`
- `app/services/notifications/hub.py`
- `app/services/notifications/repository.py`

### Novos Arquivos (Testes)
- `tests/services/notifications/__init__.py`
- `tests/services/notifications/test_types.py`
- `tests/services/notifications/test_exceptions.py`
- `tests/services/notifications/test_config.py`
- `tests/services/notifications/test_cooldown.py`
- `tests/services/notifications/test_correlation.py`
- `tests/services/notifications/test_digest.py`
- `tests/services/notifications/test_formatters.py`
- `tests/services/notifications/test_hub.py`

### Arquivos a Modificar (E08)
- `app/services/slack.py`
- `app/services/alertas.py`
- `app/services/business_events/alerts.py`
- `app/services/monitor_whatsapp.py`
- `app/services/chips/health_monitor.py`
- `app/services/chips/orchestrator.py`
- `app/services/grupos/alertas.py`
- `app/services/handoff/flow.py`
- `app/services/briefing_executor.py`
- `app/services/external_handoff/service.py`
- `app/services/hospitais_bloqueados.py`
- `app/services/canal_ajuda.py`
- `app/workers/scheduler.py`
