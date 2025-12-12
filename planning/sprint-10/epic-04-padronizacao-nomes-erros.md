# Epic 04: Padronizacao de Nomes e Erros

## Objetivo

Estabelecer padroes consistentes de nomenclatura e tratamento de erros em todo o codebase.

## Problemas Atuais

### 1. Nomes Inconsistentes

| Funcionalidade | Nomes Usados | Arquivos |
|----------------|--------------|----------|
| Buscar medico | `get_medico_by_telefone`, `obter_medico`, `buscar_medico` | supabase, medico |
| Salvar dados | `salvar_interacao`, `adicionar_mensagem`, `registrar` | interacao, conversa |
| Verificar limite | `pode_enviar`, `pode_enviar_proativo`, `verificar_limite` | rate_limiter |
| Enviar msg | `enviar_mensagem`, `enviar_com_digitacao`, `enviar_slack` | whatsapp, slack |

### 2. Tratamento de Erro Inconsistente

```python
# Padrao 1: Try/except generico
try:
    response = supabase.table("x").select().execute()
except Exception as e:
    logger.error(f"Erro: {e}")
    return None

# Padrao 2: Check de response.data
response = supabase.table("x").select().execute()
if not response.data:
    return []

# Padrao 3: Sem tratamento (crash!)
response = supabase.table("x").select().execute()
return response.data[0]  # IndexError se vazio
```

---

## Stories

### S10.E4.1: Definir Padrao de Nomenclatura

**Objetivo:** Documentar e aplicar padrao consistente de nomes.

**Padrao Proposto:**

| Operacao | Prefixo | Exemplo |
|----------|---------|---------|
| Buscar um | `buscar_` | `buscar_medico_por_telefone()` |
| Buscar varios | `listar_` | `listar_medicos_ativos()` |
| Criar | `criar_` | `criar_conversa()` |
| Atualizar | `atualizar_` | `atualizar_status_vaga()` |
| Deletar | `deletar_` | `deletar_handoff()` |
| Verificar | `verificar_` | `verificar_rate_limit()` |
| Validar | `validar_` | `validar_telefone()` |
| Formatar | `formatar_` | `formatar_data()` |
| Calcular | `calcular_` | `calcular_taxa_resposta()` |
| Enviar | `enviar_` | `enviar_mensagem()` |
| Processar | `processar_` | `processar_webhook()` |
| Gerar | `gerar_` | `gerar_relatorio()` |

**Regras Adicionais:**

1. **Parametros de filtro:** Sufixo `_por_` ou `_com_`
   - `buscar_medico_por_telefone()`
   - `listar_vagas_com_filtros()`

2. **Retorno booleano:** Prefixo `pode_`, `tem_`, `esta_`, `eh_`
   - `pode_enviar_mensagem()`
   - `tem_preferencias()`
   - `esta_em_handoff()`
   - `eh_horario_comercial()`

3. **Async:** Todas as funcoes que fazem I/O sao async
   - Banco de dados
   - APIs externas
   - Cache Redis

**Tarefas:**

1. Criar documento de padroes:
   ```python
   # app/CONVENTIONS.md
   # Convencoes de Codigo - Agente Julia

   ## Nomenclatura de Funcoes

   ### Operacoes de Dados
   - `buscar_*` - Retorna um item ou None
   - `listar_*` - Retorna lista (pode ser vazia)
   - `criar_*` - Cria e retorna novo item
   - `atualizar_*` - Atualiza item existente
   - `deletar_*` - Remove item

   ### Validacoes
   - `verificar_*` - Verifica condicao, pode ter side effects
   - `validar_*` - Valida dados, retorna bool ou raises

   ### Predicados (retornam bool)
   - `pode_*` - Permissao/capacidade
   - `tem_*` - Existencia
   - `esta_*` - Estado atual
   - `eh_*` - Identidade/tipo

   ### Acoes
   - `enviar_*` - Envia para externo
   - `processar_*` - Transforma/processa
   - `gerar_*` - Cria output
   ```

2. Identificar funcoes que precisam renomear:
   ```bash
   # Buscar padroes inconsistentes
   grep -rn "def get_\|def obter_" app/services/
   grep -rn "def add_\|def adicionar_" app/services/
   ```

3. Criar mapeamento de renomeacao:

   | Arquivo | De | Para |
   |---------|-----|------|
   | `supabase.py` | `get_medico_by_telefone` | `buscar_medico_por_telefone` |
   | `medico.py` | `obter_medico` | `buscar_medico_por_id` |
   | `interacao.py` | `adicionar_mensagem` | `criar_interacao` |
   | `rate_limiter.py` | `pode_enviar` | `pode_enviar_mensagem` |
   | `rate_limiter.py` | `verificar_limite_hora` | `verificar_rate_limit` |

4. Renomear funcoes e atualizar chamadas

