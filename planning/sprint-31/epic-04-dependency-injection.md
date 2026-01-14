# Epic 04: Dependency Injection Completo

## Severidade: P1 - ALTO

## Objetivo

Substituir singletons globais por dependency injection via FastAPI Depends, melhorando testabilidade e configurabilidade.

---

## Problema Atual

Múltiplos singletons globais dificultam testes:

```python
# app/services/llm.py
client = get_anthropic_client()  # Singleton global

# app/services/supabase.py
supabase = get_supabase_client()  # Singleton global

# app/services/conversation_mode/router.py
_router: Optional[ModeRouter] = None  # Singleton manual
```

### Impacto

- Testes precisam de `@patch` no nível de import
- Impossível rodar testes em paralelo com configs diferentes
- Dependências são ocultas (não declaradas nos parâmetros)

---

## Solução

Usar FastAPI `Depends` para injeção:

```python
# ANTES
from app.services.llm import client

async def minha_funcao():
    return client.messages.create(...)

# DEPOIS
from app.services.llm import LLMProvider

async def minha_funcao(provider: LLMProvider = Depends(get_llm_provider)):
    return await provider.generate(...)
```

---

## Stories

### S31.E4.1: Criar Factory get_llm_provider

**Depende de:** Epic 01 (LLM Provider Abstraction)

**Arquivo:** Já criado em `app/services/llm/factory.py`

```python
from fastapi import Depends

def get_llm_provider() -> LLMProvider:
    """Factory para DI do LLM Provider."""
    return AnthropicProvider()
```

**Uso em endpoints:**
```python
@router.post("/chat")
async def chat(
    message: str,
    provider: LLMProvider = Depends(get_llm_provider)
):
    ...
```

**DoD:**
- [ ] Factory existe e funciona
- [ ] Pode ser usado com Depends
- [ ] Commit: `feat(di): factory get_llm_provider`

---

### S31.E4.2: Criar Factory get_mode_router

**Arquivo:** `app/services/conversation_mode/factory.py`

```python
"""
Factory para ModeRouter.

Sprint 31 - S31.E4.2
"""
from typing import Optional
from .router import ModeRouter


_router_instance: Optional[ModeRouter] = None


def get_mode_router() -> ModeRouter:
    """
    Retorna instância do ModeRouter.

    Usa lazy initialization para evitar import circular.
    """
    global _router_instance
    if _router_instance is None:
        _router_instance = ModeRouter()
    return _router_instance


def reset_mode_router() -> None:
    """Reset para testes."""
    global _router_instance
    _router_instance = None
```

**Atualizar `router.py`:**
```python
# Remover singleton global
# _router = None  # REMOVER

# No final, re-exportar factory
from .factory import get_mode_router
```

**DoD:**
- [ ] Factory criada
- [ ] Singleton removido de router.py
- [ ] reset_mode_router() para testes
- [ ] Commit: `feat(di): factory get_mode_router`

---

### S31.E4.3: Criar Factory get_redis_client

**Arquivo:** `app/services/redis/factory.py`

```python
"""
Factory para Redis Client.

Sprint 31 - S31.E4.3
"""
from typing import Optional
import redis.asyncio as redis

from app.core.config import settings


_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """
    Retorna cliente Redis.

    Usa lazy initialization.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis_client() -> None:
    """Fecha conexão (para shutdown)."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
```

**DoD:**
- [ ] Factory criada
- [ ] Função de close para shutdown
- [ ] Commit: `feat(di): factory get_redis_client`

---

### S31.E4.4: Migrar Webhook para usar DI

**Arquivo:** `app/api/routes/webhook.py`

**ANTES:**
```python
from app.services.agente import gerar_resposta_julia
from app.services.conversation_mode.router import get_mode_router

@router.post("/evolution")
async def evolution_webhook(payload: dict):
    router = get_mode_router()
    ...
```

