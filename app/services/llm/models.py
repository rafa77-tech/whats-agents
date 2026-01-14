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
