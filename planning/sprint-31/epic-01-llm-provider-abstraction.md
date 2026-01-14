# Epic 01: LLM Provider Abstraction

## Severidade: P0 - CRÍTICO

## Objetivo

Criar uma camada de abstração sobre o LLM que permita:
- Trocar de provider (Anthropic → OpenAI → Local) sem mudar código
- Mockar LLM em testes unitários sem patches complexos
- Adicionar observabilidade (logging, métricas, cache) de forma centralizada
- Implementar fallback entre providers no futuro

---

## Problema Atual

### Código Atual (`app/services/llm.py`)

```python
# PROBLEMA: Acoplamento direto à Anthropic
import anthropic

@lru_cache()
def get_anthropic_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

# Singleton global - impossível injetar mock
client = get_anthropic_client()

async def chamar_llm(mensagens, tools=None, max_tokens=300):
    # Chama Anthropic diretamente
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        messages=mensagens,
        tools=tools,
        max_tokens=max_tokens,
    )
    return response
```

### Problemas Identificados

| Problema | Impacto | Severidade |
|----------|---------|------------|
| Não há interface/protocol | Impossível trocar provider | Alto |
| Singleton global `client` | Testes precisam mockar import | Alto |
| Response é objeto Anthropic | Código consumidor acoplado | Médio |
| Sem logging centralizado | Debug difícil em produção | Médio |

---

## Solução: Provider Pattern

### Arquitetura Proposta

```
app/services/llm/
├── __init__.py           # Exports públicos
├── protocol.py           # Interface LLMProvider (Protocol)
├── models.py             # Dataclasses: LLMRequest, LLMResponse, ToolCall
├── anthropic_provider.py # Implementação Anthropic
├── mock_provider.py      # Mock para testes
└── factory.py            # Factory get_llm_provider()
```

### Diagrama de Dependência

```
┌─────────────────────┐
│     agente.py       │
└──────────┬──────────┘
           │ usa
           ▼
┌─────────────────────┐
│   LLMProvider       │  ← Protocol (interface)
│   (protocol.py)     │
└──────────┬──────────┘
           │ implementado por
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐  ┌─────────┐
│Anthropic│  │  Mock   │
│Provider │  │Provider │
└─────────┘  └─────────┘
```

---

## Stories

### S31.E1.1: Criar Protocol LLMProvider

**Objetivo:** Definir a interface que todos os providers devem implementar.

**Arquivo:** `app/services/llm/protocol.py`

**Por que Protocol?** Python 3.8+ suporta `Protocol` (structural subtyping), permitindo que qualquer classe que implemente os métodos seja aceita, sem herança explícita.

#### Tarefas Passo a Passo

1. **Criar diretório:**
   ```bash
   mkdir -p app/services/llm
   touch app/services/llm/__init__.py
   ```

2. **Criar arquivo `app/services/llm/protocol.py`:**

```python
"""
LLM Provider Protocol - Interface para qualquer provider de LLM.

Sprint 31 - S31.E1.1

Este módulo define a interface que todos os providers devem implementar.
Usar Protocol permite duck typing com type checking estático.

Exemplo de uso:
    def minha_funcao(provider: LLMProvider):
        response = await provider.generate(request)
"""
from typing import Protocol, Optional, List, runtime_checkable
from .models import LLMRequest, LLMResponse


@runtime_checkable
class LLMProvider(Protocol):
    """
    Interface para providers de LLM.

    Qualquer classe que implemente estes métodos é um LLMProvider válido.
    Não precisa herdar explicitamente.

    Attributes:
        model_id: Identificador do modelo (ex: "claude-3-haiku-20240307")
    """

    @property
    def model_id(self) -> str:
        """Retorna o ID do modelo sendo usado."""
        ...

    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """
        Gera uma resposta do LLM.

        Args:
            request: Objeto LLMRequest com mensagens, tools, etc.

        Returns:
            LLMResponse com texto, tool_calls, e metadata.

        Raises:
            LLMError: Se houver erro na chamada ao provider.
        """
        ...

    async def generate_with_tools(
        self,
        request: LLMRequest,
        tool_results: List[dict],
    ) -> LLMResponse:
        """
        Continua geração após execução de tools.

        Args:
            request: Request original
            tool_results: Resultados das tools executadas

        Returns:
            LLMResponse com continuação

        Raises:
            LLMError: Se houver erro na chamada.
        """
        ...


class LLMError(Exception):
    """Erro genérico de LLM."""

    def __init__(
        self,
        message: str,
        provider: str = "unknown",
        retryable: bool = False,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable
        self.original_error = original_error
```

3. **Verificar sintaxe:**
   ```bash
   python -c "from app.services.llm.protocol import LLMProvider, LLMError; print('OK')"
   ```

#### Definition of Done (DoD)

- [ ] Arquivo `app/services/llm/protocol.py` existe
- [ ] `LLMProvider` é um `Protocol` com decorator `@runtime_checkable`
- [ ] Método `generate()` definido com type hints corretos
- [ ] Método `generate_with_tools()` definido
- [ ] Property `model_id` definida
- [ ] Classe `LLMError` criada com campos: `provider`, `retryable`, `original_error`
- [ ] Import funciona sem erros: `python -c "from app.services.llm.protocol import LLMProvider"`
- [ ] Commit criado: `feat(llm): cria Protocol LLMProvider`

---

### S31.E1.2: Criar Dataclasses de Request/Response

**Objetivo:** Definir estruturas de dados desacopladas de qualquer provider.

**Arquivo:** `app/services/llm/models.py`

