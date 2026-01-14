# Epic 02: Consolidacao de Queries Duplicadas

## Severidade: CRITICO

## Objetivo

Eliminar queries duplicadas no codebase, estabelecendo uma unica fonte de verdade para cada operacao de banco de dados.

## Problema Atual

### Queries Duplicadas Identificadas

#### 1. `buscar_conversa_ativa` (3 lugares!)

| Arquivo | Linha | Usado por |
|---------|-------|-----------|
| `app/services/conversa.py` | 13 | conversa.py internamente |
| `app/services/supabase.py` | 274 | Wrapper deprecated |
| `app/database.py` | 56 | Apenas `app/agent.py` (legado) |

#### 2. `buscar_ou_criar_medico` (3 lugares!)

| Arquivo | Linha | Usado por |
|---------|-------|-----------|
| `app/services/medico.py` | 95 | `pipeline/pre_processors.py` |
| `app/services/supabase.py` | 419 | Wrapper |
| `app/database.py` | 41 | Apenas `app/agent.py` (legado) |

### Impacto

- **Inconsistencia:** Cada implementacao pode ter comportamento ligeiramente diferente
- **Manutencao:** Mudancas no schema requerem atualizacao em multiplos lugares
- **Bugs silenciosos:** Uma versao pode ter fix que outra nao tem

---

## Stories

### S30.E2.1: Auditar Todas as Queries Duplicadas

**Objetivo:** Mapear completamente quais funcoes estao duplicadas e quem as consome.

**Contexto:** Antes de consolidar, precisamos saber exatamente o que existe e quem usa.

**Tarefas:**

1. Executar busca por funcoes de banco duplicadas:
   ```bash
   # Buscar funcoes que comecam com buscar_, listar_, criar_
   grep -rn "^async def buscar_\|^async def listar_\|^async def criar_" app/services/*.py app/database.py | sort
   ```

2. Para cada funcao encontrada, verificar quem a importa:
   ```bash
   # Exemplo para buscar_conversa_ativa
   grep -rn "buscar_conversa_ativa" app/ --include="*.py"
   ```

3. Documentar em uma tabela:

   | Funcao | Arquivo Canonical | Arquivos Duplicados | Consumidores |
   |--------|-------------------|---------------------|--------------|
   | `buscar_conversa_ativa` | conversa.py | supabase.py, database.py | conversa.py |
   | `buscar_ou_criar_medico` | medico.py | supabase.py, database.py | pre_processors.py |

4. Criar issue ou documento com o mapeamento completo

**Como Testar:**

```bash
# Script de auditoria
for func in buscar_conversa_ativa buscar_ou_criar_medico buscar_medico_por_telefone; do
  echo "=== $func ==="
  grep -rn "def $func\|$func(" app/ --include="*.py"
  echo ""
done
```

**DoD:**
- [ ] Tabela completa de funcoes duplicadas
- [ ] Lista de todos os consumidores de cada funcao
- [ ] Decisao sobre qual sera a versao canonical de cada uma
- [ ] Commit: `docs(sprint-30): auditoria de queries duplicadas`

---

### S30.E2.2: Consolidar `buscar_conversa_ativa`

**Objetivo:** Manter apenas uma implementacao em `app/services/conversa.py`.

**Contexto:** Esta funcao existe em 3 lugares. A versao em `conversa.py` eh a mais completa.

**Arquivos a Modificar:**
- `app/services/supabase.py` - Remover/deprecar
- `app/database.py` - Sera removido no Epic 05

**Tarefas:**

1. Verificar a implementacao atual em `conversa.py`:
   ```python
   # app/services/conversa.py - VERSAO CANONICAL
   async def buscar_conversa_ativa(cliente_id: str) -> Optional[dict]:
       response = (
           supabase.table("conversations")
           .select("id, cliente_id, status, controlled_by, chatwoot_conversation_id, created_at")
           .eq("cliente_id", cliente_id)
           .eq("status", "ativa")
           .execute()
       )
       return response.data[0] if response.data else None
   ```