**Como Testar:**
```bash
# Verificar que nao ha funcoes com padroes antigos
grep -rn "def get_\|def obter_\|def add_" app/services/ | wc -l
# Deve retornar 0

# Rodar testes
uv run pytest tests/ -v
```

**DoD:**
- [ ] `CONVENTIONS.md` criado em `app/`
- [ ] Todas as funcoes `get_*` renomeadas para `buscar_*`
- [ ] Todas as funcoes `obter_*` renomeadas para `buscar_*`
- [ ] Todas as funcoes `add_*` renomeadas para `criar_*`
- [ ] Imports atualizados em todos os arquivos
- [ ] Todos os testes passando
- [ ] Commit: `refactor: padroniza nomenclatura de funcoes`

---

### S10.E4.2: Padronizar Tratamento de Erros

**Objetivo:** Criar padrao unico de tratamento de erros com exceptions customizadas.

**Padrao Proposto:**

```python
# app/core/exceptions.py
"""Exceptions customizadas do Agente Julia."""

class JuliaException(Exception):
    """Base exception para todos os erros."""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(JuliaException):
    """Erro de banco de dados."""
    pass


class ExternalAPIError(JuliaException):
    """Erro de API externa (WhatsApp, Slack, etc)."""
    pass


class ValidationError(JuliaException):
    """Erro de validacao de dados."""
    pass


class RateLimitError(JuliaException):
    """Rate limit atingido."""
    pass


class NotFoundError(JuliaException):
    """Recurso nao encontrado."""
    pass
```

**Padrao de Uso:**

```python
# ANTES (inconsistente)
def buscar_medico(telefone: str):
    response = supabase.table("clientes").select().eq("telefone", telefone).execute()
    return response.data[0]  # Crash se vazio!

# DEPOIS (padronizado)
from app.core.exceptions import NotFoundError, DatabaseError

async def buscar_medico_por_telefone(telefone: str) -> dict:
    """Busca medico pelo telefone.

    Args:
        telefone: Numero do telefone

    Returns:
        Dict com dados do medico

    Raises:
        NotFoundError: Se medico nao existe
        DatabaseError: Se erro no banco
    """
    try:
        response = supabase.table("clientes").select("*").eq("telefone", telefone).execute()
    except Exception as e:
        raise DatabaseError(f"Erro ao buscar medico: {e}")

    if not response.data:
        raise NotFoundError(
            f"Medico nao encontrado",
            details={"telefone": telefone}
        )

    return response.data[0]
```

**Tarefas:**

1. Criar `app/core/exceptions.py` com exceptions customizadas

2. Criar decorator para tratamento padronizado:
   ```python
   # app/core/decorators.py
   import functools
   import logging
   from app.core.exceptions import JuliaException, DatabaseError

   logger = logging.getLogger(__name__)

   def handle_errors(default_return=None):
       """Decorator para tratamento padronizado de erros.

       Args:
           default_return: Valor retornado em caso de erro
       """
       def decorator(func):
           @functools.wraps(func)
           async def wrapper(*args, **kwargs):
               try:
                   return await func(*args, **kwargs)
               except JuliaException:
                   raise  # Re-raise exceptions conhecidas
               except Exception as e:
                   logger.exception(f"Erro inesperado em {func.__name__}")
                   if default_return is not None:
                       return default_return
                   raise DatabaseError(f"Erro em {func.__name__}: {e}")
           return wrapper
       return decorator
   ```

3. Aplicar em funcoes de alto risco (queries sem tratamento):
   ```bash
   # Identificar funcoes sem tratamento
   grep -rn "response.data\[0\]" app/services/
   ```

4. Atualizar handlers HTTP para converter exceptions:
   ```python
   # app/api/error_handlers.py
   from fastapi import Request
   from fastapi.responses import JSONResponse
   from app.core.exceptions import (
       JuliaException, NotFoundError, ValidationError, RateLimitError
   )

   async def julia_exception_handler(request: Request, exc: JuliaException):
       status_code = 500

       if isinstance(exc, NotFoundError):
           status_code = 404
       elif isinstance(exc, ValidationError):
           status_code = 400
       elif isinstance(exc, RateLimitError):
           status_code = 429

       return JSONResponse(
           status_code=status_code,
           content={
               "error": exc.__class__.__name__,
               "message": exc.message,
               "details": exc.details
           }
       )
   ```

**Como Testar:**
```bash
# Verificar que nao ha acessos diretos sem tratamento
grep -rn "\.data\[0\]" app/services/ | grep -v "if.*data"
# Deve retornar 0

# Rodar testes
uv run pytest tests/ -v
```

**DoD:**
- [ ] `exceptions.py` criado com 5 exceptions
- [ ] `decorators.py` criado com `handle_errors`
- [ ] `error_handlers.py` configurado no FastAPI
- [ ] Zero acessos `response.data[0]` sem verificacao
- [ ] Exceptions documentadas com docstrings
- [ ] Todos os testes passando
- [ ] Commit: `feat(core): adiciona exceptions customizadas e handlers`

