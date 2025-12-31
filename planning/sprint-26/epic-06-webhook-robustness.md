# Epic 06: Webhook Robustness

## Objetivo

Garantir **robustez no processamento de webhooks** para que nenhuma mensagem seja perdida:
- Dead Letter Queue (DLQ) para falhas
- Idempotency para evitar duplicatas
- Retry com backoff exponencial
- Metricas de processamento

## Contexto

Com N chips recebendo webhooks, a robustez e critica:

| Problema | Solucao |
|----------|---------|
| Webhook falha | Retry com DLQ |
| Webhook duplicado | Idempotency key |
| Processamento lento | Async com queue |
| Perda de dados | Persistencia antes de processar |

---

## Story 6.1: Dead Letter Queue

### Objetivo
Implementar DLQ para webhooks que falharem.

### Implementacao

**Arquivo:** `app/services/webhooks/dlq.py`

```python
"""
Dead Letter Queue para webhooks.

Armazena webhooks que falharam para reprocessamento.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict
import json

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


async def salvar_dlq(
    instance_name: str,
    event_type: str,
    payload: dict,
    erro: str,
    tentativa: int = 1,
) -> str:
    """
    Salva webhook na DLQ.

    Args:
        instance_name: Instancia que recebeu
        event_type: Tipo do evento
        payload: Payload original
        erro: Mensagem de erro
        tentativa: Numero da tentativa

    Returns:
        ID do registro DLQ
    """
    result = supabase.table("webhook_dlq").insert({
        "instance_name": instance_name,
        "event_type": event_type,
        "payload": payload,
        "erro": erro,
        "tentativa": tentativa,
        "status": "pending" if tentativa < MAX_RETRIES else "failed",
    }).execute()

    dlq_id = result.data[0]["id"]

    logger.warning(
        f"[DLQ] Webhook salvo: {dlq_id} ({instance_name}/{event_type}) - "
        f"Tentativa {tentativa}/{MAX_RETRIES}"
    )

    return dlq_id


async def listar_pendentes(limit: int = 50) -> list:
    """
    Lista webhooks pendentes para reprocessamento.

    Returns:
        Lista de webhooks pendentes
    """
    result = supabase.table("webhook_dlq").select("*").eq(
        "status", "pending"
    ).order(
        "created_at", desc=False  # FIFO
    ).limit(limit).execute()

    return result.data or []


async def marcar_sucesso(dlq_id: str):
    """Marca webhook como processado com sucesso."""
    supabase.table("webhook_dlq").update({
        "status": "processed",
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", dlq_id).execute()


async def marcar_falha_permanente(dlq_id: str, erro: str):
    """Marca webhook como falha permanente."""
    supabase.table("webhook_dlq").update({
        "status": "failed",
        "erro": erro,
    }).eq("id", dlq_id).execute()


async def incrementar_tentativa(dlq_id: str, erro: str) -> int:
    """
    Incrementa tentativa e atualiza erro.

    Returns:
        Nova contagem de tentativas
    """
    # Buscar atual
    result = supabase.table("webhook_dlq").select("tentativa").eq(
        "id", dlq_id
    ).single().execute()

    nova_tentativa = result.data["tentativa"] + 1

    status = "pending" if nova_tentativa < MAX_RETRIES else "failed"

    supabase.table("webhook_dlq").update({
        "tentativa": nova_tentativa,
        "erro": erro,
        "status": status,
    }).eq("id", dlq_id).execute()

    return nova_tentativa
```

**Migration:**

```sql
-- Migration: create_webhook_dlq
-- Sprint 26 - E06 - Dead Letter Queue

CREATE TABLE webhook_dlq (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    instance_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,

    erro TEXT,
    tentativa INT DEFAULT 1,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'processed', 'failed')),

    created_at TIMESTAMPTZ DEFAULT now(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX idx_webhook_dlq_pending ON webhook_dlq(status, created_at)
    WHERE status = 'pending';
CREATE INDEX idx_webhook_dlq_instance ON webhook_dlq(instance_name, created_at DESC);

COMMENT ON TABLE webhook_dlq IS 'Dead Letter Queue para webhooks que falharam';
```

### DoD

- [ ] DLQ implementada
- [ ] Migration criada
- [ ] Funcoes de gestao

---

## Story 6.2: Idempotency

### Objetivo
Evitar processamento duplicado de webhooks.

### Implementacao

**Arquivo:** `app/services/webhooks/idempotency.py`

