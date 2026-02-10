"""
Modelos de dados internos do agente Julia.

Sprint 31 - S31.E2.1

Dataclasses que representam o estado e fluxo de dados
durante a geração de respostas.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class JuliaContext:
    """
    Contexto completo para geração de resposta.

    Agrupa todos os dados necessários para gerar uma resposta,
    eliminando a necessidade de passar múltiplos parâmetros.
    """

    mensagem: str
    medico: Dict[str, Any]
    conversa: Dict[str, Any]

    # Contexto montado
    contexto_medico: str = ""
    contexto_vagas: str = ""
    contexto_historico: str = ""
    contexto_memorias: str = ""
    contexto_diretrizes: str = ""

    # Flags
    primeira_mensagem: bool = False
    incluir_historico: bool = True
    usar_tools: bool = True

    # Histórico raw (para converter em messages)
    historico_raw: List[Dict] = field(default_factory=list)

    # Metadata
    data_hora: str = ""
    dia_semana: str = ""
    trace_id: Optional[str] = None


@dataclass
class PolicyContext:
    """
    Contexto de políticas e constraints.

    Agrupa informações da Policy Engine e Conversation Mode.
    """

    policy_constraints: str = ""
    capabilities_gate: Any = None  # CapabilitiesGate
    mode_info: Any = None  # ModeInfo
    tools_filtradas: List[Dict] = field(default_factory=list)


@dataclass
class ToolExecutionResult:
    """
    Resultado da execução de uma tool.

    Encapsula o resultado e status de uma chamada de tool.
    """

    tool_call_id: str
    tool_name: str
    result: Dict[str, Any]
    success: bool = True
    error: Optional[str] = None

    def to_api_format(self) -> Dict[str, Any]:
        """Converte para formato esperado pela API do Claude."""
        return {
            "type": "tool_result",
            "tool_use_id": self.tool_call_id,
            "content": str(self.result) if self.success else self.error,
        }


@dataclass
class GenerationResult:
    """
    Resultado de uma geração do LLM.

    Normaliza a resposta do LLM para processamento interno.
    """

    text: str
    tool_calls: List[Dict] = field(default_factory=list)
    stop_reason: str = "end_turn"
    needs_retry: bool = False

    @property
    def has_tool_calls(self) -> bool:
        """Verifica se há tool calls na resposta."""
        return len(self.tool_calls) > 0

    @classmethod
    def from_llm_response(cls, response: Dict[str, Any]) -> "GenerationResult":
        """
        Cria GenerationResult a partir da resposta legada.

        Args:
            response: Dict com 'text', 'tool_use', 'stop_reason'
        """
        return cls(
            text=response.get("text") or "",
            tool_calls=response.get("tool_use") or [],
            stop_reason=response.get("stop_reason") or "end_turn",
        )


@dataclass
class JuliaResponse:
    """
    Resposta final da Julia.

    Inclui a resposta e metadata para logging/debugging.
    """

    texto: str
    tool_calls_executadas: int = 0
    retry_necessario: bool = False
    conhecimento_usado: bool = False
    trace_id: Optional[str] = None

    @property
    def sucesso(self) -> bool:
        """Verifica se a resposta foi gerada com sucesso."""
        return bool(self.texto)
