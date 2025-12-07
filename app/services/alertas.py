"""
Serviço para detecção e notificação de alertas/anomalias.
"""
from datetime import datetime, timedelta
from typing import List, Dict
import logging

from app.services.supabase import supabase
from app.services.slack import enviar_slack

logger = logging.getLogger(__name__)

ALERTAS = {
    "taxa_handoff_alta": {
        "descricao": "Taxa de handoff acima do normal",
        "threshold": 0.20,  # > 20%
        "janela_minutos": 60,
        "severidade": "warning"
    },
    "tempo_resposta_alto": {
        "descricao": "Tempo médio de resposta muito alto",
        "threshold": 120,  # > 120 segundos
        "janela_minutos": 30,
        "severidade": "warning"
    },
    "score_qualidade_baixo": {
        "descricao": "Score de qualidade abaixo do aceitável",
        "threshold": 5,  # < 5/10
        "janela_minutos": 60,
        "severidade": "error"
    },
    "sem_respostas": {
        "descricao": "Nenhuma resposta enviada",
        "threshold": 0,
        "janela_minutos": 30,
        "severidade": "critical"
    },
}

CORES_SEVERIDADE = {
    "info": "#2196F3",
    "warning": "#FF9800",
    "error": "#F44336",
    "critical": "#9C27B0",
}


async def verificar_taxa_handoff() -> List[Dict]:
    """Verifica se taxa de handoff está alta."""
    config = ALERTAS["taxa_handoff_alta"]
    desde = (datetime.now() - timedelta(minutes=config["janela_minutos"])).isoformat()

    try:
        # Buscar conversas e handoffs
        conversas_response = (
            supabase.table("conversations")
            .select("id")
            .gte("created_at", desde)
            .execute()
        )
        conversas = conversas_response.data or []

        handoffs_response = (
            supabase.table("handoffs")
            .select("id")
            .gte("created_at", desde)
            .execute()
        )
        handoffs = handoffs_response.data or []

        if len(conversas) > 0:
            taxa = len(handoffs) / len(conversas)
            if taxa > config["threshold"]:
                return [{
                    "tipo": "taxa_handoff_alta",
                    "mensagem": f"Taxa de handoff em {taxa*100:.1f}% (threshold: {config['threshold']*100}%)",
                    "severidade": config["severidade"],
                    "valor": taxa
                }]

        return []
    except Exception as e:
        logger.error(f"Erro ao verificar taxa de handoff: {e}")
        return []


async def verificar_tempo_resposta() -> List[Dict]:
    """Verifica se tempo médio de resposta está alto."""
    config = ALERTAS["tempo_resposta_alto"]
    desde = (datetime.now() - timedelta(minutes=config["janela_minutos"])).isoformat()

    try:
        # Buscar métricas de conversa
        metricas_response = (
            supabase.table("metricas_conversa")
            .select("tempo_medio_resposta_segundos")
            .gte("updated_at", desde)
            .execute()
        )
        metricas = metricas_response.data or []

        if metricas:
            tempos = [m.get("tempo_medio_resposta_segundos") for m in metricas if m.get("tempo_medio_resposta_segundos")]
            if tempos:
                tempo_medio = sum(tempos) / len(tempos)
                if tempo_medio > config["threshold"]:
                    return [{
                        "tipo": "tempo_resposta_alto",
                        "mensagem": f"Tempo médio de resposta: {tempo_medio:.1f}s (threshold: {config['threshold']}s)",
                        "severidade": config["severidade"],
                        "valor": tempo_medio
                    }]

        return []
    except Exception as e:
        logger.error(f"Erro ao verificar tempo de resposta: {e}")
        return []