**Por que dataclasses?** São imutáveis por padrão (com `frozen=True`), têm `__eq__` automático, e funcionam bem com type checkers.

#### Tarefas Passo a Passo

1. **Criar arquivo `app/services/llm/models.py`:**

```python
"""
Modelos de dados para LLM Provider.

Sprint 31 - S31.E1.2

Dataclasses para request/response desacoplados de qualquer provider.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Literal
from enum import Enum


class MessageRole(str, Enum):
    """Roles de mensagem suportados."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class StopReason(str, Enum):
    """Motivos de parada da geração."""
    END_TURN = "end_turn"
    TOOL_USE = "tool_use"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"


@dataclass(frozen=True)
class Message:
    """
    Uma mensagem na conversa.

    Attributes:
        role: Quem enviou (user, assistant, system)
        content: Conteúdo da mensagem
    """
    role: MessageRole
    content: str

    @classmethod
    def user(cls, content: str) -> "Message":
        """Cria mensagem do usuário."""
        return cls(role=MessageRole.USER, content=content)

    @classmethod
    def assistant(cls, content: str) -> "Message":
        """Cria mensagem do assistente."""
        return cls(role=MessageRole.ASSISTANT, content=content)

    @classmethod
    def system(cls, content: str) -> "Message":
        """Cria mensagem de sistema."""
        return cls(role=MessageRole.SYSTEM, content=content)

    def to_dict(self) -> dict:
        """Converte para dict (formato API)."""
        return {"role": self.role.value, "content": self.content}


@dataclass(frozen=True)
class ToolDefinition:
    """
    Definição de uma tool disponível para o LLM.

    Attributes:
        name: Nome único da tool
        description: Descrição do que a tool faz
        input_schema: JSON Schema dos parâmetros
    """
    name: str
    description: str
    input_schema: Dict[str, Any]

    def to_dict(self) -> dict:
        """Converte para formato de API."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


@dataclass(frozen=True)
class ToolCall:
    """
    Chamada de tool feita pelo LLM.

    Attributes:
        id: ID único da chamada (para correlacionar resultado)
        name: Nome da tool chamada
        input: Argumentos passados para a tool
    """
    id: str
    name: str
    input: Dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    """
    Resultado de uma tool executada.

    Attributes:
        tool_call_id: ID da chamada original
        content: Resultado como string
        is_error: Se o resultado é um erro
    """
    tool_call_id: str
    content: str
    is_error: bool = False

    def to_dict(self) -> dict:
        """Converte para formato de API."""
        return {
            "type": "tool_result",
            "tool_use_id": self.tool_call_id,
            "content": self.content,
            "is_error": self.is_error,
        }


@dataclass
class LLMRequest:
    """
    Request para o LLM.

    Attributes:
        messages: Lista de mensagens da conversa
        system_prompt: Prompt de sistema (opcional)
        tools: Tools disponíveis (opcional)
        max_tokens: Máximo de tokens na resposta
        temperature: Temperatura (0.0 = determinístico, 1.0 = criativo)
        stop_sequences: Sequências que param a geração
    """
    messages: List[Message]
    system_prompt: Optional[str] = None
    tools: Optional[List[ToolDefinition]] = None
    max_tokens: int = 300
    temperature: float = 0.7
    stop_sequences: Optional[List[str]] = None

    # Metadata para logging/tracing
    trace_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """
    Response do LLM.

    Attributes:
        content: Texto gerado (pode ser vazio se só tool_calls)
        tool_calls: Lista de tools chamadas pelo LLM
        stop_reason: Por que a geração parou
        usage: Tokens usados (input, output)
        model_id: Modelo que gerou a resposta
        raw_response: Response original do provider (para debug)
    """
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    stop_reason: StopReason = StopReason.END_TURN
    usage: Dict[str, int] = field(default_factory=dict)
    model_id: str = ""
    raw_response: Optional[Any] = None

    @property
    def has_tool_calls(self) -> bool:
        """Verifica se há chamadas de tool."""
        return len(self.tool_calls) > 0

    @property
    def input_tokens(self) -> int:
        """Tokens de input usados."""
        return self.usage.get("input_tokens", 0)

    @property
    def output_tokens(self) -> int:
        """Tokens de output usados."""
        return self.usage.get("output_tokens", 0)


@dataclass
class UsageStats:
    """
    Estatísticas de uso acumuladas.

    Útil para tracking de custos.
    """
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_requests: int = 0

    def add(self, response: LLMResponse):
        """Adiciona uso de uma response."""
        self.total_input_tokens += response.input_tokens
        self.total_output_tokens += response.output_tokens
        self.total_requests += 1

    @property
    def total_tokens(self) -> int:
        """Total de tokens (input + output)."""
        return self.total_input_tokens + self.total_output_tokens
```

2. **Verificar sintaxe:**
   ```bash
   python -c "from app.services.llm.models import LLMRequest, LLMResponse, Message; print('OK')"
   ```

3. **Teste rápido de uso:**
   ```python
   # Testar no Python REPL
   from app.services.llm.models import Message, LLMRequest

   msg = Message.user("Olá")
   print(msg.to_dict())  # {'role': 'user', 'content': 'Olá'}

   req = LLMRequest(messages=[msg], max_tokens=100)
   print(req.max_tokens)  # 100
   ```

#### Definition of Done (DoD)