2. Atualizar `supabase.py` para usar a versao canonical:
   ```python
   # app/services/supabase.py
   # REMOVER a implementacao duplicada (linhas 274-295)
   # MANTER apenas o wrapper deprecated se existir

   # Se ja existe wrapper deprecated, atualizar para:
   from app.services.conversa import buscar_conversa_ativa as _buscar_conversa_ativa

   async def buscar_conversa_ativa_deprecated(cliente_id: str) -> Optional[dict]:
       """DEPRECATED: Use `from app.services.conversa import buscar_conversa_ativa`."""
       import warnings
       warnings.warn(
           "buscar_conversa_ativa em supabase.py esta deprecated. "
           "Use 'from app.services.conversa import buscar_conversa_ativa'",
           DeprecationWarning,
           stacklevel=2
       )
       return await _buscar_conversa_ativa(cliente_id)
   ```

3. Buscar e atualizar consumidores (se houver):
   ```bash
   grep -rn "from app.services.supabase import.*buscar_conversa_ativa" app/
   ```

4. Rodar testes:
   ```bash
   uv run pytest tests/ -v -k "conversa"
   ```

**Como Testar:**

```bash
# 1. Verificar que so existe uma definicao (exceto deprecated)
grep -rn "^async def buscar_conversa_ativa" app/services/

# Deve retornar apenas:
# app/services/conversa.py:13:async def buscar_conversa_ativa

# 2. Rodar testes
uv run pytest tests/ -v
```

**DoD:**
- [ ] Funcao existe apenas em `app/services/conversa.py`
- [ ] Wrapper deprecated em `supabase.py` (se necessario para compatibilidade)
- [ ] Nenhum import de `buscar_conversa_ativa` de `supabase.py`
- [ ] Todos os testes passando
- [ ] Commit: `refactor(conversa): consolida buscar_conversa_ativa`

---

### S30.E2.3: Consolidar `buscar_ou_criar_medico`

**Objetivo:** Manter apenas uma implementacao em `app/services/medico.py`.

**Contexto:** Esta funcao existe em 3 lugares. A versao em `medico.py` eh a mais robusta.

**Arquivos a Modificar:**
- `app/services/supabase.py` - Remover/deprecar
- `app/pipeline/pre_processors.py` - Verificar import
- `app/database.py` - Sera removido no Epic 05

**Tarefas:**

1. Verificar implementacao atual em `medico.py`:
   ```bash
   # Ver a funcao completa
   grep -A 50 "^async def buscar_ou_criar_medico" app/services/medico.py
   ```

2. Verificar quem importa de onde:
   ```bash
   grep -rn "import.*buscar_ou_criar_medico\|from.*import.*buscar_ou_criar_medico" app/
   ```

3. Atualizar `pre_processors.py` se necessario:
   ```python
   # Garantir que importa de medico.py
   from app.services.medico import buscar_ou_criar_medico
   ```

4. Remover/deprecar em `supabase.py`:
   ```python
   # Remover linhas 419-470 (implementacao duplicada)
   # OU converter para wrapper deprecated
   ```

5. Rodar testes:
   ```bash
   uv run pytest tests/ -v -k "medico"
   ```

**Como Testar:**

```bash
# 1. Verificar que so existe uma definicao
grep -rn "^async def buscar_ou_criar_medico" app/services/

# Deve retornar apenas:
# app/services/medico.py:95:async def buscar_ou_criar_medico

# 2. Verificar imports
grep -rn "buscar_ou_criar_medico" app/ --include="*.py" | grep -v "def buscar"

# 3. Rodar testes
uv run pytest tests/ -v
```

**DoD:**
- [ ] Funcao existe apenas em `app/services/medico.py`
- [ ] Todos os consumidores importam de `medico.py`
- [ ] Wrapper deprecated em `supabase.py` (se necessario)
- [ ] Todos os testes passando
- [ ] Commit: `refactor(medico): consolida buscar_ou_criar_medico`

---

### S30.E2.4: Limpar `supabase.py`

**Objetivo:** Remover funcoes orfas e manter `supabase.py` apenas como cliente de conexao.

**Contexto:** O arquivo `supabase.py` acumulou funcoes de query que deveriam estar nos services especificos.

**Arquivo:** `app/services/supabase.py`

**Tarefas:**

1. Listar todas as funcoes em `supabase.py`:
   ```bash
   grep -n "^async def\|^def" app/services/supabase.py
   ```

