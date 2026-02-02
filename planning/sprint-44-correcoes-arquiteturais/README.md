# Sprint 44 - Correções Arquiteturais Completas

**Início:** 03/02/2026
**Duração:** 4 semanas (8 épicos)
**Objetivo:** Corrigir 100% dos problemas identificados na análise arquitetural de 02/02/2026

---

## Resumo da Sprint

| Épico | Área | Tarefas | Críticas | Story Points |
|-------|------|---------|----------|--------------|
| E01 | Bugs Críticos & Race Conditions | 8 | 3 | 21 |
| E02 | Arquitetura de Agente | 7 | 2 | 18 |
| E03 | Pipeline & Orquestração | 5 | 1 | 13 |
| E04 | Banco de Dados | 12 | 3 | 21 |
| E05 | Frontend/Dashboard | 12 | 2 | 18 |
| E06 | Performance & Escalabilidade | 10 | 2 | 16 |
| E07 | Observabilidade & Logging | 6 | 0 | 8 |
| E08 | Testes & Documentação | 4 | 0 | 5 |
| **TOTAL** | | **64** | **13** | **120** |

---

## Épico 01: Bugs Críticos & Race Conditions

**Prioridade:** P0 - Semana 1
**Owner:** Backend Senior

### T01.1 - [CRÍTICO] Fix Race Condition Deduplicação Webhook
**Arquivo:** `app/api/routes/webhook.py:54-66`
**Story Points:** 3

**Problema:**
```python
# ATUAL - Race condition entre verificação e marcação
if await _mensagem_ja_processada(message_id):
    return JSONResponse({"status": "ignored"})
await _marcar_mensagem_processada(message_id)  # Não atômico!
```

**Solução:**
```python
async def _marcar_se_nao_processada(message_id: str) -> bool:
    """Operação atômica: retorna True se marcou, False se já existia."""
    result = await redis_client.set(
        f"evolution:msg:{message_id}",
        "1",
        nx=True,  # SET if Not eXists
        ex=300    # TTL 5 minutos
    )
    return result is not None

# Uso no webhook
if not await _marcar_se_nao_processada(message_id):
    logger.debug(f"Mensagem {message_id} já processada, ignorando duplicata")
    return JSONResponse({"status": "ignored", "reason": "duplicate"})
```

**Testes:**
- [ ] Teste unitário com mock Redis
- [ ] Teste de concorrência com 100 requisições simultâneas
- [ ] Teste de integração com Evolution API

---

### T01.2 - [CRÍTICO] Fix Rate Limiting Fail-Open
**Arquivo:** `app/services/rate_limiter.py:98-121`
**Story Points:** 3

**Problema:**
```python
except Exception as e:
    logger.error(f"Erro ao verificar limite hora: {e}")
    return True, 0  # PERMITE envio em caso de erro!
```

**Solução:**
```python
async def verificar_limite_hora(cliente_id: str, tipo: TipoMensagem) -> tuple[bool, int]:
    try:
        # Verificação principal via Redis
        return await _verificar_limite_redis(cliente_id, tipo)
    except Exception as e:
        logger.warning(f"Redis falhou, tentando fallback Supabase: {e}")
        try:
            # Fallback para banco de dados
            return await _verificar_limite_supabase(cliente_id, tipo)
        except Exception as e2:
            logger.error(f"Fallback também falhou: {e2}")
            # FAIL-CLOSED: bloqueia se ambos falharem
            return False, 0

async def _verificar_limite_supabase(cliente_id: str, tipo: TipoMensagem) -> tuple[bool, int]:
    """Fallback: conta mensagens na última hora via banco."""
    uma_hora_atras = datetime.now(timezone.utc) - timedelta(hours=1)
    result = supabase.table("interacoes") \
        .select("id", count="exact") \
        .eq("cliente_id", cliente_id) \
        .eq("direcao", "enviada") \
        .gte("created_at", uma_hora_atras.isoformat()) \
        .execute()

    count = result.count or 0
    limite = LIMITES_POR_TIPO.get(tipo, 20)
    return count < limite, count
```

**Testes:**
- [ ] Teste com Redis indisponível
- [ ] Teste com Supabase indisponível
- [ ] Teste com ambos indisponíveis (deve bloquear)

---

### T01.3 - [CRÍTICO] Fix Circuit Breaker Thread-Safe
**Arquivo:** `app/services/circuit_breaker.py:154-189`
**Story Points:** 3

**Problema:**
```python
def _registrar_falha(self, erro: Exception, tipo_erro: ErrorType):
    self.falhas_consecutivas += 1  # Race condition!
```

**Solução:**
```python
import asyncio
from dataclasses import dataclass, field

@dataclass
class CircuitBreaker:
    nome: str
    # ... outros campos
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    async def _registrar_falha(self, erro: Exception, tipo_erro: ErrorType):
        async with self._lock:
            self.ultima_falha = datetime.now(timezone.utc)
            self.ultimo_erro_tipo = tipo_erro
            self.falhas_consecutivas += 1

            if self.falhas_consecutivas >= self.max_falhas:
                await self._transicionar(CircuitState.OPEN, f"falhas: {self.falhas_consecutivas}")

    async def _registrar_sucesso(self):
        async with self._lock:
            self.falhas_consecutivas = 0
            self.ultimo_sucesso = datetime.now(timezone.utc)

            if self.estado == CircuitState.HALF_OPEN:
                self.tentativas_half_open = 0
                await self._transicionar(CircuitState.CLOSED, "recuperado")
```

**Testes:**
- [ ] Teste de concorrência com múltiplas falhas simultâneas
- [ ] Teste de transição de estado thread-safe

---

### T01.4 - [ALTO] Fix Acesso Não Guardado a .data[0]
**Arquivos:** Múltiplos (12 ocorrências identificadas)
**Story Points:** 2

**Problema:**
```python
if vaga.data:
    vaga_data = vaga.data[0]  # IndexError se data for []
```

**Solução:**
```python
def safe_first(result) -> dict | None:
    """Retorna primeiro item ou None se vazio."""
    if result.data and len(result.data) > 0:
        return result.data[0]
    return None

# Uso
vaga_data = safe_first(vaga)
if not vaga_data:
    return {"success": False, "error": "Vaga não encontrada"}
```

**Arquivos a corrigir:**
- [ ] `app/tools/slack/vagas.py:199`
- [ ] `app/services/vagas/repository.py:45`
- [ ] `app/services/cliente.py:78`
- [ ] `app/services/conversa.py:92`
- [ ] `app/services/chips/selector.py:216`
- [ ] (7 outros arquivos - listar após grep)

---

### T01.5 - [ALTO] Fix Opt-Out Bypass em Campanhas
**Arquivo:** `app/services/campanha.py:295-365`
**Story Points:** 2

**Problema:** Campanhas não filtram opted-out na segmentação.

**Solução:**
```python
async def criar_envios_campanha(campanha_id: str, filtros: dict) -> int:
    # Buscar destinatários
    destinatarios = await segmentacao_service.buscar_segmento(filtros, limite=10000)

    # NOVO: Filtrar opted-out ANTES de enfileirar
    destinatarios = [
        d for d in destinatarios
        if not d.get("opted_out") and not d.get("optado_saida")
    ]

    logger.info(f"Campanha {campanha_id}: {len(destinatarios)} destinatários após filtro opt-out")

    # Continuar com enfileiramento
    for dest in destinatarios:
        # ...
```

---

