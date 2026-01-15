"""
Tool Executor - Executa tools e processa resultados.

Sprint 31 - S31.E2.3

Responsabilidades:
- Executar tool calls individuais
- Processar múltiplas tool calls em sequência
- Mapear tool_name para handler
- Formatar resultados para o LLM
"""
import logging
from typing import Dict, Any, List, Callable, Awaitable, Optional

from .models import ToolExecutionResult

logger = logging.getLogger(__name__)


# Tipo para handlers de tools
ToolHandler = Callable[[Dict, Dict, Dict], Awaitable[Dict]]


class ToolExecutor:
    """
    Executa tools do agente Julia.

    Centraliza a lógica de execução de tools, permitindo:
    - Registro dinâmico de handlers
    - Execução de múltiplas tools em sequência
    - Formatação de resultados para a API

    Uso:
        executor = ToolExecutor()

        # Executar uma tool
        result = await executor.execute(
            tool_name="buscar_vagas",
            tool_input={"especialidade": "cardiologia"},
            medico=medico_data,
            conversa=conversa_data,
        )

        # Processar lista de tool calls
        results = await executor.process_tool_calls(
            tool_calls=[{"id": "1", "name": "buscar_vagas", "input": {...}}],
            medico=medico_data,
            conversa=conversa_data,
        )
    """

    def __init__(self):
        self._handlers: Dict[str, ToolHandler] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Registra handlers padrão das tools da Julia."""
        # Import lazy para evitar circular imports
        from app.tools.vagas import (
            handle_buscar_vagas,
            handle_reservar_plantao,
            handle_buscar_info_hospital,
        )
        from app.tools.lembrete import handle_agendar_lembrete
        from app.tools.memoria import handle_salvar_memoria
        from app.tools.intermediacao import (
            handle_criar_handoff_externo,
            handle_registrar_status_intermediacao,
        )

        self.register("buscar_vagas", handle_buscar_vagas)
        self.register("reservar_plantao", handle_reservar_plantao)
        self.register("buscar_info_hospital", handle_buscar_info_hospital)
        self.register("agendar_lembrete", handle_agendar_lembrete)
        self.register("salvar_memoria", handle_salvar_memoria)
        self.register("criar_handoff_externo", handle_criar_handoff_externo)
        self.register("registrar_status_intermediacao", handle_registrar_status_intermediacao)

    def register(self, tool_name: str, handler: ToolHandler):
        """
        Registra um handler para uma tool.

        Args:
            tool_name: Nome da tool
            handler: Função async que processa a tool
        """
        self._handlers[tool_name] = handler
        logger.debug(f"Handler registrado para tool: {tool_name}")

    def get_available_tools(self) -> List[str]:
        """Retorna lista de tools disponíveis."""
        return list(self._handlers.keys())

    async def execute(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        medico: Dict[str, Any],
        conversa: Dict[str, Any],
    ) -> ToolExecutionResult:
        """
        Executa uma tool individual.

        Args:
            tool_name: Nome da tool a executar
            tool_input: Parâmetros da tool
            medico: Dados do médico
            conversa: Dados da conversa

        Returns:
            ToolExecutionResult com resultado ou erro
        """
        logger.info(f"Executando tool: {tool_name}")

        handler = self._handlers.get(tool_name)
        if not handler:
            logger.warning(f"Tool desconhecida: {tool_name}")
            return ToolExecutionResult(
                tool_call_id="",
                tool_name=tool_name,
                result={},
                success=False,
                error=f"Tool desconhecida: {tool_name}",
            )

        try:
            result = await handler(tool_input, medico, conversa)
            return ToolExecutionResult(
                tool_call_id="",
                tool_name=tool_name,
                result=result,
                success=True,
            )
        except Exception as e:
            logger.error(f"Erro ao executar tool {tool_name}: {e}")
            return ToolExecutionResult(
                tool_call_id="",
                tool_name=tool_name,
                result={},
                success=False,
                error=str(e),
            )

    async def process_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        medico: Dict[str, Any],
        conversa: Dict[str, Any],
    ) -> List[ToolExecutionResult]:
        """
        Processa múltiplas tool calls.

        Args:
            tool_calls: Lista de tool calls com id, name, input
            medico: Dados do médico
            conversa: Dados da conversa

        Returns:
            Lista de ToolExecutionResult
        """
        results = []

        for tool_call in tool_calls:
            tool_id = tool_call.get("id", "")
            tool_name = tool_call.get("name", "")
            tool_input = tool_call.get("input", {})

            result = await self.execute(
                tool_name=tool_name,
                tool_input=tool_input,
                medico=medico,
                conversa=conversa,
            )

            # Adicionar o ID do tool call ao resultado
            result.tool_call_id = tool_id
            results.append(result)

        return results

    def format_results_for_api(
        self,
        results: List[ToolExecutionResult],
    ) -> List[Dict[str, Any]]:
        """
        Formata resultados para enviar ao LLM.

        Args:
            results: Lista de ToolExecutionResult

        Returns:
            Lista no formato esperado pela API do Claude
        """
        return [result.to_api_format() for result in results]

    def build_assistant_content(
        self,
        text: Optional[str],
        tool_calls: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Monta o content do assistant para histórico.

        Combina texto (se houver) e tool_use blocks.

        Args:
            text: Texto da resposta (pode ser None)
            tool_calls: Lista de tool calls

        Returns:
            Lista de content blocks para o assistant
        """
        content = []

        if text:
            content.append({"type": "text", "text": text})

        for tool_call in tool_calls:
            content.append({
                "type": "tool_use",
                "id": tool_call.get("id", ""),
                "name": tool_call.get("name", ""),
                "input": tool_call.get("input", {}),
            })

        return content


# Instância default para uso direto
_default_executor: Optional[ToolExecutor] = None


def get_tool_executor() -> ToolExecutor:
    """Retorna instância default do ToolExecutor."""
    global _default_executor
    if _default_executor is None:
        _default_executor = ToolExecutor()
    return _default_executor


# Lista de tools disponíveis (para compatibilidade com código legado)
def get_julia_tools() -> List[Dict]:
    """
    Retorna lista de definições de tools da Julia.

    Mantém compatibilidade com JULIA_TOOLS do agente.py.
    """
    from app.tools.vagas import (
        TOOL_BUSCAR_VAGAS,
        TOOL_RESERVAR_PLANTAO,
        TOOL_BUSCAR_INFO_HOSPITAL,
    )
    from app.tools.lembrete import TOOL_AGENDAR_LEMBRETE
    from app.tools.memoria import TOOL_SALVAR_MEMORIA
    from app.tools.intermediacao import (
        TOOL_CRIAR_HANDOFF_EXTERNO,
        TOOL_REGISTRAR_STATUS_INTERMEDIACAO,
    )

    return [
        TOOL_BUSCAR_VAGAS,
        TOOL_RESERVAR_PLANTAO,
        TOOL_BUSCAR_INFO_HOSPITAL,
        TOOL_AGENDAR_LEMBRETE,
        TOOL_SALVAR_MEMORIA,
        TOOL_CRIAR_HANDOFF_EXTERNO,
        TOOL_REGISTRAR_STATUS_INTERMEDIACAO,
    ]
