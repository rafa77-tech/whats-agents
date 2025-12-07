"""
Servico de notificacoes via Slack.
"""
import httpx
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


async def enviar_slack(mensagem: dict) -> bool:
    """
    Envia mensagem para o Slack via webhook.

    Args:
        mensagem: Dict com formato de mensagem do Slack

    Returns:
        True se enviou com sucesso
    """
    if not settings.SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL nao configurado, ignorando notificacao")
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.SLACK_WEBHOOK_URL,
                json=mensagem,
                timeout=10.0
            )

            if response.status_code == 200:
                logger.info("Notificacao Slack enviada com sucesso")
                return True
            else:
                logger.error(f"Erro ao enviar Slack: {response.status_code}")
                return False

    except Exception as e:
        logger.error(f"Erro ao conectar com Slack: {e}")
        return False


async def notificar_plantao_reservado(
    medico: dict,
    vaga: dict
) -> bool:
    """
    Notifica gestor via Slack sobre plantao reservado.

    Args:
        medico: Dados do medico
        vaga: Dados da vaga reservada

    Returns:
        True se notificou com sucesso
    """
    # Extrair dados
    nome_medico = medico.get("primeiro_nome", "Medico")
    if medico.get("sobrenome"):
        nome_medico += f" {medico['sobrenome']}"

    hospital = vaga.get("hospitais", {}).get("nome", "Hospital")
    data = vaga.get("data", "")
    periodo = vaga.get("periodos", {}).get("nome", "")
    valor = vaga.get("valor") or 0
    setor = vaga.get("setores", {}).get("nome", "")

    # Formatar data
    data_formatada = data
    if data:
        try:
            from datetime import datetime
            data_obj = datetime.strptime(data, "%Y-%m-%d")
            data_formatada = data_obj.strftime("%d/%m/%Y")
        except ValueError:
            pass

    # Montar campos
    fields = [
        {"title": "Medico", "value": nome_medico, "short": True},
        {"title": "Hospital", "value": hospital, "short": True},
        {"title": "Data", "value": data_formatada, "short": True},
        {"title": "Periodo", "value": periodo, "short": True},
    ]

    if setor:
        fields.append({"title": "Setor", "value": setor, "short": True})

    if valor:
        fields.append({"title": "Valor", "value": f"R$ {valor:,.0f}".replace(",", "."), "short": True})

    mensagem = {
        "text": "Plantao reservado!",
        "attachments": [{
            "color": "#00ff00",
            "title": "Novo plantao fechado pela Julia",
            "fields": fields,
            "footer": "Agente Julia",
            "ts": int(__import__("time").time())
        }]
    }

    return await enviar_slack(mensagem)


async def notificar_handoff(
    medico: dict,
    motivo: str,
    conversa_id: str
) -> bool:
    """
    Notifica gestor sobre handoff para humano.

    Args:
        medico: Dados do medico
        motivo: Motivo do handoff
        conversa_id: ID da conversa

    Returns:
        True se notificou com sucesso
    """
    nome_medico = medico.get("primeiro_nome", "Medico")
    telefone = medico.get("telefone", "")

    mensagem = {
        "text": "Atencao: Handoff solicitado!",
        "attachments": [{
            "color": "#ff9900",
            "title": "Conversa precisa de atencao humana",
            "fields": [
                {"title": "Medico", "value": nome_medico, "short": True},
                {"title": "Telefone", "value": telefone, "short": True},
                {"title": "Motivo", "value": motivo, "short": False},
            ],
            "footer": f"Conversa ID: {conversa_id[:8]}",
            "ts": int(__import__("time").time())
        }]
    }

    return await enviar_slack(mensagem)


async def notificar_erro(
    titulo: str,
    detalhes: str,
    contexto: Optional[dict] = None
) -> bool:
    """
    Notifica erro no sistema.

    Args:
        titulo: Titulo do erro
        detalhes: Detalhes do erro
        contexto: Contexto adicional (opcional)

    Returns:
        True se notificou com sucesso
    """
    fields = [
        {"title": "Erro", "value": titulo, "short": False},
        {"title": "Detalhes", "value": detalhes[:500], "short": False},
    ]

    if contexto:
        for key, value in list(contexto.items())[:3]:
            fields.append({"title": str(key), "value": str(value)[:100], "short": True})

    mensagem = {
        "text": "Erro no sistema Julia",
        "attachments": [{
            "color": "#ff0000",
            "title": "Erro detectado",
            "fields": fields,
            "footer": "Agente Julia",
            "ts": int(__import__("time").time())
        }]
    }

    return await enviar_slack(mensagem)