### T01.6 - [ALTO] Fix Timeout de LLM sem Resposta
**Arquivo:** `app/services/agente.py:310-433`
**Story Points:** 3

**Solução:**
```python
TIMEOUT_GERACAO_RESPOSTA = 60  # segundos

async def gerar_resposta_julia(...) -> str:
    try:
        return await asyncio.wait_for(
            _gerar_resposta_julia_impl(...),
            timeout=TIMEOUT_GERACAO_RESPOSTA
        )
    except asyncio.TimeoutError:
        logger.error(f"Timeout ao gerar resposta para conversa {conversa_id}")
        # Retorna mensagem de fallback
        return "Desculpa, tive um probleminha aqui. Pode repetir?"
```

---

### T01.7 - [ALTO] Fix Handoff Silencioso
**Arquivo:** `app/services/handoff/flow.py:122-126`
**Story Points:** 3

**Solução:**
```python
async def criar_handoff(...) -> Handoff:
    # ... criar handoff no banco

    # Notificar com retry
    notificado = False
    for attempt in range(3):
        try:
            await notificar_handoff(conversa, handoff)
            notificado = True
            break
        except Exception as e:
            logger.warning(f"Tentativa {attempt + 1} de notificação falhou: {e}")
            await asyncio.sleep(2 ** attempt)  # Backoff exponencial

    if not notificado:
        # Fallback: criar alerta crítico no dashboard
        await criar_alerta_critico(
            tipo="handoff_sem_notificacao",
            conversa_id=conversa["id"],
            handoff_id=handoff.id,
            mensagem=f"Handoff criado mas notificação falhou após 3 tentativas"
        )
        # Também enviar email de emergência
        await enviar_email_emergencia(
            assunto="[CRÍTICO] Handoff sem notificação",
            corpo=f"Conversa {conversa['id']} aguarda atendimento humano"
        )

    return handoff
```

---

### T01.8 - [ALTO] Fix Chip Selection Race Condition
**Arquivo:** `app/services/chips/selector.py:361-375`
**Story Points:** 2

**Solução:**
```python
async def selecionar_chip_com_reserva(tipo_mensagem: str) -> Chip | None:
    """Seleciona chip com reserva atômica via Redis."""
    hora_atual = datetime.now(timezone.utc).strftime("%Y%m%d%H")

    # Buscar chips ativos ordenados por trust
    chips = await _listar_chips_ativos()

    for chip in chips:
        # Tentar reservar slot atomicamente
        key = f"chip:{chip.id}:hora:{hora_atual}"
        count = await redis_client.incr(key)

        # Definir TTL na primeira vez
        if count == 1:
            await redis_client.expire(key, 3700)  # 1h + margem

        # Verificar se dentro do limite
        if count <= chip.limite_hora:
            return chip
        else:
            # Reverter incremento se ultrapassou
            await redis_client.decr(key)

    logger.warning("Nenhum chip disponível dentro dos limites")
    return None
```

---

## Épico 02: Arquitetura de Agente

**Prioridade:** P1 - Semana 1-2
**Owner:** Backend Senior

### T02.1 - [CRÍTICO] Adicionar Timeout Global no Loop de Tools
**Arquivo:** `app/services/agente.py:364-416`
**Story Points:** 2

**Solução:**
```python
TIMEOUT_LOOP_TOOLS = 60  # segundos para todo o loop

async def gerar_resposta_com_tools(...) -> dict:
    try:
        return await asyncio.wait_for(
            _gerar_resposta_com_tools_impl(...),
            timeout=TIMEOUT_LOOP_TOOLS
        )
    except asyncio.TimeoutError:
        logger.error("Timeout no loop de tools")
        return {
            "resposta": "Desculpa, demorei demais aqui. Pode repetir o que precisa?",
            "tool_use": False,
            "timeout": True
        }
```

---

### T02.2 - [CRÍTICO] Integrar Response Validator no Fluxo
**Arquivo:** `app/services/agente.py` + `app/services/conversation_mode/response_validator.py`
**Story Points:** 3

**Solução:**
```python
from app.services.conversation_mode.response_validator import (
    validar_resposta_julia,
    FALLBACK_RESPONSES
)

async def gerar_resposta_julia(...) -> str:
    resposta = await _gerar_resposta_julia_impl(...)

    # NOVO: Validar resposta antes de retornar
    valida, violacao = validar_resposta_julia(
        resposta=resposta,
        mode=conversation_mode,
        conversa_id=conversa_id
    )

    if not valida:
        logger.warning(f"Resposta violou guardrail: {violacao}")
        # Usar fallback seguro
        if violacao in FALLBACK_RESPONSES:
            return FALLBACK_RESPONSES[violacao]
        # Fallback genérico
        return "Deixa eu verificar isso melhor e já te retorno!"

    return resposta
```

---

### T02.3 - [ALTO] Implementar Summarization de Conversas
**Arquivo:** `app/services/contexto.py` (novo: `app/services/summarization.py`)
**Story Points:** 5

**Solução:**
```python
# app/services/summarization.py
LIMITE_MENSAGENS_SEM_RESUMO = 10
MODELO_SUMMARIZATION = "claude-3-5-haiku-20241022"

async def obter_historico_com_resumo(conversa_id: str, limite: int = 10) -> list[dict]:
    """Retorna histórico com resumo se conversa for longa."""
    # Contar total de mensagens
    total = await contar_interacoes(conversa_id)

    if total <= limite:
        # Conversa curta: retornar tudo
        return await carregar_historico(conversa_id, limite=limite)

    # Conversa longa: buscar ou criar resumo
    resumo = await buscar_resumo_conversa(conversa_id)

    if not resumo or resumo["ultima_interacao_id"] != await obter_ultima_interacao_id(conversa_id):
        # Resumo desatualizado: regenerar
        resumo = await gerar_resumo_conversa(conversa_id)

    # Retornar resumo + últimas N mensagens
    ultimas = await carregar_historico(conversa_id, limite=5)

    return [
        {"role": "system", "content": f"[RESUMO DA CONVERSA ANTERIOR]\n{resumo['conteudo']}"},
        *ultimas
    ]

async def gerar_resumo_conversa(conversa_id: str) -> dict:
    """Gera resumo usando LLM."""
    historico = await carregar_historico(conversa_id, limite=50)

    prompt = """Resuma esta conversa em 2-3 parágrafos, destacando:
    1. Informações sobre o médico (especialidade, preferências, objeções)
    2. Vagas discutidas e status
    3. Próximos passos acordados

    Conversa:
    {historico}
    """

    resumo_texto = await gerar_resposta_llm(
        prompt=prompt.format(historico=formatar_historico(historico)),
        model=MODELO_SUMMARIZATION,
        max_tokens=500
    )

    # Salvar resumo
    resumo = await salvar_resumo_conversa(conversa_id, resumo_texto)
    return resumo
```

---

### T02.4 - [ALTO] Refatorar agente.py em Módulos
**Arquivo:** `app/services/agente.py` (1012 linhas)
**Story Points:** 5

**Nova estrutura:**
```
app/services/julia/
├── __init__.py
├── orchestrator.py      # Orquestração principal (já existe, expandir)
├── tool_executor.py     # Execução de tools
├── response_handler.py  # Validação e formatação de respostas
├── context_builder.py   # Construção de contexto
├── event_emitter.py     # Emissão de business events
└── legacy.py            # Funções legadas (deprecar gradualmente)
```

---

