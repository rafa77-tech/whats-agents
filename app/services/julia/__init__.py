"""
Julia Agent Module - Core do agente conversacional.

Sprint 31 - Decomposição do agente

Este módulo contém a lógica core da Julia, decomposta em
componentes menores e testáveis.

Uso:
    from app.services.julia import gerar_resposta_julia

    resposta = await gerar_resposta_julia(
        mensagem="Oi",
        contexto={...},
        medico={...},
        conversa={...},
    )

Componentes:
    - models.py: Dataclasses internas (JuliaContext, JuliaResponse, etc)
    - context_builder.py: Monta contexto e system prompt
    - tool_executor.py: Executa tools e processa resultados
    - response_handler.py: Valida e processa respostas
    - orchestrator.py: Orquestrador principal (função entry point)
"""

# Models
from .models import (
    JuliaContext,
    PolicyContext,
    ToolExecutionResult,
    GenerationResult,
    JuliaResponse,
)

# Context Builder
from .context_builder import ContextBuilder, get_context_builder

# Tool Executor
from .tool_executor import ToolExecutor, get_tool_executor, get_julia_tools

# Response Handler
from .response_handler import ResponseHandler, get_response_handler, resposta_parece_incompleta

# Orchestrator
from .orchestrator import gerar_resposta_julia_v2

# Re-exportar função principal (backward compatibility)
# Por enquanto aponta para o agente.py original
from app.services.agente import gerar_resposta_julia

__all__ = [
    # Função principal
    "gerar_resposta_julia",
    "gerar_resposta_julia_v2",
    # Models
    "JuliaContext",
    "PolicyContext",
    "ToolExecutionResult",
    "GenerationResult",
    "JuliaResponse",
    # Context Builder
    "ContextBuilder",
    "get_context_builder",
    # Tool Executor
    "ToolExecutor",
    "get_tool_executor",
    "get_julia_tools",
    # Response Handler
    "ResponseHandler",
    "get_response_handler",
    "resposta_parece_incompleta",
]
