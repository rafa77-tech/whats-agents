"""
Coleta de alertas consolidados do sistema.

Sprint 58 - Epic 3: Extraido de app/api/routes/health.py
"""

import logging

from app.services.supabase import supabase
from app.services.circuit_breaker import obter_status_circuits

logger = logging.getLogger(__name__)


async def coletar_alertas_sistema() -> dict:
    """
    Coleta alertas de todos os subsistemas.

    Subsistemas verificados:
    - Fila de mensagens
    - Circuit breakers
    - Chips/pool

    Returns:
        dict com status, total_alerts e lista de alerts.
    """
    alerts = []

    try:
        # 1. Alertas da fila
        alerts.extend(await _coletar_alertas_fila())

        # 2. Alertas dos circuit breakers
        alerts.extend(_coletar_alertas_circuits())

        # 3. Alertas do pool de chips
        alerts.extend(_coletar_alertas_chips())

        # Ordenar por severidade
        severity_order = {"critical": 0, "error": 1, "warning": 2, "info": 3}
        alerts.sort(key=lambda a: severity_order.get(a.get("severity", "info"), 99))

        # Determinar status geral
        has_critical = any(a.get("severity") == "critical" for a in alerts)
        has_warning = any(a.get("severity") == "warning" for a in alerts)

        if has_critical:
            status = "critical"
        elif has_warning:
            status = "warning"
        else:
            status = "ok"

        return {
            "status": status,
            "total_alerts": len(alerts),
            "alerts": alerts,
        }

    except Exception as e:
        logger.error(f"[health/alerts] Error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "alerts": alerts,
        }


async def _coletar_alertas_fila() -> list:
    """Coleta alertas da fila de mensagens."""
    alerts = []
    try:
        from app.services.fila import fila_service

        fila_stats = await fila_service.obter_estatisticas_completas()
        if fila_stats.get("travadas", 0) > 0:
            alerts.append(
                {
                    "severity": "warning" if fila_stats["travadas"] < 10 else "critical",
                    "source": "fila",
                    "message": f"{fila_stats['travadas']} mensagens travadas",
                    "value": fila_stats["travadas"],
                }
            )
        if fila_stats.get("pendentes", 0) > 100:
            alerts.append(
                {
                    "severity": "warning" if fila_stats["pendentes"] < 500 else "critical",
                    "source": "fila",
                    "message": f"Backlog alto: {fila_stats['pendentes']} pendentes",
                    "value": fila_stats["pendentes"],
                }
            )
    except Exception as e:
        alerts.append(
            {
                "severity": "error",
                "source": "fila",
                "message": f"Erro ao verificar fila: {e}",
            }
        )
    return alerts


def _coletar_alertas_circuits() -> list:
    """Coleta alertas dos circuit breakers."""
    alerts = []
    try:
        circuits = obter_status_circuits()
        for name, circuit in circuits.items():
            if circuit.get("estado") == "open":
                alerts.append(
                    {
                        "severity": "critical",
                        "source": "circuit_breaker",
                        "message": f"Circuit {name} está ABERTO",
                        "circuit": name,
                        "falhas": circuit.get("falhas_consecutivas"),
                    }
                )
            elif circuit.get("estado") == "half_open":
                alerts.append(
                    {
                        "severity": "warning",
                        "source": "circuit_breaker",
                        "message": f"Circuit {name} testando recuperação",
                        "circuit": name,
                    }
                )
    except Exception as e:
        alerts.append(
            {
                "severity": "error",
                "source": "circuit_breaker",
                "message": f"Erro ao verificar circuits: {e}",
            }
        )
    return alerts


def _coletar_alertas_chips() -> list:
    """Coleta alertas do pool de chips."""
    alerts = []
    try:
        result = (
            supabase.table("chips")
            .select("id, trust_score, evolution_connected, status")
            .eq("status", "active")
            .execute()
        )

        chips = result.data or []
        total = len(chips)
        conectados = len([c for c in chips if c.get("evolution_connected")])
        criticos = len([c for c in chips if (c.get("trust_score") or 0) < 40])

        if total == 0:
            alerts.append(
                {
                    "severity": "critical",
                    "source": "chips",
                    "message": "Pool de chips vazio!",
                }
            )
        elif conectados == 0:
            alerts.append(
                {
                    "severity": "critical",
                    "source": "chips",
                    "message": "Nenhum chip conectado!",
                }
            )
        elif conectados < total * 0.5:
            alerts.append(
                {
                    "severity": "warning",
                    "source": "chips",
                    "message": f"Poucos chips conectados: {conectados}/{total}",
                    "conectados": conectados,
                    "total": total,
                }
            )
        if criticos > total * 0.3:
            alerts.append(
                {
                    "severity": "warning",
                    "source": "chips",
                    "message": f"Muitos chips críticos: {criticos}/{total}",
                    "criticos": criticos,
                }
            )
    except Exception as e:
        alerts.append(
            {
                "severity": "error",
                "source": "chips",
                "message": f"Erro ao verificar chips: {e}",
            }
        )
    return alerts
