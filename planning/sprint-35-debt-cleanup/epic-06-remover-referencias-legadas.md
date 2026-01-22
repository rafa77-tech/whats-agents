# Epic 06: Remover Referencias Legadas

## Objetivo

Eliminar todas as referencias a `envios_campanha` e outros artefatos legados do codebase.

## Contexto

A tabela `envios_campanha` foi removida do banco, mas o codigo ainda a referencia em varios lugares. Este epico remove todas essas referencias.

---

## Story 6.1: Auditar Referencias

### Objetivo

Identificar todos os locais que ainda referenciam `envios_campanha`.

### Tarefas

1. **Buscar referencias** no codigo:

```bash
grep -r "envios_campanha" app/ --include="*.py" | grep -v "__pycache__"
```

2. **Documentar locais encontrados**:

| Arquivo | Linha | Contexto |
|---------|-------|----------|
| `app/services/campanha.py` | 52 | `supabase.table("envios_campanha")` |
| `app/services/campanha.py` | 66 | `supabase.table("envios_campanha")` |
| `app/services/campanha.py` | 157 | `.insert()` |
| `app/services/campanha.py` | 184 | `.select()` |
| `app/services/campanha.py` | 222 | `.update()` |
| `app/services/campanha.py` | 232 | `.update()` |
| `app/services/campanha.py` | 246 | `.update()` |
| `app/services/campanha.py` | 395 | `.insert()` |
| `app/api/routes/piloto.py` | 32 | `.select()` |

3. **Buscar outras referencias legadas**:

```bash
grep -r "mensagem_template" app/ --include="*.py" | grep -v "__pycache__"
grep -r '"nome"' app/api/routes/campanhas.py
grep -r '"tipo"' app/services/campanha.py | grep -v "tipo_campanha"
```

### DoD

- [ ] Lista completa de referencias a `envios_campanha`
- [ ] Lista de outras referencias legadas
- [ ] Documentado em checklist para remocao

---

## Story 6.2: Limpar app/services/campanha.py

### Objetivo

Remover ou atualizar todas as funcoes que usam `envios_campanha`.

### Tarefas

1. **Marcar funcoes como deprecated** ou remover:

```python
# Funcoes a remover/refatorar em app/services/campanha.py:

# 1. pode_enviar_primeiro_contato() - linhas 27-78
#    ACAO: Remover ou mover para novo modulo se ainda necessario

# 2. criar_campanha_piloto() - linhas 106-175
#    ACAO: Refatorar para usar campanha_repository e fila_service

# 3. executar_campanha() - linhas 178-252
#    ACAO: Remover (substituido por campanha_executor)

# 4. criar_envios_campanha() - linhas 255-313
#    ACAO: Remover (substituido por campanha_executor)

# 5. enviar_mensagem_prospeccao() - linhas 316-409
#    ACAO: Refatorar para usar fila_service
```

2. **Para cada funcao, decidir**:

| Funcao | Decisao | Justificativa |
|--------|---------|---------------|
| `pode_enviar_primeiro_contato` | REMOVER | Logica movida para guardrails |
| `criar_campanha_piloto` | REFATORAR | Ainda pode ser util, mas usar novos modulos |
| `executar_campanha` | REMOVER | Substituido por `campanha_executor.executar()` |
| `criar_envios_campanha` | REMOVER | Substituido por `campanha_executor.executar()` |
| `enviar_mensagem_prospeccao` | REFATORAR | Mover para `campanha_executor` ou remover |

3. **Adicionar deprecation warnings** (se manter temporariamente):

```python
import warnings

async def criar_envios_campanha(campanha_id: str):
    """
    DEPRECATED: Use campanha_executor.executar() em vez disso.
    """
    warnings.warn(
        "criar_envios_campanha esta deprecated. Use campanha_executor.executar()",
        DeprecationWarning,
        stacklevel=2
    )
    # Redirecionar para novo codigo
    from app.services.campanhas import campanha_executor
    return await campanha_executor.executar(int(campanha_id))
```

### DoD

- [ ] Funcoes obsoletas marcadas como deprecated ou removidas
- [ ] Nenhuma referencia direta a `envios_campanha`
- [ ] Imports atualizados

---

## Story 6.3: Limpar app/api/routes/piloto.py

### Objetivo

Remover referencia a `envios_campanha` no endpoint de piloto.

### Tarefas

