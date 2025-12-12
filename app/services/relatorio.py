"""
Servico para geracao e envio de relatorios.

Horarios de report (conforme docs/FLUXOS.md):
- 10:00 - manha
- 13:00 - almoco
- 17:00 - tarde
- 20:00 - fim do dia
- Seg 09:00 - semanal
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List
import logging

from app.services.supabase import supabase, contar_interacoes_periodo
from app.services.slack import enviar_slack

logger = logging.getLogger(__name__)


# =============================================================================
# REPORTS PERIODICOS (S7.E5.1)
# =============================================================================

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

    # Definir inicio do periodo
    periodos = {
        "manha": agora.replace(hour=0, minute=0, second=0, microsecond=0),
        "almoco": agora.replace(hour=10, minute=0, second=0, microsecond=0),
        "tarde": agora.replace(hour=13, minute=0, second=0, microsecond=0),
        "fim_dia": agora.replace(hour=17, minute=0, second=0, microsecond=0),
    }
    inicio = periodos.get(tipo, periodos["manha"])

    # Coletar metricas
    metricas = await _coletar_metricas_periodo(inicio, agora)

    # Buscar destaques
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
        # Mensagens enviadas e recebidas usando helper centralizado
        total_enviadas = await contar_interacoes_periodo(inicio, fim, direcao="saida")
        total_recebidas = await contar_interacoes_periodo(inicio, fim, direcao="entrada")

        # Plantoes fechados
        plantoes_resp = (
            supabase.table("vagas")
            .select("id", count="exact")
            .eq("status", "reservada")
            .gte("fechada_em", inicio.isoformat())
            .lte("fechada_em", fim.isoformat())
            .execute()
        )

        # Handoffs
        handoffs_resp = (
            supabase.table("handoffs")
            .select("id", count="exact")
            .gte("created_at", inicio.isoformat())
            .lte("created_at", fim.isoformat())
            .execute()
        )

        # Deteccao de bot (S7.E6.4)
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
        # Plantoes fechados (detalhes)
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

        # Handoffs pendentes
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

    return destaques[:5]  # Maximo 5 destaques


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

    # Alerta visual se taxa de deteccao > 5%
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

    # Adicionar destaques
    if destaques:
        destaque_text = "\n".join([f"[{d['icone']}] {d['texto']}" for d in destaques])
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Destaques:*\n{destaque_text}"}
        })

    await enviar_slack({"blocks": blocks})
    logger.info(f"Report {report['periodo']} enviado para Slack")


# =============================================================================
# REPORT SEMANAL (S7.E5.2)
# =============================================================================

async def gerar_report_semanal() -> dict:
    """
    Gera report consolidado da semana anterior.

    Enviado toda segunda-feira as 9h.
    """
    agora = datetime.now(timezone.utc)

    # Semana anterior (segunda a domingo)
    dias_desde_segunda = agora.weekday()  # 0 = segunda
    inicio_semana = agora - timedelta(days=dias_desde_segunda + 7)
    inicio_semana = inicio_semana.replace(hour=0, minute=0, second=0, microsecond=0)
    fim_semana = inicio_semana + timedelta(days=7)

    # Metricas da semana
    metricas = await _coletar_metricas_periodo(inicio_semana, fim_semana)

    # Metricas adicionais para semanal
    metricas_extras = await _coletar_metricas_semanais(inicio_semana, fim_semana)

    # Top objecoes
    objecoes = await _analisar_objecoes(inicio_semana, fim_semana)

    return {
        "periodo": "semanal",
        "semana": inicio_semana.strftime("%d/%m") + " - " + fim_semana.strftime("%d/%m"),
        "metricas": {**metricas, **metricas_extras},
        "objecoes": objecoes
    }


async def _coletar_metricas_semanais(inicio: datetime, fim: datetime) -> dict:
    """Metricas adicionais para report semanal."""
    try:
        # Medicos contatados (unicos)
        contatados_resp = (
            supabase.table("interacoes")
            .select("cliente_id")
            .eq("direcao", "saida")
            .gte("created_at", inicio.isoformat())
            .lte("created_at", fim.isoformat())
            .execute()
        )
        unicos = len(set(c["cliente_id"] for c in contatados_resp.data or [] if c.get("cliente_id")))

        # Conversoes (responderam -> fecharam)
        conversoes_resp = (
            supabase.table("conversations")
            .select("id", count="exact")
            .in_("stage", ["fechou", "confirmado"])
            .gte("updated_at", inicio.isoformat())
            .lte("updated_at", fim.isoformat())
            .execute()
        )

        return {
            "medicos_contatados": unicos,
            "conversoes": conversoes_resp.count or 0
        }
    except Exception as e:
        logger.error(f"Erro ao coletar metricas semanais: {e}")
        return {
            "medicos_contatados": 0,
            "conversoes": 0
        }


async def _analisar_objecoes(inicio: datetime, fim: datetime) -> list:
    """Analisa principais objecoes da semana."""
    # Simplificado: retorna placeholder
    # Em producao, analisar mensagens com LLM ou palavras-chave
    return [
        {"objecao": "Valor baixo", "percentual": 34},
        {"objecao": "Sem disponibilidade", "percentual": 28},
        {"objecao": "Hospital longe", "percentual": 18},
    ]


async def enviar_report_semanal_slack(report: dict):
    """Formata e envia report semanal para Slack."""
    metricas = report["metricas"]
    objecoes = report["objecoes"]

    # Alerta visual se taxa de deteccao > 5%
    taxa_deteccao = metricas.get("deteccao_bot", 0)
    deteccoes_total = metricas.get("deteccoes_total", 0)
    alerta_bot = "ALERTA" if taxa_deteccao > 5 else "OK"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Relatorio Semanal ({report['semana']})"}
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*FUNIL*"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"Contatados: {metricas.get('medicos_contatados', 0)}"},
                {"type": "mrkdwn", "text": f"Responderam: {metricas.get('msgs_recebidas', 0)} ({metricas.get('taxa_resposta', 0)}%)"},
                {"type": "mrkdwn", "text": f"Conversoes: {metricas.get('conversoes', 0)}"},
                {"type": "mrkdwn", "text": f"Plantoes: {metricas.get('plantoes_fechados', 0)}"},
            ]
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*QUALIDADE*"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"Deteccao bot: {taxa_deteccao}% ({deteccoes_total} casos) [{alerta_bot}]"},
                {"type": "mrkdwn", "text": f"Handoffs: {metricas.get('handoffs', 0)}"},
            ]
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*TOP OBJECOES*"}
        }
    ]

    # Adicionar objecoes
    objecao_text = "\n".join([f"- {o['objecao']}: {o['percentual']}%" for o in objecoes])
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": objecao_text}
    })

    await enviar_slack({"blocks": blocks})
    logger.info("Report semanal enviado para Slack")


# =============================================================================
# RELATORIO DIARIO LEGADO (mantido para compatibilidade)
# =============================================================================


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

