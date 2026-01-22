# Epic 07: Limpeza Codigo Deprecated

## Objetivo

Remover modulos wrapper deprecated e codigo que nao e mais utilizado.

## Contexto

Durante a evolucao do projeto (Twilio -> Evolution API), varios modulos foram criados como wrappers ou adaptadores temporarios. Este epico remove esses artefatos.

---

## Story 7.1: Identificar Modulos Deprecated

### Objetivo

Mapear todos os modulos que podem ser removidos ou consolidados.

### Tarefas

1. **Buscar modulos wrapper**:

```bash
grep -r "DEPRECATED\|deprecated\|TODO: remover" app/ --include="*.py" | grep -v "__pycache__"
```

2. **Verificar modulos nao importados**:

```bash
# Listar todos os modulos em app/services
find app/services -name "*.py" -type f | sort

# Para cada modulo, verificar se e importado
# Exemplo:
grep -r "from app.services.campanha import" app/ --include="*.py" | grep -v "__pycache__"
```

3. **Documentar modulos candidatos**:

| Modulo | Status | Motivo |
|--------|--------|--------|
| `app/services/campanha.py` | CONSOLIDAR | Funcoes movidas para campanhas/ |
| `app/services/segmentacao.py` | VERIFICAR | Pode estar deprecated |
| `app/services/envio_mensagem.py` | VERIFICAR | Pode ter sido substituido |

### DoD

- [ ] Lista completa de modulos deprecated
- [ ] Cada modulo verificado se tem imports ativos
- [ ] Documentado em checklist

---

## Story 7.2: Consolidar app/services/campanha.py

### Objetivo

Migrar funcoes uteis e remover o resto do arquivo `app/services/campanha.py`.

### Tarefas

1. **Analisar cada funcao**:

| Funcao | Linhas | Decisao | Destino |
|--------|--------|---------|---------|
| `pode_enviar_primeiro_contato` | 27-78 | MOVER | `app/services/campanhas/guardrails.py` |
| `criar_campanha_piloto` | 106-175 | REMOVER | Substituido por repository |
| `executar_campanha` | 178-252 | REMOVER | Substituido por executor |
| `criar_envios_campanha` | 255-313 | REMOVER | Substituido por executor |
| `enviar_mensagem_prospeccao` | 316-409 | AVALIAR | Pode ir para executor |

2. **Mover funcoes necessarias** (se houver):

```python
# Se pode_enviar_primeiro_contato ainda for util:
# Criar app/services/campanhas/guardrails.py

"""Guardrails para envio de campanhas."""

async def pode_enviar_primeiro_contato(medico_id: str) -> bool:
    """
    Verifica se pode enviar primeiro contato para medico.

    Regras:
    - Nao enviou nos ultimos 7 dias
    - Medico nao optou out
    - Dentro do horario comercial
    """
    # Mover logica de campanha.py
    pass
```

3. **Atualizar imports em outros arquivos**:

```bash
# Buscar quem importa de campanha.py
grep -r "from app.services.campanha import" app/ --include="*.py" | grep -v "__pycache__"
```

4. **Remover ou deprecar arquivo**:

```python
# Opcao A: Remover completamente
# rm app/services/campanha.py

# Opcao B: Deixar apenas imports de compatibilidade
"""
DEPRECATED: Este modulo foi substituido por app/services/campanhas/

Use:
- campanha_repository para CRUD
- campanha_executor para execucao
- guardrails para validacoes
"""
import warnings

def criar_campanha_piloto(*args, **kwargs):
    warnings.warn(
        "criar_campanha_piloto deprecated. Use campanha_repository.criar()",
        DeprecationWarning
    )
    from app.services.campanhas import campanha_repository
    return campanha_repository.criar(*args, **kwargs)
```

### DoD

- [ ] Funcoes uteis movidas para novos modulos
- [ ] Arquivo original removido ou apenas com stubs deprecated
- [ ] Nenhum import quebrado
- [ ] Testes passam

---

## Story 7.3: Verificar Outros Modulos Legados

### Objetivo

Identificar e limpar outros modulos que podem estar deprecated.

### Tarefas

1. **Verificar `app/services/segmentacao.py`**:

```bash
# Verificar se e usado
grep -r "from app.services.segmentacao" app/ --include="*.py" | grep -v "__pycache__"
grep -r "segmentacao_service" app/ --include="*.py" | grep -v "__pycache__"
```

Se nao for usado, remover.

2. **Verificar `app/services/envio_mensagem.py`**:

```bash
grep -r "from app.services.envio_mensagem" app/ --include="*.py" | grep -v "__pycache__"
```

Se substituido por `fila_service`, remover.

3. **Verificar modulos de Twilio** (se existirem):

```bash
grep -r "twilio" app/ --include="*.py" -i | grep -v "__pycache__"
```

Remover qualquer referencia a Twilio.

4. **Verificar imports nao usados em __init__.py**:

```bash
# Para cada __init__.py, verificar exports
cat app/services/__init__.py
cat app/services/campanhas/__init__.py
```

### DoD

- [ ] Modulos `segmentacao.py` verificado e limpo
- [ ] Modulos de envio verificados e limpos
- [ ] Zero referencias a Twilio
- [ ] `__init__.py` limpos

---

## Story 7.4: Limpar Imports Nao Usados

### Objetivo

Remover imports nao usados em todos os arquivos modificados.

### Tarefas

1. **Rodar ruff em arquivos de campanha**:

```bash
uv run ruff check app/services/campanhas/ --select F401
uv run ruff check app/api/routes/campanhas.py --select F401
uv run ruff check app/api/routes/piloto.py --select F401
```

2. **Corrigir automaticamente**:

```bash
uv run ruff check app/services/campanhas/ --select F401 --fix
```

3. **Verificar imports circulares**:

```bash
# Se houver erros de import circular, reorganizar
uv run python -c "from app.services.campanhas import campanha_repository, campanha_executor"
```

### DoD

- [ ] Zero F401 (unused imports) nos arquivos de campanha
- [ ] Nenhum import circular
- [ ] Codigo importa corretamente

---

## Story 7.5: Remover Arquivos Orfaos

### Objetivo

Identificar e remover arquivos Python que nao sao importados em lugar nenhum.

### Tarefas

1. **Listar todos os arquivos Python em app/**:

```bash
find app -name "*.py" -type f | grep -v "__pycache__" | sort > /tmp/all_files.txt
```

2. **Para cada arquivo, verificar se e importado**:

```python
# Script de verificacao (rodar manualmente)
import os
import re

def check_imports(filepath):
    module = filepath.replace('/', '.').replace('.py', '').replace('app.', '')
    # Buscar imports deste modulo
    result = os.popen(f'grep -r "from app.{module}" app/ --include="*.py" | grep -v "__pycache__" | wc -l').read()
    return int(result.strip())

# Listar arquivos com zero imports
```

3. **Decidir para cada arquivo orfao**:

| Arquivo | Imports | Decisao |
|---------|---------|---------|
| (preencher) | 0 | REMOVER/MANTER |

4. **Remover arquivos confirmados como orfaos**:

```bash
# Exemplo
rm app/services/modulo_orfao.py
```

### DoD

- [ ] Lista de arquivos orfaos gerada
- [ ] Cada arquivo analisado
- [ ] Arquivos confirmados como inuteis removidos
- [ ] Testes passam apos remocao

---

## Checklist do Epico

- [ ] **S35.E07.1** - Modulos deprecated identificados
- [ ] **S35.E07.2** - campanha.py consolidado
- [ ] **S35.E07.3** - Outros modulos verificados
- [ ] **S35.E07.4** - Imports limpos
- [ ] **S35.E07.5** - Arquivos orfaos removidos

### Comandos de Verificacao

```bash
# Verificar que nao tem deprecated warnings
grep -r "DEPRECATED\|deprecated" app/ --include="*.py" | grep -v "__pycache__" | wc -l

# Verificar imports nao usados
uv run ruff check app/ --select F401

# Rodar testes
uv run pytest tests/ -v --tb=short
```

---

## Tempo Estimado

| Story | Tempo |
|-------|-------|
| 7.1 Identificar deprecated | 30min |
| 7.2 Consolidar campanha.py | 45min |
| 7.3 Verificar outros modulos | 30min |
| 7.4 Limpar imports | 15min |
| 7.5 Remover orfaos | 30min |
| **Total** | **2h30min** |

---

## Riscos e Mitigacoes

| Risco | Mitigacao |
|-------|-----------|
| Remover codigo ainda usado | Sempre verificar imports antes de remover |
| Quebrar imports | Rodar testes apos cada remocao |
| Import circular | Reorganizar imports, usar imports tardios |

---

## Criterios de Rollback

Se apos remocao de codigo:
1. Testes falham
2. Aplicacao nao inicia
3. Endpoints retornam erro

**Acao:** Reverter commit e analisar dependencias nao mapeadas.