### T02.5 - [MÉDIO] Implementar Registry Pattern para Tools
**Arquivo:** `app/tools/registry.py` (novo)
**Story Points:** 3

**Solução:**
```python
# app/tools/registry.py
from typing import Callable, Dict, Any
from functools import wraps

_TOOL_REGISTRY: Dict[str, dict] = {}

def register_tool(
    name: str,
    description: str,
    input_schema: dict,
    requires_confirmation: bool = False
):
    """Decorator para registrar tools automaticamente."""
    def decorator(func: Callable):
        _TOOL_REGISTRY[name] = {
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "handler": func,
            "requires_confirmation": requires_confirmation
        }

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapper
    return decorator

def get_tool(name: str) -> dict | None:
    return _TOOL_REGISTRY.get(name)

def get_all_tools() -> list[dict]:
    return [
        {k: v for k, v in tool.items() if k != "handler"}
        for tool in _TOOL_REGISTRY.values()
    ]

async def execute_tool(name: str, input_data: dict, context: dict) -> dict:
    tool = get_tool(name)
    if not tool:
        return {"success": False, "error": f"Tool desconhecida: {name}"}

    try:
        return await tool["handler"](input_data, context)
    except Exception as e:
        logger.error(f"Erro ao executar tool {name}: {e}")
        return {"success": False, "error": str(e)}

# Uso:
@register_tool(
    name="buscar_vagas",
    description="Busca vagas de plantão disponíveis",
    input_schema={
        "type": "object",
        "properties": {
            "especialidade": {"type": "string"},
            "localizacao": {"type": "string"}
        }
    }
)
async def handle_buscar_vagas(input_data: dict, context: dict) -> dict:
    # Implementação
    pass
```

---

### T02.6 - [MÉDIO] Centralizar Configurações Hardcoded
**Arquivo:** `app/core/settings.py`
**Story Points:** 2

**Adicionar:**
```python
# LLM Settings
LLM_MAX_TOKENS: int = Field(default=300, env="LLM_MAX_TOKENS")
LLM_MAX_TOOL_ITERATIONS: int = Field(default=3, env="LLM_MAX_TOOL_ITERATIONS")
LLM_TIMEOUT_SEGUNDOS: int = Field(default=30, env="LLM_TIMEOUT_SEGUNDOS")
LLM_LOOP_TIMEOUT_SEGUNDOS: int = Field(default=60, env="LLM_LOOP_TIMEOUT_SEGUNDOS")

# Cache Settings
CACHE_TTL_PROMPTS: int = Field(default=300, env="CACHE_TTL_PROMPTS")
CACHE_TTL_CONTEXTO: int = Field(default=60, env="CACHE_TTL_CONTEXTO")

# Rate Limiting
RATE_LIMIT_HORA: int = Field(default=20, env="RATE_LIMIT_HORA")
RATE_LIMIT_DIA: int = Field(default=100, env="RATE_LIMIT_DIA")
RATE_LIMIT_INTERVALO_MIN: int = Field(default=45, env="RATE_LIMIT_INTERVALO_MIN")
RATE_LIMIT_INTERVALO_MAX: int = Field(default=180, env="RATE_LIMIT_INTERVALO_MAX")

# Pipeline
PIPELINE_MAX_CONCURRENT: int = Field(default=10, env="PIPELINE_MAX_CONCURRENT")
```

---

### T02.7 - [BAIXO] Adicionar Tracing para Conhecimento RAG
**Arquivo:** `app/services/conhecimento/orquestrador.py`
**Story Points:** 1

**Solução:**
```python
async def analisar_situacao(...) -> ContextoSituacao:
    # ... análise

    # NOVO: Log detalhado para debugging
    logger.info(
        "RAG analysis complete",
        extra={
            "conversa_id": conversa_id,
            "chunks_encontrados": len(resultado.chunks),
            "chunk_ids": [c.id for c in resultado.chunks[:5]],
            "scores": [c.score for c in resultado.chunks[:5]],
            "objecao_detectada": resultado.objecao,
            "perfil_detectado": resultado.perfil,
            "tempo_ms": (time.time() - inicio) * 1000
        }
    )

    return resultado
```

---

## Épico 03: Pipeline & Orquestração

**Prioridade:** P1 - Semana 2
**Owner:** Backend Senior

### T03.1 - [ALTO] Adicionar Distributed Lock no ChipOrchestrator
**Arquivo:** `app/services/chips/orchestrator.py:619-670`
**Story Points:** 3

**Solução:**
```python
from app.services.redis import redis_client

class DistributedLock:
    def __init__(self, key: str, timeout: int = 300):
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.token = str(uuid.uuid4())

    async def __aenter__(self):
        acquired = await redis_client.set(
            self.key, self.token, nx=True, ex=self.timeout
        )
        if not acquired:
            raise LockNotAcquiredError(f"Could not acquire lock: {self.key}")
        return self

    async def __aexit__(self, *args):
        # Só libera se ainda for o dono
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        await redis_client.eval(script, 1, self.key, self.token)

# Uso no orchestrator
async def executar_ciclo(self):
    try:
        async with DistributedLock("chip_orchestrator_cycle", timeout=300):
            await self._executar_ciclo_impl()
    except LockNotAcquiredError:
        logger.info("Outro processo já está executando o ciclo de chips")
```

---

### T03.2 - [MÉDIO] Converter ProcessorContext para Imutável
**Arquivo:** `app/pipeline/base.py:12-24`
**Story Points:** 3

**Solução:**
```python
from dataclasses import dataclass, replace
from typing import FrozenSet

@dataclass(frozen=True)
class ProcessorContext:
    """Contexto imutável compartilhado entre processadores."""
    mensagem_raw: dict
    mensagem_texto: str = ""
    telefone: str = ""
    medico: dict | None = None
    conversa: dict | None = None
    metadata: tuple = ()  # Imutável

    def with_updates(self, **kwargs) -> "ProcessorContext":
        """Retorna novo contexto com campos atualizados."""
        return replace(self, **kwargs)

    def add_metadata(self, key: str, value: any) -> "ProcessorContext":
        """Retorna novo contexto com metadata adicional."""
        new_metadata = dict(self.metadata) if self.metadata else {}
        new_metadata[key] = value
        return replace(self, metadata=tuple(new_metadata.items()))

# Processadores retornam novo contexto
class PreProcessor(ABC):
    @abstractmethod
    async def process(self, context: ProcessorContext) -> tuple[ProcessorResult, ProcessorContext]:
        """Processa e retorna (resultado, novo_contexto)."""
        pass
```

---

### T03.3 - [MÉDIO] Separar pre_processors.py em Módulos
**Arquivo:** `app/pipeline/pre_processors.py` (923 linhas)
**Story Points:** 3

**Nova estrutura:**
```
app/pipeline/processors/
├── __init__.py
├── parse.py           # ParseMessageProcessor
├── presence.py        # PresenceProcessor
├── entities.py        # LoadEntitiesProcessor
├── chip_mapping.py    # ChipMappingProcessor
├── business_events.py # BusinessEventInboundProcessor
├── chatwoot.py        # ChatwootSyncProcessor
├── optout.py          # OptOutProcessor
├── bot_detection.py   # BotDetectionProcessor
├── media.py           # MediaProcessor
├── long_message.py    # LongMessageProcessor
├── handoff.py         # HandoffTriggerProcessor, HandoffKeywordProcessor
└── human_control.py   # HumanControlProcessor
```

---