- [ ] Arquivo `app/services/llm/models.py` existe
- [ ] `Message` dataclass com factory methods (`user()`, `assistant()`, `system()`)
- [ ] `ToolDefinition` dataclass com `to_dict()`
- [ ] `ToolCall` dataclass com `id`, `name`, `input`
- [ ] `ToolResult` dataclass com `to_dict()`
- [ ] `LLMRequest` dataclass com: `messages`, `system_prompt`, `tools`, `max_tokens`, `temperature`, `trace_id`
- [ ] `LLMResponse` dataclass com: `content`, `tool_calls`, `stop_reason`, `usage`, `has_tool_calls` property
- [ ] `StopReason` enum com: `END_TURN`, `TOOL_USE`, `MAX_TOKENS`
- [ ] Import funciona: `python -c "from app.services.llm.models import *"`
- [ ] Commit criado: `feat(llm): cria dataclasses LLMRequest e LLMResponse`

---

### S31.E1.3: Implementar AnthropicProvider

**Objetivo:** Criar implementação concreta do LLMProvider para Anthropic.

**Arquivo:** `app/services/llm/anthropic_provider.py`

#### Tarefas Passo a Passo

1. **Criar arquivo `app/services/llm/anthropic_provider.py`:**

```python
"""
Anthropic Provider - Implementação do LLMProvider para Claude.

Sprint 31 - S31.E1.3

Este módulo implementa a interface LLMProvider usando a API da Anthropic.
"""
import logging
import asyncio
from typing import List, Optional, Any

import anthropic

from app.core.config import settings
from .protocol import LLMProvider, LLMError
from .models import (
    LLMRequest,
    LLMResponse,
    ToolCall,
    ToolResult,
    StopReason,
    Message,
    MessageRole,
)

logger = logging.getLogger(__name__)


class AnthropicProvider:
    """
    Provider de LLM usando Anthropic Claude.

    Implementa a interface LLMProvider.

    Attributes:
        model_id: ID do modelo Claude a usar
        client: Cliente Anthropic

    Exemplo:
        provider = AnthropicProvider(model_id="claude-3-haiku-20240307")
        response = await provider.generate(request)
    """

    # Mapeamento de stop_reason da Anthropic para nosso enum
    STOP_REASON_MAP = {
        "end_turn": StopReason.END_TURN,
        "tool_use": StopReason.TOOL_USE,
        "max_tokens": StopReason.MAX_TOKENS,
        "stop_sequence": StopReason.STOP_SEQUENCE,
    }

    def __init__(
        self,
        model_id: str = "claude-3-haiku-20240307",
        api_key: Optional[str] = None,
    ):
        """
        Inicializa o provider.

        Args:
            model_id: ID do modelo Claude
            api_key: API key (usa settings se não fornecida)
        """
        self._model_id = model_id
        self._api_key = api_key or settings.ANTHROPIC_API_KEY

        if not self._api_key:
            raise LLMError(
                "ANTHROPIC_API_KEY não configurada",
                provider="anthropic",
                retryable=False,
            )

        self._client = anthropic.Anthropic(api_key=self._api_key)

    @property
    def model_id(self) -> str:
        """Retorna o ID do modelo."""
        return self._model_id

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Gera resposta do Claude.

        Args:
            request: LLMRequest com mensagens e configurações

        Returns:
            LLMResponse com texto e/ou tool_calls

        Raises:
            LLMError: Se houver erro na API
        """
        try:
            # Converter mensagens para formato Anthropic
            messages = self._convert_messages(request.messages)

            # Converter tools se existirem
            tools = None
            if request.tools:
                tools = [tool.to_dict() for tool in request.tools]

            # Preparar kwargs
            kwargs = {
                "model": self._model_id,
                "messages": messages,
                "max_tokens": request.max_tokens,
            }

            if request.system_prompt:
                kwargs["system"] = request.system_prompt

            if tools:
                kwargs["tools"] = tools

            if request.temperature is not None:
                kwargs["temperature"] = request.temperature

            if request.stop_sequences:
                kwargs["stop_sequences"] = request.stop_sequences

            # Log da chamada
            logger.debug(
                "Chamando Anthropic",
                extra={
                    "model": self._model_id,
                    "message_count": len(messages),
                    "has_tools": bool(tools),
                    "trace_id": request.trace_id,
                }
            )

            # Chamar API (síncrona, via executor)
            response = await self._call_api(kwargs)

            # Converter response
            return self._convert_response(response)

        except anthropic.APIConnectionError as e:
            raise LLMError(
                f"Erro de conexão com Anthropic: {e}",
                provider="anthropic",
                retryable=True,
                original_error=e,
            )
        except anthropic.RateLimitError as e:
            raise LLMError(
                f"Rate limit Anthropic: {e}",
                provider="anthropic",
                retryable=True,
                original_error=e,
            )
        except anthropic.APIStatusError as e:
            raise LLMError(
                f"Erro API Anthropic: {e}",
                provider="anthropic",
                retryable=e.status_code >= 500,
                original_error=e,
            )
        except Exception as e:
            logger.exception("Erro inesperado ao chamar Anthropic")
            raise LLMError(
                f"Erro inesperado: {e}",
                provider="anthropic",
                retryable=False,
                original_error=e,
            )

    async def generate_with_tools(
        self,
        request: LLMRequest,
        tool_results: List[ToolResult],
    ) -> LLMResponse:
        """
        Continua geração após execução de tools.

        Args:
            request: Request original
            tool_results: Resultados das tools

        Returns:
            LLMResponse com continuação
        """
        # Construir mensagens com tool results
        messages = list(request.messages)

        # Adicionar tool results como mensagem do user
        tool_result_content = [tr.to_dict() for tr in tool_results]

        # Criar nova mensagem com os resultados
        messages.append(Message(
            role=MessageRole.USER,
            content=str(tool_result_content),  # Será convertido corretamente
        ))

        # Criar novo request
        new_request = LLMRequest(
            messages=messages,
            system_prompt=request.system_prompt,
            tools=request.tools,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            trace_id=request.trace_id,
            context=request.context,
        )

        return await self.generate(new_request)

    async def _call_api(self, kwargs: dict) -> Any:
        """
        Chama a API de forma assíncrona.

        Usa run_in_executor porque o client Anthropic é síncrono.
        """
        loop = asyncio.get_event_loop()

        def _sync_call():
            return self._client.messages.create(**kwargs)

        return await loop.run_in_executor(None, _sync_call)

    def _convert_messages(self, messages: List[Message]) -> List[dict]:
        """Converte nossas mensagens para formato Anthropic."""
        result = []
        for msg in messages:
            result.append({
                "role": msg.role.value,
                "content": msg.content,
            })
        return result

    def _convert_response(self, response: Any) -> LLMResponse:
        """Converte response da Anthropic para nosso formato."""
        # Extrair conteúdo de texto
        content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    input=block.input,
                ))

        # Mapear stop reason
        stop_reason = self.STOP_REASON_MAP.get(
            response.stop_reason,
            StopReason.END_TURN
        )

        # Extrair usage
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            usage=usage,
            model_id=response.model,
            raw_response=response,
        )


# Factory function para criar provider com configurações padrão
def create_haiku_provider() -> AnthropicProvider:
    """Cria provider com Claude Haiku (mais barato)."""
    return AnthropicProvider(model_id="claude-3-haiku-20240307")


def create_sonnet_provider() -> AnthropicProvider:
    """Cria provider com Claude Sonnet (mais capaz)."""
    return AnthropicProvider(model_id="claude-sonnet-4-20250514")
```

