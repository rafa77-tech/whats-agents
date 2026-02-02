"""
Serviço para detecção e notificação de alertas/anomalias.

V2 - Slack baixo ruido (31/12/2025):
- Janela operacional 08-20h para alertas nao-criticos
- Cooldown global por severidade
- Condicao "houve envios" para alerta "sem_respostas"
"""
from datetime import datetime, timedelta
from typing import List, Dict
import logging

from app.core.timezone import agora_brasilia
from app.services.supabase import supabase
from app.services.redis import cache_get_json, cache_set_json
# Sprint 47: enviar_slack removido - alertas agora são apenas logados

logger = logging.getLogger(__name__)

# V2: Configuracao de janela operacional e cooldown
ALERTAS_CONFIG = {
    "janela_operacional": {
        "inicio": 8,   # 08:00
        "fim": 20,     # 20:00
    },
    "cooldown_por_severidade": {
        "info": 60,      # 60 min
        "warning": 30,   # 30 min
        "error": 30,     # 30 min
        "critical": 45,  # 45 min
    },
    # Alertas que IGNORAM janela operacional (infra critica)
    "alertas_24h": {"performance_critica"},
}

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
    desde = (agora_brasilia() - timedelta(minutes=config["janela_minutos"])).isoformat()

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
    desde = (agora_brasilia() - timedelta(minutes=config["janela_minutos"])).isoformat()

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
    desde = (agora_brasilia() - timedelta(minutes=config["janela_minutos"])).isoformat()

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
    """
    Verifica se há atividade (mensagens enviadas).

    V2: So alerta se:
    1. Estamos dentro da janela operacional (08-20h)
    2. Houve mensagens de ENTRADA (medicos mandaram msg) mas nenhuma SAIDA (Julia nao respondeu)

    Isso evita falsos positivos fora do horario ou quando ninguem mandou msg.
    """
    config = ALERTAS["sem_respostas"]
    desde = (agora_brasilia() - timedelta(minutes=config["janela_minutos"])).isoformat()

    try:
        # V2: Verificar janela operacional primeiro
        agora_sp = agora_brasilia()
        hora_atual = agora_sp.hour
        janela = ALERTAS_CONFIG["janela_operacional"]

        if hora_atual < janela["inicio"] or hora_atual >= janela["fim"]:
            # Fora do horario operacional - nao alertar
            return []

        # Buscar mensagens de SAIDA (Julia respondendo)
        saidas_response = (
            supabase.table("interacoes")
            .select("id", count="exact")
            .eq("direcao", "saida")
            .gte("created_at", desde)
            .execute()
        )
        total_saidas = saidas_response.count or 0

        # V2: So alertar se nao houve saidas E houve entradas (medicos esperando)
        if total_saidas == 0:
            entradas_response = (
                supabase.table("interacoes")
                .select("id", count="exact")
                .eq("direcao", "entrada")
                .gte("created_at", desde)
                .execute()
            )
            total_entradas = entradas_response.count or 0

            # So alertar se medicos mandaram msg mas Julia nao respondeu
            if total_entradas > 0:
                return [{
                    "tipo": "sem_respostas",
                    "mensagem": f"{total_entradas} mensagens recebidas sem resposta nos ultimos {config['janela_minutos']} minutos",
                    "severidade": config["severidade"],
                    "valor": total_entradas
                }]

        return []
    except Exception as e:
        logger.error(f"Erro ao verificar atividade: {e}")
        return []


async def verificar_performance() -> List[Dict]:
    """Verifica performance e envia alertas se necessário."""
    from app.core.metrics import metrics
    
    resumo = metrics.obter_resumo()
    alertas = []

    for nome, dados in resumo.get("tempos", {}).items():
        if isinstance(dados, dict) and "media_ms" in dados:
            # Tempo médio > 2s
            if dados["media_ms"] > 2000:
                alertas.append({
                    "tipo": "performance_critica",
                    "mensagem": f"{nome}: tempo médio {dados['media_ms']:.0f}ms",
                    "severidade": "critical",
                    "valor": dados["media_ms"]
                })
            # Tempo médio > 1s
            elif dados["media_ms"] > 1000:
                alertas.append({
                    "tipo": "performance_warning",
                    "mensagem": f"{nome}: tempo médio {dados['media_ms']:.0f}ms",
                    "severidade": "warning",
                    "valor": dados["media_ms"]
                })

    return alertas


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
    
    # Performance
    alertas_ativos.extend(await verificar_performance())

    return alertas_ativos


async def enviar_alerta_slack(alerta: Dict):
    """
    Loga alerta (notificação Slack removida Sprint 47).

    Alertas agora são apenas logados e salvos no banco.
    O dashboard é responsável por exibir alertas.
    """
    nivel_log = {
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error,
        "critical": logger.critical,
    }
    log_fn = nivel_log.get(alerta["severidade"], logger.warning)
    log_fn(
        f"Alerta [{alerta['severidade'].upper()}] {alerta['tipo']}: {alerta['mensagem']}",
        extra={"alerta_tipo": alerta["tipo"], "severidade": alerta["severidade"]}
    )


