# Epic 06: Cleanup e Ajustes Menores

## Severidade: P2 - BAIXO

## Objetivo

Limpar pequenos débitos técnicos identificados na análise arquitetural.

---

## Stories

### S31.E6.1: Remover Duplicação no Loop de Tools

**Arquivo:** `app/services/agente.py`

**Problema:** O loop de processamento de tool calls está duplicado (linhas 351-396 e 462-506).

**Solução:** Já resolvido pelo Epic 02 (ToolExecutor.execute_tool_loop).

**Se Epic 02 não foi feito:**
```python
# Extrair para função auxiliar
async def _processar_loop_tools(
    resultado: Dict,
    historico: List[Dict],
    system_prompt: str,
    tools: List[Dict],
    medico: Dict,
    conversa: Dict,
    max_iterations: int = 3,
) -> str:
    """Loop unificado de processamento de tools."""
    # Implementação única
    ...
```

**DoD:**
- [ ] Loop duplicado removido OU confirmado que Epic 02 resolveu
- [ ] Testes passando
- [ ] Commit: `refactor(agente): remove duplicação de loop de tools`

---

### S31.E6.2: Extrair Constantes Hardcoded

**Arquivos:** Múltiplos

**Problema:** Valores hardcoded espalhados pelo código:
- `max_tokens=300` em vários lugares
- `max_tool_iterations=3`
- Timeouts, limites, etc.

**Solução:** Criar arquivo de constantes ou usar settings:

**Arquivo:** `app/core/constants.py`
```python
"""
Constantes do sistema.

Sprint 31 - S31.E6.2
"""

# LLM
DEFAULT_MAX_TOKENS = 300
DEFAULT_MAX_TOKENS_SHORT = 150
DEFAULT_TEMPERATURE = 0.7

# Tool Execution
MAX_TOOL_ITERATIONS = 3
TOOL_TIMEOUT_SECONDS = 30

# Response Detection
MIN_RESPONSE_LENGTH = 20
INCOMPLETE_RESPONSE_PATTERNS = [
    r"vou\s+verificar",
    r"deixa\s+eu\s+ver",
    # ... movidos de response_handler.py
]

# Rate Limiting
MESSAGES_PER_HOUR = 20
MESSAGES_PER_DAY = 100
MIN_INTERVAL_SECONDS = 45
MAX_INTERVAL_SECONDS = 180
```

**Atualizar código para usar constantes:**
```python
from app.core.constants import DEFAULT_MAX_TOKENS, MAX_TOOL_ITERATIONS

resultado = await chamar_llm(
    ...,
    max_tokens=DEFAULT_MAX_TOKENS,  # Em vez de 300
)
```

**DoD:**
- [ ] `app/core/constants.py` criado
- [ ] Pelo menos 5 constantes extraídas
- [ ] Código atualizado para usar constantes
- [ ] Commit: `refactor(core): extrai constantes hardcoded`

---

### S31.E6.3: Adicionar Type Hints Faltantes

**Arquivos:** Funções principais sem type hints completos

**Tarefa:** Adicionar type hints onde faltam:

```python
# ANTES
async def processar_mensagem(payload, instance_name):
    ...

# DEPOIS
from typing import Dict, Any, Optional

async def processar_mensagem(
    payload: Dict[str, Any],
    instance_name: str,
) -> Optional[str]:
    ...
```

**Priorizar:**
1. Funções públicas em `app/services/`
2. Handlers de tools em `app/tools/`
3. Endpoints em `app/api/routes/`

**DoD:**
- [ ] Type hints adicionados em pelo menos 10 funções
- [ ] Mypy não reporta erros novos
- [ ] Commit: `refactor: adiciona type hints faltantes`

---

### S31.E6.4: Atualizar Docstrings Desatualizadas

**Tarefa:** Revisar e atualizar docstrings que mencionam comportamentos antigos.

**Buscar:**
```bash
# Docstrings que mencionam sprints antigas
grep -rn "Sprint [0-9]" app/ --include="*.py" | head -20

# Docstrings com TODO
grep -rn "TODO\|FIXME\|HACK" app/ --include="*.py"
```

**Atualizar:**
- Remover referências a sprints muito antigas (< 20)
- Atualizar descrições que não refletem mais o código
- Resolver ou remover TODOs obsoletos

**DoD:**
- [ ] Docstrings revisadas
- [ ] TODOs obsoletos removidos
- [ ] Commit: `docs: atualiza docstrings desatualizadas`

---

### S31.E6.5: Rodar Linter e Corrigir Warnings

**Tarefa:** Rodar ferramentas de linting e corrigir warnings.

**Comandos:**
```bash
# Ruff (linter rápido)
uv run ruff check app/ --fix

# Mypy (type checking)
uv run mypy app/ --ignore-missing-imports

# Bandit (security)
uv run bandit -r app/ -ll
```

**Categorias a corrigir:**
1. **Imports não usados** - Remover
2. **Variáveis não usadas** - Remover ou usar `_`
3. **Linhas muito longas** - Quebrar
4. **Imports fora de ordem** - Reordenar

**DoD:**
- [ ] `ruff check` sem erros
- [ ] Warnings de segurança críticos resolvidos
- [ ] Commit: `refactor: corrige warnings do linter`

---

## Checklist Final

- [ ] **S31.E6.1** - Duplicação removida
- [ ] **S31.E6.2** - Constantes extraídas
- [ ] **S31.E6.3** - Type hints adicionados
- [ ] **S31.E6.4** - Docstrings atualizadas
- [ ] **S31.E6.5** - Warnings corrigidos

---

## Nota

Este épico pode ser feito incrementalmente. Cada story é independente e pode ser commitada separadamente. Priorize S31.E6.2 (constantes) se o tempo for limitado, pois facilita manutenção futura.