2. **Verificar import:**
   ```bash
   python -c "from app.services.llm.anthropic_provider import AnthropicProvider; print('OK')"
   ```

#### Definition of Done (DoD)

- [ ] Arquivo `app/services/llm/anthropic_provider.py` existe
- [ ] Classe `AnthropicProvider` implementa todos os métodos do Protocol
- [ ] Property `model_id` retorna o modelo correto
- [ ] `generate()` converte mensagens e chama API
- [ ] `generate_with_tools()` continua após tool execution
- [ ] Erros são convertidos para `LLMError` com `retryable` correto
- [ ] Logging incluído com `trace_id`
- [ ] Factory functions `create_haiku_provider()` e `create_sonnet_provider()` existem
- [ ] Import funciona: `python -c "from app.services.llm.anthropic_provider import AnthropicProvider"`
- [ ] Commit criado: `feat(llm): implementa AnthropicProvider`

---

### S31.E1.4: Criar MockLLMProvider para Testes

**Objetivo:** Criar provider mockado que não faz chamadas reais.

**Arquivo:** `app/services/llm/mock_provider.py`

#### Tarefas Passo a Passo

1. **Criar arquivo `app/services/llm/mock_provider.py`:**

```python
"""
Mock LLM Provider - Para testes sem chamadas reais.

Sprint 31 - S31.E1.4

Este provider permite testar código que usa LLM sem custos ou latência.
"""
from typing import List, Optional, Callable
from dataclasses import dataclass, field

from .protocol import LLMProvider
from .models import (
    LLMRequest,
    LLMResponse,
    ToolCall,
    ToolResult,
    StopReason,
)


@dataclass
class MockLLMProvider:
    """
    Provider mockado para testes.

    Permite configurar respostas fixas ou dinâmicas.

    Exemplo de uso básico:
        mock = MockLLMProvider(default_response="Olá!")
        response = await mock.generate(request)
        assert response.content == "Olá!"

    Exemplo com tool calls:
        mock = MockLLMProvider(
            tool_calls=[ToolCall(id="1", name="buscar_vagas", input={})]
        )
        response = await mock.generate(request)
        assert response.has_tool_calls

    Exemplo com callback:
        def custom_response(request):
            return LLMResponse(content=f"Recebi: {request.messages[-1].content}")

        mock = MockLLMProvider(response_callback=custom_response)
    """

    # Configurações
    default_response: str = "Mock response"
    tool_calls: List[ToolCall] = field(default_factory=list)
    stop_reason: StopReason = StopReason.END_TURN
    model_id: str = "mock-model"

    # Callback opcional para respostas dinâmicas
    response_callback: Optional[Callable[[LLMRequest], LLMResponse]] = None

    # Tracking de chamadas (para assertions em testes)
    calls: List[LLMRequest] = field(default_factory=list)
    tool_continuation_calls: List[tuple] = field(default_factory=list)

    # Simular erros
    should_fail: bool = False
    fail_message: str = "Mock error"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Gera resposta mockada.

        Args:
            request: LLMRequest (será registrado para assertions)

        Returns:
            LLMResponse configurada ou via callback
        """
        # Registrar chamada
        self.calls.append(request)

        # Simular erro se configurado
        if self.should_fail:
            from .protocol import LLMError
            raise LLMError(
                self.fail_message,
                provider="mock",
                retryable=False,
            )

        # Usar callback se fornecido
        if self.response_callback:
            return self.response_callback(request)

        # Retornar response padrão
        return LLMResponse(
            content=self.default_response,
            tool_calls=self.tool_calls,
            stop_reason=self.stop_reason,
            usage={"input_tokens": 10, "output_tokens": 20},
            model_id=self.model_id,
        )

    async def generate_with_tools(
        self,
        request: LLMRequest,
        tool_results: List[ToolResult],
    ) -> LLMResponse:
        """
        Continua após tool execution (mockado).

        Registra a chamada e retorna response configurada.
        """
        self.tool_continuation_calls.append((request, tool_results))

        if self.response_callback:
            return self.response_callback(request)

        return LLMResponse(
            content=f"Processado {len(tool_results)} tool results",
            tool_calls=[],
            stop_reason=StopReason.END_TURN,
            usage={"input_tokens": 5, "output_tokens": 10},
            model_id=self.model_id,
        )

    # Métodos auxiliares para testes

    def reset(self):
        """Limpa histórico de chamadas."""
        self.calls.clear()
        self.tool_continuation_calls.clear()

    @property
    def call_count(self) -> int:
        """Número de chamadas a generate()."""
        return len(self.calls)

    @property
    def last_call(self) -> Optional[LLMRequest]:
        """Última chamada feita."""
        return self.calls[-1] if self.calls else None

    def assert_called(self):
        """Asserta que generate() foi chamado."""
        assert self.call_count > 0, "MockLLMProvider.generate() não foi chamado"

    def assert_called_with_tool(self, tool_name: str):
        """Asserta que foi chamado com determinada tool disponível."""
        assert self.last_call is not None, "Nenhuma chamada registrada"
        assert self.last_call.tools is not None, "Chamada não incluiu tools"
        tool_names = [t.name for t in self.last_call.tools]
        assert tool_name in tool_names, f"Tool {tool_name} não estava disponível. Tools: {tool_names}"


# Factories para casos comuns

def create_mock_that_returns(content: str) -> MockLLMProvider:
    """Cria mock que sempre retorna o conteúdo especificado."""
    return MockLLMProvider(default_response=content)


def create_mock_that_calls_tool(tool_name: str, tool_input: dict = None) -> MockLLMProvider:
    """Cria mock que retorna uma chamada de tool."""
    return MockLLMProvider(
        tool_calls=[ToolCall(id="mock-tool-1", name=tool_name, input=tool_input or {})],
        stop_reason=StopReason.TOOL_USE,
        default_response="",  # Quando há tool_use, geralmente não há texto
    )


def create_mock_that_fails(message: str = "Mock error") -> MockLLMProvider:
    """Cria mock que sempre falha."""
    return MockLLMProvider(should_fail=True, fail_message=message)
```

