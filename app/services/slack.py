"""
Servico de notificacoes via Slack.
"""

import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.services.http_client import get_http_client

logger = logging.getLogger(__name__)

# =============================================================================
# CONTROLE DE NOTIFICAÇÕES (Sprint 18)
# =============================================================================

NOTIFICATIONS_KEY = "slack:notifications:enabled"


async def is_notifications_enabled() -> bool:
    """
    Verifica se notificações Slack estão habilitadas.

    Default: True (habilitado)
    """
    from app.services.redis import cache_get_json

    try:
        result = await cache_get_json(NOTIFICATIONS_KEY)
        if result is None:
            return True  # Default: habilitado
        return result.get("enabled", True)
    except Exception as e:
        logger.warning(f"Erro ao verificar status notificações: {e}")
        return True  # Em caso de erro, assume habilitado


async def set_notifications_enabled(enabled: bool, user_id: str = None) -> dict:
    """
    Habilita ou desabilita notificações Slack.

    Args:
        enabled: True para habilitar, False para desabilitar
        user_id: ID do usuário que fez a alteração

    Returns:
        Dict com status e mensagem
    """
    from app.services.redis import cache_set_json

    try:
        # TTL de 7 dias - configuração operacional deve persistir
        # (default de 300s causava expiração prematura)
        await cache_set_json(
            NOTIFICATIONS_KEY,
            {
                "enabled": enabled,
                "changed_by": user_id,
                "changed_at": datetime.now(timezone.utc).isoformat(),
            },
            ttl=604800,
        )  # 7 dias

        status = "habilitadas" if enabled else "desabilitadas"
        logger.info(f"Notificações Slack {status} por {user_id}")

        return {
            "success": True,
            "enabled": enabled,
            "message": f"Notificações {status} com sucesso",
        }
    except Exception as e:
        logger.error(f"Erro ao alterar status notificações: {e}")
        return {"success": False, "error": str(e)}


async def get_notifications_status() -> dict:
    """
    Retorna status detalhado das notificações.
    """
    from app.services.redis import cache_get_json

    try:
        result = await cache_get_json(NOTIFICATIONS_KEY)
        if result is None:
            return {
                "enabled": True,
                "changed_by": None,
                "changed_at": None,
                "status": "default (habilitado)",
            }
        return {**result, "status": "habilitado" if result.get("enabled", True) else "desabilitado"}
    except Exception as e:
        return {"enabled": True, "error": str(e), "status": "erro (assumindo habilitado)"}


async def enviar_slack(mensagem: dict, force: bool = False) -> bool:
    """
    Envia mensagem para o Slack via webhook.

    Args:
        mensagem: Dict com formato de mensagem do Slack
        force: Se True, ignora o flag de notificações desabilitadas

    Returns:
        True se enviou com sucesso
    """
    if not settings.SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL nao configurado, ignorando notificacao")
        return False

    # Verificar se notificações estão habilitadas (exceto se force=True)
    if not force:
        enabled = await is_notifications_enabled()
        if not enabled:
            logger.info("Notificações Slack desabilitadas, ignorando")
            return False

    try:
        client = await get_http_client()
        response = await client.post(settings.SLACK_WEBHOOK_URL, json=mensagem, timeout=10.0)

        if response.status_code == 200:
            logger.info("Notificacao Slack enviada com sucesso")
            return True
        else:
            logger.error(f"Erro ao enviar Slack: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"Erro ao conectar com Slack: {e}")
        return False


# =============================================================================
# FUNÇÕES DE NOTIFICAÇÃO REMOVIDAS (Sprint 47)
# =============================================================================
# As seguintes funções foram removidas pois o Slack agora é usado
# exclusivamente para interação com Helena (agente de analytics):
# - notificar_plantao_reservado
# - notificar_handoff
# - notificar_handoff_resolvido
# - notificar_confirmacao_plantao
# - atualizar_mensagem_confirmada
# - notificar_erro
#
# O dashboard agora é responsável por exibir essas informações.
# =============================================================================
