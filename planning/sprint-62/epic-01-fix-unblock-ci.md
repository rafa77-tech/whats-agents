# EPIC 01: Fix & Unblock CI

## Contexto

O CI do backend e 100% decorativo — todos os quality gates tem `continue-on-error: true`.
Antes de adicionar testes novos, precisamos que o CI existente funcione.

## Escopo

- **Incluido**: Corrigir 4 testes falhando, 27 erros de lint, 21 arquivos de formatacao, remover `continue-on-error`, ativar coverage
- **Excluido**: Adicionar testes novos (epics 02-06), mudar thresholds (epic 07)

---

## Tarefa 1.1: Corrigir erros de lint auto-fixaveis (F401)

### Objetivo
Remover 21 imports nao utilizados que o ruff pode corrigir automaticamente.

### Arquivos
| Acao | Arquivo |
|------|---------|
| Modificar | `app/api/routes/health.py` (9 F401) |
| Modificar | `app/services/agente/orchestrator.py` (8 F401) |
| Modificar | `app/services/agente/types.py` (1 F401) |
| Modificar | `app/services/outbound/sender.py` (1 F401) |
| Modificar | `app/workers/temperature_decay.py` (1 F401) |

### Implementacao

```bash
uv run ruff check app/ --fix
uv run ruff check app/  # verificar zero F401 restante
```

### Testes Obrigatorios

- [ ] `uv run ruff check app/` retorna 0 erros F401
- [ ] `uv run pytest tests/ -x --no-cov` — nenhum teste quebrou por causa da remocao

### Definition of Done
- [ ] Zero erros F401 no ruff
- [ ] Testes existentes continuam passando

---

## Tarefa 1.2: Corrigir erros F821 (nomes indefinidos)

### Objetivo
Corrigir 6 bugs reais onde variaveis/tipos sao usados antes de serem definidos.

### Arquivos
| Acao | Arquivo | Problema |
|------|---------|----------|
| Modificar | `app/tools/vagas/reservar_plantao.py` | `resultado` usado nas linhas 166, 170, 182 mas so atribuido na 203 |
| Modificar | `app/services/grupos/hospital_web.py` | `InfoCNES` e `InfoGooglePlaces` usados como anotacoes sem import |
| Modificar | `app/services/outbound/finalization.py` | `OutboundContext` usado como anotacao sem import |

### Implementacao

**reservar_plantao.py:** O `resultado` e referenciado em blocos de early-return antes de ser atribuido. Analisar o fluxo e garantir que `resultado` seja inicializado antes dos blocos que o referenciam, ou reestruturar a logica para nao precisar dele nos early-returns.

**hospital_web.py:** Adicionar imports sob `TYPE_CHECKING`:
```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.grupos.hospital_cnes import InfoCNES
    from app.services.grupos.hospital_google_places import InfoGooglePlaces
```

**finalization.py:** Adicionar import sob `TYPE_CHECKING`:
```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.outbound.types import OutboundContext
```

### Testes Obrigatorios

- [ ] `uv run ruff check app/` retorna 0 erros F821
- [ ] `uv run pytest tests/characterization/test_vagas_tools.py -v` — testes de reserva continuam passando
- [ ] Teste manual: verificar que `reservar_plantao` nao levanta `UnboundLocalError` nos caminhos de early-return

### Definition of Done
- [ ] Zero erros F821
- [ ] Nenhum `UnboundLocalError` possivel nos caminhos de execucao

---

## Tarefa 1.3: Formatar codigo com ruff

### Objetivo
Formatar os 21 arquivos pendentes para que `ruff format --check` passe.

### Implementacao

```bash
uv run ruff format app/
uv run ruff format --check app/  # verificar zero erros
```

### Testes Obrigatorios

- [ ] `uv run ruff format --check app/` retorna 0 erros
- [ ] Testes existentes continuam passando

### Definition of Done
- [ ] Formatter check passa limpo

---

## Tarefa 1.4: Corrigir os 4 testes falhando

### Objetivo
Corrigir os 4 testes que falham hoje para que o suite fique verde.

### Arquivos
| Acao | Arquivo | Problema |
|------|---------|----------|
| Modificar | `tests/unit/test_validacao_telefone.py` | 2 testes mocam `httpx.AsyncClient` mas codigo usa `get_http_client()` singleton |
| Modificar | `tests/e2e/test_campaign_context_e2e.py` | Fixture `campanha_discovery` tem `status: "ativa"` mas executor exige `"agendada"` |
| Modificar | `app/services/grupos/hospital_google_places.py` | Cria `httpx.AsyncClient()` efemero, violando teste arquitetural `test_zero_ephemeral_clients` |

