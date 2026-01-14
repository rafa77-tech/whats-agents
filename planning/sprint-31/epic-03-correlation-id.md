# Epic 03: Correlation ID Tracing

## Severidade: P1 - ALTO

## Objetivo

Implementar sistema de correlation ID para rastrear requisições do webhook até a resposta, facilitando debug em produção.

---

## Problema Atual

- Logs não têm contexto compartilhado entre funções
- Impossível rastrear uma mensagem específica pelos logs
- Debug em produção é demorado e impreciso
- Não há correlação entre logs de diferentes serviços

---

## Solução

Adicionar `trace_id` (UUID) que:
1. É gerado no webhook (entrada)
2. Propaga por todo o pipeline via context var
3. Aparece em todos os logs
4. É salvo nas tabelas de interações

---

## Stories

### S31.E3.1: Criar Módulo de Tracing

**Arquivo:** `app/core/tracing.py`

```python
"""
Tracing Module - Correlation ID para rastreamento.

Sprint 31 - S31.E3.1
"""
import uuid
from contextvars import ContextVar
from typing import Optional

# Context var para propagar trace_id
_trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)


def generate_trace_id() -> str:
    """Gera novo trace ID."""
    return str(uuid.uuid4())[:8]  # 8 chars é suficiente


def set_trace_id(trace_id: str) -> None:
    """Define trace ID para o contexto atual."""
    _trace_id_var.set(trace_id)


def get_trace_id() -> Optional[str]:
    """Retorna trace ID do contexto atual."""
    return _trace_id_var.get()


def clear_trace_id() -> None:
    """Limpa trace ID do contexto."""
    _trace_id_var.set(None)
```

**DoD:**
- [ ] Arquivo criado
- [ ] Context var funcionando
- [ ] Commit: `feat(tracing): cria módulo de correlation ID`

---

### S31.E3.2: Criar Middleware de Tracing

**Arquivo:** `app/api/middleware.py`

```python
"""
Middleware de Tracing.

Sprint 31 - S31.E3.2
"""
import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.tracing import generate_trace_id, set_trace_id, clear_trace_id, get_trace_id

logger = logging.getLogger(__name__)


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware que adiciona trace_id a cada request."""

    async def dispatch(self, request: Request, call_next):
        # Gerar ou usar trace_id do header
        trace_id = request.headers.get("X-Trace-ID") or generate_trace_id()
        set_trace_id(trace_id)

        # Adicionar ao request state
        request.state.trace_id = trace_id

        start_time = time.time()

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            logger.info(
                f"Request completed",
                extra={
                    "trace_id": trace_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": int(duration * 1000),
                }
            )

            # Adicionar trace_id no response header
            response.headers["X-Trace-ID"] = trace_id
            return response

        finally:
            clear_trace_id()
```

**Registrar em `main.py`:**
```python
from app.api.middleware import TracingMiddleware

app.add_middleware(TracingMiddleware)
```

**DoD:**
- [ ] Middleware criado
- [ ] Registrado em main.py
- [ ] Header X-Trace-ID retornado
- [ ] Commit: `feat(tracing): middleware de correlation ID`

---

### S31.E3.3: Atualizar Logging com Trace ID

**Arquivo:** `app/core/logging.py` (ou onde configura logging)

```python
"""
Configuração de Logging com Trace ID.

Sprint 31 - S31.E3.3
"""
import logging
from app.core.tracing import get_trace_id


class TraceIdFilter(logging.Filter):
    """Filter que adiciona trace_id aos logs."""

    def filter(self, record):
        record.trace_id = get_trace_id() or "-"
        return True


# Formato atualizado
LOG_FORMAT = "%(asctime)s [%(trace_id)s] %(levelname)s %(name)s: %(message)s"


def configure_logging():
    """Configura logging com trace_id."""
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.addFilter(TraceIdFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
```

**Exemplo de log após configuração:**
```
2025-01-14 10:30:45 [a1b2c3d4] INFO app.services.agente: Gerando resposta...
2025-01-14 10:30:46 [a1b2c3d4] INFO app.services.llm: Chamando Anthropic...
2025-01-14 10:30:47 [a1b2c3d4] INFO app.services.agente: Resposta gerada
```