```python
"""
Idempotency para webhooks.

Garante que cada webhook seja processado apenas uma vez.
"""
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.services.redis_client import redis_client

logger = logging.getLogger(__name__)

# TTL de 24h para chaves de idempotency
IDEMPOTENCY_TTL = 60 * 60 * 24  # 24 horas


def gerar_idempotency_key(instance_name: str, payload: dict) -> str:
    """
    Gera chave unica para o webhook.

    Baseado em:
    - instance_name
    - message_id (se existir)
    - timestamp
    - hash do payload

    Args:
        instance_name: Nome da instancia
        payload: Payload do webhook

    Returns:
        Chave de idempotency
    """
    # Extrair identificadores unicos do payload
    data = payload.get("data", {})
    key = data.get("key", {})

    message_id = key.get("id", "")
    remote_jid = key.get("remoteJid", "")
    timestamp = data.get("messageTimestamp", "")

    # Se nao tem identificadores, usar hash do payload
    if not message_id:
        payload_str = json.dumps(payload, sort_keys=True)
        message_id = hashlib.md5(payload_str.encode()).hexdigest()[:16]

    return f"webhook:idem:{instance_name}:{message_id}:{remote_jid}:{timestamp}"


async def verificar_e_marcar(idempotency_key: str) -> bool:
    """
    Verifica se webhook ja foi processado e marca como processando.

    Usa SETNX do Redis para atomicidade.

    Args:
        idempotency_key: Chave de idempotency

    Returns:
        True se e novo (pode processar), False se ja foi processado
    """
    # SETNX - Set if Not eXists
    resultado = await redis_client.set(
        idempotency_key,
        datetime.now(timezone.utc).isoformat(),
        nx=True,  # Apenas se nao existir
        ex=IDEMPOTENCY_TTL,
    )

    if resultado:
        logger.debug(f"[Idempotency] Novo webhook: {idempotency_key}")
        return True
    else:
        logger.debug(f"[Idempotency] Webhook duplicado ignorado: {idempotency_key}")
        return False


async def limpar_chave(idempotency_key: str):
    """
    Remove chave de idempotency.

    Usar se processamento falhou e deve ser reprocessado.
    """
    await redis_client.delete(idempotency_key)
```

### DoD

- [ ] Geracao de chave
- [ ] Verificacao atomica
- [ ] TTL configurado

---

## Story 6.3: Retry com Backoff

### Objetivo
Implementar retry com backoff exponencial.

### Implementacao

**Arquivo:** `app/services/webhooks/retry.py`

```python
"""
Retry com backoff exponencial para webhooks.
"""
import asyncio
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)


async def retry_with_backoff(
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    **kwargs,
) -> Any:
    """
    Executa funcao com retry e backoff exponencial.

    Args:
        func: Funcao async a executar
        max_retries: Numero maximo de tentativas
        base_delay: Delay inicial em segundos
        max_delay: Delay maximo em segundos
        *args, **kwargs: Argumentos para a funcao

    Returns:
        Resultado da funcao

    Raises:
        Exception: Se todas as tentativas falharem
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)

        except Exception as e:
            last_exception = e

            if attempt < max_retries - 1:
                # Calcular delay exponencial: 1s, 2s, 4s, 8s, ...
                delay = min(base_delay * (2 ** attempt), max_delay)

                logger.warning(
                    f"[Retry] Tentativa {attempt + 1}/{max_retries} falhou: {e}. "
                    f"Aguardando {delay}s..."
                )

                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"[Retry] Todas as {max_retries} tentativas falharam: {e}"
                )

    raise last_exception
```

### DoD

- [ ] Backoff exponencial
- [ ] Logging de tentativas

---

## Story 6.4: Wrapper de Processamento

### Objetivo
Integrar DLQ, idempotency e retry no processamento.

### Implementacao

**Arquivo:** `app/services/webhooks/processor.py`

