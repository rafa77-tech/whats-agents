"""
Reports periodicos (manha, almoco, tarde, fim_dia).

Sprint 10 - S10.E3.3
"""
from datetime import datetime, timezone
import logging

from app.services.supabase import supabase, contar_interacoes_periodo
from app.services.slack import enviar_slack

logger = logging.getLogger(__name__)


async def gerar_report_periodo(tipo: str = "manha") -> dict:
    """
    Gera report de metricas para o periodo especificado.

    Args:
        tipo: 'manha' (desde 00h), 'almoco' (desde 10h),
              'tarde' (desde 13h), 'fim_dia' (desde 17h)

    Returns:
        dict com metricas do periodo
    """
    agora = datetime.now(timezone.utc)

    periodos = {
        "manha": agora.replace(hour=0, minute=0, second=0, microsecond=0),
        "almoco": agora.replace(hour=10, minute=0, second=0, microsecond=0),
        "tarde": agora.replace(hour=13, minute=0, second=0, microsecond=0),
        "fim_dia": agora.replace(hour=17, minute=0, second=0, microsecond=0),
    }
    inicio = periodos.get(tipo, periodos["manha"])

    metricas = await _coletar_metricas_periodo(inicio, agora)
    destaques = await _buscar_destaques_periodo(inicio, agora)

    return {
        "periodo": tipo,
        "inicio": inicio.isoformat(),
        "fim": agora.isoformat(),
        "metricas": metricas,
        "destaques": destaques
    }


async def _coletar_metricas_periodo(inicio: datetime, fim: datetime) -> dict:
    """Coleta metricas do periodo."""
    try:
        total_enviadas = await contar_interacoes_periodo(inicio, fim, direcao="saida")
        total_recebidas = await contar_interacoes_periodo(inicio, fim, direcao="entrada")

        plantoes_resp = (
            supabase.table("vagas")
            .select("id", count="exact")
            .eq("status", "reservada")
            .gte("fechada_em", inicio.isoformat())
            .lte("fechada_em", fim.isoformat())
            .execute()
        )

        handoffs_resp = (
            supabase.table("handoffs")
            .select("id", count="exact")
            .gte("created_at", inicio.isoformat())
            .lte("created_at", fim.isoformat())
            .execute()
        )

        from app.services.deteccao_bot import calcular_taxa_deteccao_periodo
        deteccao = await calcular_taxa_deteccao_periodo(inicio, fim)

        taxa_resposta = (total_recebidas / total_enviadas * 100) if total_enviadas > 0 else 0

        return {
            "msgs_enviadas": total_enviadas,
            "msgs_recebidas": total_recebidas,
            "taxa_resposta": round(taxa_resposta, 1),
            "plantoes_fechados": plantoes_resp.count or 0,
            "handoffs": handoffs_resp.count or 0,
            "deteccao_bot": deteccao["taxa_percentual"],
            "deteccoes_total": deteccao["deteccoes"]
        }
    except Exception as e:
        logger.error(f"Erro ao coletar metricas do periodo: {e}")
        return {
            "msgs_enviadas": 0,
            "msgs_recebidas": 0,
            "taxa_resposta": 0,
            "plantoes_fechados": 0,
            "handoffs": 0,
            "deteccao_bot": 0,
            "deteccoes_total": 0
        }


async def _buscar_destaques_periodo(inicio: datetime, fim: datetime) -> list:
    """Busca eventos destacados do periodo."""
    destaques = []

    try:
        plantoes_resp = (
            supabase.table("vagas")
            .select("*, clientes(primeiro_nome), hospitais(nome)")
            .eq("status", "reservada")
            .gte("fechada_em", inicio.isoformat())
            .limit(5)
            .execute()
        )

        for p in plantoes_resp.data or []:
            medico = p.get("clientes", {}).get("primeiro_nome", "Medico")
            hospital = p.get("hospitais", {}).get("nome", "Hospital")
            destaques.append({
                "tipo": "plantao_fechado",
                "icone": "OK",
                "texto": f"{medico} fechou vaga no {hospital}"
            })

        handoffs_resp = (
            supabase.table("handoffs")
            .select("*, conversations(cliente_id)")
            .gte("created_at", inicio.isoformat())
            .is_("resolvido_em", "null")
            .limit(3)
            .execute()
        )

        for h in handoffs_resp.data or []:
            motivo = h.get("motivo", "Sem motivo")[:50]
            destaques.append({
                "tipo": "handoff",
                "icone": "ATENCAO",
                "texto": f"Handoff: {motivo}"
            })

    except Exception as e:
        logger.error(f"Erro ao buscar destaques: {e}")

    return destaques[:5]


async def enviar_report_periodo_slack(report: dict):
    """Formata e envia report periodico para Slack."""
    metricas = report["metricas"]
    destaques = report["destaques"]

    titulos = {
        "manha": "Relatorio Manha",
        "almoco": "Relatorio Almoco",
        "tarde": "Relatorio Tarde",
        "fim_dia": "Relatorio Fim do Dia",
        "semanal": "Relatorio Semanal"
    }

    taxa_deteccao = metricas.get("deteccao_bot", 0)
    deteccoes_total = metricas.get("deteccoes_total", 0)
    alerta_bot = "ALERTA" if taxa_deteccao > 5 else "OK"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": titulos.get(report["periodo"], "Relatorio")}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Mensagens:* {metricas['msgs_enviadas']} enviadas"},
                {"type": "mrkdwn", "text": f"*Respostas:* {metricas['msgs_recebidas']} ({metricas['taxa_resposta']}%)"},
                {"type": "mrkdwn", "text": f"*Plantoes:* {metricas['plantoes_fechados']} fechados"},
                {"type": "mrkdwn", "text": f"*Handoffs:* {metricas['handoffs']}"},
            ]
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Deteccao bot:* {taxa_deteccao}% ({deteccoes_total} casos) [{alerta_bot}]"},
            ]
        }
    ]

    if destaques:
        destaque_text = "\n".join([f"[{d['icone']}] {d['texto']}" for d in destaques])
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Destaques:*\n{destaque_text}"}
        })

    await enviar_slack({"blocks": blocks})
    logger.info(f"Report {report['periodo']} enviado para Slack")
