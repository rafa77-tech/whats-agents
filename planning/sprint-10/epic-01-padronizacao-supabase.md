# Epic 01: Padronizacao Supabase

## Objetivo

Eliminar redundancia e inconsistencia no acesso ao banco de dados, criando um padrao unico e helpers reutilizaveis.

## Problema Atual

### 1. Dois Padroes Coexistem

```python
# Padrao 1: Import global (maioria dos arquivos)
from app.services.supabase import supabase
result = supabase.table("clientes").select("*").execute()

# Padrao 2: Funcao wrapper (alguns arquivos)
from app.services.supabase import get_supabase
supabase = get_supabase()
result = supabase.table("clientes").select("*").execute()
```

**Arquivos com Padrao 2:** `abertura.py`, `chatwoot.py`, `contexto.py`

### 2. Queries Duplicadas

Mesmo padrao de query repetido em 5+ arquivos:

```python
# Repetido em: handoff.py, campanha.py, relatorio.py, metricas.py
response = supabase.table("interacoes").select("id", count="exact")
    .eq("direcao", "saida")
    .gte("created_at", inicio.isoformat())
    .lte("created_at", fim.isoformat())
    .execute()
```

### 3. Sem Type Safety

Queries retornam `dict` sem validacao, causando erros silenciosos.

---

## Stories

### S10.E1.1: Padronizar Import do Supabase

**Objetivo:** Eliminar `get_supabase()` e usar apenas import direto.

**Contexto:** A funcao `get_supabase()` eh redundante - apenas retorna o singleton `supabase`. Causa confusao sobre qual padrao usar.

**Arquivos a Modificar:**
- `app/services/supabase.py` - Remover/deprecar `get_supabase()`
- `app/services/abertura.py` - Trocar para import direto
- `app/services/chatwoot.py` - Trocar para import direto
- `app/services/contexto.py` - Trocar para import direto

**Tarefas:**

1. Verificar todos os usos de `get_supabase()`:
   ```bash
   grep -r "get_supabase" app/
   ```

2. Em cada arquivo, trocar:
   ```python
   # DE:
   from app.services.supabase import get_supabase
   supabase = get_supabase()

   # PARA:
   from app.services.supabase import supabase
   ```

3. Marcar `get_supabase()` como deprecated:
   ```python
   import warnings

   def get_supabase():
       """DEPRECATED: Use `from app.services.supabase import supabase` diretamente."""
       warnings.warn(
           "get_supabase() is deprecated. Use 'from app.services.supabase import supabase'",
           DeprecationWarning,
           stacklevel=2
       )
       return supabase
   ```

4. Rodar testes para garantir que nada quebrou

**Como Testar:**
```bash
# Verificar se ainda ha usos de get_supabase (deve retornar 0 exceto o proprio arquivo)
grep -r "get_supabase()" app/services/ --include="*.py" | grep -v "supabase.py"

# Rodar testes
uv run pytest tests/ -v
```

**DoD:**
- [ ] Zero chamadas a `get_supabase()` fora de `supabase.py`
- [ ] `get_supabase()` marcada como deprecated com warning
- [ ] Todos os testes passando
- [ ] Commit com mensagem: `refactor(supabase): padroniza import direto do singleton`

---

### S10.E1.2: Criar Helpers de Queries Comuns

**Objetivo:** Centralizar queries repetidas em funcoes reutilizaveis com type hints.

**Contexto:** Queries como "contar interacoes por periodo" estao duplicadas em 5+ arquivos. Mudanca no schema quebra em varios lugares.

**Arquivos a Modificar:**
- `app/services/supabase.py` - Adicionar helpers

**Helpers a Criar:**