2. **Verificar import:**
   ```bash
   python -c "from app.services.llm.mock_provider import MockLLMProvider, create_mock_that_returns; print('OK')"
   ```

3. **Teste rápido:**
   ```python
   import asyncio
   from app.services.llm.mock_provider import MockLLMProvider, create_mock_that_returns
   from app.services.llm.models import LLMRequest, Message

   async def test():
       mock = create_mock_that_returns("Olá mundo!")
       request = LLMRequest(messages=[Message.user("Oi")])
       response = await mock.generate(request)
       print(response.content)  # "Olá mundo!"
       mock.assert_called()
       print("OK!")

   asyncio.run(test())
   ```

#### Definition of Done (DoD)

- [ ] Arquivo `app/services/llm/mock_provider.py` existe
- [ ] `MockLLMProvider` é uma dataclass configurável
- [ ] Propriedade `model_id` existe
- [ ] `generate()` registra chamadas em `self.calls`
- [ ] `generate_with_tools()` registra em `self.tool_continuation_calls`
- [ ] `should_fail` permite simular erros
- [ ] `response_callback` permite respostas dinâmicas
- [ ] Helpers: `reset()`, `call_count`, `last_call`, `assert_called()`, `assert_called_with_tool()`
- [ ] Factories: `create_mock_that_returns()`, `create_mock_that_calls_tool()`, `create_mock_that_fails()`
- [ ] Import funciona sem erros
- [ ] Commit criado: `feat(llm): cria MockLLMProvider para testes`

---

### S31.E1.5: Migrar agente.py para Usar Interface

**Objetivo:** Atualizar `gerar_resposta_julia()` para usar `LLMProvider` em vez de chamada direta.

**Arquivo:** `app/services/agente.py`

**ATENÇÃO:** Esta story modifica código crítico. Fazer backup antes e testar extensivamente.

#### Tarefas Passo a Passo

1. **Criar backup:**
   ```bash
   cp app/services/agente.py app/services/agente.py.backup
   ```

2. **Identificar pontos de mudança:**
   ```bash
   grep -n "chamar_llm\|from.*llm import\|client.messages" app/services/agente.py
   ```

3. **Atualizar imports no `agente.py`:**

   **ANTES:**
   ```python
   from app.services.llm import chamar_llm
   ```

   **DEPOIS:**
   ```python
   from app.services.llm import LLMProvider, LLMRequest, Message, LLMResponse
   from app.services.llm.factory import get_llm_provider
   ```

4. **Atualizar assinatura de `gerar_resposta_julia()`:**

   **ANTES:**
   ```python
   async def gerar_resposta_julia(
       mensagem: str,
       contexto: dict,
       medico: dict,
       ...
   ) -> str:
   ```

   **DEPOIS:**
   ```python
   async def gerar_resposta_julia(
       mensagem: str,
       contexto: dict,
       medico: dict,
       ...,
       llm_provider: LLMProvider = None,  # Novo parâmetro opcional
   ) -> str:
       # Se não fornecido, usar default
       if llm_provider is None:
           llm_provider = get_llm_provider()
   ```

5. **Atualizar chamada ao LLM:**

   **ANTES:**
   ```python
   resultado = await chamar_llm(
       mensagens=mensagens_formatadas,
       tools=tools_to_use,
       max_tokens=300,
   )
   ```

   **DEPOIS:**
   ```python
   request = LLMRequest(
       messages=[Message(role=m["role"], content=m["content"]) for m in mensagens_formatadas],
       system_prompt=system_prompt,
       tools=tools_to_use,  # Já convertido para ToolDefinition
       max_tokens=300,
       trace_id=contexto.get("trace_id"),
   )

   response = await llm_provider.generate(request)
   ```

