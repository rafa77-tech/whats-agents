"""
Health check da fila de mensagens.

Sprint 58 - Epic 3: Extraido de app/api/routes/health.py
"""

import logging

logger = logging.getLogger(__name__)


async def obter_saude_fila() -> dict:
    """
    Retorna metricas e status da fila de mensagens.

    Returns:
        dict com status, alerts, metrics e thresholds.
    """
    try:
        from app.services.fila import fila_service

        stats = await fila_service.obter_estatisticas_completas()
        pendentes = stats.get("pendentes", 0)
        travadas = stats.get("travadas", 0)
        erros = stats.get("erros_ultima_hora", 0)
        idade_minutos = stats.get("mensagem_mais_antiga_min")

        status = "healthy"
        alerts = []

        if travadas > 0:
            status = "degraded"
            alerts.append(f"{travadas} mensagens travadas")
        if travadas > 10:
            status = "critical"
            alerts.append("Muitas mensagens travadas!")
        if pendentes > 100:
            status = "degraded"
            alerts.append(f"Backlog alto: {pendentes} pendentes")
        if pendentes > 500:
            status = "critical"
            alerts.append("Backlog crítico!")
        if erros > 10:
            if status != "critical":
                status = "degraded"
            alerts.append(f"{erros} erros na última hora")
        if idade_minutos and idade_minutos > 60:
            if status != "critical":
                status = "degraded"
            alerts.append(f"Mensagem mais antiga: {idade_minutos:.1f}min")

        return {
            "status": status,
            "alerts": alerts,
            "metrics": stats,
            "thresholds": {
                "backlog_warning": 100,
                "backlog_critical": 500,
                "travadas_warning": 1,
                "travadas_critical": 10,
                "erros_hora_warning": 10,
                "idade_warning_min": 60,
            },
        }

    except Exception as e:
        logger.error(f"[health/fila] Error: {e}")
        return {
            "status": "error",
            "error": str(e),
        }