```python
# app/services/supabase.py

from datetime import datetime
from typing import Optional

async def contar_interacoes_periodo(
    inicio: datetime,
    fim: datetime,
    direcao: Optional[str] = None,
    medico_id: Optional[str] = None
) -> int:
    """Conta interacoes em um periodo.

    Args:
        inicio: Data/hora inicial
        fim: Data/hora final
        direcao: 'entrada' ou 'saida' (opcional)
        medico_id: Filtrar por medico (opcional)

    Returns:
        Numero de interacoes
    """
    query = supabase.table("interacoes").select("id", count="exact")
    query = query.gte("created_at", inicio.isoformat())
    query = query.lte("created_at", fim.isoformat())

    if direcao:
        query = query.eq("direcao", direcao)
    if medico_id:
        query = query.eq("medico_id", medico_id)

    response = query.execute()
    return response.count or 0


async def buscar_medico_por_telefone(telefone: str) -> Optional[dict]:
    """Busca medico pelo telefone.

    Args:
        telefone: Numero do telefone (com ou sem formatacao)

    Returns:
        Dict com dados do medico ou None
    """
    telefone_limpo = "".join(filter(str.isdigit, telefone))
    response = supabase.table("clientes").select("*").eq("telefone", telefone_limpo).execute()
    return response.data[0] if response.data else None


async def buscar_conversa_ativa(medico_id: str) -> Optional[dict]:
    """Busca conversa ativa de um medico.

    Args:
        medico_id: ID do medico

    Returns:
        Dict com dados da conversa ou None
    """
    response = supabase.table("conversations").select("*").eq("cliente_id", medico_id).eq("status", "ativa").execute()
    return response.data[0] if response.data else None


async def listar_handoffs_pendentes() -> list[dict]:
    """Lista todos os handoffs pendentes de resolucao.

    Returns:
        Lista de handoffs com dados do medico
    """
    response = supabase.table("handoffs").select(
        "*, clientes(nome, telefone)"
    ).eq("status", "pendente").order("created_at", desc=True).execute()
    return response.data or []


async def buscar_vagas_disponiveis(
    especialidade_id: Optional[str] = None,
    regiao: Optional[str] = None,
    limite: int = 10
) -> list[dict]:
    """Busca vagas disponiveis com filtros.

    Args:
        especialidade_id: Filtrar por especialidade
        regiao: Filtrar por regiao
        limite: Maximo de resultados

    Returns:
        Lista de vagas
    """
    query = supabase.table("vagas").select(
        "*, hospitais(nome, endereco), especialidades(nome)"
    ).eq("status", "aberta")

    if especialidade_id:
        query = query.eq("especialidade_id", especialidade_id)
    if regiao:
        query = query.eq("regiao", regiao)

    response = query.limit(limite).execute()
    return response.data or []
```

**Tarefas:**

1. Adicionar helpers em `supabase.py`
2. Criar testes para cada helper
3. Documentar cada funcao com docstring

**Como Testar:**
```bash
# Criar arquivo de teste
uv run pytest tests/test_supabase_helpers.py -v
```

**DoD:**
- [ ] 5 helpers criados em `supabase.py`
- [ ] Cada helper com type hints completos
- [ ] Cada helper com docstring explicativa
- [ ] Testes para cada helper (minimo 2 casos por helper)
- [ ] Commit: `feat(supabase): adiciona helpers de queries comuns`

---

### S10.E1.3: Substituir Queries Duplicadas pelos Helpers

**Objetivo:** Usar os helpers criados no lugar das queries duplicadas.

**Contexto:** Agora que temos helpers centralizados, precisamos substituir as queries duplicadas.

**Arquivos a Modificar:**
- `app/services/handoff.py`
- `app/services/campanha.py`
- `app/services/relatorio.py`
- `app/services/metricas.py`
- `app/services/medico.py`

**Tarefas:**

1. Para cada arquivo, identificar queries que podem usar helpers:
   ```bash
   grep -n "supabase.table" app/services/handoff.py
   ```

2. Substituir pela chamada ao helper:
   ```python
   # DE:
   response = supabase.table("interacoes").select("id", count="exact")
       .eq("direcao", "saida")
       .gte("created_at", inicio.isoformat())
       .lte("created_at", fim.isoformat())
       .execute()
   count = response.count

   # PARA:
   from app.services.supabase import contar_interacoes_periodo
   count = await contar_interacoes_periodo(inicio, fim, direcao="saida")
   ```

3. Rodar testes apos cada arquivo modificado

**Mapeamento de Substituicoes:**

