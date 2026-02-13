"""
Ponto unico de envio de mensagens outbound.

Sprint 58 E04 - Refatorado de modulo monolitico para package.

Re-exporta toda API publica para manter backward compatibility:
  from app.services.outbound import send_outbound_message, OutboundResult
"""

# Public API
from app.services.outbound.types import OutboundResult
from app.services.outbound.sender import (
    send_outbound_message,
    _gerar_content_hash,
)
from app.services.outbound.multi_chip import (
    _is_multi_chip_enabled,
    _determinar_tipo_mensagem,
    _enviar_via_multi_chip,
)
from app.services.outbound.dev_guardrails import _verificar_dev_allowlist
from app.services.outbound.finalization import (
    _finalizar_envio,
    _atualizar_last_touch,
)
from app.services.outbound.context_factories import (
    criar_contexto_campanha,
    criar_contexto_followup,
    criar_contexto_reativacao,
    criar_contexto_reply,
    criar_contexto_manual_slack,
)

__all__ = [
    # Public API
    "send_outbound_message",
    "OutboundResult",
    # Context factories
    "criar_contexto_campanha",
    "criar_contexto_followup",
    "criar_contexto_reativacao",
    "criar_contexto_reply",
    "criar_contexto_manual_slack",
    # Internal (re-exported for backward compat)
    "_verificar_dev_allowlist",
    "_finalizar_envio",
    "_atualizar_last_touch",
    "_is_multi_chip_enabled",
    "_determinar_tipo_mensagem",
    "_enviar_via_multi_chip",
    "_gerar_content_hash",
]
