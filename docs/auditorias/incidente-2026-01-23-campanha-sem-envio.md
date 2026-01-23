# Incidente: Campanha sem envio de mensagens + Restrição WhatsApp

**Data:** 2026-01-23
**Severidade:** Alta
**Duração:** ~3 horas (investigação) + 6 minutos (incidente ativo)
**Status:** Resolvido

---

## Resumo Executivo

Campanha agendada foi criada e iniciada corretamente, mas nenhuma mensagem foi enviada. Durante a investigação, identificamos que o serviço `fila_worker` não estava rodando em produção. Após correção, o worker iniciou o envio mas o chip recebeu restrição do WhatsApp após poucos envios.

---

## Timeline

| Hora (UTC-3) | Evento |
|--------------|--------|
| 14:51 | Campanha "Piloto Discovery Aleatorio - 20Jan" agendada |
| 14:55 | Scheduler detecta e inicia campanha |
| 14:55 | 50 mensagens enfileiradas em `fila_mensagens` |
| 14:55 - 18:30 | Mensagens ficam pendentes (worker não rodando) |
| 18:30 | Início da investigação |
| 18:58 | Fix do `fila_worker.py` deployado |
| 18:58:26 | 1ª mensagem enviada com sucesso |
| 18:58:36 | 2ª mensagem enviada com sucesso |
| 18:59:16 | Primeiro erro 400 Bad Request |
| 18:59:55 | 5º erro - Circuit breaker abre |
| 19:00:05 | FAILED_CIRCUIT_OPEN registrado |
| 19:00 - 19:04 | Circuit alterna entre OPEN e half-open |
| 19:04 | Campanha pausada, chip bloqueado |

---

## Causa Raiz

### Problema 1: Worker não executava

O arquivo `app/workers/fila_worker.py` definia a função `processar_fila()` mas **não tinha o código para executá-la** quando rodado como módulo.

**Faltava:**
```python
if __name__ == "__main__":
    asyncio.run(processar_fila())
```

**Impacto:** O serviço `whats-worker` iniciava sem erros, mas a função nunca era chamada. Mensagens ficavam pendentes indefinidamente.

### Problema 2: Serviço worker não existia no Railway

O projeto foi configurado com apenas 2 serviços:
- `whats-agents` (RUN_MODE=api)
- `whats-scheduler` (RUN_MODE=scheduler)

O serviço `whats-worker` (RUN_MODE=worker) **nunca foi criado**.

### Problema 3: Circuit breaker com reset muito rápido

Configuração anterior:
```python
circuit_evolution = CircuitBreaker(
    tempo_reset_segundos=15  # Muito curto!
)
```

**Impacto:** Após abrir, o circuit tentava half-open a cada 15 segundos, resultando em requisições contínuas mesmo com erro persistente.

---

## Impacto

| Métrica | Valor |
|---------|-------|
| Mensagens que deveriam ser enviadas | 100 |
| Mensagens enviadas com sucesso | 4 |
| Mensagens com erro | 33 |
| Mensagens canceladas | 65 |
| Chip restrito | 5511916175810 |

---

## Resolução

### Fix 1: Entrypoint do fila_worker

```python
# Adicionado ao final de app/workers/fila_worker.py
if __name__ == "__main__":
    asyncio.run(processar_fila())
```

**Commit:** `1b26720` - fix(worker): add main entrypoint to fila_worker

### Fix 2: Serviço whats-worker no Railway

Criado novo serviço no Railway:
- Nome: `whats-worker`
- Repositório: `rafa77-tech/whats-agents`
- Builder: Dockerfile
- Variável: `RUN_MODE=worker`
- Shared variables do projeto

### Fix 3: Circuit breaker com reset mais longo

```python
circuit_evolution = CircuitBreaker(
    tempo_reset_segundos=300  # 5 minutos (era 15s)
)
```

**Commit:** `03a32fc` - fix(circuit-breaker): increase evolution reset time to 5 minutes

### Ações de contenção

1. Campanha pausada: `UPDATE campanhas SET status='pausada' WHERE id=16`
2. Chip bloqueado: `UPDATE chips SET pode_prospectar=false, pode_followup=false WHERE telefone='5511916175810'`
3. Mensagens pendentes canceladas

---

## Lições Aprendidas

### O que funcionou bem

1. **Circuit breaker abriu** após 5 falhas consecutivas
2. **Outcomes foram registrados** corretamente para análise
3. **Investigação identificou** múltiplos problemas de uma vez

### O que não funcionou

1. **Falta de smoke test** para verificar se worker processa mensagens
2. **Nenhum alerta** quando fila acumula mensagens pendentes
3. **Circuit breaker** com configuração inadequada para erros WhatsApp

---

## Ações Preventivas

### Imediato (feito)

- [x] Fix do entrypoint do fila_worker
- [x] Serviço whats-worker criado no Railway
- [x] Circuit breaker com tempo de reset adequado

### Curto prazo (pendente)

- [ ] Adicionar alerta quando `fila_mensagens.pendente > 50` por mais de 30 minutos
- [ ] Smoke test: verificar se worker está processando (health check)
- [ ] Documentar arquitetura de 3 serviços (api, scheduler, worker)

### Médio prazo (backlog)

- [ ] Dashboard de monitoramento da fila
- [ ] Backoff exponencial no circuit breaker
- [ ] Retry automático com delay para mensagens com erro transitório

---

## Análise do Circuit Breaker

### Comportamento Durante o Incidente

```
21:58:26 - SENT (sucesso)
21:58:36 - SENT (sucesso)
21:59:16 - FAILED_PROVIDER (1º erro)
21:59:26 - FAILED_PROVIDER (2º erro)
21:59:36 - FAILED_PROVIDER (3º erro)
21:59:46 - FAILED_PROVIDER (4º erro)
21:59:55 - FAILED_PROVIDER (5º erro)
22:00:05 - CIRCUIT_OPEN (abriu!)
22:00:15 - FAILED_PROVIDER (half-open falhou)
22:00:25 - CIRCUIT_OPEN
... alternando a cada ~10-15 segundos
```

### Métricas

| Métrica | Valor |
|---------|-------|
| Tempo para abrir | ~50 segundos (5 erros) |
| Requisições antes de abrir | 5 |
| Requisições durante circuit open | ~17 (half-open) |
| Requisições evitáveis | ~17 |

### Configuração Atualizada

| Parâmetro | Antes | Depois | Motivo |
|-----------|-------|--------|--------|
| `tempo_reset_segundos` | 15s | 300s | Erros WhatsApp não se resolvem em segundos |

---

## Checklist de Verificação Pós-Incidente

- [x] Worker está rodando (`whats-worker` no Railway)
- [x] Logs mostram "Worker de fila iniciado"
- [x] Chip restrito está bloqueado no banco
- [x] Campanha está pausada
- [x] Circuit breaker atualizado
- [ ] Chip liberado pelo WhatsApp (aguardando review)

---

## Referências

- Commit fix worker: `1b26720`
- Commit fix circuit breaker: `03a32fc`
- Campanha afetada: ID 16 ("Piloto Discovery Aleatorio - 20Jan")
- Chip afetado: 5511916175810

---

## Contato

**Investigação:** Claude Code + Rafael
**Data do documento:** 2026-01-23
