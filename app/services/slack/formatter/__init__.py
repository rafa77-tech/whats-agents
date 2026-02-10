"""
Formatador de respostas para Slack.

Re-exports de todos os modulos de formatacao.
Sprint 10 - S10.E2.1
"""

from .primitives import (
    bold,
    italic,
    code,
    code_block,
    quote,
    lista,
    lista_numerada,
    link,
)

from .converters import (
    formatar_telefone,
    formatar_valor,
    formatar_valor_completo,
    formatar_porcentagem,
    formatar_data,
    formatar_data_hora,
    formatar_data_longa,
)

from .templates import (
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
    "formatar_valor_completo",
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