---

### S10.E4.3: Centralizar Configuracoes Espalhadas

**Objetivo:** Mover todas as constantes de services para `core/config.py`.

**Constantes Espalhadas Identificadas:**

| Arquivo | Constante | Valor |
|---------|-----------|-------|
| `rate_limiter.py` | `LIMITE_HORA` | 20 |
| `rate_limiter.py` | `LIMITE_DIA` | 100 |
| `vaga.py` | `CACHE_TTL_VAGAS` | 60 |
| `agente_slack.py` | `SESSION_TIMEOUT_MINUTES` | 30 |
| `timing.py` | `HORARIO_INICIO` | 8 |
| `timing.py` | `HORARIO_FIM` | 20 |
| `deteccao_bot.py` | `THRESHOLD_BOT` | 0.7 |
| `handoff.py` | `TIMEOUT_HANDOFF_HORAS` | 24 |

**Nova Estrutura em config.py:**

```python
# app/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Configuracoes da aplicacao."""

    # API Keys (ja existentes)
    ANTHROPIC_API_KEY: str
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Rate Limiting
    RATE_LIMIT_HORA: int = 20
    RATE_LIMIT_DIA: int = 100
    RATE_LIMIT_INTERVALO_MIN: int = 45
    RATE_LIMIT_INTERVALO_MAX: int = 180

    # Horario Comercial
    HORARIO_INICIO: int = 8
    HORARIO_FIM: int = 20
    DIAS_UTEIS: list[int] = [0, 1, 2, 3, 4]  # Seg-Sex

    # Cache TTLs (segundos)
    CACHE_TTL_VAGAS: int = 60
    CACHE_TTL_MEDICOS: int = 300
    CACHE_TTL_SESSAO_SLACK: int = 1800  # 30 min

    # Timeouts
    TIMEOUT_LLM: int = 30
    TIMEOUT_WHATSAPP: int = 10
    TIMEOUT_HANDOFF_HORAS: int = 24

    # Thresholds
    THRESHOLD_BOT_DETECTION: float = 0.7
    THRESHOLD_HANDOFF_IRRITACAO: float = 0.6

    # Limites
    MAX_MENSAGENS_CONTEXTO: int = 10
    MAX_VAGAS_RETORNO: int = 5
    MAX_RETRIES: int = 3

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton
settings = Settings()
```

**Tarefas:**

1. Identificar todas as constantes:
   ```bash
   grep -rn "^[A-Z_]* = " app/services/ --include="*.py"
   ```

2. Adicionar em `core/config.py` organizado por categoria

3. Atualizar cada service para usar settings:
   ```python
   # DE:
   LIMITE_HORA = 20

   if count >= LIMITE_HORA:
       return False

   # PARA:
   from app.core.config import settings

   if count >= settings.RATE_LIMIT_HORA:
       return False
   ```

4. Remover constantes dos services

5. Atualizar `.env.example` com novas variaveis:
   ```env
   # Rate Limiting
   RATE_LIMIT_HORA=20
   RATE_LIMIT_DIA=100

   # Horario Comercial
   HORARIO_INICIO=8
   HORARIO_FIM=20

   # Cache TTLs
   CACHE_TTL_VAGAS=60
   ```

**Como Testar:**
```bash
# Verificar que nao ha constantes hardcoded
grep -rn "^[A-Z_]* = [0-9]" app/services/ --include="*.py" | wc -l
# Deve retornar 0

# Verificar que settings carrega
python -c "from app.core.config import settings; print(settings.RATE_LIMIT_HORA)"

# Rodar testes
uv run pytest tests/ -v
```

**DoD:**
- [ ] Todas as constantes movidas para `core/config.py`
- [ ] Constantes organizadas por categoria com comentarios
- [ ] Zero constantes hardcoded em services
- [ ] `.env.example` atualizado
- [ ] Todos os services usando `settings.*`
- [ ] Todos os testes passando
- [ ] Commit: `refactor(config): centraliza todas as configuracoes`

---

## Resumo do Epic

| Story | Objetivo | Impacto |
|-------|----------|---------|
| S10.E4.1 | Padrao de nomes | Consistencia, legibilidade |
| S10.E4.2 | Tratamento de erros | Robustez, debugging |
| S10.E4.3 | Centralizar config | Manutenibilidade |

**Ordem de Execucao:** S10.E4.1 -> S10.E4.2 -> S10.E4.3 (independentes, podem ser paralelas)

**Artefatos Criados:**
- `app/CONVENTIONS.md` - Documento de padroes
- `app/core/exceptions.py` - Exceptions customizadas
- `app/core/decorators.py` - Decorators utilitarios
- `app/api/error_handlers.py` - Handlers HTTP
- `app/core/config.py` - Configuracoes centralizadas (expandido)