**DEPOIS:**
```python
from fastapi import Depends
from app.services.julia import gerar_resposta_julia
from app.services.conversation_mode.factory import get_mode_router
from app.services.llm import LLMProvider, get_llm_provider

@router.post("/evolution")
async def evolution_webhook(
    payload: dict,
    mode_router: ModeRouter = Depends(get_mode_router),
    llm_provider: LLMProvider = Depends(get_llm_provider),
):
    ...
```

**DoD:**
- [ ] Webhook usa Depends para ModeRouter
- [ ] Webhook usa Depends para LLMProvider (se aplicável)
- [ ] Testes do webhook atualizados
- [ ] Commit: `refactor(webhook): migra para DI`

---

### S31.E4.5: Migrar Pipeline para receber Deps

**Arquivo:** `app/pipeline/processor.py`

**Estratégia:** Pipeline recebe dependencies via construtor:

```python
class MessageProcessor:
    def __init__(
        self,
        cliente_repo: ClienteRepository = None,
        conversa_repo: ConversaRepository = None,
        llm_provider: LLMProvider = None,
    ):
        self._cliente_repo = cliente_repo or get_cliente_repo()
        self._conversa_repo = conversa_repo or get_conversa_repo()
        self._llm_provider = llm_provider or get_llm_provider()

    async def process(self, context):
        # Usar self._cliente_repo em vez de import global
        ...
```

**Factory para pipeline:**
```python
def get_message_processor(
    cliente_repo: ClienteRepository = Depends(get_cliente_repo),
    conversa_repo: ConversaRepository = Depends(get_conversa_repo),
) -> MessageProcessor:
    return MessageProcessor(
        cliente_repo=cliente_repo,
        conversa_repo=conversa_repo,
    )
```

**DoD:**
- [ ] MessageProcessor aceita deps no construtor
- [ ] Factory get_message_processor criada
- [ ] Testes podem injetar mocks
- [ ] Commit: `refactor(pipeline): aceita dependencies injetadas`

---

### S31.E4.6: Documentar Padrão de DI

**Arquivo:** `docs/arquitetura/dependency-injection.md`

Conteúdo:
1. Por que usamos DI
2. Como criar factories
3. Como usar em endpoints
4. Como mockar em testes
5. Lista de factories disponíveis

**DoD:**
- [ ] Documento criado
- [ ] Exemplos de código incluídos
- [ ] Commit: `docs(di): documenta padrão de dependency injection`

---

## Checklist Final

- [ ] **S31.E4.1** - get_llm_provider funcionando
- [ ] **S31.E4.2** - get_mode_router funcionando
- [ ] **S31.E4.3** - get_redis_client funcionando
- [ ] **S31.E4.4** - Webhook migrado
- [ ] **S31.E4.5** - Pipeline migrado
- [ ] **S31.E4.6** - Documentação criada
- [ ] Testes podem injetar mocks via Depends override

---

## Exemplo de Teste com DI

```python
from fastapi.testclient import TestClient
from app.main import app
from app.services.llm import get_llm_provider, MockLLMProvider

def test_webhook_com_mock():
    """Teste usando DI override."""

    # Criar mock
    mock_provider = MockLLMProvider(default_response="Resposta mock")

    # Override
    app.dependency_overrides[get_llm_provider] = lambda: mock_provider

    try:
        client = TestClient(app)
        response = client.post("/webhook/evolution", json={...})
        assert response.status_code == 200
    finally:
        # Limpar override
        app.dependency_overrides.clear()
```

---

## Arquivos Criados/Modificados

| Arquivo | Ação |
|---------|------|
| `app/services/llm/factory.py` | Já existe (Epic 01) |
| `app/services/conversation_mode/factory.py` | Criar |
| `app/services/redis/factory.py` | Criar |
| `app/api/routes/webhook.py` | Modificar |
| `app/pipeline/processor.py` | Modificar |
| `docs/arquitetura/dependency-injection.md` | Criar |
