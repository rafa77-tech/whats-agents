# Epic 05: Remocao de Codigo Legado

## Severidade: MEDIO

## Objetivo

Remover codigo obsoleto e arquivos nao utilizados para reduzir confusao e divida tecnica.

## Problema Atual

### Arquivos Legados Identificados

#### 1. `app/agent.py` (170 linhas)

**Status:** Completamente obsoleto
**Substituto:** `app/services/agente.py`

**Evidencias de obsolescencia:**
```python
# Imports antigos (padrao nao usado mais)
from config import settings           # Deveria ser: from app.core.config import settings
from config.prompts import build_prompt  # Nao existe mais
from app.database import db           # Classe obsoleta

# Singleton nunca importado em lugar nenhum
julia = JuliaAgent()
```

#### 2. `app/database.py` (182 linhas)

**Status:** Completamente obsoleto
**Substituto:** `app/services/supabase.py` + services especificos

**Evidencias de obsolescencia:**
```python
# Import antigo
from config import settings  # Deveria ser: from app.core.config import settings

# Singleton usado apenas por app/agent.py (tambem obsoleto)
db = DatabaseClient()
```

#### 3. Funcoes Deprecated em `supabase.py`

Apos Epic 02 (consolidacao), algumas funcoes deprecated permaneceram para compatibilidade.
Devem ser removidas apos confirmar que nao ha mais consumidores.

---

## Stories

### S30.E5.1: Remover `app/agent.py`

**Objetivo:** Deletar arquivo completamente obsoleto.

**Contexto:** Este arquivo foi a primeira versao do agente, antes da refatoracao em Sprint 8-10. O agente atual esta em `app/services/agente.py`.

**Tarefas:**

1. Verificar que ninguem importa este arquivo:
   ```bash
   grep -rn "from app.agent import\|from app import agent\|import app.agent" .
   # Deve retornar vazio (nenhum consumidor)
   ```

2. Verificar que ninguem importa `julia` (singleton):
   ```bash
   grep -rn "from app.agent import julia\|app.agent.julia" .
   # Deve retornar vazio
   ```

3. Verificar que `config.prompts` nao existe mais:
   ```bash
   ls -la config/prompts.py 2>/dev/null || echo "Nao existe (esperado)"
   ```

4. Deletar o arquivo:
   ```bash
   rm app/agent.py
   ```

5. Rodar testes para confirmar que nada quebrou:
   ```bash
   uv run pytest tests/ -v
   ```

**Como Testar:**

```bash
# 1. Verificar que nao ha imports
grep -rn "app.agent" . --include="*.py"

# 2. Deletar
rm app/agent.py

# 3. Rodar testes
uv run pytest tests/ -v

# 4. Iniciar servidor
uv run uvicorn app.main:app --reload
```

**DoD:**
- [ ] Nenhum consumidor de `app/agent.py` encontrado
- [ ] Arquivo deletado
- [ ] Todos os testes passando
- [ ] Servidor inicia normalmente
- [ ] Commit: `refactor: remove app/agent.py legado`

---

### S30.E5.2: Remover `app/database.py`

**Objetivo:** Deletar arquivo de banco obsoleto.

**Contexto:** Este arquivo foi a primeira implementacao do cliente de banco. O atual esta em `app/services/supabase.py`.

**Tarefas:**

1. Verificar consumidores:
   ```bash
   grep -rn "from app.database import\|from app import database\|import app.database" .
   # Deve retornar apenas app/agent.py (que sera removido)
   ```

2. Se `app/agent.py` ja foi removido (S30.E5.1), verificar novamente:
   ```bash
   grep -rn "app.database" . --include="*.py"
   # Deve retornar vazio
   ```

3. Deletar o arquivo:
   ```bash
   rm app/database.py
   ```

4. Rodar testes:
   ```bash
   uv run pytest tests/ -v
   ```

**Dependencia:** S30.E5.1 deve ser feita primeiro

**DoD:**
- [ ] `app/agent.py` ja removido
- [ ] Nenhum outro consumidor de `app/database.py`
- [ ] Arquivo deletado
- [ ] Todos os testes passando
- [ ] Commit: `refactor: remove app/database.py legado`

---

### S30.E5.3: Limpar Funcoes Deprecated

**Objetivo:** Remover funcoes marcadas como deprecated que nao tem mais consumidores.

**Contexto:** Durante refatoracoes anteriores, algumas funcoes foram marcadas deprecated mas mantidas para compatibilidade.

**Arquivo:** `app/services/supabase.py`

**Tarefas:**

1. Identificar funcoes deprecated:
   ```bash
   grep -n "DEPRECATED\|deprecated" app/services/supabase.py
   ```