6. **Atualizar processamento de response:**

   **ANTES:**
   ```python
   if resultado.get("tool_use"):
       for tool_call in resultado["tool_use"]:
           ...
   ```

   **DEPOIS:**
   ```python
   if response.has_tool_calls:
       for tool_call in response.tool_calls:
           tool_name = tool_call.name
           tool_input = tool_call.input
           tool_id = tool_call.id
           ...
   ```

7. **Rodar testes:**
   ```bash
   uv run pytest tests/services/test_agente.py -v
   ```

8. **Se testes falharem, reverter:**
   ```bash
   cp app/services/agente.py.backup app/services/agente.py
   ```

#### Definition of Done (DoD)

- [ ] Import `from app.services.llm import chamar_llm` removido
- [ ] Import dos novos módulos adicionado
- [ ] `gerar_resposta_julia()` aceita parâmetro opcional `llm_provider: LLMProvider`
- [ ] Chamada usa `LLMRequest` e `llm_provider.generate()`
- [ ] Processamento de response usa `response.content` e `response.tool_calls`
- [ ] `response.has_tool_calls` usado em vez de `resultado.get("tool_use")`
- [ ] Todos os testes existentes passando: `uv run pytest tests/services/test_agente.py`
- [ ] Teste manual de uma conversa funcionando
- [ ] Backup removido após sucesso
- [ ] Commit criado: `refactor(agente): migra para LLMProvider interface`

---

### S31.E1.6: Criar Testes Unitários do Provider

**Objetivo:** Garantir que o provider funciona corretamente.

**Arquivo:** `tests/services/llm/test_providers.py`

#### Tarefas Passo a Passo

1. **Criar estrutura de diretório:**
   ```bash
   mkdir -p tests/services/llm
   touch tests/services/llm/__init__.py
   ```

2. **Criar arquivo `tests/services/llm/test_providers.py`:**