async def _verificar_cooldown_alerta(tipo: str, severidade: str) -> bool:
    """
    V2: Verifica se alerta esta em cooldown.

    Returns:
        True se pode enviar, False se em cooldown
    """
    cache_key = f"alerta:cooldown:{tipo}"

    try:
        ultimo = await cache_get_json(cache_key)
        if not ultimo:
            return True  # Nunca enviado, pode enviar

        ultimo_envio = datetime.fromisoformat(ultimo.get("timestamp", "2000-01-01"))
        cooldown_min = ALERTAS_CONFIG["cooldown_por_severidade"].get(severidade, 30)
        cooldown = timedelta(minutes=cooldown_min)

        if agora_brasilia() - ultimo_envio < cooldown:
            logger.debug(f"Alerta {tipo} em cooldown ({cooldown_min}min)")
            return False

        return True
    except Exception as e:
        logger.error(f"Erro ao verificar cooldown: {e}")
        return True  # Em caso de erro, permite envio


async def _registrar_envio_alerta(tipo: str):
    """V2: Registra envio de alerta para cooldown."""
    cache_key = f"alerta:cooldown:{tipo}"
    try:
        await cache_set_json(cache_key, {
            "timestamp": agora_brasilia().isoformat(),
            "tipo": tipo
        }, ttl=7200)  # 2 horas
    except Exception as e:
        logger.error(f"Erro ao registrar envio alerta: {e}")


async def executar_verificacao_alertas():
    """
    Job para verificar alertas periodicamente.

    V2: Implementa cooldown por severidade e janela operacional.
    """
    try:
        alertas = await verificar_alertas()

        for alerta in alertas:
            tipo = alerta["tipo"]
            severidade = alerta["severidade"]

            # V2: Verificar cooldown antes de enviar
            if not await _verificar_cooldown_alerta(tipo, severidade):
                continue

            await enviar_alerta_slack(alerta)
            await _registrar_envio_alerta(tipo)

            # Salvar no banco para histórico (se tabela existir)
            try:
                supabase.table("alertas_enviados").insert({
                    "tipo": tipo,
                    "mensagem": alerta["mensagem"],
                    "severidade": severidade,
                    "valor": alerta.get("valor")
                }).execute()
            except Exception as e:
                # Tabela pode não existir ainda
                logger.debug(f"Tabela alertas_enviados não existe ou erro ao salvar: {e}")

        # Sprint 17 - E07: Verificar alertas de Business Events (funil)
        await _verificar_alertas_business_events()

    except Exception as e:
        logger.error(f"Erro ao executar verificação de alertas: {e}")


async def _verificar_alertas_business_events():
    """
    Verifica alertas de anomalias no funil de negocio.

    Sprint 17 - E07
    """
    try:
        from app.services.business_events.alerts import (
            detect_all_anomalies,
            process_and_notify_alerts,
        )

        alertas = await detect_all_anomalies()

        if alertas:
            logger.info(f"Detectados {len(alertas)} alertas de business events")
            enviados = await process_and_notify_alerts(alertas)
            logger.info(f"Enviados {enviados} alertas ao Slack (com cooldown)")

    except Exception as e:
        logger.error(f"Erro ao verificar alertas de business events: {e}")


# =============================================================================
# Sprint 44 T07.5: Alertas de Infraestrutura Crítica
# =============================================================================

async def alertar_circuit_breaker_aberto(
    servico: str,
    falhas: int,
    ultimo_erro: str,
) -> None:
    """
    Loga alerta de circuit breaker (notificação Slack removida Sprint 47).

    Alertas críticos são logados e podem ser visualizados no dashboard.
    """
    from app.core.logging import get_trace_id

    logger.critical(
        f"Circuit breaker aberto: {servico} - {falhas} falhas consecutivas",
        extra={
            "trace_id": get_trace_id(),
            "servico": servico,
            "falhas": falhas,
            "ultimo_erro": ultimo_erro[:200],
            "alerta_tipo": "circuit_breaker_aberto",
        }
    )


async def alertar_handoff_sem_notificacao(
    conversa_id: str,
    handoff_id: str,
    motivo: str,
) -> None:
    """
    Loga alerta de handoff sem notificação (Slack removido Sprint 47).

    Handoffs são monitorados pelo dashboard.
    """
    logger.critical(
        f"Handoff criado sem notificação - conversa {conversa_id[:8]} aguarda atendimento",
        extra={
            "conversa_id": conversa_id,
            "handoff_id": handoff_id,
            "motivo": motivo[:200],
            "alerta_tipo": "handoff_sem_notificacao",
        }
    )


async def alertar_llm_timeout(
    conversa_id: str,
    telefone: str,
    tempo_segundos: float,
) -> None:
    """
    Loga alerta de LLM timeout (Slack removido Sprint 47).
    """
    from app.core.logging import mask_phone

    logger.warning(
        f"LLM timeout após {tempo_segundos:.1f}s - conversa {conversa_id[:8]}",
        extra={
            "conversa_id": conversa_id,
            "telefone_masked": mask_phone(telefone),
            "tempo_segundos": tempo_segundos,
            "alerta_tipo": "llm_timeout",
        }
    )


async def alertar_database_error(
    operacao: str,
    erro: str,
    tabela: str = None,
) -> None:
    """
    Loga alerta de erro de banco (Slack removido Sprint 47).
    """
    logger.error(
        f"Database error: {operacao} - {erro[:100]}",
        extra={
            "operacao": operacao,
            "tabela": tabela or "N/A",
            "erro": erro[:300],
            "alerta_tipo": "database_error",
        }
    )