### T03.4 - [MÉDIO] Implementar Idempotência em Workers
**Arquivo:** `app/workers/fila_worker.py`
**Story Points:** 3

**Solução:**
```python
async def processar_mensagem_idempotente(mensagem: dict) -> bool:
    """Processa mensagem com garantia de idempotência."""
    idempotency_key = f"fila:{mensagem['id']}"

    # Tentar marcar como em processamento
    acquired = await redis_client.set(
        idempotency_key,
        "processing",
        nx=True,
        ex=300  # 5 minutos
    )

    if not acquired:
        logger.info(f"Mensagem {mensagem['id']} já está sendo processada")
        return False

    try:
        # Processar
        resultado = await enviar_mensagem(mensagem)

        # Marcar como concluída
        await redis_client.set(idempotency_key, "completed", ex=3600)

        return True
    except Exception as e:
        # Marcar como falha para retry
        await redis_client.set(idempotency_key, f"failed:{e}", ex=300)
        raise
```

---

### T03.5 - [BAIXO] Adicionar Dead Letter Queue
**Arquivo:** `app/services/fila_mensagens.py`
**Story Points:** 2

**Solução:**
```python
MAX_RETRIES = 3

async def mover_para_dlq(mensagem: dict, erro: str):
    """Move mensagem para dead letter queue após falhas repetidas."""
    await supabase.table("fila_mensagens_dlq").insert({
        "mensagem_original_id": mensagem["id"],
        "conteudo": mensagem["conteudo"],
        "cliente_id": mensagem["cliente_id"],
        "erro": erro,
        "tentativas": mensagem.get("tentativas", 0),
        "created_at": datetime.now(timezone.utc).isoformat()
    }).execute()

    # Criar alerta
    await criar_alerta(
        tipo="mensagem_dlq",
        severidade="warning",
        mensagem=f"Mensagem {mensagem['id']} movida para DLQ após {MAX_RETRIES} falhas"
    )
```

---

## Épico 04: Banco de Dados

**Prioridade:** P1 - Semana 2-3
**Owner:** Backend + DBA

### T04.1 - [CRÍTICO] Implementar Transações para Operações Multi-Tabela
**Arquivo:** `app/services/vagas/repository.py` + migrations
**Story Points:** 5

**Solução via Supabase RPC:**
```sql
-- Migration: criar função de reserva transacional
CREATE OR REPLACE FUNCTION reservar_vaga_transacional(
    p_vaga_id UUID,
    p_cliente_id UUID,
    p_dados_reserva JSONB
) RETURNS JSONB AS $$
DECLARE
    v_vaga RECORD;
    v_result JSONB;
BEGIN
    -- Lock na vaga para evitar race condition
    SELECT * INTO v_vaga
    FROM vagas
    WHERE id = p_vaga_id
    FOR UPDATE NOWAIT;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'error', 'Vaga não encontrada');
    END IF;

    IF v_vaga.status != 'aberta' THEN
        RETURN jsonb_build_object('success', false, 'error', 'Vaga não está disponível');
    END IF;

    -- Atualizar vaga
    UPDATE vagas
    SET status = 'reservada',
        cliente_id = p_cliente_id,
        updated_at = NOW()
    WHERE id = p_vaga_id;

    -- Criar business event
    INSERT INTO business_events (event_type, cliente_id, vaga_id, event_props)
    VALUES ('vaga_reservada', p_cliente_id, p_vaga_id, p_dados_reserva);

    RETURN jsonb_build_object('success', true, 'vaga_id', p_vaga_id);
EXCEPTION
    WHEN lock_not_available THEN
        RETURN jsonb_build_object('success', false, 'error', 'Vaga em uso, tente novamente');
    WHEN OTHERS THEN
        RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$ LANGUAGE plpgsql;
```

```python
# Uso no Python
async def reservar_vaga(vaga_id: str, cliente_id: str, dados: dict) -> dict:
    result = supabase.rpc(
        "reservar_vaga_transacional",
        {
            "p_vaga_id": vaga_id,
            "p_cliente_id": cliente_id,
            "p_dados_reserva": dados
        }
    ).execute()

    return result.data
```

---

### T04.2 - [CRÍTICO] Fix Queries N+1 em Campanhas
**Arquivo:** `app/services/campanha.py:332-358`
**Story Points:** 3

**Solução:**
```python
async def criar_envios_campanha_batch(campanha_id: str, filtros: dict) -> int:
    """Cria envios em batch para evitar N+1."""
    destinatarios = await segmentacao_service.buscar_segmento(filtros, limite=10000)

    # Filtrar opted-out
    destinatarios = [d for d in destinatarios if not d.get("opted_out")]

    # Gerar mensagens em batch
    mensagens = await gerar_mensagens_batch(campanha_id, destinatarios)

    # Inserir em batch
    envios = [
        {
            "campanha_id": campanha_id,
            "cliente_id": dest["id"],
            "conteudo": msg,
            "status": "pendente",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        for dest, msg in zip(destinatarios, mensagens)
    ]

    # Batch insert (chunks de 1000)
    for i in range(0, len(envios), 1000):
        chunk = envios[i:i+1000]
        await supabase.table("fila_mensagens").insert(chunk).execute()

    return len(envios)
```

---

### T04.3 - [CRÍTICO] Implementar Particionamento de Tabelas
**Story Points:** 5

**Migration:**
```sql
-- Particionar interacoes por mês
CREATE TABLE interacoes_partitioned (
    id UUID DEFAULT gen_random_uuid(),
    conversation_id UUID,
    cliente_id UUID,
    tipo VARCHAR(50),
    conteudo TEXT,
    direcao VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Criar partições para 12 meses
CREATE TABLE interacoes_2026_01 PARTITION OF interacoes_partitioned
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE interacoes_2026_02 PARTITION OF interacoes_partitioned
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
-- ... até 2026_12

-- Função para criar partições automaticamente
CREATE OR REPLACE FUNCTION criar_particao_interacoes()
RETURNS void AS $$
DECLARE
    proximo_mes DATE := date_trunc('month', NOW()) + interval '1 month';
    nome_particao TEXT;
BEGIN
    nome_particao := 'interacoes_' || to_char(proximo_mes, 'YYYY_MM');

    IF NOT EXISTS (
        SELECT 1 FROM pg_tables WHERE tablename = nome_particao
    ) THEN
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF interacoes_partitioned
             FOR VALUES FROM (%L) TO (%L)',
            nome_particao,
            proximo_mes,
            proximo_mes + interval '1 month'
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Agendar criação automática
SELECT cron.schedule('criar-particoes', '0 0 25 * *', 'SELECT criar_particao_interacoes()');
```

---

### T04.4 - [ALTO] Substituir SELECT * por Campos Específicos
**Story Points:** 3

**Script de identificação e correção:**
```python
# scripts/fix_select_star.py
import re
import os

ARQUIVOS = [
    "app/services/interacao.py",
    "app/services/cliente.py",
    "app/services/conversa.py",
    "app/services/vagas/repository.py",
    "app/services/chips/selector.py",
    # ... mais arquivos
]

# Mapeamento de tabelas para campos necessários
CAMPOS_POR_TABELA = {
    "interacoes": "id, conversation_id, cliente_id, tipo, conteudo, direcao, created_at",
    "clientes": "id, telefone, primeiro_nome, crm, especialidade, status, opted_out",
    "conversations": "id, cliente_id, status, controlled_by, created_at, updated_at",
    "vagas": "id, hospital_id, especialidade_id, data, hora_inicio, hora_fim, valor, status",
    "chips": "id, telefone, instance_name, status, trust_score, msgs_enviadas_hoje",
}

def fix_select_star(content: str, tabela: str) -> str:
    campos = CAMPOS_POR_TABELA.get(tabela, "*")
    pattern = rf'\.table\("{tabela}"\)\.select\("\*"\)'
    replacement = f'.table("{tabela}").select("{campos}")'
    return re.sub(pattern, replacement, content)
```