```python
"""
Webhook Processor - Processamento robusto com DLQ, idempotency e retry.
"""
import logging
from typing import Callable, Dict

from app.services.webhooks.idempotency import gerar_idempotency_key, verificar_e_marcar, limpar_chave
from app.services.webhooks.dlq import salvar_dlq, marcar_sucesso, incrementar_tentativa
from app.services.webhooks.retry import retry_with_backoff

logger = logging.getLogger(__name__)


async def processar_webhook_robusto(
    instance_name: str,
    payload: dict,
    processor: Callable,
) -> dict:
    """
    Processa webhook com robustez completa.

    Fluxo:
    1. Verificar idempotency
    2. Tentar processar com retry
    3. Se falhar, salvar na DLQ
    4. Retornar resultado

    Args:
        instance_name: Nome da instancia
        payload: Payload do webhook
        processor: Funcao que processa o webhook

    Returns:
        {"status": "ok" | "duplicate" | "queued", ...}
    """
    # 1. Verificar idempotency
    idem_key = gerar_idempotency_key(instance_name, payload)
    eh_novo = await verificar_e_marcar(idem_key)

    if not eh_novo:
        return {"status": "duplicate", "message": "Webhook already processed"}

    # 2. Tentar processar com retry
    try:
        resultado = await retry_with_backoff(
            processor,
            instance_name,
            payload,
            max_retries=2,  # Retry rapido
            base_delay=0.5,
        )

        return {"status": "ok", "result": resultado}

    except Exception as e:
        logger.error(f"[WebhookProcessor] Falha apos retries: {e}")

        # 3. Salvar na DLQ
        await limpar_chave(idem_key)  # Permitir reprocessamento via DLQ

        dlq_id = await salvar_dlq(
            instance_name=instance_name,
            event_type=payload.get("event", "unknown"),
            payload=payload,
            erro=str(e),
        )

        return {
            "status": "queued",
            "message": "Webhook queued for retry",
            "dlq_id": dlq_id,
        }


async def reprocessar_dlq(limit: int = 10):
    """
    Reprocessa webhooks da DLQ.

    Rodar periodicamente via job.
    """
    from app.services.webhooks.dlq import listar_pendentes, marcar_sucesso, incrementar_tentativa

    pendentes = await listar_pendentes(limit)

    processados = 0
    falhas = 0

    for item in pendentes:
        try:
            # Importar processor aqui para evitar circular import
            from app.api.routes.webhook_router import webhook_evolution

            # Simular request
            class FakeRequest:
                async def json(self):
                    return item["payload"]

            await webhook_evolution(item["instance_name"], FakeRequest())

            await marcar_sucesso(item["id"])
            processados += 1

        except Exception as e:
            tentativa = await incrementar_tentativa(item["id"], str(e))
            logger.error(
                f"[DLQ] Reprocessamento falhou: {item['id']} - "
                f"Tentativa {tentativa}"
            )
            falhas += 1

    logger.info(f"[DLQ] Reprocessamento: {processados} ok, {falhas} falhas")

    return {"processados": processados, "falhas": falhas}
```

### DoD

- [ ] Wrapper integrado
- [ ] Reprocessamento de DLQ

---

## Story 6.5: Metricas de Webhook

### Objetivo
Rastrear metricas de processamento.

### Implementacao

```python
# Incrementar contadores por evento/status
# Exportar via /metrics endpoint
```

### DoD

- [ ] Contadores implementados
- [ ] Endpoint de metricas

---

## Checklist do Epico

- [ ] **E06.1** - Dead Letter Queue
- [ ] **E06.2** - Idempotency
- [ ] **E06.3** - Retry com backoff
- [ ] **E06.4** - Wrapper de processamento
- [ ] **E06.5** - Metricas
- [ ] Testes de integracao
- [ ] Job de reprocessamento DLQ

---

## Diagrama: Fluxo Robusto

```
┌─────────────────────────────────────────────────────────────────┐
│                 WEBHOOK ROBUST PROCESSING                        │
└─────────────────────────────────────────────────────────────────┘

  Webhook                      Processor                         DLQ
     │                            │                               │
     │  POST /webhook/julia-xxx   │                               │
     │ ──────────────────────────>│                               │
     │                            │                               │
     │                            │ 1. Gerar idempotency key      │
     │                            │    md5(instance+msg_id+ts)    │
     │                            │                               │
     │                            │ 2. SETNX no Redis            │
     │                            │    Se existe → DUPLICATE      │
     │                            │<──────────────────────────    │
     │<───────────────────────────│    {"status": "duplicate"}    │
     │                            │                               │
     │                            │ 3. Se novo, processar         │
     │                            │    com retry (max 2x)         │
     │                            │                               │
     │                            │    Tentativa 1 ───────────┐   │
     │                            │         │                 │   │
     │                            │         │ FALHA           │   │
     │                            │         ▼                 │   │
     │                            │    sleep(0.5s)            │   │
     │                            │         │                 │   │
     │                            │    Tentativa 2 ───────────┤   │
     │                            │         │                 │   │
     │                            │         │ SUCESSO         │   │
     │                            │         ▼                 │   │
     │<───────────────────────────│    {"status": "ok"}       │   │
     │                            │                           │   │
     │                            │         │ FALHA           │   │
     │                            │         ▼                 │   │
     │                            │ 4. Salvar na DLQ          │   │
     │                            │ ─────────────────────────────>│
     │                            │                               │
     │<───────────────────────────│    {"status": "queued"}       │
     │                            │                               │
     │                            │                               │
     │                            │                               │
  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│─
     │                            │                               │
     │                     JOB PERIODICO                          │
     │                     (cada 5 min)                           │
     │                            │                               │
     │                            │ 5. Reprocessar pendentes     │
     │                            │<─────────────────────────────│
     │                            │                               │
     │                            │    Para cada webhook:         │
     │                            │    - Processar                │
     │                            │    - Se ok: marcar processed │
     │                            │    - Se falha: incrementar   │
     │                            │      tentativa                │
     │                            │    - Se max: marcar failed   │
     │                            │                               │

ESTADOS DA DLQ:
  pending → processing → processed
                      → failed (apos 3 tentativas)
```
