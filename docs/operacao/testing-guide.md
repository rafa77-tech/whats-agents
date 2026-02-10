# Testing Guide - Guia de Testes

Enterprise-grade testing procedures for Agente Julia.

---

## Estrutura de Testes

O projeto possui aproximadamente 2.550 testes organizados em uma hierarquia de 3 níveis.

### Diretórios de Teste

```
tests/
├── conftest.py                      # Fixtures compartilhadas globalmente
├── unit/                            # Testes unitários (~35 arquivos)
│   ├── services/                    # Serviços de negócio
│   │   ├── vagas/                   # Módulo de vagas
│   │   ├── extraction/              # Extração de dados
│   │   └── hospitais/               # Módulo de hospitais
│   └── prompts/                     # Sistema de prompts
├── e2e/                             # Testes end-to-end (4 arquivos)
│   ├── test_discovery_nao_oferta.py
│   ├── test_hospital_bloqueado.py
│   ├── test_modo_piloto.py
│   └── test_oferta_consulta_vagas.py
├── api/                             # Testes de API/routers (6 arquivos)
├── business_events/                 # Testes de eventos de negócio (8 arquivos)
├── grupos/                          # Pipeline de grupos WhatsApp (17 arquivos)
├── tools/                           # Tools do agente (5 arquivos)
│   ├── helena/                      # Agente Helena
│   └── slack/                       # Integração Slack
├── policy/                          # Policy Engine (11 arquivos)
├── persona/                         # Testes de persona Julia (11 arquivos)
├── conhecimento/                    # Sistema de conhecimento/RAG (5 arquivos)
├── comportamento/                   # Testes comportamentais (3 arquivos)
├── core/                            # Testes de infraestrutura (5 arquivos)
├── memoria/                         # Sistema de memória (1 arquivo)
├── optout/                          # Detecção de opt-out (4 arquivos)
├── resiliencia/                     # Circuit breaker, rate limiter (4 arquivos)
├── repositories/                    # Camada de dados (3 arquivos)
├── services/                        # Serviços gerais (15 arquivos)
├── vagas/                           # Vagas (legacy) (4 arquivos)
└── (root level)                     # Testes de integração (~18 arquivos)
```

### Categorização por Tipo

| Categoria | Diretório | Propósito | Qtd Estimada |
|-----------|-----------|-----------|--------------|
| Unitários | unit/ | Lógica isolada, mocks extensivos | ~800 |
| Integração | (root), services/, tools/ | Módulos integrados, DB mockado | ~1200 |
| E2E | e2e/ | Fluxos completos, persona real | ~50 |
| Funcionalidades | business_events/, grupos/, policy/ | Features específicas | ~500 |

---

## Shared Fixtures (conftest.py)

O arquivo `/tests/conftest.py` contém fixtures globais disponíveis para todos os testes.

### Mock Factories

Funções para criar mocks configuráveis:

```python
# Mock do Supabase com chain de métodos
mock = criar_mock_supabase([{"id": "123", "nome": "Teste"}])
resultado = mock.table("clientes").select("*").execute().data

# Mock do Redis
mock_redis = criar_mock_redis()
await mock_redis.get("key")

# Mock de HTTP response
mock_response = criar_mock_http_response(
    status_code=200,
    json_data={"ok": True}
)
```

### Fixtures de Mocks (Serviços Externos)

Disponíveis automaticamente via dependency injection do pytest:

```python
def test_algo(mock_supabase):
    # mock_supabase já está configurado
    mock_supabase.table.return_value.select.return_value.execute.return_value.data = [...]

def test_redis(mock_redis):
    # mock_redis já mockado
    mock_redis.get.return_value = "valor"

def test_evolution(mock_evolution_api):
    # Evolution API mockada
    await enviar_mensagem(...)
    mock_evolution_api.assert_called_once()

def test_slack(mock_slack):
    # Slack mockado
    await notificar_gestor(...)
    mock_slack.assert_called()

def test_llm(mock_llm):
    # LLM simples (texto)
    mock_llm.return_value = "Resposta mockada"

def test_http(mock_httpx_client):
    # httpx.AsyncClient mockado
    mock_httpx_client.post.return_value = criar_mock_http_response(200, {"ok": True})
```