---

### T04.5 - [ALTO] Adicionar LIMIT em Queries sem Limite
**Story Points:** 2

**Arquivos a corrigir:**
- [ ] `app/services/confirmacao_plantao.py:121-124`
- [ ] `app/tools/slack/medicos.py:145-164`
- [ ] `app/services/business_events/repository.py:188-226`

---

### T04.6 - [ALTO] Fix Race Condition em Business Events Dedupe
**Arquivo:** `app/services/business_events/repository.py:30-90`
**Story Points:** 2

**Solução:**
```sql
-- Usar INSERT ON CONFLICT para dedupe atômico
CREATE UNIQUE INDEX IF NOT EXISTS idx_business_events_dedupe
ON business_events(dedupe_key)
WHERE dedupe_key IS NOT NULL;
```

```python
async def emit_event(event: BusinessEvent) -> str:
    data = {
        "event_type": event.event_type,
        "cliente_id": event.cliente_id,
        "vaga_id": event.vaga_id,
        "event_props": event.event_props,
        "dedupe_key": event.dedupe_key,
    }

    # Insert com ON CONFLICT (dedupe atômico)
    result = supabase.table("business_events") \
        .upsert(data, on_conflict="dedupe_key", ignore_duplicates=True) \
        .execute()

    return result.data[0]["id"] if result.data else None
```

---

### T04.7 - [MÉDIO] Migrar Contagens para GROUP BY no Banco
**Arquivo:** `app/services/business_events/repository.py:188-226`
**Story Points:** 2

**Antes:**
```python
# Conta em Python
counts = {}
for row in response.data:
    event_type = row["event_type"]
    counts[event_type] = counts.get(event_type, 0) + 1
```

**Depois:**
```sql
-- Função RPC
CREATE OR REPLACE FUNCTION get_event_counts(
    p_hours INT DEFAULT 24,
    p_event_types TEXT[] DEFAULT NULL
) RETURNS TABLE(event_type TEXT, count BIGINT) AS $$
BEGIN
    RETURN QUERY
    SELECT
        be.event_type::TEXT,
        COUNT(*)::BIGINT
    FROM business_events be
    WHERE be.created_at > NOW() - (p_hours || ' hours')::INTERVAL
      AND (p_event_types IS NULL OR be.event_type = ANY(p_event_types))
    GROUP BY be.event_type;
END;
$$ LANGUAGE plpgsql;
```

---

### T04.8 - T04.12 - Outras Correções de DB
**Story Points:** 8 (total)

- [ ] T04.8: Criar views materializadas para métricas (SP: 2)
- [ ] T04.9: Implementar soft delete padronizado (SP: 2)
- [ ] T04.10: Adicionar índices faltantes (SP: 1)
- [ ] T04.11: Configurar archiving para tabelas antigas (SP: 2)
- [ ] T04.12: Documentar schema atualizado (SP: 1)

---

## Épico 05: Frontend/Dashboard

**Prioridade:** P2 - Semana 3
**Owner:** Frontend Developer

### T05.1 - [CRÍTICO] Adicionar Error Boundaries
**Story Points:** 2

```typescript
// dashboard/app/(dashboard)/error.tsx
'use client'

import { useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { AlertTriangle } from 'lucide-react'

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log para serviço de monitoramento
    console.error('Dashboard error:', error)
  }, [error])

  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
      <AlertTriangle className="h-12 w-12 text-destructive" />
      <h2 className="text-xl font-semibold">Algo deu errado</h2>
      <p className="text-muted-foreground text-center max-w-md">
        Ocorreu um erro ao carregar esta página. Tente novamente ou entre em contato com o suporte.
      </p>
      <div className="flex gap-2">
        <Button onClick={() => reset()}>Tentar novamente</Button>
        <Button variant="outline" onClick={() => window.location.href = '/dashboard'}>
          Voltar ao início
        </Button>
      </div>
      {process.env.NODE_ENV === 'development' && (
        <pre className="mt-4 p-4 bg-muted rounded text-xs max-w-lg overflow-auto">
          {error.message}
        </pre>
      )}
    </div>
  )
}
```

---

### T05.2 - [CRÍTICO] Converter Dashboard Layout para Server Component
**Arquivo:** `dashboard/app/(dashboard)/layout.tsx`
**Story Points:** 3

```typescript
// dashboard/app/(dashboard)/layout.tsx (Server Component)
import { Sidebar } from '@/components/layout/sidebar'
import { Header } from '@/components/layout/header'
import { BottomNav } from '@/components/layout/bottom-nav'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="bg-secondary min-h-screen">
      <aside className="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-64 lg:flex-col">
        <Sidebar />
      </aside>
      <div className="lg:pl-64">
        <Header />
        <main className="p-4 lg:p-6">{children}</main>
      </div>
      <BottomNav />
    </div>
  )
}

// dashboard/components/layout/bottom-nav.tsx (Client Component)
'use client'

import { usePathname } from 'next/navigation'
// ... resto da implementação
```

---

### T05.3 - [ALTO] Implementar SWR para Data Fetching
**Story Points:** 5

```typescript
// dashboard/lib/swr/config.ts
import { SWRConfig } from 'swr'

export const swrConfig = {
  fetcher: async (url: string) => {
    const res = await fetch(url)
    if (!res.ok) {
      const error = new Error('Erro ao carregar dados')
      error.info = await res.json()
      error.status = res.status
      throw error
    }
    return res.json()
  },
  revalidateOnFocus: false,
  dedupingInterval: 5000,
}

// dashboard/hooks/use-metrics.ts
import useSWR from 'swr'

export function useMetrics(period: string) {
  const { data, error, isLoading, mutate } = useSWR(
    `/api/dashboard/metrics?period=${period}`,
    {
      refreshInterval: 60000, // 1 minuto
    }
  )

  return {
    metrics: data,
    isLoading,
    isError: error,
    refresh: mutate,
  }
}

// Uso no componente
function MetricsPanel({ period }: { period: string }) {
  const { metrics, isLoading, isError, refresh } = useMetrics(period)

  if (isLoading) return <MetricsSkeleton />
  if (isError) return <ErrorState onRetry={refresh} />

  return <MetricsGrid data={metrics} />
}
```

---

### T05.4 - [ALTO] Adicionar Zod Validation em API Routes
**Story Points:** 3

```typescript
// dashboard/lib/validations/api.ts
import { z } from 'zod'

export const metricsQuerySchema = z.object({
  period: z.enum(['24h', '7d', '30d', '90d']).default('7d'),
  tipo: z.string().optional(),
})

export const chipActionSchema = z.object({
  chipId: z.string().uuid(),
  action: z.enum(['activate', 'deactivate', 'promote', 'demote']),
  reason: z.string().min(1).max(500).optional(),
})

// dashboard/app/api/dashboard/metrics/route.ts
import { NextRequest, NextResponse } from 'next/server'
import { metricsQuerySchema } from '@/lib/validations/api'

export async function GET(request: NextRequest) {
  const searchParams = Object.fromEntries(request.nextUrl.searchParams)

  const validation = metricsQuerySchema.safeParse(searchParams)
  if (!validation.success) {
    return NextResponse.json(
      { error: 'Invalid parameters', details: validation.error.flatten() },
      { status: 400 }
    )
  }

  const { period, tipo } = validation.data
  // ... resto da implementação
}
```

