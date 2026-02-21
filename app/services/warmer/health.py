"""
Warmup Health Check - Diagnóstico do pool de warmup.

Sprint 65: Endpoint unificado para verificar saúde do sistema de warmup.
"""

import logging

from app.core.timezone import agora_brasilia
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


async def diagnostico_warmup() -> dict:
    """
    Retorna diagnóstico completo do pool de warmup.

    Returns:
        Dict com:
        - health_status: "healthy" | "degraded" | "critical"
        - pool: resumo de chips por status/fase
        - atividades_hoje: taxa de sucesso por tipo
        - alertas_ativos: contagem de alertas não resolvidos
        - timestamp: momento do diagnóstico
    """
    agora = agora_brasilia()
    inicio_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. Pool summary
    chips_result = (
        supabase.table("chips")
        .select(
            "id, telefone, status, fase_warmup, trust_score, trust_level, "
            "warming_day, msgs_enviadas_hoje, evolution_connected, provider"
        )
        .execute()
    )

    chips = chips_result.data or []
    por_fase = {}
    por_status = {}
    chips_warming_ou_active = 0
    trust_total = 0

    for chip in chips:
        fase = chip.get("fase_warmup", "repouso")
        por_fase[fase] = por_fase.get(fase, 0) + 1

        status = chip.get("status", "unknown")
        por_status[status] = por_status.get(status, 0) + 1

        if status in ("warming", "active"):
            chips_warming_ou_active += 1

        trust_total += chip.get("trust_score", 0)

    trust_medio = round(trust_total / len(chips), 1) if chips else 0

    # 2. Atividades de hoje
    atividades_result = (
        supabase.table("warmup_schedule")
        .select("tipo, status")
        .gte("created_at", inicio_dia.isoformat())
        .execute()
    )

    por_tipo = {}
    for a in atividades_result.data or []:
        tipo = a["tipo"]
        if tipo not in por_tipo:
            por_tipo[tipo] = {"total": 0, "sucesso": 0, "falha": 0, "pendente": 0}
        por_tipo[tipo]["total"] += 1
        if a["status"] == "executada":
            por_tipo[tipo]["sucesso"] += 1
        elif a["status"] == "falhou":
            por_tipo[tipo]["falha"] += 1
        elif a["status"] == "planejada":
            por_tipo[tipo]["pendente"] += 1

    for tipo, stats in por_tipo.items():
        executadas = stats["sucesso"] + stats["falha"]
        stats["taxa_sucesso"] = (
            round(stats["sucesso"] / executadas * 100, 1) if executadas > 0 else None
        )

    # 3. Alertas ativos
    try:
        alertas_result = (
            supabase.table("chip_alerts")
            .select("id", count="exact")
            .eq("resolved", False)
            .execute()
        )
        alertas_ativos = alertas_result.count or 0
    except Exception:
        alertas_ativos = 0

    # 4. Determinar health status
    taxa_conversa_par = por_tipo.get("CONVERSA_PAR", {}).get("taxa_sucesso")

    if taxa_conversa_par is None:
        # Sem dados de CONVERSA_PAR hoje
        if chips_warming_ou_active > 0:
            health = "degraded"
        else:
            health = "critical"
    elif taxa_conversa_par >= 80 and chips_warming_ou_active > 0:
        health = "healthy"
    elif taxa_conversa_par >= 50:
        health = "degraded"
    else:
        health = "critical"

    return {
        "health_status": health,
        "pool": {
            "total": len(chips),
            "warming_ou_active": chips_warming_ou_active,
            "por_fase": por_fase,
            "por_status": por_status,
            "trust_medio": trust_medio,
        },
        "atividades_hoje": por_tipo,
        "alertas_ativos": alertas_ativos,
        "timestamp": agora.isoformat(),
    }
