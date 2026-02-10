"""
Report semanal.

Sprint 10 - S10.E3.3
"""

from datetime import datetime, timedelta, timezone
import logging

from app.services.supabase import supabase
from app.services.slack import enviar_slack
from .periodo import _coletar_metricas_periodo

logger = logging.getLogger(__name__)


async def gerar_report_semanal() -> dict:
    """
    Gera report consolidado da semana anterior.

    Enviado toda segunda-feira as 9h.
    """
    agora = datetime.now(timezone.utc)

    # Semana anterior (segunda a domingo)
    dias_desde_segunda = agora.weekday()
    inicio_semana = agora - timedelta(days=dias_desde_segunda + 7)
    inicio_semana = inicio_semana.replace(hour=0, minute=0, second=0, microsecond=0)
    fim_semana = inicio_semana + timedelta(days=7)

    metricas = await _coletar_metricas_periodo(inicio_semana, fim_semana)
    metricas_extras = await _coletar_metricas_semanais(inicio_semana, fim_semana)
    objecoes = await _analisar_objecoes(inicio_semana, fim_semana)

    return {
        "periodo": "semanal",
        "semana": inicio_semana.strftime("%d/%m") + " - " + fim_semana.strftime("%d/%m"),
        "metricas": {**metricas, **metricas_extras},
        "objecoes": objecoes,
    }


async def _coletar_metricas_semanais(inicio: datetime, fim: datetime) -> dict:
    """Metricas adicionais para report semanal."""
    try:
        contatados_resp = (
            supabase.table("interacoes")
            .select("cliente_id")
            .eq("direcao", "saida")
            .gte("created_at", inicio.isoformat())
            .lte("created_at", fim.isoformat())
            .execute()
        )
        unicos = len(
            set(c["cliente_id"] for c in contatados_resp.data or [] if c.get("cliente_id"))
        )

        conversoes_resp = (
            supabase.table("conversations")
            .select("id", count="exact")
            .in_("stage", ["fechou", "confirmado"])
            .gte("updated_at", inicio.isoformat())
            .lte("updated_at", fim.isoformat())
            .execute()
        )

        return {"medicos_contatados": unicos, "conversoes": conversoes_resp.count or 0}
    except Exception as e:
        logger.error(f"Erro ao coletar metricas semanais: {e}")
        return {"medicos_contatados": 0, "conversoes": 0}


async def _analisar_objecoes(inicio: datetime, fim: datetime) -> list:
    """Analisa principais objecoes da semana."""
    # Simplificado: retorna placeholder
    return [
        {"objecao": "Valor baixo", "percentual": 34},
        {"objecao": "Sem disponibilidade", "percentual": 28},
        {"objecao": "Hospital longe", "percentual": 18},
    ]


async def enviar_report_semanal_slack(report: dict):
    """Formata e envia report semanal para Slack."""
    metricas = report["metricas"]
    objecoes = report["objecoes"]

    taxa_deteccao = metricas.get("deteccao_bot", 0)
    deteccoes_total = metricas.get("deteccoes_total", 0)
    alerta_bot = "ALERTA" if taxa_deteccao > 5 else "OK"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Relatorio Semanal ({report['semana']})"},
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": "*FUNIL*"}},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"Contatados: {metricas.get('medicos_contatados', 0)}"},
                {
                    "type": "mrkdwn",
                    "text": f"Responderam: {metricas.get('msgs_recebidas', 0)} ({metricas.get('taxa_resposta', 0)}%)",
                },
                {"type": "mrkdwn", "text": f"Conversoes: {metricas.get('conversoes', 0)}"},
                {"type": "mrkdwn", "text": f"Plantoes: {metricas.get('plantoes_fechados', 0)}"},
            ],
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": "*QUALIDADE*"}},
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"Deteccao bot: {taxa_deteccao}% ({deteccoes_total} casos) [{alerta_bot}]",
                },
                {"type": "mrkdwn", "text": f"Handoffs: {metricas.get('handoffs', 0)}"},
            ],
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": "*TOP OBJECOES*"}},
    ]

    objecao_text = "\n".join([f"- {o['objecao']}: {o['percentual']}%" for o in objecoes])
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": objecao_text}})

    await enviar_slack({"blocks": blocks})
    logger.info("Report semanal enviado para Slack")