---

### T05.5 - T05.12 - Outras Correções de Frontend
**Story Points:** 10 (total)

- [ ] T05.5: Adicionar loading.tsx para Suspense (SP: 1)
- [ ] T05.6: Remover console.logs de produção (SP: 1)
- [ ] T05.7: Implementar Supabase Realtime para chat (SP: 3)
- [ ] T05.8: Adicionar React.memo em listas grandes (SP: 1)
- [ ] T05.9: Re-habilitar ESLint rules gradualmente (SP: 1)
- [ ] T05.10: Audit de acessibilidade (ARIA) (SP: 1)
- [ ] T05.11: Refatorar estado do dashboard (SP: 2)
- [ ] T05.12: Criar logging abstraction (SP: 1)

---

## Épico 06: Performance & Escalabilidade

**Prioridade:** P1 - Semana 2-3
**Owner:** Backend Senior

### T06.1 - [CRÍTICO] Aumentar Semáforo de Processamento
**Arquivo:** `app/api/routes/webhook.py:20-21`
**Story Points:** 1

```python
import os

MAX_CONCURRENT_MESSAGES = int(os.getenv("MAX_CONCURRENT_MESSAGES", "10"))
_semaforo_processamento = asyncio.Semaphore(MAX_CONCURRENT_MESSAGES)

# Adicionar métrica de uso
async def processar_webhook(...):
    logger.info(
        "Webhook received",
        extra={
            "semaphore_available": _semaforo_processamento._value,
            "semaphore_max": MAX_CONCURRENT_MESSAGES
        }
    )
    async with _semaforo_processamento:
        # ...
```

---

### T06.2 - [CRÍTICO] Criar HTTP Client Singleton
**Arquivo:** `app/services/http_client.py` (novo)
**Story Points:** 2

```python
# app/services/http_client.py
import httpx
from typing import Optional

_client: Optional[httpx.AsyncClient] = None

async def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
                keepalive_expiry=30.0
            ),
            http2=True,
        )
    return _client

async def close_http_client():
    global _client
    if _client:
        await _client.aclose()
        _client = None

# Registrar no shutdown da aplicação
# app/main.py
@app.on_event("shutdown")
async def shutdown_event():
    await close_http_client()
```

---

### T06.3 - [ALTO] Paralelizar Context Building
**Arquivo:** `app/services/contexto.py:267-350`
**Story Points:** 2

```python
async def montar_contexto_completo(...) -> ContextoConversa:
    # Buscar dados em paralelo
    historico, handoff, diretrizes, memorias = await asyncio.gather(
        carregar_historico(conversa["id"], limite=10),
        verificar_handoff_recente(conversa["id"]),
        carregar_diretrizes_ativas(),
        enriquecer_contexto_com_memorias(cliente_id, mensagem) if mensagem else None,
        return_exceptions=True
    )

    # Tratar possíveis exceções
    if isinstance(historico, Exception):
        logger.error(f"Erro ao carregar histórico: {historico}")
        historico = []

    # ... montar contexto
```

---

### T06.4 - [ALTO] Implementar Cache de Respostas LLM
**Arquivo:** `app/services/llm/cache.py` (novo)
**Story Points:** 3

```python
# app/services/llm/cache.py
import hashlib
from app.services.redis import redis_client

CACHE_TTL = 3600  # 1 hora
SIMILARITY_THRESHOLD = 0.95

async def get_cached_response(
    mensagem: str,
    contexto_hash: str,
) -> str | None:
    """Busca resposta em cache para mensagens similares."""
    cache_key = _gerar_cache_key(mensagem, contexto_hash)

    cached = await redis_client.get(cache_key)
    if cached:
        logger.info("Cache hit para resposta LLM")
        return cached

    return None

async def cache_response(
    mensagem: str,
    contexto_hash: str,
    resposta: str,
):
    """Armazena resposta no cache."""
    cache_key = _gerar_cache_key(mensagem, contexto_hash)
    await redis_client.set(cache_key, resposta, ex=CACHE_TTL)

def _gerar_cache_key(mensagem: str, contexto_hash: str) -> str:
    # Normalizar mensagem
    msg_normalizada = mensagem.lower().strip()
    combined = f"{msg_normalizada}:{contexto_hash}"
    return f"llm:resp:{hashlib.sha256(combined.encode()).hexdigest()[:16]}"
```

---

### T06.5 - [ALTO] Distribuir Circuit Breaker State via Redis
**Arquivo:** `app/services/circuit_breaker.py`
**Story Points:** 3

```python
class DistributedCircuitBreaker:
    """Circuit breaker com estado distribuído via Redis."""

    def __init__(self, nome: str, ...):
        self.nome = nome
        self.redis_key = f"circuit:{nome}"

    async def _get_state(self) -> dict:
        state = await redis_client.hgetall(self.redis_key)
        return {
            "estado": CircuitState(state.get("estado", "closed")),
            "falhas_consecutivas": int(state.get("falhas", 0)),
            "ultimo_erro": state.get("ultimo_erro"),
            "aberto_em": state.get("aberto_em"),
        }

    async def _set_state(self, **updates):
        await redis_client.hset(self.redis_key, mapping=updates)
        await redis_client.expire(self.redis_key, 3600)  # TTL 1h

    async def registrar_falha(self, erro: Exception):
        async with self._lock:
            falhas = await redis_client.hincrby(self.redis_key, "falhas", 1)
            await redis_client.hset(self.redis_key, "ultimo_erro", str(erro))

            if falhas >= self.max_falhas:
                await self._abrir()
```

---

### T06.6 - T06.10 - Outras Correções de Performance
**Story Points:** 5 (total)

- [ ] T06.6: Pre-compilar regex patterns (SP: 1)
- [ ] T06.7: Configurar connection pooling Supabase (SP: 1)
- [ ] T06.8: Adicionar jitter no retry (SP: 1)
- [ ] T06.9: Implementar métricas por componente (SP: 1)
- [ ] T06.10: Configurar alertas de degradação (SP: 1)

---

## Épico 07: Observabilidade & Logging

**Prioridade:** P2 - Semana 3-4
**Owner:** Backend + DevOps

### T07.1 - Implementar Logging Abstraction
**Story Points:** 2

```python
# app/core/logging.py
import structlog
from typing import Any

def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)

def configure_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.PrintLoggerFactory(),
    )

# Uso
logger = get_logger(__name__)
logger.info("mensagem", conversa_id=id, medico_id=mid)
```

---

### T07.2 - Padronizar Formato de Logs
**Story Points:** 1

```python
# Antes (inconsistente)
logger.info(f"Mensagem enviada para {telefone[:8]}...")
logger.info(f"ACK para {context.telefone[-4:]}...")

# Depois (padronizado)
def mask_phone(telefone: str) -> str:
    """Mascara telefone: 5511...1234"""
    if len(telefone) >= 8:
        return f"{telefone[:4]}...{telefone[-4:]}"
    return "****"

logger.info("Mensagem enviada", telefone=mask_phone(telefone))
```

---

### T07.3 - T07.6 - Outras Melhorias de Observabilidade
**Story Points:** 5 (total)

