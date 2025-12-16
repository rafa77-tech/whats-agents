# Convencoes de Codigo - Agente Julia

Documento de referencia para padroes de nomenclatura e estilo de codigo.

## Nomenclatura de Funcoes

### Operacoes de Dados (CRUD)

| Operacao | Prefixo | Retorno | Exemplo |
|----------|---------|---------|---------|
| Buscar um | `buscar_` | item ou None | `buscar_medico_por_telefone()` |
| Buscar varios | `listar_` | lista (pode ser vazia) | `listar_vagas_disponiveis()` |
| Criar | `criar_` | novo item | `criar_conversa()` |
| Atualizar | `atualizar_` | item atualizado | `atualizar_status_vaga()` |
| Deletar | `deletar_` | bool | `deletar_handoff()` |

### Sufixos para Filtros

- `_por_` - filtro por campo unico: `buscar_medico_por_telefone()`
- `_com_` - filtro com multiplos criterios: `listar_vagas_com_filtros()`

### Predicados (retornam bool)

| Prefixo | Uso | Exemplo |
|---------|-----|---------|
| `pode_` | Permissao/capacidade | `pode_enviar_mensagem()` |
| `tem_` | Existencia | `tem_preferencias()` |
| `esta_` | Estado atual | `esta_em_handoff()` |
| `eh_` | Identidade/tipo | `eh_horario_comercial()` |

### Validacoes

| Prefixo | Uso | Retorno |
|---------|-----|---------|
| `verificar_` | Verifica condicao, pode ter side effects | bool |
| `validar_` | Valida dados de entrada | bool ou raises |

### Acoes

| Prefixo | Uso | Exemplo |
|---------|-----|---------|
| `enviar_` | Envia para sistema externo | `enviar_mensagem()` |
| `processar_` | Transforma/processa dados | `processar_webhook()` |
| `gerar_` | Cria output/relatorio | `gerar_relatorio_diario()` |
| `calcular_` | Computa valor | `calcular_taxa_resposta()` |
| `formatar_` | Formata para exibicao | `formatar_telefone()` |
| `notificar_` | Envia notificacao | `notificar_handoff()` |

### Singletons e Factories

Funcoes que retornam instancias singleton ou factories usam `get_`:

```python
# OK - singletons/factories
def get_settings() -> Settings
def get_supabase_client() -> Client
def get_anthropic_client() -> Anthropic
def get_logger(name: str) -> Logger
```

### Metodos de Classe

Metodos internos de classes seguem o mesmo padrao, mas `adicionar_*` eh aceito para colecoes:

```python
class Session:
    def adicionar_mensagem(self, msg)  # OK - adiciona a colecao
    def get_contexto(self)             # OK - getter de estado
```

## Async

Todas as funcoes que fazem I/O devem ser async:

- Queries ao banco de dados
- Chamadas a APIs externas (WhatsApp, Slack, LLM)
- Operacoes de cache Redis

```python
# Correto
async def buscar_medico_por_telefone(telefone: str) -> dict:
    response = await supabase.table("clientes")...

# Incorreto
def buscar_medico_por_telefone(telefone: str) -> dict:
    response = supabase.table("clientes")...
```

## Type Hints

Todas as funcoes devem ter type hints completos:

```python
# Correto
async def buscar_vagas(
    especialidade_id: Optional[str] = None,
    limite: int = 10
) -> list[dict]:

# Incorreto
async def buscar_vagas(especialidade_id=None, limite=10):
```

## Docstrings

Funcoes publicas devem ter docstrings no formato Google:

```python
async def buscar_medico_por_telefone(telefone: str) -> Optional[dict]:
    """Busca medico pelo numero de telefone.

    Args:
        telefone: Numero do telefone no formato brasileiro

    Returns:
        Dict com dados do medico ou None se nao encontrado

    Raises:
        DatabaseError: Se erro de conexao com banco
    """
```

## Constantes

Constantes devem estar centralizadas em `app/core/config.py`:

```python
# Correto - usar settings
from app.core.config import settings

if count >= settings.RATE_LIMIT_HORA:
    return False

# Incorreto - constante hardcoded
LIMITE_HORA = 20

if count >= LIMITE_HORA:
    return False
```

## Imports

### Ordem de Imports

1. Standard library
2. Third-party packages
3. Local imports

```python
# Standard library
from datetime import datetime
from typing import Optional

# Third-party
from fastapi import HTTPException

# Local
from app.core.config import settings
from app.services.supabase import supabase
```

### Import do Supabase

Sempre usar import direto do singleton:

```python
# Correto
from app.services.supabase import supabase

response = supabase.table("clientes").select("*").execute()

# Incorreto
from app.services.supabase import get_supabase_client

client = get_supabase_client()
response = client.table("clientes").select("*").execute()
```

## Tratamento de Erros

### Exceptions Customizadas

Usar exceptions de `app/core/exceptions.py`:

- `DatabaseError` - erros de banco
- `ExternalAPIError` - erros de APIs externas
- `ValidationError` - erros de validacao
- `RateLimitError` - rate limit atingido
- `NotFoundError` - recurso nao encontrado

### Padrao de Query

```python
async def buscar_medico_por_telefone(telefone: str) -> Optional[dict]:
    try:
        response = supabase.table("clientes").select("*").eq("telefone", telefone).execute()
    except Exception as e:
        raise DatabaseError(f"Erro ao buscar medico: {e}")

    if not response.data:
        return None  # Ou raise NotFoundError se obrigatorio

    return response.data[0]
```

## Logging

Usar logging estruturado com contexto:

```python
import logging

logger = logging.getLogger(__name__)

# Com contexto
logger.info(f"Mensagem enviada", extra={
    "medico_id": medico_id,
    "conversa_id": conversa_id
})

# Evitar
logger.info(f"Mensagem enviada para {medico_id}")  # Dados no texto
```
