"""
Response Handler - Processa e valida respostas do LLM.

Sprint 31 - S31.E2.4

Responsabilidades:
- Detectar respostas incompletas
- Validar qualidade da resposta
- Gerenciar lógica de retry
- Processar stop_reason
"""

import logging
from typing import Optional, List, Dict, Any

from .models import GenerationResult, JuliaResponse

logger = logging.getLogger(__name__)


# Padrões que indicam resposta incompleta
PADROES_RESPOSTA_INCOMPLETA = [
    ":",  # "Vou verificar o que temos:"
    "...",  # Reticências no final
    "vou verificar",
    "deixa eu ver",
    "um momento",
    "vou buscar",
    "vou checar",
    "deixa eu buscar",
]

# Limite de retries para resposta incompleta
MAX_RETRIES_INCOMPLETO = 2


class ResponseHandler:
    """
    Processa e valida respostas do LLM.

    Centraliza a lógica de:
    - Detectar respostas incompletas que deveriam ter chamado tools
    - Validar se a resposta é adequada
    - Gerenciar retries automáticos

    Uso:
        handler = ResponseHandler()

        # Verificar se resposta está incompleta
        if handler.resposta_incompleta(texto, stop_reason):
            # Forçar retry com tool

        # Processar resultado do LLM
        generation = handler.processar_resultado_llm(resultado)
    """

    def __init__(
        self,
        padroes_incompleta: Optional[List[str]] = None,
        max_retries: int = MAX_RETRIES_INCOMPLETO,
    ):
        """
        Inicializa o handler.

        Args:
            padroes_incompleta: Padrões customizados para detecção
            max_retries: Máximo de retries para resposta incompleta
        """
        self._padroes = padroes_incompleta or PADROES_RESPOSTA_INCOMPLETA
        self._max_retries = max_retries

    def resposta_incompleta(
        self,
        texto: str,
        stop_reason: Optional[str] = None,
    ) -> bool:
        """
        Detecta se resposta parece incompleta.

        Uma resposta é considerada incompleta se:
        - Termina com padrões que indicam continuação pendente
        - NÃO parou por tool_use (nesse caso a tool será executada)

        Args:
            texto: Texto da resposta
            stop_reason: Motivo de parada (tool_use, end_turn, etc)

        Returns:
            True se resposta parece incompleta
        """
        if not texto:
            return False

        # Se parou por tool_use, a tool vai ser executada - não é incompleta
        if stop_reason == "tool_use":
            return False

        texto_lower = texto.lower().strip()

        for padrao in self._padroes:
            if texto_lower.endswith(padrao):
                logger.warning(
                    f"Resposta parece incompleta: termina com '{padrao}' "
                    f"(stop_reason={stop_reason})"
                )
                return True

        return False

    def processar_resultado_llm(
        self,
        resultado: Dict[str, Any],
    ) -> GenerationResult:
        """
        Processa resultado do LLM para formato interno.

        Converte o dict retornado pelas funções legadas para
        GenerationResult.

        Args:
            resultado: Dict com 'text', 'tool_use', 'stop_reason'

        Returns:
            GenerationResult normalizado
        """
        text = resultado.get("text") or ""
        tool_calls = resultado.get("tool_use") or []
        stop_reason = resultado.get("stop_reason") or "end_turn"

        # Marcar se precisa retry (incompleta e sem tool calls)
        needs_retry = not tool_calls and self.resposta_incompleta(text, stop_reason)

        return GenerationResult(
            text=text,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            needs_retry=needs_retry,
        )

    def extrair_texto_final(
        self,
        resultado: GenerationResult,
        fallback: str = "",
    ) -> str:
        """
        Extrai texto final da resposta.

        Args:
            resultado: GenerationResult processado
            fallback: Texto a usar se não houver resposta

        Returns:
            Texto da resposta ou fallback
        """
        return resultado.text or fallback

    def criar_resposta_final(
        self,
        texto: str,
        tool_calls_executadas: int = 0,
        retry_necessario: bool = False,
        conhecimento_usado: bool = False,
        trace_id: Optional[str] = None,
    ) -> JuliaResponse:
        """
        Cria resposta final da Julia.

        Args:
            texto: Texto da resposta
            tool_calls_executadas: Quantidade de tools executadas
            retry_necessario: Se houve retry
            conhecimento_usado: Se usou conhecimento dinâmico
            trace_id: ID de trace para debugging

        Returns:
            JuliaResponse completa
        """
        return JuliaResponse(
            texto=texto,
            tool_calls_executadas=tool_calls_executadas,
            retry_necessario=retry_necessario,
            conhecimento_usado=conhecimento_usado,
            trace_id=trace_id,
        )

    def montar_prompt_retry(self) -> str:
        """
        Monta prompt para forçar uso de tool em retry.

        Returns:
            Prompt para continuar conversa forçando tool
        """
        return (
            "Use a ferramenta buscar_vagas para encontrar as vagas disponíveis "
            "e depois responda ao médico com as opções."
        )

    def deve_forcar_retry(
        self,
        resultado: GenerationResult,
        houve_tool_use: bool,
        retry_count: int = 0,
    ) -> bool:
        """
        Verifica se deve forçar retry com tool.

        Args:
            resultado: Resultado da geração
            houve_tool_use: Se já houve tool use na conversa
            retry_count: Quantidade de retries já feitos

        Returns:
            True se deve forçar retry
        """
        if retry_count >= self._max_retries:
            logger.warning(f"Máximo de retries ({self._max_retries}) atingido")
            return False

        # Se já houve tool use, não forçar
        if houve_tool_use:
            return False

        return resultado.needs_retry


# Instância default para uso direto
_default_handler: Optional[ResponseHandler] = None


def get_response_handler() -> ResponseHandler:
    """Retorna instância default do ResponseHandler."""
    global _default_handler
    if _default_handler is None:
        _default_handler = ResponseHandler()
    return _default_handler


# Função de compatibilidade com código legado
def resposta_parece_incompleta(texto: str, stop_reason: str = None) -> bool:
    """
    Função de compatibilidade com o agente.py original.

    Usa o ResponseHandler por baixo.
    """
    return get_response_handler().resposta_incompleta(texto, stop_reason)
