"""
Servico de notificacoes via Slack.
"""
import httpx
import logging
from datetime import datetime
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
    conversa: dict,
    handoff: dict
) -> bool:
    """
    Notifica gestor sobre handoff para humano.

    Args:
        conversa: Dados da conversa (com clientes)
        handoff: Dados do handoff

    Returns:
        True se notificou com sucesso
    """
    from app.core.config import settings

    medico = conversa.get("clientes", {})
    nome_medico = medico.get("primeiro_nome", "Medico")
    telefone = medico.get("telefone", "")
    chatwoot_id = conversa.get("chatwoot_conversation_id")
    trigger_type = handoff.get("trigger_type", "manual")
    motivo = handoff.get("motivo", handoff.get("reason", "Handoff solicitado"))

    # Montar link do Chatwoot
    chatwoot_link = ""
    if chatwoot_id:
        chatwoot_link = (
            f"{settings.CHATWOOT_URL}/app/accounts/"
            f"{settings.CHATWOOT_ACCOUNT_ID}/conversations/{chatwoot_id}"
        )

    # Cor baseada no tipo
    cores = {
        "pedido_humano": "#2196F3",  # Azul
        "juridico": "#F44336",       # Vermelho
        "sentimento_negativo": "#FF9800",  # Laranja
        "baixa_confianca": "#9C27B0",  # Roxo
        "manual": "#4CAF50",          # Verde
    }

    cor = cores.get(trigger_type, "#607D8B")  # Cinza como padrão

    attachment = {
        "color": cor,
        "title": "🚨 Handoff necessário!",
        "fields": [
            {
                "title": "Medico",
                "value": nome_medico,
                "short": True
            },
            {
                "title": "Telefone",
                "value": telefone,
                "short": True
            },
            {
                "title": "Motivo",
                "value": motivo,
                "short": False
            },
            {
                "title": "Tipo",
                "value": trigger_type,
                "short": True
            },
        ],
        "footer": f"Conversa ID: {conversa.get('id', '')[:8]}",
        "ts": int(__import__("time").time())
    }

    # Adicionar link do Chatwoot se disponível
    if chatwoot_link:
        attachment["actions"] = [{
            "type": "button",
            "text": "Abrir no Chatwoot",
            "url": chatwoot_link
        }]

    mensagem = {
        "text": "🚨 Handoff necessário!",
        "attachments": [attachment]
    }

    return await enviar_slack(mensagem)


async def notificar_handoff_resolvido(
    conversa: dict,
    handoff: dict
) -> bool:
    """
    Notifica que handoff foi resolvido.

    Args:
        conversa: Dados da conversa (com clientes)
        handoff: Dados do handoff resolvido

    Returns:
        True se notificou com sucesso
    """
    medico = conversa.get("clientes", {})
    nome_medico = medico.get("primeiro_nome", "Medico")

    # Calcular duração
    duracao = "N/A"
    try:
        if handoff.get("created_at") and handoff.get("resolvido_em"):
            criado = datetime.fromisoformat(handoff["created_at"].replace("Z", "+00:00"))
            resolvido = datetime.fromisoformat(handoff["resolvido_em"].replace("Z", "+00:00"))
            minutos = int((resolvido - criado).total_seconds() / 60)
            if minutos < 60:
                duracao = f"{minutos} minutos"
            else:
                horas = minutos // 60
                mins = minutos % 60
                duracao = f"{horas}h {mins}min"
    except Exception:
        pass

    notas = handoff.get("notas", "Sem notas")

    mensagem = {
        "text": "✅ Handoff resolvido!",
        "attachments": [{
            "color": "#4CAF50",
            "title": "Handoff finalizado",
            "fields": [
                {
                    "title": "Medico",
                    "value": nome_medico,
                    "short": True
                },
                {
                    "title": "Duracao",
                    "value": duracao,
                    "short": True
                },
                {
                    "title": "Notas",
                    "value": notas[:500],  # Limitar tamanho
                    "short": False
                },
            ],
            "footer": "Agente Julia",
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
