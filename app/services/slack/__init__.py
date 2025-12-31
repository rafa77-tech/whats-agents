"""
Servicos Slack.

Modulo principal para integracao com Slack.
Sprint 10 - S10.E2.1, S10.E2.2
"""
# Re-export funcoes de notificacao do arquivo slack.py original
# Workaround para conflito de namespace (diretorio slack/ vs arquivo slack.py)
import sys
import importlib.util

# Carregar slack.py diretamente
_spec = importlib.util.spec_from_file_location(
    "slack_notifications",
    str(__file__).replace("slack/__init__.py", "slack.py")
)
_slack_notifications = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_slack_notifications)

enviar_slack = _slack_notifications.enviar_slack
notificar_plantao_reservado = _slack_notifications.notificar_plantao_reservado
notificar_handoff = _slack_notifications.notificar_handoff
notificar_handoff_resolvido = _slack_notifications.notificar_handoff_resolvido
notificar_erro = _slack_notifications.notificar_erro
# Sprint 18 - Controle de notificações
is_notifications_enabled = _slack_notifications.is_notifications_enabled
set_notifications_enabled = _slack_notifications.set_notifications_enabled
get_notifications_status = _slack_notifications.get_notifications_status

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
    # Notifications (from slack.py)
    "enviar_slack",
    "notificar_plantao_reservado",
    "notificar_handoff",
    "notificar_handoff_resolvido",
    "notificar_erro",
    # Sprint 18 - Controle de notificações
    "is_notifications_enabled",
    "set_notifications_enabled",
    "get_notifications_status",
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