2. Para cada funcao, verificar se:
   - Existe versao em service especifico → Remover de supabase.py
   - Eh helper generico (ex: `contar_interacoes_periodo`) → Manter
   - Eh wrapper deprecated → Manter por ora, marcar para remocao futura

3. Estrutura ideal de `supabase.py`:
   ```python
   """
   Cliente Supabase - Sprint 30 Refatorado

   Este arquivo deve conter APENAS:
   - Inicializacao do cliente Supabase
   - Helpers genericos de query (nao especificos de entidade)
   """
   from supabase import create_client, Client
   from app.core.config import settings

   # Cliente singleton
   supabase: Client = create_client(
       settings.SUPABASE_URL,
       settings.SUPABASE_ANON_KEY
   )

   # Helpers genericos (OK manter aqui)
   async def contar_interacoes_periodo(...): ...
   async def executar_query_com_retry(...): ...

   # NAO MANTER: funcoes especificas de entidade
   # - buscar_conversa_ativa → app/services/conversa.py
   # - buscar_ou_criar_medico → app/services/medico.py
   # - buscar_vagas_disponiveis → app/services/vaga.py
   ```

4. Mover funcoes para services apropriados ou remover se duplicadas

**Como Testar:**

```bash
# 1. Listar funcoes restantes em supabase.py
grep -n "^async def\|^def" app/services/supabase.py

# 2. Verificar que nao ha funcoes especificas de entidade
# (exceto wrappers deprecated)

# 3. Rodar todos os testes
uv run pytest tests/ -v
```

**DoD:**
- [ ] `supabase.py` contem apenas cliente e helpers genericos
- [ ] Funcoes de entidade movidas para services apropriados
- [ ] Wrappers deprecated claramente marcados
- [ ] Todos os testes passando
- [ ] Commit: `refactor(supabase): limpa funcoes orfas`

---

### S30.E2.5: Criar Testes de Regressao

**Objetivo:** Garantir que a consolidacao nao quebrou nenhuma funcionalidade.

**Contexto:** Apos mover funcoes, precisamos garantir que os comportamentos sao identicos.

**Arquivo:** `tests/services/test_query_consolidation.py` (criar)

**Tarefas:**

1. Criar testes que verificam comportamento esperado:

```python
# tests/services/test_query_consolidation.py
"""
Testes de regressao para consolidacao de queries.

Sprint 30 - S30.E2.5
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.conversa import buscar_conversa_ativa
from app.services.medico import buscar_ou_criar_medico


class TestBuscarConversaAtiva:
    """Testes para buscar_conversa_ativa."""

    @pytest.mark.asyncio
    @patch("app.services.conversa.supabase")
    async def test_retorna_conversa_quando_existe(self, mock_supabase):
        """Deve retornar conversa quando existe uma ativa."""
        mock_response = MagicMock()
        mock_response.data = [{
            "id": "conv-123",
            "cliente_id": "cliente-456",
            "status": "ativa",
            "controlled_by": "ai"
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

        resultado = await buscar_conversa_ativa("cliente-456")

        assert resultado is not None
        assert resultado["id"] == "conv-123"
        assert resultado["status"] == "ativa"

    @pytest.mark.asyncio
    @patch("app.services.conversa.supabase")
    async def test_retorna_none_quando_nao_existe(self, mock_supabase):
        """Deve retornar None quando nao ha conversa ativa."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

        resultado = await buscar_conversa_ativa("cliente-inexistente")

        assert resultado is None

    @pytest.mark.asyncio
    @patch("app.services.conversa.supabase")
    async def test_filtra_por_status_ativa(self, mock_supabase):
        """Deve filtrar apenas conversas com status 'ativa'."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response

        await buscar_conversa_ativa("cliente-123")

        # Verificar que filtrou por status ativa
        calls = mock_supabase.table.return_value.select.return_value.eq.call_args_list
        assert any("ativa" in str(call) for call in calls)


class TestBuscarOuCriarMedico:
    """Testes para buscar_ou_criar_medico."""

    @pytest.mark.asyncio
    @patch("app.services.medico.supabase")
    async def test_retorna_medico_existente(self, mock_supabase):
        """Deve retornar medico se ja existe."""
        mock_response = MagicMock()
        mock_response.data = [{
            "id": "medico-123",
            "telefone": "5511999999999",
            "nome": "Dr. Teste"
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        resultado = await buscar_ou_criar_medico("5511999999999")

        assert resultado is not None
        assert resultado["telefone"] == "5511999999999"

    @pytest.mark.asyncio
    @patch("app.services.medico.supabase")
    async def test_cria_medico_quando_nao_existe(self, mock_supabase):
        """Deve criar medico se nao existe."""
        # Primeira chamada (select) retorna vazio
        mock_select = MagicMock()
        mock_select.data = []

        # Segunda chamada (insert) retorna o novo medico
        mock_insert = MagicMock()
        mock_insert.data = [{
            "id": "novo-medico",
            "telefone": "5511888888888",
            "nome": "Medico"
        }]

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_select
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_insert

        resultado = await buscar_ou_criar_medico("5511888888888")

        assert resultado is not None
        # Verifica que tentou inserir
        mock_supabase.table.return_value.insert.assert_called()

    @pytest.mark.asyncio
    @patch("app.services.medico.supabase")
    async def test_normaliza_telefone(self, mock_supabase):
        """Deve normalizar telefone (remover formatacao)."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        # Telefone com formatacao
        await buscar_ou_criar_medico("+55 (11) 99999-9999")

        # Deve ter buscado com telefone normalizado
        call_args = mock_supabase.table.return_value.select.return_value.eq.call_args
        # Verificar que o telefone foi normalizado para apenas digitos
```

