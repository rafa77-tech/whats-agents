# Epic 01: Exception Handlers

## Severidade: CRÍTICO

## Objetivo

Registrar os exception handlers já existentes no FastAPI para garantir respostas de erro consistentes em toda a API.

## Problema Atual

Os exception handlers foram criados na Sprint 10 (`app/api/error_handlers.py`) mas **nunca foram registrados** no app FastAPI (`app/main.py`).

### Evidência

```python
# app/api/error_handlers.py - Handlers EXISTEM e estão bem implementados
def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(JuliaException, julia_exception_handler)
    # ...

# app/main.py - MAS não são registrados!
app = FastAPI(...)
# Linha faltante: register_exception_handlers(app)
```

### Impacto

- Erros não tratados retornam stack trace em produção (vazamento de informação)
- Status codes inconsistentes (sempre 500 em vez de 404, 429, etc.)
- Logs de erro não estruturados

---

## Stories

### S30.E1.1: Registrar Exception Handlers

**Objetivo:** Adicionar a chamada `register_exception_handlers(app)` no `main.py`.

**Contexto:** Esta é uma mudança de uma linha, mas extremamente importante para a consistência da API.

**Arquivo:** `app/main.py`

**Tarefas:**

1. Abrir `app/main.py`

2. Adicionar import no topo do arquivo:
   ```python
   from app.api.error_handlers import register_exception_handlers
   ```

3. Após a criação do app, adicionar a chamada:
   ```python
   app = FastAPI(
       title=settings.APP_NAME,
       description="Agente Júlia - Escalista Virtual para Staffing Médico",
       version="0.1.0",
       lifespan=lifespan,
   )

   # Registrar exception handlers ANTES dos middlewares
   register_exception_handlers(app)

   # CORS - configurável via CORS_ORIGINS no .env
   app.add_middleware(
       CORSMiddleware,
       # ...
   )
   ```

4. Verificar que o app inicia sem erros:
   ```bash
   uv run uvicorn app.main:app --reload --port 8000
   ```

**Como Testar:**

```bash
# 1. Iniciar o servidor
uv run uvicorn app.main:app --reload --port 8000

# 2. Em outro terminal, testar endpoint inexistente (deve retornar 404 estruturado)
curl -s http://localhost:8000/nao-existe | jq

# Esperado:
# {
#   "detail": "Not Found"  <- Comportamento padrão FastAPI (OK)
# }

# 3. Testar se handlers customizados funcionam criando um teste
uv run pytest tests/api/test_error_handlers.py -v
```

**DoD:**
- [ ] Import adicionado em `main.py`
- [ ] `register_exception_handlers(app)` chamado após criação do app
- [ ] Servidor inicia sem erros
- [ ] Commit: `fix(api): registra exception handlers no FastAPI`

---

### S30.E1.2: Criar Testes para Exception Handlers

**Objetivo:** Garantir que cada tipo de exception retorna o status code correto.

**Contexto:** Os handlers existem mas não tinham testes. Precisamos garantir que funcionam.

**Arquivo:** `tests/api/test_error_handlers.py` (criar)

**Tarefas:**

1. Criar arquivo de teste:

```python
# tests/api/test_error_handlers.py
"""
Testes para exception handlers do FastAPI.

Sprint 30 - S30.E1.2
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.error_handlers import register_exception_handlers
from app.core.exceptions import (
    DatabaseError,
    ExternalAPIError,
    ValidationError,
    RateLimitError,
    NotFoundError,
    HandoffError,
    ConfigurationError,
)


@pytest.fixture
def app_with_handlers():
    """Cria app FastAPI com handlers registrados."""
    app = FastAPI()
    register_exception_handlers(app)
    return app


@pytest.fixture
def client(app_with_handlers):
    """Cliente de teste."""
    return TestClient(app_with_handlers, raise_server_exceptions=False)


class TestExceptionHandlers:
    """Testes para cada tipo de exception."""

    def test_not_found_error_returns_404(self, app_with_handlers, client):
        """NotFoundError deve retornar 404."""
        @app_with_handlers.get("/test-not-found")
        async def raise_not_found():
            raise NotFoundError("Recurso nao encontrado", details={"id": "123"})

        response = client.get("/test-not-found")

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "NotFoundError"
        assert "Recurso nao encontrado" in data["message"]
        assert data["details"]["id"] == "123"

    def test_validation_error_returns_400(self, app_with_handlers, client):
        """ValidationError deve retornar 400."""
        @app_with_handlers.get("/test-validation")
        async def raise_validation():
            raise ValidationError("Campo invalido", details={"field": "email"})

        response = client.get("/test-validation")

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "ValidationError"

    def test_rate_limit_error_returns_429(self, app_with_handlers, client):
        """RateLimitError deve retornar 429."""
        @app_with_handlers.get("/test-rate-limit")
        async def raise_rate_limit():
            raise RateLimitError("Limite excedido", details={"limit": 100})

        response = client.get("/test-rate-limit")

        assert response.status_code == 429
        data = response.json()
        assert data["error"] == "RateLimitError"

    def test_external_api_error_returns_502(self, app_with_handlers, client):
        """ExternalAPIError deve retornar 502."""
        @app_with_handlers.get("/test-external")
        async def raise_external():
            raise ExternalAPIError("Evolution API falhou", details={"service": "evolution"})

        response = client.get("/test-external")

        assert response.status_code == 502
        data = response.json()
        assert data["error"] == "ExternalAPIError"

    def test_database_error_returns_503(self, app_with_handlers, client):
        """DatabaseError deve retornar 503."""
        @app_with_handlers.get("/test-database")
        async def raise_database():
            raise DatabaseError("Conexao perdida", details={"table": "clientes"})

        response = client.get("/test-database")

        assert response.status_code == 503
        data = response.json()
        assert data["error"] == "DatabaseError"

    def test_configuration_error_returns_500(self, app_with_handlers, client):
        """ConfigurationError deve retornar 500."""
        @app_with_handlers.get("/test-config")
        async def raise_config():
            raise ConfigurationError("API key faltando")

        response = client.get("/test-config")

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "ConfigurationError"

    def test_handoff_error_returns_500(self, app_with_handlers, client):
        """HandoffError deve retornar 500."""
        @app_with_handlers.get("/test-handoff")
        async def raise_handoff():
            raise HandoffError("Falha no handoff")

        response = client.get("/test-handoff")

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "HandoffError"

    def test_generic_exception_returns_500(self, app_with_handlers, client):
        """Exception generica deve retornar 500 sem expor detalhes."""
        @app_with_handlers.get("/test-generic")
        async def raise_generic():
            raise ValueError("Erro interno secreto")

        response = client.get("/test-generic")

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "InternalServerError"
        # NAO deve expor a mensagem interna
        assert "secreto" not in data["message"]
        assert data["message"] == "Erro interno do servidor"


class TestErrorResponseFormat:
    """Testes para formato da resposta de erro."""

    def test_error_response_has_required_fields(self, app_with_handlers, client):
        """Resposta de erro deve ter error, message e details."""
        @app_with_handlers.get("/test-format")
        async def raise_error():
            raise NotFoundError("Teste", details={"key": "value"})

        response = client.get("/test-format")
        data = response.json()

        assert "error" in data
        assert "message" in data
        assert "details" in data

    def test_details_can_be_empty(self, app_with_handlers, client):
        """Details pode ser dict vazio."""
        @app_with_handlers.get("/test-empty-details")
        async def raise_error():
            raise NotFoundError("Teste")  # Sem details

        response = client.get("/test-empty-details")
        data = response.json()

        assert data["details"] == {} or data["details"] is None
```