| Arquivo | Query Atual | Helper |
|---------|-------------|--------|
| `handoff.py` | `table("clientes").select().eq("telefone")` | `buscar_medico_por_telefone()` |
| `handoff.py` | `table("handoffs").select().eq("status", "pendente")` | `listar_handoffs_pendentes()` |
| `campanha.py` | `table("interacoes").select(count=)` | `contar_interacoes_periodo()` |
| `relatorio.py` | `table("interacoes").select(count=)` | `contar_interacoes_periodo()` |
| `metricas.py` | `table("interacoes").select(count=)` | `contar_interacoes_periodo()` |
| `medico.py` | `table("clientes").select().eq("telefone")` | `buscar_medico_por_telefone()` |

**Como Testar:**
```bash
# Apos cada arquivo
uv run pytest tests/ -v -k "handoff or campanha or relatorio or metricas or medico"
```

**DoD:**
- [ ] `handoff.py` usando helpers (2 substituicoes)
- [ ] `campanha.py` usando helpers (1 substituicao)
- [ ] `relatorio.py` usando helpers (2 substituicoes)
- [ ] `metricas.py` usando helpers (1 substituicao)
- [ ] `medico.py` usando helpers (1 substituicao)
- [ ] Todos os testes passando
- [ ] Commit: `refactor: substitui queries duplicadas por helpers centralizados`

---

### S10.E1.4: Centralizar Configuracoes de Banco

**Objetivo:** Mover constantes relacionadas ao banco para `core/config.py`.

**Contexto:** Constantes como timeouts, limites de query e nomes de tabelas estao espalhadas nos services.

**Arquivos a Modificar:**
- `app/core/config.py` - Adicionar constantes
- `app/services/supabase.py` - Usar constantes centralizadas

**Constantes a Centralizar:**

```python
# app/core/config.py

class DatabaseConfig:
    """Configuracoes do banco de dados."""

    # Timeouts
    QUERY_TIMEOUT_SECONDS: int = 30
    CONNECTION_TIMEOUT_SECONDS: int = 10

    # Limites
    MAX_RESULTS_DEFAULT: int = 100
    MAX_RESULTS_ABSOLUTE: int = 1000

    # Retry
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: float = 0.5

    # Cache TTL (segundos)
    CACHE_TTL_VAGAS: int = 60
    CACHE_TTL_MEDICOS: int = 300
    CACHE_TTL_HOSPITAIS: int = 3600
```

**Tarefas:**

1. Identificar constantes espalhadas:
   ```bash
   grep -rn "CACHE_TTL\|TIMEOUT\|MAX_" app/services/ --include="*.py"
   ```

2. Adicionar `DatabaseConfig` em `core/config.py`

3. Atualizar imports nos services:
   ```python
   from app.core.config import DatabaseConfig

   # Usar assim:
   query.limit(DatabaseConfig.MAX_RESULTS_DEFAULT)
   ```

4. Remover constantes duplicadas dos services

**Como Testar:**
```bash
# Verificar que nao ha mais constantes hardcoded
grep -rn "= 60\|= 100\|= 30" app/services/ --include="*.py" | grep -i "cache\|timeout\|limit"

# Rodar testes
uv run pytest tests/ -v
```

**DoD:**
- [ ] `DatabaseConfig` criada em `core/config.py`
- [ ] Constantes de banco removidas dos services
- [ ] `supabase.py` usando `DatabaseConfig`
- [ ] Nenhum timeout/limite hardcoded em services
- [ ] Todos os testes passando
- [ ] Commit: `refactor(config): centraliza configuracoes de banco`

---

## Resumo do Epic

| Story | Objetivo | Arquivos | Complexidade |
|-------|----------|----------|--------------|
| S10.E1.1 | Padronizar import | 4 | Baixa |
| S10.E1.2 | Criar helpers | 1 | Media |
| S10.E1.3 | Substituir queries | 5 | Media |
| S10.E1.4 | Centralizar config | 2 | Baixa |

**Ordem de Execucao:** S10.E1.1 -> S10.E1.2 -> S10.E1.3 -> S10.E1.4

**Dependencias:**
- S10.E1.2 depende de S10.E1.1 (padrao unico)
- S10.E1.3 depende de S10.E1.2 (helpers existem)
