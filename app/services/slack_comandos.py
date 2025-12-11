"""
Servico de processamento de comandos via Slack.

Usa o agente conversacional para interpretar mensagens em linguagem natural
e executar acoes de gestao.

O gestor pode conversar com a Julia como se fosse uma colega de trabalho:
- "Julia, manda msg pro 11999..."
- "Quantos responderam hoje?"
- "Bloqueia o 11988..."
"""
import re
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.config import settings
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


async def processar_comando(texto: str, channel: str, user: str):
    """
    Processa mensagem recebida do Slack usando o agente conversacional.

    Args:
        texto: Texto da mensagem (inclui mencao ao bot)
        channel: ID do canal
        user: ID do usuario que enviou
    """
    # Remover mencao ao bot do texto
    # Formato: <@U123ABC> mensagem
    texto_limpo = re.sub(r'<@[A-Z0-9]+>', '', texto).strip()

    logger.info(f"Mensagem recebida: '{texto_limpo}' de {user} em {channel}")

    # Salvar comando no banco
    comando_id = await _salvar_comando(texto, texto_limpo, user, channel)

    try:
        # Usar agente conversacional
        from app.services.agente_slack import processar_mensagem_slack

        resposta = await processar_mensagem_slack(texto_limpo, channel, user)

        await _responder_slack(channel, resposta)
        await _atualizar_comando(comando_id, resposta, sucesso=True)

    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        erro = "Ops, tive um problema aqui. Tenta de novo?"
        await _responder_slack(channel, erro)
        await _atualizar_comando(comando_id, str(e), sucesso=False)


# =============================================================================
# FUNCOES AUXILIARES
# =============================================================================

async def _responder_slack(channel: str, mensagem: str):
    """
    Envia resposta para o canal do Slack.
    """
    if not settings.SLACK_BOT_TOKEN:
        logger.warning("SLACK_BOT_TOKEN nao configurado")
        return

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={
                    "channel": channel,
                    "text": mensagem,
                    "unfurl_links": False
                },
                timeout=10.0
            )

            data = response.json()
            if not data.get("ok"):
                logger.error(f"Erro ao responder Slack: {data.get('error')}")

    except Exception as e:
        logger.error(f"Erro ao enviar resposta Slack: {e}")


async def _salvar_comando(texto_original: str, texto_limpo: str, user: str, channel: str) -> Optional[str]:
    """
    Salva comando no banco para historico.
    """
    try:
        partes = texto_limpo.split(maxsplit=1)
        comando = partes[0] if partes else ""
        args = partes[1].split() if len(partes) > 1 else []

        result = supabase.table("slack_comandos").insert({
            "texto_original": texto_original,
            "comando": comando,
            "argumentos": args,
            "user_id": user,
            "channel_id": channel,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        if result.data:
            return result.data[0].get("id")

    except Exception as e:
        logger.error(f"Erro ao salvar comando: {e}")

    return None


async def _atualizar_comando(comando_id: Optional[str], resposta: str, sucesso: bool):
    """
    Atualiza comando com resposta.
    """
    if not comando_id:
        return

    try:
        supabase.table("slack_comandos").update({
            "resposta": resposta,
            "respondido": True,
            "respondido_em": datetime.now(timezone.utc).isoformat(),
            "erro": None if sucesso else resposta
        }).eq("id", comando_id).execute()

    except Exception as e:
        logger.error(f"Erro ao atualizar comando: {e}")