2. Rodar os testes:
   ```bash
   uv run pytest tests/api/test_error_handlers.py -v
   ```

**Como Testar:**

```bash
# Rodar testes
uv run pytest tests/api/test_error_handlers.py -v

# Verificar cobertura
uv run pytest tests/api/test_error_handlers.py --cov=app/api/error_handlers --cov-report=term-missing
```

**DoD:**
- [ ] Arquivo `tests/api/test_error_handlers.py` criado
- [ ] Teste para cada tipo de exception (8 tipos)
- [ ] Teste para formato de resposta
- [ ] Teste para exception generica (sem vazamento)
- [ ] Todos os testes passando
- [ ] Commit: `test(api): adiciona testes para exception handlers`

---

### S30.E1.3: Verificar em Ambiente de Teste

**Objetivo:** Confirmar que os handlers funcionam em cenarios reais.

**Contexto:** Apos registrar os handlers, precisamos validar que erros reais da API retornam respostas corretas.

**Tarefas:**

1. Identificar endpoints que podem gerar erros:
   - `GET /api/medicos/{id}` → NotFoundError
   - `POST /webhook` com payload invalido → ValidationError

2. Testar manualmente:
   ```bash
   # Testar 404
   curl -s http://localhost:8000/api/medicos/id-inexistente | jq

   # Esperado:
   # {
   #   "error": "NotFoundError",
   #   "message": "Medico nao encontrado",
   #   "details": {"id": "id-inexistente"}
   # }
   ```

3. Verificar logs:
   ```bash
   # Logs devem mostrar erro estruturado
   # [ERROR] NotFoundError: Medico nao encontrado {"error_type": "NotFoundError", ...}
   ```

4. (Opcional) Testar em staging se disponivel

**Como Testar:**

```bash
# 1. Subir servidor local
uv run uvicorn app.main:app --reload --port 8000

# 2. Fazer requests que geram erros
curl -s http://localhost:8000/api/medicos/00000000-0000-0000-0000-000000000000 | jq

# 3. Verificar que resposta eh estruturada (nao stack trace)
```

**DoD:**
- [ ] Handlers funcionando em servidor local
- [ ] Respostas de erro em formato JSON estruturado
- [ ] Sem stack traces expostos
- [ ] Logs de erro estruturados
- [ ] Commit: `docs(sprint-30): valida exception handlers em ambiente local`

---

## Checklist do Epic

- [ ] **S30.E1.1** - Exception handlers registrados em `main.py`
- [ ] **S30.E1.2** - Testes criados e passando
- [ ] **S30.E1.3** - Validado em ambiente local
- [ ] Todos os testes da suite passando (`uv run pytest`)
- [ ] PR criado e aprovado

---

## Arquivos Modificados

| Arquivo | Acao | Linhas |
|---------|------|--------|
| `app/main.py` | Modificar | +2 |
| `tests/api/test_error_handlers.py` | Criar | ~120 |

---

## Tempo Estimado

| Story | Complexidade | Estimativa |
|-------|--------------|------------|
| S30.E1.1 | Baixa | 15 min |
| S30.E1.2 | Baixa | 45 min |
| S30.E1.3 | Baixa | 30 min |
| **Total** | | **~1.5h** |
