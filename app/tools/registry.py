"""
Tool Registry - Registro centralizado de tools do agente.

Sprint 44 T02.5: Registry Pattern para Tools.

Permite:
- Registro dinâmico de tools via decorator
- Descoberta automática de tools disponíveis
- Execução centralizada com tratamento de erros
- Suporte a confirmação para ações críticas
"""
import logging
from typing import Callable, Dict, Any, Optional, List
from functools import wraps

logger = logging.getLogger(__name__)

# Registry global de tools
_TOOL_REGISTRY: Dict[str, dict] = {}


def register_tool(
    name: str,
    description: str,
    input_schema: dict,
    requires_confirmation: bool = False,
    category: str = "general",
):
    """
    Decorator para registrar tools automaticamente.

    Args:
        name: Nome único da tool
        description: Descrição da tool para o LLM
        input_schema: JSON Schema dos parâmetros
        requires_confirmation: Se requer confirmação antes de executar
        category: Categoria da tool (general, vagas, memoria, etc)

    Usage:
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
        async def handle_buscar_vagas(input_data: dict, medico: dict, conversa: dict) -> dict:
            # Implementação
            pass
    """
    def decorator(func: Callable):
        _TOOL_REGISTRY[name] = {
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "handler": func,
            "requires_confirmation": requires_confirmation,
            "category": category,
        }
        logger.debug(f"Tool registrada: {name} (category={category})")

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapper
    return decorator


def get_tool(name: str) -> Optional[dict]:
    """
    Retorna definição de uma tool pelo nome.

    Args:
        name: Nome da tool

    Returns:
        Dict com definição da tool ou None se não encontrada
    """
    return _TOOL_REGISTRY.get(name)


def get_all_tools() -> List[dict]:
    """
    Retorna lista de todas as tools registradas (sem handlers).

    Returns:
        Lista de definições de tools no formato esperado pelo LLM
    """
    return [
        {
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["input_schema"],
        }
        for tool in _TOOL_REGISTRY.values()
    ]


def get_tools_by_category(category: str) -> List[dict]:
    """
    Retorna tools de uma categoria específica.

    Args:
        category: Nome da categoria

    Returns:
        Lista de tools da categoria
    """
    return [
        {
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["input_schema"],
        }
        for tool in _TOOL_REGISTRY.values()
        if tool["category"] == category
    ]


def list_tool_names() -> List[str]:
    """Retorna lista de nomes de tools registradas."""
    return list(_TOOL_REGISTRY.keys())


def tool_requires_confirmation(name: str) -> bool:
    """
    Verifica se uma tool requer confirmação.

    Args:
        name: Nome da tool

    Returns:
        True se requer confirmação, False caso contrário
    """
    tool = _TOOL_REGISTRY.get(name)
    return tool.get("requires_confirmation", False) if tool else False


async def execute_tool(
    name: str,
    input_data: dict,
    medico: dict,
    conversa: dict,
) -> dict:
    """
    Executa uma tool pelo nome.

    Args:
        name: Nome da tool
        input_data: Parâmetros da tool
        medico: Dados do médico
        conversa: Dados da conversa

    Returns:
        Resultado da execução (dict com success, error, etc)
    """
    tool = get_tool(name)
    if not tool:
        logger.warning(f"Tool desconhecida: {name}")
        return {"success": False, "error": f"Tool desconhecida: {name}"}

    handler = tool.get("handler")
    if not handler:
        logger.error(f"Tool {name} não tem handler registrado")
        return {"success": False, "error": f"Tool {name} sem handler"}

    try:
        logger.info(f"Executando tool: {name}")
        result = await handler(input_data, medico, conversa)
        return result
    except Exception as e:
        logger.error(f"Erro ao executar tool {name}: {e}")
        return {"success": False, "error": str(e)}


def clear_registry():
    """Limpa o registry (útil para testes)."""
    global _TOOL_REGISTRY
    _TOOL_REGISTRY = {}
    logger.debug("Registry de tools limpo")


def register_legacy_tools():
    """
    Registra tools existentes no registry.

    Chamado na inicialização para manter compatibilidade com
    as tools definidas em arquivos separados.
    """
    # Import lazy para evitar circular imports
    from app.tools.vagas import (
        TOOL_BUSCAR_VAGAS,
        TOOL_RESERVAR_PLANTAO,
        TOOL_BUSCAR_INFO_HOSPITAL,
        handle_buscar_vagas,
        handle_reservar_plantao,
        handle_buscar_info_hospital,
    )
    from app.tools.lembrete import TOOL_AGENDAR_LEMBRETE, handle_agendar_lembrete
    from app.tools.memoria import TOOL_SALVAR_MEMORIA, handle_salvar_memoria
    from app.tools.intermediacao import (
        TOOL_CRIAR_HANDOFF_EXTERNO,
        TOOL_REGISTRAR_STATUS_INTERMEDIACAO,
        handle_criar_handoff_externo,
        handle_registrar_status_intermediacao,
    )

    # Registrar cada tool com seu handler
    legacy_tools = [
        (TOOL_BUSCAR_VAGAS, handle_buscar_vagas, "vagas"),
        (TOOL_RESERVAR_PLANTAO, handle_reservar_plantao, "vagas"),
        (TOOL_BUSCAR_INFO_HOSPITAL, handle_buscar_info_hospital, "vagas"),
        (TOOL_AGENDAR_LEMBRETE, handle_agendar_lembrete, "lembretes"),
        (TOOL_SALVAR_MEMORIA, handle_salvar_memoria, "memoria"),
        (TOOL_CRIAR_HANDOFF_EXTERNO, handle_criar_handoff_externo, "intermediacao"),
        (TOOL_REGISTRAR_STATUS_INTERMEDIACAO, handle_registrar_status_intermediacao, "intermediacao"),
    ]

    for tool_def, handler, category in legacy_tools:
        name = tool_def.get("name", "")
        if name and name not in _TOOL_REGISTRY:
            _TOOL_REGISTRY[name] = {
                "name": name,
                "description": tool_def.get("description", ""),
                "input_schema": tool_def.get("input_schema", {}),
                "handler": handler,
                "requires_confirmation": name == "reservar_plantao",  # Reserva requer confirmação
                "category": category,
            }
            logger.debug(f"Tool legada registrada: {name}")


# Auto-inicialização: registrar tools legadas quando módulo é importado
# Comentado para evitar imports circulares na inicialização
# register_legacy_tools()