- [ ] T07.3: Adicionar trace_id em todos os logs (SP: 2)
- [ ] T07.4: Criar dashboard de métricas em tempo real (SP: 1)
- [ ] T07.5: Configurar alertas Slack para erros críticos (SP: 1)
- [ ] T07.6: Documentar runbook de troubleshooting (SP: 1)

---

## Épico 08: Testes & Documentação

**Prioridade:** P3 - Semana 4
**Owner:** QA + Tech Writer

### T08.1 - Adicionar Testes para Correções Críticas
**Story Points:** 3

```python
# tests/test_webhook_deduplication.py
import pytest
import asyncio
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_webhook_deduplication_race_condition():
    """Testa que mensagens duplicadas são rejeitadas atomicamente."""
    message_id = "test-msg-123"

    # Simular 100 requisições simultâneas
    async def process_webhook():
        return await _marcar_se_nao_processada(message_id)

    results = await asyncio.gather(*[process_webhook() for _ in range(100)])

    # Apenas uma deve ter sucesso
    assert sum(results) == 1


@pytest.mark.asyncio
async def test_rate_limit_fail_closed():
    """Testa que rate limiting bloqueia quando Redis e Supabase falham."""
    with patch('app.services.rate_limiter.redis_client') as mock_redis:
        with patch('app.services.rate_limiter.supabase') as mock_supabase:
            mock_redis.get.side_effect = Exception("Redis down")
            mock_supabase.table.side_effect = Exception("Supabase down")

            pode_enviar, _ = await verificar_limite_hora("cliente-1", TipoMensagem.PROSPECCAO)

            # Deve bloquear (fail-closed)
            assert pode_enviar is False
```

---

### T08.2 - Atualizar Documentação de Arquitetura
**Story Points:** 1

- [ ] Atualizar `docs/arquitetura/visao-geral.md`
- [ ] Documentar novos patterns implementados
- [ ] Criar diagrama de sequência atualizado

---

### T08.3 - Criar Runbook de Operações
**Story Points:** 1

```markdown
# Runbook: Problemas Comuns

## Circuit Breaker Aberto
1. Verificar logs: `railway logs | grep "circuit"`
2. Verificar status: `GET /health/circuits`
3. Se Evolution API down, aguardar recovery automático
4. Se persistir, forçar reset: `POST /admin/circuits/reset`

## Rate Limit Excedido
1. Verificar Redis: `redis-cli GET rate:*`
2. Se médico urgente, liberar manualmente: `POST /admin/rate-limit/override`

## Mensagens Duplicadas
1. Verificar Redis keys: `redis-cli KEYS evolution:msg:*`
2. Verificar TTL: `redis-cli TTL evolution:msg:<id>`
```

---

## Progresso (Atualizado: 02/02/2026)

### Semana 1 - MUST Items ✅ CONCLUÍDO

| Tarefa | Descrição | Status | Commit |
|--------|-----------|--------|--------|
| T01.1 | Fix Race Condition Webhook (Redis SETNX) | ✅ DONE | Sprint 44 |
| T01.2 | Fix Rate Limiting Fail-Closed | ✅ DONE | Sprint 44 |
| T01.3 | Fix Circuit Breaker Thread-Safe (asyncio.Lock) | ✅ DONE | Sprint 44 |
| T02.1 | Global Timeout para Tools Loop (60s) | ✅ DONE | Sprint 44 |
| T06.1 | Aumentar Semáforo para 10 (configurável) | ✅ DONE | Sprint 44 |
| T06.2 | HTTP Client Singleton com Connection Pooling | ✅ DONE | Sprint 44 |
| T02.2 | Response Validator integrado no fluxo | ✅ DONE | Sprint 44 |

### Semana 2 - Progresso

| Tarefa | Descrição | Status | Commit |
|--------|-----------|--------|--------|
| T01.4 | Fix Acesso Não Guardado a .data[0] | ✅ DONE | Criado `safe_first` utility |
| T01.5 | Fix Opt-Out Bypass em Campanhas | ✅ DONE | Sprint 44 |
| T01.7 | Fix Handoff Silencioso (retry + alerta) | ✅ DONE | Sprint 44 |
| T01.8 | Fix Chip Selection Race Condition | ✅ DONE | Redis INCR atômico |
| T02.3 | Implementar Summarization de Conversas | ✅ DONE | `julia/summarizer.py` |
| T03.1 | Distributed Lock no ChipOrchestrator | ✅ DONE | `core/distributed_lock.py` |
| T03.2 | ProcessorContext Imutável (híbrido) | ✅ DONE | `with_updates`, `add_metadata` |
| T03.4 | Idempotência em Workers (Redis SETNX) | ✅ DONE | `fila_worker.py` |
| T03.5 | Dead Letter Queue | ✅ DONE | `fila.py` + migration |
| T06.3 | Paralelizar Context Building | ✅ DONE | `asyncio.gather` em contexto.py |
| T06.4 | Cache de Respostas LLM | ✅ DONE | `llm/cache.py` + integração agente.py |
| T06.5 | Distributed Circuit Breaker via Redis | ✅ DONE | `DistributedCircuitBreaker` class |
| T01.6 | Timeout de LLM sem Resposta | ✅ DONE | `TIMEOUT_GERACAO_RESPOSTA` 60s |
| T03.3 | Separar pre_processors.py em Módulos | ✅ DONE | `pipeline/processors/` 15 arquivos |
| T02.4 | Refatorar agente.py em Módulos | ✅ DONE | `julia/` + event_emitter.py |
| T02.5 | Registry Pattern para Tools | ✅ DONE | `tools/registry.py` |
| T02.6 | Centralizar Configs Hardcoded | ✅ DONE | `config.py` LLM/Pipeline settings |
| T02.7 | Tracing para RAG | ✅ DONE | `orquestrador.py` tracing detalhado |
| T04.1 | Transações Multi-Tabela | ✅ DONE | `reservar_vaga_transacional` RPC |
| T04.5 | Adicionar LIMIT em Queries | ✅ DONE | Múltiplos arquivos |
| T04.6 | Business Events Dedupe Index | ✅ DONE | Índice único parcial |
| T04.7 | Contagens GROUP BY no Banco | ✅ DONE | `get_event_counts` RPC |
| T06.6 | Pre-compilar Regex Patterns | ✅ DONE | `HandoffKeywordProcessor` |
| T06.8 | Adicionar Jitter no Retry | ✅ DONE | `handoff/flow.py` backoff + jitter |
| T07.1 | Logging Abstraction | ✅ DONE | `logging.py` contextvars |
| T07.2 | Padronizar Formato Logs | ✅ DONE | `mask_phone()` + context manager |
| T07.3 | Adicionar trace_id em Logs | ✅ DONE | ContextVar + JSONFormatter |
| T07.5 | Alertas Slack Erros Críticos | ✅ DONE | `alertas.py` funções infra |
| T08.1 | Testes Correções Críticas | ✅ DONE | `test_sprint44_corrections.py` 18 testes |

### Semana 3 - Frontend/Dashboard (E05)

| Tarefa | Descrição | Status | Commit |
|--------|-----------|--------|--------|
| T05.1 | Error Boundaries Dashboard/Chips | ✅ DONE | `error.tsx` em ambos módulos |
| T05.2 | Layout Server Component | ✅ DONE | `DashboardLayoutWrapper` client |
| T05.3 | SWR para Data Fetching | ✅ DONE | `lib/swr/` config + hooks |
| T05.4 | Zod Validation API Routes | ✅ DONE | `lib/validations/api.ts` |
| T05.5 | Loading.tsx para Suspense | ✅ DONE | `loading.tsx` em dashboard/chips |
| T05.6 | Logging Abstraction Frontend | ✅ DONE | `lib/logger.ts` |

