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

## Timezone (Sprint 40)

O projeto usa timezone centralizado em `app/core/timezone.py`:

- **UTC** para armazenamento no banco de dados
- **America/Sao_Paulo** para logica de negocio (horario comercial, schedules de jobs)

### Funcoes Disponiveis

| Funcao | Uso | Retorno |
|--------|-----|---------|
| `agora_utc()` | Timestamps para banco | datetime UTC |
| `agora_brasilia()` | Logica de negocio | datetime BRT |
| `para_brasilia(dt)` | Converter para BRT | datetime BRT |
| `para_utc(dt)` | Converter para UTC | datetime UTC |
| `iso_utc(dt)` | String ISO para banco | str |
| `formatar_data_brasilia(dt)` | Exibicao para usuario | str |

### Exemplos de Uso

```python
from app.core.timezone import agora_utc, agora_brasilia, iso_utc

# Para salvar no banco (sempre UTC)
supabase.table("eventos").insert({
    "created_at": iso_utc()  # ou agora_utc().isoformat()
})

# Para logica de horario comercial
hora_atual = agora_brasilia().hour
if hora_atual < 8 or hora_atual >= 20:
    return "Fora do horario comercial"

# Para verificar dia da semana (seg-sex = 0-4 em Brasilia)
if agora_brasilia().weekday() > 4:
    return "Final de semana"
```

### O Que NAO Fazer

```python
# ERRADO - datetime.now() usa timezone do servidor (UTC no Railway)
hora = datetime.now().hour  # Sera 3h a mais que Brasilia!

# ERRADO - datetime.utcnow() eh deprecated
dt = datetime.utcnow()

# CORRETO
from app.core.timezone import agora_brasilia, agora_utc
hora_brt = agora_brasilia().hour
dt_utc = agora_utc()
```

## Modulos de Extracao (Sprint 52-53)

O projeto usa modulos especializados para extracao de dados de conversas usando LLM.

### Estrutura de Modulos

| Modulo | Responsabilidade | Localizacao |
|--------|------------------|-------------|
| `extraction` | Extracao generica de insights de conversas | `app/services/extraction/` |
| `grupos/extrator_v2` | Extracao de vagas de grupos WhatsApp (regex) | `app/services/grupos/extrator_v2/` |
| `grupos/extrator_v3` | Extracao de vagas usando LLM unificado | `app/services/grupos/extrator_v2/extrator_llm.py` |

### Nomenclatura de Funcoes de Extracao

| Operacao | Prefixo | Exemplo |
|----------|---------|---------|
| Extrair dados via LLM | `extrair_` | `extrair_dados_conversa()`, `extrair_com_llm()` |
| Salvar dados extraidos | `salvar_` | `salvar_insight()`, `salvar_memorias_extraidas()` |
| Gerar relatorio/output | `gerar_` | `gerar_relatorio_campanha()` |
| Buscar dados extraidos | `buscar_` | `buscar_insights_conversa()`, `buscar_insights_cliente()` |
| Converter formato | `converter_` | `converter_para_vagas_atomicas()` |
| Normalizar dados | `_normalizar_` | `_normalizar_telefone()` (privada) |
| Parsear resposta | `_parsear_` | `_parsear_resposta()`, `_parsear_objecao()` (privada) |

### Convencoes Especificas

```python
# Extratores sempre retornam dataclasses tipadas
async def extrair_dados_conversa(context: ExtractionContext) -> ExtractionResult:
    """Extrai dados estruturados de um turno de conversa."""
    pass

# Cache usa hash MD5 do conteudo normalizado
def _gerar_cache_key(context: ExtractionContext) -> str:
    """Gera chave de cache baseada no conteudo."""
    content = f"{context.mensagem_medico}|{context.resposta_julia}"
    hash_value = hashlib.md5(content.encode()).hexdigest()
    return f"{CACHE_PREFIX}{hash_value}"

# Funcoes privadas de LLM usam retry decorator
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def _chamar_llm(prompt: str) -> tuple[str, int, int]:
    """Chama o LLM para extracao com retry."""
    pass

# Sempre retornar metricas de tokens e latencia
result.tokens_input = tokens_input
result.tokens_output = tokens_output
result.latencia_ms = int((time.time() - start_time) * 1000)
```