**DoD:**
- [ ] Filter criado
- [ ] Formato atualizado com `[%(trace_id)s]`
- [ ] Logs exibem trace_id
- [ ] Commit: `feat(tracing): logging com correlation ID`

---

### S31.E3.4: Propagar Trace ID no Pipeline

**Modificar:** `app/pipeline/processor.py`, `app/services/agente.py`

**Padrão:**
```python
from app.core.tracing import get_trace_id

async def processar_mensagem(mensagem, ...):
    trace_id = get_trace_id()
    logger.info(f"Processando mensagem", extra={"trace_id": trace_id})

    # Passar trace_id para contexto
    contexto["trace_id"] = trace_id

    # Em chamadas assíncronas, propagar
    resultado = await gerar_resposta_julia(
        ...,
        trace_id=trace_id,  # Ou via contexto
    )
```

**DoD:**
- [ ] Pipeline usa get_trace_id()
- [ ] Contexto inclui trace_id
- [ ] Logs do pipeline têm trace_id
- [ ] Commit: `feat(tracing): propaga trace_id no pipeline`

---

### S31.E3.5: Salvar Trace ID nas Interações

**Migração para adicionar coluna:**
```sql
ALTER TABLE interacoes ADD COLUMN IF NOT EXISTS trace_id VARCHAR(10);
CREATE INDEX IF NOT EXISTS idx_interacoes_trace_id ON interacoes(trace_id);
```

**Atualizar código que salva interação:**
```python
await supabase.table("interacoes").insert({
    "conversa_id": conversa_id,
    "tipo": "recebida",
    "conteudo": mensagem,
    "trace_id": get_trace_id(),  # Novo campo
})
```

**DoD:**
- [ ] Coluna trace_id adicionada
- [ ] Índice criado
- [ ] Interações salvam trace_id
- [ ] Commit: `feat(tracing): salva trace_id nas interações`

---

### S31.E3.6: Criar Endpoint de Busca por Trace

**Arquivo:** `app/api/routes/debug.py`

```python
"""
Endpoints de Debug.

Sprint 31 - S31.E3.6
"""
from fastapi import APIRouter, HTTPException

from app.services.supabase import supabase

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/trace/{trace_id}")
async def get_trace(trace_id: str):
    """
    Busca interações por trace_id.

    Útil para debug de problemas específicos.
    """
    if len(trace_id) < 6:
        raise HTTPException(400, "trace_id muito curto")

    response = (
        supabase.table("interacoes")
        .select("*, conversations(cliente_id)")
        .eq("trace_id", trace_id)
        .order("created_at")
        .execute()
    )

    if not response.data:
        raise HTTPException(404, f"Trace {trace_id} não encontrado")

    return {
        "trace_id": trace_id,
        "interacoes": response.data,
        "count": len(response.data),
    }
```

**DoD:**
- [ ] Endpoint GET /debug/trace/{trace_id} criado
- [ ] Retorna interações ordenadas
- [ ] Documentado no OpenAPI
- [ ] Commit: `feat(tracing): endpoint de busca por trace`

---

## Checklist Final

- [ ] **S31.E3.1** - Módulo de tracing criado
- [ ] **S31.E3.2** - Middleware implementado
- [ ] **S31.E3.3** - Logging atualizado
- [ ] **S31.E3.4** - Pipeline propagando trace_id
- [ ] **S31.E3.5** - Interações salvando trace_id
- [ ] **S31.E3.6** - Endpoint de debug criado
- [ ] Logs em produção exibem trace_id

---

## Arquivos Criados/Modificados

| Arquivo | Ação |
|---------|------|
| `app/core/tracing.py` | Criar |
| `app/api/middleware.py` | Criar/Modificar |
| `app/core/logging.py` | Modificar |
| `app/pipeline/processor.py` | Modificar |
| `app/api/routes/debug.py` | Criar |