2. Rodar testes:
   ```bash
   uv run pytest tests/services/test_query_consolidation.py -v
   ```

**Como Testar:**

```bash
# Rodar testes de consolidacao
uv run pytest tests/services/test_query_consolidation.py -v

# Rodar todos os testes para garantir nada quebrou
uv run pytest tests/ -v
```

**DoD:**
- [ ] Arquivo de testes criado
- [ ] Testes para `buscar_conversa_ativa` (minimo 3)
- [ ] Testes para `buscar_ou_criar_medico` (minimo 3)
- [ ] Todos os testes passando
- [ ] Commit: `test(services): testes de regressao para queries consolidadas`

---

## Checklist do Epic

- [ ] **S30.E2.1** - Auditoria completa
- [ ] **S30.E2.2** - `buscar_conversa_ativa` consolidada
- [ ] **S30.E2.3** - `buscar_ou_criar_medico` consolidada
- [ ] **S30.E2.4** - `supabase.py` limpo
- [ ] **S30.E2.5** - Testes de regressao passando
- [ ] Zero queries duplicadas (verificar com grep)
- [ ] Todos os testes da suite passando

---

## Arquivos Modificados

| Arquivo | Acao | Estimativa |
|---------|------|------------|
| `app/services/supabase.py` | Modificar | -100 linhas |
| `app/services/conversa.py` | Manter | 0 |
| `app/services/medico.py` | Manter | 0 |
| `tests/services/test_query_consolidation.py` | Criar | ~80 linhas |

---

## Verificacao Final

```bash
# Script de verificacao - deve retornar 0 duplicatas
echo "=== Verificando duplicatas ==="

# buscar_conversa_ativa deve aparecer apenas em conversa.py
COUNT=$(grep -rn "^async def buscar_conversa_ativa" app/services/*.py | grep -v "conversa.py" | wc -l)
if [ $COUNT -gt 0 ]; then
  echo "ERRO: buscar_conversa_ativa duplicada!"
  exit 1
fi

# buscar_ou_criar_medico deve aparecer apenas em medico.py
COUNT=$(grep -rn "^async def buscar_ou_criar_medico" app/services/*.py | grep -v "medico.py" | wc -l)
if [ $COUNT -gt 0 ]; then
  echo "ERRO: buscar_ou_criar_medico duplicada!"
  exit 1
fi

echo "OK: Nenhuma duplicata encontrada!"
```

---

## Tempo Estimado

| Story | Complexidade | Estimativa |
|-------|--------------|------------|
| S30.E2.1 | Media | 1h |
| S30.E2.2 | Baixa | 30min |
| S30.E2.3 | Media | 45min |
| S30.E2.4 | Baixa | 30min |
| S30.E2.5 | Media | 1h |
| **Total** | | **~4h** |
