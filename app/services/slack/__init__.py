"""
Servicos Slack.

Modulo principal para integracao com Slack.
Sprint 10 - S10.E2.1, S10.E2.2
"""
from .agent import AgenteSlack, processar_mensagem_slack
from .session import SessionManager
from .tool_executor import ToolExecutor
from .prompts import SYSTEM_PROMPT_AGENTE
from .formatter import (
    bold,
    italic,
    code,
    code_block,
    quote,
    lista,
    lista_numerada,
    link,
    formatar_telefone,
    formatar_valor,
    formatar_porcentagem,
    formatar_data,
    formatar_data_hora,
    formatar_data_longa,
    template_metricas,
    template_comparacao,
    template_lista_medicos,
    template_lista_vagas,
    template_medico_info,
    template_confirmacao_envio,
    template_sucesso_envio,
    template_sucesso_bloqueio,
    template_sucesso_desbloqueio,
    template_sucesso_reserva,
    template_status_sistema,
    template_lista_handoffs,
    template_historico,
    formatar_erro,
    ERROS_AMIGAVEIS,
)

__all__ = [
    # Agent components
    "AgenteSlack",
    "processar_mensagem_slack",
    "SessionManager",
    "ToolExecutor",
    "SYSTEM_PROMPT_AGENTE",
    # Primitives
    "bold",
    "italic",
    "code",
    "code_block",
    "quote",
    "lista",
    "lista_numerada",
    "link",
    # Converters
    "formatar_telefone",
    "formatar_valor",
    "formatar_porcentagem",
    "formatar_data",
    "formatar_data_hora",
    "formatar_data_longa",
    # Templates
    "template_metricas",
    "template_comparacao",
    "template_lista_medicos",
    "template_lista_vagas",
    "template_medico_info",
    "template_confirmacao_envio",
    "template_sucesso_envio",
    "template_sucesso_bloqueio",
    "template_sucesso_desbloqueio",
    "template_sucesso_reserva",
    "template_status_sistema",
    "template_lista_handoffs",
    "template_historico",
    "formatar_erro",
    "ERROS_AMIGAVEIS",
]
