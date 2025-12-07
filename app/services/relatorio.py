"""
Serviço para geração e envio de relatórios diários.
"""
from datetime import datetime, timedelta
from typing import Dict
import logging

from app.services.supabase import supabase
from app.services.slack import enviar_slack

logger = logging.getLogger(__name__)


async def gerar_relatorio_diario() -> Dict:
    """Gera relatório do dia anterior."""
    ontem = datetime.now() - timedelta(days=1)
    inicio = ontem.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    fim = ontem.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()

    try:
        # Buscar dados
        conversas_response = (
            supabase.table("conversations")
            .select("*")
            .gte("created_at", inicio)
            .lte("created_at", fim)
            .execute()
        )
        conversas = conversas_response.data or []

        interacoes_response = (
            supabase.table("interacoes")
            .select("*")
            .gte("created_at", inicio)
            .lte("created_at", fim)
            .execute()
        )
        interacoes = interacoes_response.data or []

        handoffs_response = (
            supabase.table("handoffs")
            .select("*")
            .gte("created_at", inicio)
            .lte("created_at", fim)
            .execute()
        )
        handoffs = handoffs_response.data or []

        avaliacoes_response = (
            supabase.table("avaliacoes_qualidade")
            .select("score_geral")
            .gte("created_at", inicio)
            .lte("created_at", fim)
            .execute()
        )
        avaliacoes = avaliacoes_response.data or []

        # Calcular métricas
        total_conversas = len(conversas)
        total_msgs_recebidas = len([i for i in interacoes if i.get("direcao") == "entrada"])
        total_msgs_enviadas = len([i for i in interacoes if i.get("direcao") == "saida"])
        total_handoffs = len(handoffs)

        score_medio = 0
        if avaliacoes:
            scores = [a.get("score_geral") for a in avaliacoes if a.get("score_geral")]
            if scores:
                score_medio = sum(scores) / len(scores)

        return {
            "data": ontem.strftime("%d/%m/%Y"),
            "conversas": {
                "total": total_conversas,
                "novas": len([c for c in conversas if c.get("created_at") >= inicio]),
            },
            "mensagens": {
                "recebidas": total_msgs_recebidas,
                "enviadas": total_msgs_enviadas,
            },
            "handoffs": {
                "total": total_handoffs,
                "taxa": total_handoffs / total_conversas if total_conversas > 0 else 0,
            },
            "qualidade": {
                "score_medio": round(score_medio, 1),
                "avaliacoes": len(avaliacoes),
            }
        }
    except Exception as e:
        logger.error(f"Erro ao gerar relatório diário: {e}")
        return {
            "data": ontem.strftime("%d/%m/%Y"),
            "erro": str(e)
        }


async def enviar_relatorio_slack(relatorio: Dict):
    """Envia relatório formatado para Slack."""
    if "erro" in relatorio:
        mensagem = {
            "text": f"❌ Erro ao gerar relatório diário - {relatorio['data']}",
            "attachments": [{
                "color": "#F44336",
                "text": f"Erro: {relatorio['erro']}"
            }]
        }
    else:
        mensagem = {
            "text": f"📊 Relatório Diário - {relatorio['data']}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"📊 Relatório Diário - {relatorio['data']}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Conversas:* {relatorio['conversas']['total']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Novas:* {relatorio['conversas']['novas']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Msgs Recebidas:* {relatorio['mensagens']['recebidas']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Msgs Enviadas:* {relatorio['mensagens']['enviadas']}"
                        },
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Handoffs:* {relatorio['handoffs']['total']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Taxa Handoff:* {relatorio['handoffs']['taxa']*100:.1f}%"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Score Médio:* {relatorio['qualidade']['score_medio']}/10"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Avaliações:* {relatorio['qualidade']['avaliacoes']}"
                        },
                    ]
                },
            ]
        }

    await enviar_slack(mensagem)