### Implementacao

**test_validacao_telefone.py (2 testes):**
```python
# Antes: mocava httpx.AsyncClient
# Depois: mocar get_http_client
@patch("app.services.whatsapp.get_http_client")
async def test_check_number_nao_existe(self, mock_get_client):
    mock_client = AsyncMock()
    mock_get_client.return_value = mock_client
    mock_client.post.return_value = httpx.Response(200, json={"exists": False, ...})
    # ... resto do teste
```

**test_campaign_context_e2e.py (1 teste):**
```python
# Fixture campanha_discovery: mudar status de "ativa" para "agendada"
```

**hospital_google_places.py (1 teste):**
Substituir `async with httpx.AsyncClient(timeout=10.0) as client:` por uso do singleton `get_http_client()`.

### Testes Obrigatorios

- [ ] `uv run pytest tests/unit/test_validacao_telefone.py -v` — 2 testes passando
- [ ] `uv run pytest tests/e2e/test_campaign_context_e2e.py -v` — teste passando
- [ ] `uv run pytest tests/performance/test_baseline.py -v` — teste arquitetural passando
- [ ] `uv run pytest tests/ --no-cov` — suite inteiro verde

### Definition of Done
- [ ] 0 testes falhando
- [ ] Suite completo passa

---

## Tarefa 1.5: Remover `continue-on-error` e ativar coverage no CI

### Objetivo
Tornar o CI blocking — falhas de lint, testes ou coverage impedem o merge.

### Arquivos
| Acao | Arquivo |
|------|---------|
| Modificar | `.github/workflows/ci.yml` |

### Implementacao

```yaml
# Job: lint
- name: Run Ruff linter
  run: uv run ruff check app/
  # REMOVER: continue-on-error: true

- name: Run Ruff formatter check
  run: uv run ruff format --check app/
  # REMOVER: continue-on-error: true

- name: Run mypy type checker
  run: uv run mypy app/ --no-error-summary
  # MANTER continue-on-error por enquanto — mypy tem muitos erros e nao e prioridade desta sprint
  continue-on-error: true

# Job: test
- name: Run tests
  # ...
  run: uv run pytest -v --tb=short
  # REMOVER: --no-cov (para ativar coverage)
  # REMOVER: continue-on-error: true
```

**Nota sobre mypy:** Manter `continue-on-error: true` apenas para mypy. O custo de corrigir type errors e alto e o retorno e baixo comparado com lint e testes. Pode ser enderecado numa sprint futura.

### Testes Obrigatorios

- [ ] Push para branch de teste — CI deve FALHAR se lint falhar
- [ ] Push para branch de teste — CI deve FALHAR se testes falharem
- [ ] Push para branch de teste — CI deve FALHAR se coverage ficar abaixo de 45%
- [ ] Coverage report (`htmlcov/`) deve ser gerado como artefato

### Definition of Done
- [ ] `continue-on-error: true` removido de lint e testes
- [ ] `--no-cov` removido do comando pytest
- [ ] Coverage report sendo gerado e uploadado
- [ ] CI bloqueia merge em caso de falha

---

## Tarefa 1.6: Definir markers pytest (unit, integration, e2e)

### Objetivo
Categorizar testes para permitir execucao seletiva e paralelizacao futura.

### Arquivos
| Acao | Arquivo |
|------|---------|
| Modificar | `pyproject.toml` |
| Criar | `tests/markers.py` (ou em conftest.py) |

### Implementacao

```toml
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "unit: testes unitarios sem dependencia externa",
    "integration: testes que dependem de mocks de servicos externos",
    "e2e: testes end-to-end com fluxo completo",
    "slow: testes que demoram mais de 5s",
    "architectural: testes que validam regras de arquitetura",
]
```

**Nao** marcar todos os testes existentes agora — isso seria um esforco desproporcional. Apenas:
1. Definir os markers no `pyproject.toml`
2. Marcar os testes novos criados nesta sprint
3. Marcar os testes em `tests/performance/` como `architectural`
4. Marcar os testes em `tests/e2e/` como `e2e`

### Definition of Done
- [ ] Markers definidos no pyproject.toml
- [ ] `uv run pytest --markers` lista os markers customizados
- [ ] Testes novos desta sprint usam markers apropriados