### Fixtures de Dados (Entidades do Domínio)

```python
def test_conversa(medico_data, hospital_data, vaga_data, conversa_data):
    # Dados prontos para uso:
    # - medico_data: dict com id, telefone, especialidade, etc
    # - hospital_data: dict com id, nome, cidade, etc
    # - vaga_data: dict com id, hospital_id, especialidade, etc
    # - conversa_data: dict com id, cliente_id, status, etc

def test_campanha(campanha_discovery_data, campanha_oferta_data):
    # - campanha_discovery_data: tipo discovery, pode_ofertar=False
    # - campanha_oferta_data: tipo oferta, pode_ofertar=True
```

### Fixtures Utilitárias

```python
def test_ids(random_uuid, random_telefone):
    # random_uuid: gera UUID único
    # random_telefone: formato brasileiro 55XXYYYYYYYY

def test_tempo(freeze_time):
    # Congela tempo em momento específico
    with freeze_time(datetime(2024, 1, 15, 10, 0)):
        # Código que usa datetime.now()
```

---

## Executar Testes

### Todos os Testes

```bash
# Rodar todos
uv run pytest

# Com output verboso
uv run pytest -v

# Com detalhes de falhas
uv run pytest -vv

# Parallel execution (mais rápido)
uv run pytest -n auto
```

### Módulo Específico

```bash
# Arquivo específico
uv run pytest tests/test_optout.py

# Diretório específico
uv run pytest tests/unit/

# Teste específico
uv run pytest tests/test_optout.py::test_detectar_optout_explicito

# Padrão de nome
uv run pytest -k "test_optout"
```

### Ignorar Diretórios

```bash
# Ignorar pasta inteira
uv run pytest tests/ --ignore=tests/optout/

# Múltiplas exclusões
uv run pytest tests/ --ignore=tests/e2e/ --ignore=tests/manual/
```

### Filtros Avançados

```bash
# Apenas testes que falharam na última execução
uv run pytest --lf

# Apenas testes que falharam, depois os outros
uv run pytest --ff

# Parar no primeiro erro
uv run pytest -x

# Parar após N falhas
uv run pytest --maxfail=3

# Rodar testes marcados (markers)
uv run pytest -m "integration"
uv run pytest -m "not slow"
```

---

## Coverage (Cobertura de Código)

### Configuração Atual

Definida em `pyproject.toml`:

```toml
[tool.pytest.ini_options]
addopts = [
    "--cov=app",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-fail-under=45",
]

[tool.coverage.run]
source = ["app"]
omit = [
    "app/__init__.py",
    "app/main.py",
    "*/tests/*",
    "*/__pycache__/*",
]
branch = true

[tool.coverage.report]
fail_under = 45
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "@abstractmethod",
]
```

### Rodar com Cobertura

```bash
# Gerar relatório de cobertura
uv run pytest --cov=app --cov-report=term-missing

# Gerar HTML detalhado
uv run pytest --cov=app --cov-report=html
# Abrir: open htmlcov/index.html

# Apenas mostrar % geral
uv run pytest --cov=app --cov-report=term

# Falhar se cobertura < 45%
uv run pytest --cov=app --cov-fail-under=45
```

### Interpretar Relatório

```bash
Name                              Stmts   Miss  Cover   Missing
---------------------------------------------------------------
app/services/agente.py              120     15    87%   45-48, 103-108
app/services/rate_limiter.py         45      2    96%   67-68
app/tools/buscar_vagas.py            80     40    50%   15-25, 34-56
---------------------------------------------------------------
TOTAL                              2450    340    86%
```

- **Stmts**: Total de statements (linhas executáveis)
- **Miss**: Statements não cobertos
- **Cover**: Percentual de cobertura
- **Missing**: Linhas específicas não cobertas

### Targets de Cobertura por Risco

Baseado em `test-architect` skill:

| Módulo | Risk Level | Target Coverage | Rationale |
|--------|------------|-----------------|-----------|
| app/services/llm.py | CRITICAL | 90%+ | Integração com Claude, custo alto |
| app/services/rate_limiter.py | CRITICAL | 90%+ | Evitar ban WhatsApp |
| app/tools/ | HIGH | 80%+ | Ações autônomas (ofertar, reservar) |
| app/pipeline/ | HIGH | 80%+ | Processamento de mensagens |
| app/services/vagas/ | MEDIUM | 70%+ | Lógica de negócio |
| app/api/routes/ | MEDIUM | 70%+ | Endpoints HTTP |
| app/core/ | LOW | 50%+ | Config, logging, utils |

**Regra geral**: Quanto maior o risco de danos (financeiro, reputacional, operacional), maior a cobertura.

---

## Adicionar Testes para Novo Módulo

### Passo a Passo

**1. Identificar categoria do módulo**

```python
# Se for serviço isolado → tests/unit/services/
# Se for integração de módulos → tests/services/
# Se for feature completa → tests/[nome_feature]/
# Se for endpoint → tests/api/
```

**2. Criar arquivo de teste**

```bash
# Padrão: test_[nome_modulo].py
touch tests/unit/services/test_novo_servico.py
```

**3. Usar fixtures do conftest.py**

```python
"""Testes para novo_servico."""

import pytest
from app.services.novo_servico import processar_dados


def test_processar_dados_sucesso(mock_supabase):
    """Testa processamento com dados válidos."""
    # Arrange
    mock_supabase.table.return_value.select.return_value.execute.return_value.data = [
        {"id": "123", "status": "ativo"}
    ]

    # Act
    resultado = processar_dados("123")

    # Assert
    assert resultado["status"] == "ativo"
    mock_supabase.table.assert_called_once_with("tabela")


def test_processar_dados_erro(mock_supabase):
    """Testa tratamento de erro."""
    # Arrange
    mock_supabase.table.return_value.select.return_value.execute.side_effect = Exception("DB Error")

    # Act & Assert
    with pytest.raises(Exception, match="DB Error"):
        processar_dados("123")
```

**4. Se precisar de fixtures específicas do módulo**

Criar `conftest.py` local no mesmo diretório:

```python
# tests/unit/services/conftest.py
import pytest

@pytest.fixture
def dados_especificos():
    """Fixture local disponível apenas para testes em services/."""
    return {"campo": "valor"}
```

**5. Rodar e verificar cobertura**

```bash
# Rodar apenas esse módulo
uv run pytest tests/unit/services/test_novo_servico.py -v

# Com cobertura
uv run pytest tests/unit/services/test_novo_servico.py --cov=app.services.novo_servico --cov-report=term-missing
```

### Template Básico

```python
"""
Testes para [nome_do_modulo].

Coverage target: [60% / 70% / 80% / 90%] based on risk level.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.[modulo] import [funcao_principal]


class TestFuncaoPrincipal:
    """Suite de testes para funcao_principal."""

    async def test_sucesso_caso_basico(self, mock_supabase):
        """Testa caso básico de sucesso."""
        # Arrange
        mock_supabase.table.return_value.select.return_value.execute.return_value.data = [
            {"id": "123"}
        ]

        # Act
        resultado = await funcao_principal("input")

        # Assert
        assert resultado is not None
        assert resultado["id"] == "123"

    async def test_erro_validacao(self):
        """Testa erro de validação com input inválido."""
        with pytest.raises(ValueError, match="Input inválido"):
            await funcao_principal(None)

    async def test_erro_banco(self, mock_supabase):
        """Testa tratamento de erro do banco."""
        mock_supabase.table.return_value.select.side_effect = Exception("DB error")

        with pytest.raises(Exception):
            await funcao_principal("123")


# Testes parametrizados para múltiplos cenários
@pytest.mark.parametrize("input,esperado", [
    ("caso1", "resultado1"),
    ("caso2", "resultado2"),
    ("caso3", "resultado3"),
])
async def test_multiplos_casos(input, esperado):
    """Testa múltiplos casos em um único teste."""
    resultado = await funcao_principal(input)
    assert resultado == esperado
```