async def verificar_score_qualidade() -> List[Dict]:
    """Verifica se score de qualidade está baixo."""
    config = ALERTAS["score_qualidade_baixo"]
    desde = (datetime.now() - timedelta(minutes=config["janela_minutos"])).isoformat()

    try:
        # Buscar avaliações recentes
        avaliacoes_response = (
            supabase.table("avaliacoes_qualidade")
            .select("score_geral")
            .gte("created_at", desde)
            .execute()
        )
        avaliacoes = avaliacoes_response.data or []

        if avaliacoes:
            scores = [a.get("score_geral") for a in avaliacoes if a.get("score_geral")]
            if scores:
                score_medio = sum(scores) / len(scores)
                if score_medio < config["threshold"]:
                    return [{
                        "tipo": "score_qualidade_baixo",
                        "mensagem": f"Score médio de qualidade: {score_medio:.1f}/10 (threshold: {config['threshold']}/10)",
                        "severidade": config["severidade"],
                        "valor": score_medio
                    }]

        return []
    except Exception as e:
        logger.error(f"Erro ao verificar score de qualidade: {e}")
        return []


async def verificar_atividade() -> List[Dict]:
    """Verifica se há atividade (mensagens enviadas)."""
    config = ALERTAS["sem_respostas"]
    desde = (datetime.now() - timedelta(minutes=config["janela_minutos"])).isoformat()

    try:
        # Buscar mensagens enviadas
        interacoes_response = (
            supabase.table("interacoes")
            .select("id")
            .eq("direcao", "saida")
            .gte("created_at", desde)
            .execute()
        )
        interacoes = interacoes_response.data or []

        if len(interacoes) == 0:
            return [{
                "tipo": "sem_respostas",
                "mensagem": f"Nenhuma resposta enviada nos últimos {config['janela_minutos']} minutos",
                "severidade": config["severidade"],
                "valor": 0
            }]

        return []
    except Exception as e:
        logger.error(f"Erro ao verificar atividade: {e}")
        return []


async def verificar_alertas() -> List[Dict]:
    """
    Verifica todas as condições de alerta.

    Returns:
        Lista de alertas ativos
    """
    alertas_ativos = []

    # Taxa de handoff
    alertas_ativos.extend(await verificar_taxa_handoff())

    # Tempo de resposta
    alertas_ativos.extend(await verificar_tempo_resposta())

    # Score de qualidade
    alertas_ativos.extend(await verificar_score_qualidade())

    # Sem respostas
    alertas_ativos.extend(await verificar_atividade())

    return alertas_ativos


async def enviar_alerta_slack(alerta: Dict):
    """Envia alerta para Slack."""
    cor = CORES_SEVERIDADE.get(alerta["severidade"], "#607D8B")

    mensagem = {
        "text": f"⚠️ Alerta: {alerta['tipo']}",
        "attachments": [{
            "color": cor,
            "fields": [
                {"title": "Descrição", "value": alerta["mensagem"], "short": False},
                {"title": "Severidade", "value": alerta["severidade"], "short": True},
                {"title": "Horário", "value": datetime.now().strftime("%H:%M"), "short": True},
            ]
        }]
    }

    await enviar_slack(mensagem)


async def executar_verificacao_alertas():
    """Job para verificar alertas periodicamente."""
    try:
        alertas = await verificar_alertas()

        for alerta in alertas:
            # Verificar se já foi enviado recentemente (evitar spam)
            # Por simplicidade, sempre envia. Em produção, adicionar lógica de deduplicação
            await enviar_alerta_slack(alerta)

            # Salvar no banco para histórico (se tabela existir)
            try:
                supabase.table("alertas_enviados").insert({
                    "tipo": alerta["tipo"],
                    "mensagem": alerta["mensagem"],
                    "severidade": alerta["severidade"],
                    "valor": alerta.get("valor")
                }).execute()
            except Exception as e:
                # Tabela pode não existir ainda
                logger.debug(f"Tabela alertas_enviados não existe ou erro ao salvar: {e}")

    except Exception as e:
        logger.error(f"Erro ao executar verificação de alertas: {e}")