**Arquivos modificados:**
- `app/api/routes/webhook.py` - Deduplicação atômica, semáforo configurável
- `app/services/rate_limiter.py` - Fail-closed com fallback chain
- `app/services/circuit_breaker.py` - Thread-safe com asyncio.Lock
- `app/services/agente.py` - Global timeout 60s + Response Validator
- `app/services/http_client.py` - **NOVO** - Singleton com pooling
- `app/main.py` - Shutdown gracioso do HTTP client
- `app/core/utils.py` - **NOVO** - `safe_first` e `safe_get` utilities
- `app/services/campanha.py` - Filtro de opt-out em campanhas
- `app/services/handoff/flow.py` - Retry + alerta para notificações
- `app/services/chips/selector.py` - Reserva atômica de slot via Redis INCR
- `app/services/julia/summarizer.py` - **NOVO** - Summarization de conversas longas
- `app/services/julia/context_builder.py` - Integração com summarizer
- `app/services/julia/orchestrator.py` - Usa summarization no fluxo
- `app/core/distributed_lock.py` - **NOVO** - Lock distribuído via Redis
- `app/services/chips/orchestrator.py` - Usa distributed lock no ciclo
- `app/services/contexto.py` - Paralelização com asyncio.gather
- `app/pipeline/base.py` - ProcessorContext com métodos imutáveis (híbrido)
- `app/workers/fila_worker.py` - Idempotência via Redis SETNX
- `app/services/fila.py` - Dead Letter Queue completa
- `migrations/sprint44_t03_5_dlq.sql` - **NOVO** - Migration DLQ ✅ APLICADA
- `app/services/llm/cache.py` - **NOVO** - Cache de respostas LLM
- `app/services/llm/__init__.py` - Exports do cache
- `app/services/agente.py` - Integração com cache LLM
- `app/services/circuit_breaker.py` - DistributedCircuitBreaker class (Redis state)
- `app/pipeline/processors/` - **NOVO** - Diretório de processadores modulares (T03.3)
  - `__init__.py` - Exports de todos os processadores
  - `ingestao_grupo.py` - IngestaoGrupoProcessor (priority 5)
  - `parse.py` - ParseMessageProcessor (priority 10)
  - `presence.py` - PresenceProcessor (priority 15)
  - `entities.py` - LoadEntitiesProcessor (priority 20)
  - `chip_mapping.py` - ChipMappingProcessor (priority 21)
  - `business_events.py` - BusinessEventInboundProcessor (priority 22)
  - `chatwoot.py` - ChatwootSyncProcessor (priority 25)
  - `optout.py` - OptOutProcessor (priority 30)
  - `fora_horario.py` - ForaHorarioProcessor (priority 32)
  - `bot_detection.py` - BotDetectionProcessor (priority 35)
  - `media.py` - MediaProcessor (priority 40)
  - `long_message.py` - LongMessageProcessor (priority 45)
  - `handoff.py` - HandoffTriggerProcessor (50) + HandoffKeywordProcessor (55)
  - `human_control.py` - HumanControlProcessor (priority 60)
- `app/pipeline/pre_processors.py` - Atualizado para re-exportar dos novos módulos
- `app/core/logging.py` - **ATUALIZADO** - Contextvars, trace_id, mask_phone
- `app/services/alertas.py` - **ATUALIZADO** - Alertas de infraestrutura crítica
- `tests/test_sprint44_corrections.py` - **NOVO** - 18 testes para correções

**Dashboard (Next.js):**
- `dashboard/app/(dashboard)/error.tsx` - **NOVO** - Error Boundary
- `dashboard/app/(dashboard)/loading.tsx` - **NOVO** - Suspense Loading
- `dashboard/app/(dashboard)/chips/error.tsx` - **NOVO** - Error Boundary Chips
- `dashboard/app/(dashboard)/chips/loading.tsx` - **NOVO** - Suspense Loading Chips
- `dashboard/app/(dashboard)/layout.tsx` - Server Component wrapper
- `dashboard/components/dashboard/dashboard-layout-wrapper.tsx` - **NOVO** - Client wrapper
- `dashboard/lib/swr/config.ts` - **NOVO** - SWR configuration
- `dashboard/lib/swr/hooks.ts` - **NOVO** - SWR custom hooks
- `dashboard/lib/swr/index.ts` - **NOVO** - SWR exports
- `dashboard/lib/validations/api.ts` - **NOVO** - Zod schemas
- `dashboard/lib/validations/index.ts` - **NOVO** - Validations exports
- `dashboard/lib/logger.ts` - **NOVO** - Logging abstraction
- `dashboard/components/providers/swr-provider.tsx` - **NOVO** - SWR Provider

---

## Cronograma

```
Semana 1 (03-07/02): ✅ 100% CONCLUÍDO
├── E01: Bugs Críticos (T01.1-T01.3) ✅ DONE
├── E02: Timeout + Validator (T02.1-T02.2) ✅ DONE
└── E06: Semáforo + HTTP Client (T06.1-T06.2) ✅ DONE

Semana 2 (10-14/02):
├── E01: Bugs Altos (T01.4-T01.8)
├── E02: Summarization + Refactor (T02.3-T02.4)
├── E03: Pipeline (T03.1-T03.3)
└── E06: Parallelização + Cache (T06.3-T06.4)

Semana 3 (17-21/02):
├── E04: Banco de Dados (T04.1-T04.7)
├── E05: Frontend (T05.1-T05.4)
├── E06: Circuit Breaker Distribuído (T06.5)
└── E07: Logging (T07.1-T07.2)

Semana 4 (24-28/02):
├── E02: Registry + Config (T02.5-T02.7)
├── E03: Idempotência + DLQ (T03.4-T03.5)
├── E04: Restante DB (T04.8-T04.12)
├── E05: Restante Frontend (T05.5-T05.12)
├── E07: Observabilidade (T07.3-T07.6)
└── E08: Testes + Docs (T08.1-T08.3)
```

---

## Definition of Done

- [ ] Código implementado e revisado
- [ ] Testes unitários passando (cobertura > 80%)
- [ ] Testes de integração passando
- [ ] Documentação atualizada
- [ ] Deploy em staging validado
- [ ] Métricas de performance coletadas
- [ ] Rollback plan documentado

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Migration de banco quebra produção | Média | Alto | Testar em staging, backup antes |
| Refactor do agente introduz bugs | Média | Alto | Feature flags, rollback rápido |
| Performance piora após mudanças | Baixa | Médio | Benchmark antes/depois |
| Prazo não cumprido | Média | Médio | Priorizar críticos, desprioritizar baixos |

---

## Métricas de Sucesso

| Métrica | Antes | Meta | Como Medir |
|---------|-------|------|------------|
| Msgs duplicadas/dia | ~5-10 | 0 | Logs + alertas |
| Latência p95 | ~2s | <1s | APM |
| Throughput | ~2-5 msg/s | >10 msg/s | Load test |
| Erros/hora | ~20 | <5 | Sentry/Logs |
| Cobertura testes | 65% | >80% | pytest-cov |

---

*Sprint criada em 02/02/2026*
*Baseada na Análise Arquitetural Completa*