---

## Convenções de Nomenclatura

### Arquivos

```bash
# Arquivo de teste
test_[nome_modulo].py

# Arquivo de fixtures locais
conftest.py
```

### Classes de Teste

```python
# Agrupar testes relacionados
class TestNomeFuncao:
    """Suite de testes para nome_funcao."""

    def test_sucesso(self):
        pass

    def test_erro(self):
        pass

# Testes de comportamento específico
class TestValidacaoEntrada:
    """Testes de validação de entrada."""
    pass
```

### Funções de Teste

Padrão: `test_[acao]_[cenario]`

```python
# Testes de sucesso
def test_criar_usuario_sucesso():
    pass

def test_atualizar_status_sucesso():
    pass

# Testes de erro
def test_criar_usuario_email_invalido():
    pass

def test_atualizar_status_nao_encontrado():
    pass

# Testes de edge cases
def test_criar_usuario_email_duplicado():
    pass

def test_atualizar_status_transicao_invalida():
    pass
```

### Docstrings

```python
def test_processar_mensagem_com_optout():
    """
    Testa que mensagem com opt-out é detectada e não processada.

    Cenário:
    - Médico envia "SAIR" ou "CANCELAR"
    - Sistema detecta opt-out
    - Conversa marcada como encerrada
    - Nenhuma resposta é enviada
    """
    pass
```

---

## Testes Assíncronos

O projeto usa `pytest-asyncio` com configuração automática.

### Configuração (pyproject.toml)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

### Escrever Teste Async

```python
import pytest

# Teste async simples
async def test_funcao_async():
    resultado = await funcao_async()
    assert resultado is not None

# Com fixture async
@pytest.fixture
async def recurso_async():
    # Setup
    recurso = await criar_recurso()
    yield recurso
    # Teardown
    await limpar_recurso(recurso)

async def test_com_fixture(recurso_async):
    resultado = await processar(recurso_async)
    assert resultado
```

### Mockar Funções Async

```python
from unittest.mock import AsyncMock, patch

async def test_chamar_api_externa():
    with patch("app.services.api.chamar_api") as mock_api:
        # Configurar mock async
        mock_api.return_value = {"status": "ok"}

        resultado = await processar_com_api()

        assert resultado["status"] == "ok"
        mock_api.assert_called_once()

# AsyncMock diretamente
async def test_com_async_mock():
    mock = AsyncMock(return_value="valor")
    resultado = await mock()
    assert resultado == "valor"
```

---

## CI/CD - Pipeline de Testes

### GitHub Actions (se existir)

Estrutura típica em `.github/workflows/test.yml`:

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v1
      - run: uv sync
      - run: uv run pytest --cov=app --cov-fail-under=45
      - run: uv run pytest tests/e2e/ -v
```

### Comandos CI

```bash
# O que o CI roda (ordem):
1. uv sync                              # Instalar deps
2. uv run pytest --cov-fail-under=45    # Testes + coverage
3. uv run pytest tests/e2e/ -v          # E2E separado
4. (opcional) ruff check .              # Linting
5. (opcional) mypy app/                 # Type checking
```

### Verificar Antes de Commit

```bash
# Quick check (1-2 min)
uv run pytest -x --lf

# Full check (5-10 min)
uv run pytest --cov=app --cov-fail-under=45

# Lint + Type check
uv run ruff check .
uv run mypy app/
```

---

## Debugging Testes

### Rodar com Output Detalhado

```bash
# Mostrar print statements
uv run pytest -s

# Verbose + print
uv run pytest -vv -s

# Com traceback completo
uv run pytest --tb=long

# Com locals no traceback
uv run pytest --tb=auto --showlocals
```

### Usar pdb (Debugger)

```python
def test_debug():
    resultado = processar()

    # Inserir breakpoint
    import pdb; pdb.set_trace()

    assert resultado
```

```bash
# Rodar com pdb automático em falhas
uv run pytest --pdb