## Pipeline de Grupos v2/v3 (Sprint 51-53)

Pipeline de extracao de vagas de mensagens de grupos WhatsApp.

### Estrutura de Pipeline

| Componente | Responsabilidade | Arquivo |
|------------|------------------|---------|
| Parser | Classifica linhas por tipo (LOCAL, DATA, VALOR) | `parser_mensagem.py` |
| Extratores | Extraem dados especificos (hospitais, datas, valores) | `extrator_*.py` |
| Gerador | Combina dados em vagas atomicas | `gerador_vagas.py` |
| Pipeline v2 | Orquestra extratores regex | `pipeline.py` |
| Pipeline v3 | Extracao unificada via LLM | `extrator_llm.py` |

### Nomenclatura de Funcoes

| Operacao | Prefixo | Exemplo |
|----------|---------|---------|
| Extrair componente | `extrair_` | `extrair_hospitais()`, `extrair_datas_periodos()` |
| Parsear mensagem | `parsear_` | `parsear_mensagem()` |
| Gerar vagas | `gerar_` | `gerar_vagas()` |
| Validar vagas | `validar_` | `validar_vagas()` |
| Deduplicar vagas | `deduplicar_` | `deduplicar_vagas()` |
| Normalizar dado | `_normalizar_` | `_normalizar_telefone()` (privada) |
| Converter tipo | `_*_from_str` | `_dia_semana_from_str()`, `_periodo_from_str()` |

### Convencoes Especificas

```python
# Funcao principal de pipeline sempre retorna ResultadoExtracaoV2
async def extrair_vagas_v2(
    texto: str,
    mensagem_id: Optional[UUID] = None,
    grupo_id: Optional[UUID] = None,
    data_referencia: Optional[date] = None,
) -> ResultadoExtracaoV2:
    """Extrai vagas atomicas de uma mensagem de grupo."""
    pass

# Extratores recebem listas de linhas classificadas
def extrair_hospitais(linhas_local: List[str]) -> List[HospitalExtraido]:
    """Extrai hospitais das linhas de LOCAL."""
    pass

# Sempre incluir confianca no resultado
contato = ContatoExtraido(
    nome=nome,
    whatsapp=telefone_normalizado,
    whatsapp_raw=telefone_raw,
    confianca=0.95  # Alta confianca se nome + telefone
)

# Warnings sao strings descritivas, nao exceptions
warnings.append("hospital_extraido_texto_completo")
warnings.append("sem_valor_extraido")
```

## Endpoints SSE (Sprint 54)

Server-Sent Events para atualizacoes em tempo real.

### Estrutura de Endpoint SSE

```python
@router.get("/dashboard/sse/conversations/{conversation_id}")
async def stream_conversation(conversation_id: str):
    """Stream SSE de eventos para uma conversa."""

    async def event_generator():
        """Gera eventos SSE via polling do banco."""
        # Estado inicial
        last_message_at = None

        # Evento de conexao
        yield f"event: connected\ndata: {json.dumps({'conversation_id': conversation_id})}\n\n"

        while True:
            await asyncio.sleep(POLL_INTERVAL)

            # Detectar mudancas
            if current_msg_at != last_message_at:
                yield f"event: new_message\ndata: {json.dumps({'last_message_at': current_msg_at})}\n\n"

            # Heartbeat
            yield f": heartbeat {datetime.now(timezone.utc).isoformat()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

### Convencoes Especificas

| Convencao | Regra |
|-----------|-------|
| Nome do endpoint | `/dashboard/sse/{recurso}/{id}` |
| Event generator | Funcao interna async `event_generator()` |
| Eventos nomeados | `event: nome_evento\ndata: json\n\n` |
| Heartbeat | `": heartbeat {timestamp}\n\n"` (comentario SSE) |
| Headers obrigatorios | `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no` |
| Polling interval | Constante `POLL_INTERVAL` no topo do arquivo |
| Estado inicial | Sempre enviar evento `connected` primeiro |

## Sistema de Incidentes (Sprint 55)

Endpoints para registro e consulta de incidentes de saude do sistema.

### Estrutura de Endpoints

```python
@router.post("/incidents")
async def registrar_incidente(request: RegistrarIncidenteRequest):
    """Registra uma mudanca de status."""
    pass