```python
"""
Testes dos LLM Providers.

Sprint 31 - S31.E1.6
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.llm.models import (
    LLMRequest,
    LLMResponse,
    Message,
    MessageRole,
    ToolCall,
    ToolDefinition,
    StopReason,
)
from app.services.llm.mock_provider import (
    MockLLMProvider,
    create_mock_that_returns,
    create_mock_that_calls_tool,
    create_mock_that_fails,
)
from app.services.llm.protocol import LLMProvider, LLMError


class TestMessage:
    """Testes da dataclass Message."""

    def test_create_user_message(self):
        """Deve criar mensagem de usuário."""
        msg = Message.user("Olá")
        assert msg.role == MessageRole.USER
        assert msg.content == "Olá"

    def test_create_assistant_message(self):
        """Deve criar mensagem de assistente."""
        msg = Message.assistant("Oi!")
        assert msg.role == MessageRole.ASSISTANT
        assert msg.content == "Oi!"

    def test_to_dict(self):
        """Deve converter para dict."""
        msg = Message.user("Teste")
        d = msg.to_dict()
        assert d == {"role": "user", "content": "Teste"}


class TestLLMRequest:
    """Testes da dataclass LLMRequest."""

    def test_create_simple_request(self):
        """Deve criar request simples."""
        request = LLMRequest(
            messages=[Message.user("Oi")],
            max_tokens=100,
        )
        assert len(request.messages) == 1
        assert request.max_tokens == 100
        assert request.tools is None

    def test_create_request_with_tools(self):
        """Deve criar request com tools."""
        tool = ToolDefinition(
            name="buscar_vagas",
            description="Busca vagas",
            input_schema={"type": "object"},
        )
        request = LLMRequest(
            messages=[Message.user("Buscar vagas")],
            tools=[tool],
        )
        assert len(request.tools) == 1
        assert request.tools[0].name == "buscar_vagas"

    def test_trace_id_propagation(self):
        """Deve propagar trace_id."""
        request = LLMRequest(
            messages=[Message.user("Teste")],
            trace_id="trace-123",
        )
        assert request.trace_id == "trace-123"


class TestLLMResponse:
    """Testes da dataclass LLMResponse."""

    def test_simple_response(self):
        """Deve criar response simples."""
        response = LLMResponse(content="Olá!")
        assert response.content == "Olá!"
        assert response.has_tool_calls is False

    def test_response_with_tool_calls(self):
        """Deve criar response com tool calls."""
        response = LLMResponse(
            content="",
            tool_calls=[ToolCall(id="1", name="test", input={})],
            stop_reason=StopReason.TOOL_USE,
        )
        assert response.has_tool_calls is True
        assert len(response.tool_calls) == 1

    def test_usage_properties(self):
        """Deve expor usage via properties."""
        response = LLMResponse(
            content="Test",
            usage={"input_tokens": 100, "output_tokens": 50},
        )
        assert response.input_tokens == 100
        assert response.output_tokens == 50


class TestMockLLMProvider:
    """Testes do MockLLMProvider."""

    @pytest.mark.asyncio
    async def test_returns_configured_response(self):
        """Deve retornar resposta configurada."""
        mock = MockLLMProvider(default_response="Resposta fixa")
        request = LLMRequest(messages=[Message.user("Oi")])

        response = await mock.generate(request)

        assert response.content == "Resposta fixa"

    @pytest.mark.asyncio
    async def test_tracks_calls(self):
        """Deve rastrear chamadas."""
        mock = MockLLMProvider()
        request = LLMRequest(messages=[Message.user("Teste")])

        await mock.generate(request)
        await mock.generate(request)

        assert mock.call_count == 2
        mock.assert_called()

    @pytest.mark.asyncio
    async def test_returns_tool_calls(self):
        """Deve retornar tool calls configuradas."""
        mock = create_mock_that_calls_tool("buscar_vagas", {"regiao": "SP"})
        request = LLMRequest(messages=[Message.user("Buscar")])

        response = await mock.generate(request)

        assert response.has_tool_calls
        assert response.tool_calls[0].name == "buscar_vagas"
        assert response.tool_calls[0].input == {"regiao": "SP"}

    @pytest.mark.asyncio
    async def test_fails_when_configured(self):
        """Deve falhar quando configurado."""
        mock = create_mock_that_fails("Erro simulado")
        request = LLMRequest(messages=[Message.user("Teste")])

        with pytest.raises(LLMError) as exc_info:
            await mock.generate(request)

        assert "Erro simulado" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_callback_response(self):
        """Deve usar callback para resposta dinâmica."""
        def custom_callback(req: LLMRequest) -> LLMResponse:
            return LLMResponse(
                content=f"Recebi: {req.messages[-1].content}"
            )

        mock = MockLLMProvider(response_callback=custom_callback)
        request = LLMRequest(messages=[Message.user("Olá mundo")])

        response = await mock.generate(request)

        assert response.content == "Recebi: Olá mundo"

    @pytest.mark.asyncio
    async def test_assert_called_with_tool(self):
        """Deve verificar se tool estava disponível."""
        mock = MockLLMProvider()
        tool = ToolDefinition(name="minha_tool", description="Test", input_schema={})
        request = LLMRequest(messages=[Message.user("Test")], tools=[tool])

        await mock.generate(request)

        mock.assert_called_with_tool("minha_tool")

    @pytest.mark.asyncio
    async def test_generate_with_tools_tracks_calls(self):
        """Deve rastrear chamadas de continuação."""
        mock = MockLLMProvider()
        request = LLMRequest(messages=[Message.user("Test")])
        from app.services.llm.models import ToolResult
        results = [ToolResult(tool_call_id="1", content="resultado")]

        await mock.generate_with_tools(request, results)

        assert len(mock.tool_continuation_calls) == 1

    def test_reset_clears_history(self):
        """Deve limpar histórico no reset."""
        mock = MockLLMProvider()
        mock.calls.append(LLMRequest(messages=[]))

        mock.reset()

        assert mock.call_count == 0


class TestProtocolCompliance:
    """Testes de conformidade com o Protocol."""

    def test_mock_implements_protocol(self):
        """MockLLMProvider deve implementar LLMProvider."""
        mock = MockLLMProvider()
        assert isinstance(mock, LLMProvider)

    def test_mock_has_model_id(self):
        """Mock deve ter model_id."""
        mock = MockLLMProvider(model_id="test-model")
        assert mock.model_id == "test-model"


# Testes de integração (requerem API key - skip se não disponível)
@pytest.mark.integration
class TestAnthropicProviderIntegration:
    """Testes de integração com Anthropic (requer API key)."""

    @pytest.fixture
    def provider(self):
        """Cria provider real (skip se sem API key)."""
        import os
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY não configurada")

        from app.services.llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider()

    @pytest.mark.asyncio
    async def test_simple_generation(self, provider):
        """Deve gerar resposta simples."""
        request = LLMRequest(
            messages=[Message.user("Diga apenas 'OK'")],
            max_tokens=10,
        )

        response = await provider.generate(request)

        assert response.content is not None
        assert len(response.content) > 0
```

3. **Rodar testes:**
   ```bash
   # Apenas testes unitários (sem API)
   uv run pytest tests/services/llm/test_providers.py -v -m "not integration"

   # Todos os testes (inclui integração, requer API key)
   uv run pytest tests/services/llm/test_providers.py -v
   ```

#### Definition of Done (DoD)

- [ ] Diretório `tests/services/llm/` criado
- [ ] Arquivo `test_providers.py` criado
- [ ] Testes para `Message` (3+ testes)
- [ ] Testes para `LLMRequest` (3+ testes)
- [ ] Testes para `LLMResponse` (3+ testes)
- [ ] Testes para `MockLLMProvider` (7+ testes)
- [ ] Teste de conformidade com Protocol
- [ ] Todos os testes passando: `uv run pytest tests/services/llm/ -v`
- [ ] Cobertura >90% nos novos módulos
- [ ] Commit criado: `test(llm): testes unitários dos providers`

---

### S31.E1.7: Criar __init__.py e Factory

**Objetivo:** Configurar exports públicos e factory para DI.

**Arquivo:** `app/services/llm/__init__.py`, `app/services/llm/factory.py`

#### Tarefas Passo a Passo

1. **Criar `app/services/llm/factory.py`:**

```python
"""
Factory para LLM Providers.

Sprint 31 - S31.E1.7

Centraliza criação de providers para facilitar DI e configuração.
"""
from typing import Optional
from functools import lru_cache

from app.core.config import settings
from .protocol import LLMProvider
from .anthropic_provider import AnthropicProvider


@lru_cache()
def get_llm_provider(
    model: str = "haiku",
    api_key: Optional[str] = None,
) -> LLMProvider:
    """
    Retorna provider de LLM configurado.

    Args:
        model: "haiku" ou "sonnet"
        api_key: API key (usa settings se não fornecida)

    Returns:
        LLMProvider configurado

    Exemplo:
        provider = get_llm_provider()  # Haiku por padrão
        provider = get_llm_provider("sonnet")  # Sonnet para tarefas complexas
    """
    model_ids = {
        "haiku": "claude-3-haiku-20240307",
        "sonnet": "claude-sonnet-4-20250514",
    }

    model_id = model_ids.get(model, model_ids["haiku"])

    return AnthropicProvider(
        model_id=model_id,
        api_key=api_key,
    )


def get_haiku_provider() -> LLMProvider:
    """Atalho para provider Haiku."""
    return get_llm_provider("haiku")


def get_sonnet_provider() -> LLMProvider:
    """Atalho para provider Sonnet."""
    return get_llm_provider("sonnet")


# Para testes - permite limpar cache
def clear_provider_cache():
    """Limpa cache de providers (usar em testes)."""
    get_llm_provider.cache_clear()
```

