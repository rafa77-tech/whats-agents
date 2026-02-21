# EPICO 03: Pre-send Validation & Error Handling

## Prioridade: P1 (Alto)

## Contexto

O executor envia mensagens sem verificar circuit breaker ou cooldown, causando envios desnecessarios para chips que ja devem estar parados. Alem disso, todos os exception handlers fazem `except Exception as e: return False` sem stack trace, tornando debug impossivel em producao.

## Escopo

- **Incluido**: Pre-send validation (circuit breaker, cooldown), error handling com exc_info, retry basico
- **Excluido**: Mudancas no circuit breaker em si, mudancas no cooldown engine, implementacao de retry com backoff exponencial completo

---

## Tarefa 1: Pre-send validation no executor

### Objetivo

Verificar circuit breaker e cooldown ANTES de tentar enviar, evitando envios desnecessarios e falhas previsiveis.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/warmer/executor.py` |

### Implementacao

Adicionar checagem antes do envio em `_executar_conversa_par()` (apos linha 107):

```python
from app.services.chips.circuit_breaker import ChipCircuitBreaker

async def _executar_conversa_par(chip: dict, atividade: AtividadeAgendada) -> bool:
    try:
        # 1. Verificar conexao (Evolution)
        provider_tipo = chip.get("provider") or "evolution"
        if provider_tipo == "evolution" and not chip.get("evolution_connected"):
            logger.warning(f"[WarmupExecutor] Chip {chip['telefone'][-4:]} desconectado")
            return False

        # 2. NOVO: Verificar circuit breaker
        if ChipCircuitBreaker.esta_aberto(chip["id"]):
            logger.warning(
                f"[WarmupExecutor] Circuit breaker ABERTO para {chip['telefone'][-4:]}, "
                f"skip conversa_par"
            )
            return False

        # 3. NOVO: Verificar cooldown
        cooldown_until = chip.get("cooldown_until")
        if cooldown_until:
            from datetime import datetime
            cooldown_dt = datetime.fromisoformat(str(cooldown_until).replace("Z", "+00:00"))
            if agora_brasilia() < cooldown_dt:
                logger.warning(
                    f"[WarmupExecutor] Chip {chip['telefone'][-4:]} em cooldown "
                    f"ate {cooldown_until}, skip conversa_par"
                )
                return False

        # 4. Selecionar par, gerar mensagem, enviar...
        # (codigo existente)
```

Tambem adicionar para `_executar_marcar_lido()` a verificacao de circuit breaker (linhas 148-160).

### Testes Obrigatorios

**Unitarios:**
- [ ] `test_conversa_par_skip_circuit_breaker_aberto` — retorna False quando circuit breaker open
- [ ] `test_conversa_par_skip_cooldown_ativo` — retorna False quando chip em cooldown
- [ ] `test_conversa_par_executa_quando_tudo_ok` — executa normalmente quando sem bloqueios
- [ ] `test_marcar_lido_skip_circuit_breaker` — marcar_lido tambem verifica circuit breaker

**Edge cases:**
- [ ] `test_conversa_par_cooldown_expirado` — cooldown no passado nao bloqueia
- [ ] `test_conversa_par_cooldown_null` — sem cooldown nao bloqueia

### Definition of Done

- [ ] Circuit breaker verificado antes de envio em conversa_par e marcar_lido
- [ ] Cooldown verificado antes de envio em conversa_par
- [ ] Logs WARNING claros indicando motivo do skip
- [ ] Testes passando (6+)
- [ ] Cobertura >90% nos metodos de execucao

### Estimativa

2 horas

---

## Tarefa 2: Error handling com stack trace e classificacao

### Objetivo

Adicionar `exc_info=True` em todos os `logger.error` do warmer e classificar erros em transient vs permanent.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/warmer/executor.py` |
| Modificar | `app/services/warmer/orchestrator.py` |
| Modificar | `app/services/warmer/scheduler.py` |

### Implementacao

**executor.py** — todos os `except Exception as e`:

```python
# ANTES:
except Exception as e:
    logger.error(f"[WarmupExecutor] Erro ao executar atividade: {e}")
    return False

# DEPOIS:
except Exception as e:
    logger.error(
        f"[WarmupExecutor] Erro ao executar atividade: {e}",
        exc_info=True,
        extra={
            "chip_id": atividade.chip_id,
            "tipo": atividade.tipo.value,
        }
    )
    return False
```

Aplicar o mesmo padrao em:
- `executor.py` linhas 76-78 (executar_atividade)
- `executor.py` linhas 136-138 (conversa_par)
- `executor.py` linhas 158-160 (marcar_lido)
- `executor.py` linhas 211-213 (enviar_midia)
- `orchestrator.py` linhas 475-476 (ciclo_warmup atividades)
- `orchestrator.py` linhas 499-500 (calcular trust)

**orchestrator.py** — adicionar contexto nos logs de ciclo:

```python
# ANTES:
except Exception as e:
    logger.error(f"[Orchestrator] Erro em atividade: {e}")

# DEPOIS:
except Exception as e:
    logger.error(
        f"[Orchestrator] Erro em atividade {atividade.tipo.value} "
        f"chip={atividade.chip_id[:8]}: {e}",
        exc_info=True,
    )
```

### Testes Obrigatorios

**Unitarios:**
- [ ] `test_executor_loga_stack_trace_em_erro` — verifica que logger.error chamado com exc_info=True
- [ ] `test_executor_inclui_chip_id_no_log` — verifica presenca de chip_id no log extra
- [ ] `test_orchestrator_loga_stack_trace` — idem para orchestrator

### Definition of Done

- [ ] Todos os `logger.error` no modulo warmer tem `exc_info=True`
- [ ] Contexto (chip_id, tipo) incluido em logs de erro
- [ ] Testes passando (3+)
- [ ] Zero `except Exception as e` sem stack trace no modulo warmer

### Estimativa

1.5 horas

---

## Tarefa 3: Buscar chip com campos de cooldown

### Objetivo

Garantir que `_buscar_chip()` no executor retorna os campos necessarios para pre-send validation.

### Arquivos

| Acao | Arquivo |
|------|---------|
| Modificar | `app/services/warmer/executor.py` |

### Implementacao

Verificar e atualizar `_buscar_chip()` para incluir `cooldown_until`:

```python
async def _buscar_chip(chip_id: str) -> Optional[dict]:
    result = (
        supabase.table("chips")
        .select(
            "id, telefone, status, fase_warmup, trust_score, provider, "
            "evolution_connected, tipo, cooldown_until, "
            "msgs_enviadas_hoje, limite_hora, limite_dia"
        )
        .eq("id", chip_id)
        .single()
        .execute()
    )
    return result.data
```

### Testes Obrigatorios

**Unitarios:**
- [ ] `test_buscar_chip_retorna_cooldown_until` — campo cooldown_until presente no resultado
- [ ] `test_buscar_chip_retorna_none_inexistente` — chip inexistente retorna None

### Definition of Done

- [ ] `_buscar_chip()` retorna `cooldown_until` no select
- [ ] Testes passando (2+)

### Estimativa

30 minutos