2. Para cada funcao deprecated, verificar consumidores:
   ```bash
   # Exemplo para get_supabase
   grep -rn "get_supabase" app/ --include="*.py" | grep -v "supabase.py"
   ```

3. Se nao houver consumidores, remover a funcao

4. Lista provavel de funcoes a remover:
   - [ ] `get_supabase()` - wrapper desnecessario
   - [ ] Outros wrappers deprecated

5. Rodar testes apos cada remocao

**Como Testar:**

```bash
# Apos cada remocao
uv run pytest tests/ -v

# Verificar que nao quebrou imports
python -c "from app.services.supabase import supabase; print('OK')"
```

**DoD:**
- [ ] Todas as funcoes deprecated sem consumidores removidas
- [ ] Todos os testes passando
- [ ] Commit: `refactor(supabase): remove funcoes deprecated`

---

### S30.E5.4: Limpar Imports Nao Utilizados

**Objetivo:** Remover imports que nao sao mais usados nos arquivos.

**Contexto:** Com as remocoes anteriores, alguns arquivos podem ter imports orfaos.

**Tarefas:**

1. Usar ferramenta de lint para identificar:
   ```bash
   uv run ruff check app/ --select=F401
   # F401 = unused imports
   ```

2. Corrigir automaticamente:
   ```bash
   uv run ruff check app/ --select=F401 --fix
   ```

3. Revisar mudancas:
   ```bash
   git diff
   ```

4. Rodar testes:
   ```bash
   uv run pytest tests/ -v
   ```

**Como Testar:**

```bash
# Verificar que nao ha mais imports nao usados
uv run ruff check app/ --select=F401
# Deve retornar vazio
```

**DoD:**
- [ ] Zero imports nao utilizados (ruff F401)
- [ ] Todos os testes passando
- [ ] Commit: `refactor: remove imports nao utilizados`

---

### S30.E5.5: Atualizar Documentacao

**Objetivo:** Remover referencias a codigo removido na documentacao.

**Tarefas:**

1. Buscar referencias na documentacao:
   ```bash
   grep -rn "app/agent.py\|app/database.py\|get_supabase" docs/ planning/
   ```

2. Atualizar documentos encontrados

3. Atualizar CLAUDE.md se necessario

**DoD:**
- [ ] Nenhuma referencia a codigo removido na documentacao
- [ ] CLAUDE.md atualizado se necessario
- [ ] Commit: `docs: remove referencias a codigo legado`

---

## Checklist do Epic

- [ ] **S30.E5.1** - `app/agent.py` removido
- [ ] **S30.E5.2** - `app/database.py` removido
- [ ] **S30.E5.3** - Funcoes deprecated removidas
- [ ] **S30.E5.4** - Imports limpos
- [ ] **S30.E5.5** - Documentacao atualizada
- [ ] Todos os testes passando
- [ ] Zero warnings de imports nao usados

---

## Ordem de Execucao

```
S30.E5.1 (agent.py)
    │
    ▼
S30.E5.2 (database.py)
    │
    ▼
S30.E5.3 (deprecated functions)
    │
    ▼
S30.E5.4 (imports) ──▶ S30.E5.5 (docs)
```

**Importante:** E5.2 depende de E5.1 porque `database.py` so eh usado por `agent.py`.

---

## Arquivos Removidos/Modificados

| Arquivo | Acao | Linhas |
|---------|------|--------|
| `app/agent.py` | Remover | -170 |
| `app/database.py` | Remover | -182 |
| `app/services/supabase.py` | Modificar | ~-30 |
| Varios | Limpar imports | ~-20 |
| Docs | Atualizar | variavel |
| **Total removido** | | **~-400** |

---

## Verificacao Final

```bash
# Verificar que arquivos nao existem
ls app/agent.py 2>/dev/null && echo "ERRO: agent.py ainda existe!" || echo "OK: agent.py removido"
ls app/database.py 2>/dev/null && echo "ERRO: database.py ainda existe!" || echo "OK: database.py removido"

# Verificar imports limpos
uv run ruff check app/ --select=F401

# Verificar que deprecated foram removidos
grep -c "DEPRECATED" app/services/supabase.py
# Esperado: 0 ou apenas comentarios explicativos
```

---

## Tempo Estimado

| Story | Complexidade | Estimativa |
|-------|--------------|------------|
| S30.E5.1 | Baixa | 15min |
| S30.E5.2 | Baixa | 15min |
| S30.E5.3 | Baixa | 30min |
| S30.E5.4 | Baixa | 15min |
| S30.E5.5 | Baixa | 15min |
| **Total** | | **~1.5h** |