# Parar no primeiro erro e abrir pdb
uv run pytest -x --pdb
```

### pytest-watch (Auto-reload)

```bash
# Instalar
uv add --dev pytest-watch

# Rodar (reroda testes quando arquivo muda)
uv run ptw tests/
```

---

## Boas Práticas

### 1. Arrange-Act-Assert Pattern

```python
def test_exemplo():
    # Arrange: Configurar dados e mocks
    input_data = {"campo": "valor"}
    mock.return_value = "esperado"

    # Act: Executar ação
    resultado = funcao(input_data)

    # Assert: Verificar resultado
    assert resultado == "esperado"
    mock.assert_called_once()
```

### 2. Testar Comportamento, Não Implementação

```python
# Ruim: testa implementação interna
def test_ruim():
    obj = MinhaClasse()
    assert obj._variavel_privada == "valor"

# Bom: testa comportamento público
def test_bom():
    obj = MinhaClasse()
    resultado = obj.processar()
    assert resultado == "esperado"
```

### 3. Testes Isolados (Sem Side Effects)

```python
# Cada teste deve ser independente
def test_1():
    # Não depende de test_2
    pass

def test_2():
    # Não depende de test_1
    pass
```

### 4. Nomes Descritivos

```python
# Ruim
def test_1():
    pass

# Bom
def test_criar_usuario_com_email_duplicado_retorna_erro():
    pass
```

### 5. Mockar Dependências Externas

```python
# Sempre mockar:
# - Banco de dados (Supabase)
# - APIs externas (Evolution, Chatwoot, Slack)
# - LLM (Claude)
# - Redis
# - Sistema de arquivos
# - Rede

# NUNCA testar contra produção em testes
```

### 6. Usar Fixtures para Setup Comum

```python
# Em vez de repetir setup em cada teste
@pytest.fixture
def usuario_valido():
    return {"nome": "Teste", "email": "test@example.com"}

def test_1(usuario_valido):
    # Usa fixture
    pass

def test_2(usuario_valido):
    # Reutiliza mesmo setup
    pass
```

---

## Troubleshooting

### Testes Lentos

```bash
# Identificar testes lentos
uv run pytest --durations=10

# Rodar apenas testes rápidos
uv run pytest -m "not slow"

# Usar paralelização
uv run pytest -n auto
```

### Import Errors

```bash
# Verificar PYTHONPATH
echo $PYTHONPATH

# Adicionar diretório raiz
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Ou usar pytest com pythonpath
uv run pytest --pythonpath=.
```

### Fixture Not Found

```python
# Erro: fixture 'mock_supabase' not found

# Verificar:
# 1. conftest.py existe em tests/
# 2. Fixture está definida com @pytest.fixture
# 3. Nome da fixture está correto (typo?)
# 4. Escopo da fixture permite uso
```

### Async Warnings

```bash
# Warning: coroutine was never awaited

# Solução: adicionar async/await
async def test_meu_teste():
    resultado = await funcao_async()  # Não esquecer await
```

---

## Referências Rápidas

### Comandos Mais Usados

```bash
# Desenvolvimento diário
uv run pytest -x --lf                    # Roda últimos falhos, para no erro
uv run pytest tests/unit/ -v             # Testes unitários verbose
uv run pytest -k "test_nome" -v          # Teste específico

# Pre-commit
uv run pytest --cov=app --cov-fail-under=45

# Debug
uv run pytest -vv -s --pdb               # Verbose + output + debugger

# CI/CD
uv run pytest --cov=app --cov-report=term-missing --cov-fail-under=45
```

### Markers Úteis

```python
# Definir markers customizados em pyproject.toml
[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow",
    "integration: marks integration tests",
    "e2e: marks end-to-end tests",
]

# Usar em testes
@pytest.mark.slow
def test_lento():
    pass

@pytest.mark.integration
def test_integracao():
    pass

# Rodar apenas marcados
uv run pytest -m "integration"
uv run pytest -m "not slow"
```

---

**Última atualização:** 2026-02-10
**Responsável:** Engineering Team
**Revisão:** Trimestral