1. **Localizar codigo** na linha 32:

```python
# ANTES (aproximado)
supabase.table("envios_campanha")
    .select("status")
    .eq("campanha_id", campanha_id)
    .execute()
```

2. **Substituir por view** `campaign_sends`:

```python
# DEPOIS
supabase.table("campaign_sends")
    .select("queue_status, outcome")
    .eq("campaign_id", campanha_id)
    .execute()
```

3. **Ou usar repository**:

```python
# ALTERNATIVA - usar campaign_sends_repo se existir
from app.services.campaign_sends import campaign_sends_repo

envios = await campaign_sends_repo.listar_por_campanha(campanha_id)
```

### DoD

- [ ] Referencia a `envios_campanha` removida de piloto.py
- [ ] Funcionalidade equivalente usando `campaign_sends` ou repository

---

## Story 6.4: Verificar Outras Referencias

### Objetivo

Garantir que nao ha outras referencias a codigo legado.

### Tarefas

1. **Buscar `mensagem_template`**:

```bash
grep -r "mensagem_template" app/ --include="*.py" | grep -v "__pycache__"
```

Se encontrar, atualizar para usar `corpo` ou geracao dinamica.

2. **Buscar `config` usado como filtros**:

```bash
grep -r 'campanha.*config' app/ --include="*.py" | grep -v "__pycache__"
```

Se encontrar, atualizar para usar `audience_filters`.

3. **Buscar `filtro_especialidades`**:

```bash
grep -r "filtro_especialidades\|filtro_regioes" app/ --include="*.py" | grep -v "__pycache__"
```

Se encontrar, atualizar para `especialidades` e `regioes`.

4. **Buscar acesso direto a coluna `nome`** (sem `_template`):

```bash
grep -r 'campanha\["nome"\]' app/ --include="*.py" | grep -v "__pycache__"
```

Se encontrar, atualizar para `nome_template`.

### DoD

- [ ] Zero referencias a `mensagem_template`
- [ ] Zero referencias a `config` para filtros
- [ ] Zero referencias a `filtro_especialidades` ou `filtro_regioes`
- [ ] Zero referencias a `campanha["nome"]` (sem _template)

---

## Story 6.5: Validacao Final

### Objetivo

Garantir que o codigo esta limpo e funcional.

### Tarefas

1. **Rodar busca abrangente**:

```bash
# Deve retornar ZERO resultados
grep -r "envios_campanha" app/ --include="*.py" | grep -v "__pycache__" | wc -l
```

2. **Rodar testes**:

```bash
uv run pytest tests/ -v --tb=short
```

3. **Verificar imports nao usados**:

```bash
# Usar ferramenta de lint
uv run ruff check app/services/campanha.py
uv run ruff check app/api/routes/campanhas.py
uv run ruff check app/api/routes/piloto.py
```

4. **Testar endpoint de campanhas**:

```bash
# Criar campanha de teste
curl -X POST http://localhost:8000/campanhas/ \
  -H "Content-Type: application/json" \
  -d '{"nome_template": "Teste Cleanup", "tipo_campanha": "discovery", "quantidade_alvo": 5}'
```

### DoD

- [ ] Busca por `envios_campanha` retorna 0 resultados
- [ ] Todos os testes passam
- [ ] Sem erros de lint
- [ ] Endpoint de campanhas funciona

---

## Checklist do Epico

- [ ] **S35.E06.1** - Auditoria de referencias
- [ ] **S35.E06.2** - campanha.py limpo
- [ ] **S35.E06.3** - piloto.py limpo
- [ ] **S35.E06.4** - Outras referencias removidas
- [ ] **S35.E06.5** - Validacao final

### Comandos de Verificacao

```bash
# Verificar que nao tem mais referencias legadas
grep -r "envios_campanha" app/ --include="*.py" | grep -v "__pycache__"
grep -r "mensagem_template" app/ --include="*.py" | grep -v "__pycache__"

# Rodar testes
uv run pytest tests/ -v

# Verificar lint
uv run ruff check app/
```

---

## Tempo Estimado

| Story | Tempo |
|-------|-------|
| 6.1 Auditoria | 15min |
| 6.2 Limpar campanha.py | 45min |
| 6.3 Limpar piloto.py | 15min |
| 6.4 Outras referencias | 30min |
| 6.5 Validacao | 15min |
| **Total** | **2h** |