2. **Criar `app/services/llm/__init__.py`:**

```python
"""
LLM Provider Module - Abstração sobre providers de LLM.

Sprint 31

Este módulo fornece uma interface unificada para trabalhar com LLMs,
permitindo trocar providers sem mudar código consumidor.

Uso básico:
    from app.services.llm import get_llm_provider, LLMRequest, Message

    provider = get_llm_provider()
    request = LLMRequest(messages=[Message.user("Olá!")])
    response = await provider.generate(request)
    print(response.content)

Uso em testes:
    from app.services.llm import MockLLMProvider

    mock = MockLLMProvider(default_response="Mock!")
    response = await mock.generate(request)

Classes principais:
    - LLMProvider: Protocol que define a interface
    - LLMRequest: Dados de entrada para o LLM
    - LLMResponse: Dados de saída do LLM
    - AnthropicProvider: Implementação para Claude
    - MockLLMProvider: Implementação para testes
"""

# Protocol e erros
from .protocol import LLMProvider, LLMError

# Modelos de dados
from .models import (
    Message,
    MessageRole,
    LLMRequest,
    LLMResponse,
    ToolCall,
    ToolDefinition,
    ToolResult,
    StopReason,
    UsageStats,
)

# Providers
from .anthropic_provider import AnthropicProvider
from .mock_provider import (
    MockLLMProvider,
    create_mock_that_returns,
    create_mock_that_calls_tool,
    create_mock_that_fails,
)

# Factory
from .factory import (
    get_llm_provider,
    get_haiku_provider,
    get_sonnet_provider,
    clear_provider_cache,
)

__all__ = [
    # Protocol
    "LLMProvider",
    "LLMError",
    # Models
    "Message",
    "MessageRole",
    "LLMRequest",
    "LLMResponse",
    "ToolCall",
    "ToolDefinition",
    "ToolResult",
    "StopReason",
    "UsageStats",
    # Providers
    "AnthropicProvider",
    "MockLLMProvider",
    "create_mock_that_returns",
    "create_mock_that_calls_tool",
    "create_mock_that_fails",
    # Factory
    "get_llm_provider",
    "get_haiku_provider",
    "get_sonnet_provider",
    "clear_provider_cache",
]
```

3. **Verificar todos os imports:**
   ```bash
   python -c "
   from app.services.llm import (
       LLMProvider, LLMError,
       LLMRequest, LLMResponse, Message,
       AnthropicProvider, MockLLMProvider,
       get_llm_provider,
   )
   print('Todos os imports OK!')
   "
   ```

#### Definition of Done (DoD)

- [ ] `app/services/llm/factory.py` criado
- [ ] `get_llm_provider()` retorna provider configurado
- [ ] `get_haiku_provider()` e `get_sonnet_provider()` funcionam
- [ ] `clear_provider_cache()` existe para testes
- [ ] `app/services/llm/__init__.py` com todos os exports
- [ ] Docstring completa no `__init__.py`
- [ ] `__all__` define exports públicos
- [ ] Todos os imports funcionam
- [ ] Commit criado: `feat(llm): configura exports e factory`

---

## Checklist Final do Epic

- [ ] **S31.E1.1** - Protocol LLMProvider criado
- [ ] **S31.E1.2** - Dataclasses Request/Response criadas
- [ ] **S31.E1.3** - AnthropicProvider implementado
- [ ] **S31.E1.4** - MockLLMProvider criado
- [ ] **S31.E1.5** - agente.py migrado para interface
- [ ] **S31.E1.6** - Testes unitários criados
- [ ] **S31.E1.7** - __init__.py e factory configurados
- [ ] Todos os testes passando: `uv run pytest tests/services/llm/ -v`
- [ ] Testes do agente passando: `uv run pytest tests/services/test_agente.py -v`
- [ ] Nenhuma regressão nos testes existentes

---

## Arquivos Criados/Modificados

| Arquivo | Ação | Linhas |
|---------|------|--------|
| `app/services/llm/__init__.py` | Criar | ~60 |
| `app/services/llm/protocol.py` | Criar | ~60 |
| `app/services/llm/models.py` | Criar | ~180 |
| `app/services/llm/anthropic_provider.py` | Criar | ~200 |
| `app/services/llm/mock_provider.py` | Criar | ~130 |
| `app/services/llm/factory.py` | Criar | ~50 |
| `app/services/agente.py` | Modificar | ~30 linhas alteradas |
| `tests/services/llm/test_providers.py` | Criar | ~200 |
| **Total** | | **~910** |

---

## Rollback Plan

Se algo der errado após deploy:

1. **Reverter agente.py:**
   ```bash
   git checkout HEAD~1 -- app/services/agente.py
   ```

2. **Manter módulo llm/ (não quebra nada):**
   O novo módulo não afeta código existente se não for importado.

3. **Se precisar reverter tudo:**
   ```bash
   git revert HEAD
   ```