@router.get("/incidents")
async def listar_incidentes(limit: int = 20, status: Optional[str] = None):
    """Lista historico de incidentes."""
    pass

@router.get("/incidents/stats")
async def estatisticas_incidentes(dias: int = 30):
    """Retorna estatisticas de incidentes."""
    pass
```

### Convencoes Especificas

| Convencao | Regra |
|-----------|-------|
| Request/Response models | Sempre usar Pydantic BaseModel |
| Funcoes auxiliares | Prefixo `_` para funcoes privadas de resolucao |
| Metricas calculadas | MTTR, uptime_percent, etc em `stats` endpoint |
| Timestamps | Sempre usar `agora_utc().isoformat()` |
| Resolucao automatica | Funcao `_resolver_incidente_ativo()` privada |

```python
# Request sempre com defaults razoaveis
class RegistrarIncidenteRequest(BaseModel):
    from_status: Optional[str] = None
    to_status: str
    trigger_source: str = "api"
    details: Optional[dict] = None

# Response sempre com campos completos
class IncidenteResponse(BaseModel):
    id: str
    from_status: Optional[str]
    to_status: str
    started_at: str
    resolved_at: Optional[str]
    duration_seconds: Optional[int]

# Funcao de resolucao eh privada e async
async def _resolver_incidente_ativo():
    """Resolve o incidente critico ativo (se houver)."""
    pass
```

## Agente Helena (Sprint 47)

Agente de analytics para Slack com capacidade de SQL dinamico.

### Estrutura de Agente

| Componente | Responsabilidade | Arquivo |
|------------|------------------|---------|
| Agent | Logica principal do agente | `agent.py` |
| Session | Gerenciamento de sessao | `session.py` |
| Prompts | System prompts | `prompts.py` |
| Tools | Ferramentas disponiveis | `app/tools/helena/` |

### Nomenclatura de Metodos

| Operacao | Prefixo | Exemplo |
|----------|---------|---------|
| Processar mensagem | `processar_` | `processar_mensagem()` |
| Chamar LLM | `_chamar_` | `_chamar_llm()` (privado) |
| Processar resposta | `_processar_` | `_processar_resposta()` (privado) |
| Verificar condicao | `_*_incompleta` | `_resposta_incompleta()` (privado) |
| Carregar dados | `carregar` | `carregar()` (sem prefixo para session) |
| Salvar dados | `salvar` | `salvar()` (sem prefixo para session) |

### Convencoes Especificas

```python
# Agente sempre recebe user_id e channel_id no construtor
class AgenteHelena:
    def __init__(self, user_id: str, channel_id: str):
        self.user_id = user_id
        self.channel_id = channel_id
        self.session = SessionManager(user_id, channel_id)

# Processar mensagem retorna string formatada para Slack
async def processar_mensagem(self, texto: str) -> str:
    """Processa mensagem do usuario."""
    # Sempre carregar sessao primeiro
    await self.session.carregar()
    self.session.adicionar_mensagem("user", texto)

    # Processar
    resposta = await self._chamar_llm()

    # Sempre salvar sessao
    await self.session.salvar()
    return resposta

# Lazy load de tools para evitar import circular
def _get_tools(self) -> list:
    if self._tools is None:
        from app.tools.helena import HELENA_TOOLS
        self._tools = HELENA_TOOLS
    return self._tools

# SessionManager sempre usa dataclass para estado
@dataclass
class HelenaSession:
    user_id: str
    channel_id: str
    mensagens: list = field(default_factory=list)
    contexto: dict = field(default_factory=dict)

# Constantes de configuracao no topo do arquivo
SESSION_TTL_MINUTES = 30
MAX_MESSAGES = 20
MAX_TOOL_ITERATIONS = 5
```
