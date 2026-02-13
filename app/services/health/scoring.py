"""
Calculo de health score consolidado do sistema.

Sprint 58 - Epic 3: Extraido de app/api/routes/health.py

Score de 0-100 baseado em:
- Conectividade (Redis, Supabase, Evolution): 30 pontos
- Fila de mensagens: 25 pontos
- Pool de chips: 25 pontos
- Circuit breakers: 20 pontos
"""

import logging

from app.services.redis import verificar_conexao_redis
from app.services.whatsapp import evolution
from app.services.supabase import supabase
from app.services.circuit_breaker import obter_status_circuits

logger = logging.getLogger(__name__)


async def calcular_health_score() -> dict:
    """
    Calcula health score consolidado do sistema.

    Returns:
        dict com score, level, color, breakdown e thresholds.
    """
    score = 0
    breakdown = {}

    try:
        # 1. Conectividade (30 pontos)
        connectivity_score = await _calcular_score_conectividade()
        breakdown["connectivity"] = {"score": connectivity_score, "max": 30}
        score += connectivity_score

        # 2. Fila de mensagens (25 pontos)
        fila_score = await _calcular_score_fila()
        breakdown["fila"] = {"score": fila_score, "max": 25}
        score += fila_score

        # 3. Pool de chips (25 pontos)
        chips_score = _calcular_score_chips()
        breakdown["chips"] = {"score": chips_score, "max": 25}
        score += chips_score

        # 4. Circuit breakers (20 pontos)
        circuit_score = _calcular_score_circuits()
        breakdown["circuits"] = {"score": circuit_score, "max": 20}
        score += circuit_score

        # Determinar nivel
        if score >= 80:
            level = "healthy"
            color = "green"
        elif score >= 60:
            level = "attention"
            color = "yellow"
        elif score >= 40:
            level = "degraded"
            color = "orange"
        else:
            level = "critical"
            color = "red"

        return {
            "score": score,
            "max_score": 100,
            "level": level,
            "color": color,
            "breakdown": breakdown,
            "thresholds": {
                "healthy": 80,
                "attention": 60,
                "degraded": 40,
                "critical": 0,
            },
        }

    except Exception as e:
        logger.error(f"[health/score] Error: {e}")
        return {
            "score": 0,
            "level": "error",
            "error": str(e),
            "breakdown": breakdown,
        }


async def _calcular_score_conectividade() -> int:
    """Calcula score de conectividade (max 30 pontos)."""
    connectivity_score = 0

    # Redis (10 pontos)
    try:
        redis_ok = await verificar_conexao_redis()
        if redis_ok:
            connectivity_score += 10
    except Exception:
        pass

    # Supabase (10 pontos)
    try:
        supabase.table("clientes").select("id").limit(1).execute()
        connectivity_score += 10
    except Exception:
        pass

    # Evolution (10 pontos)
    try:
        status = await evolution.verificar_conexao()
        state = None
        if status:
            if "instance" in status:
                state = status.get("instance", {}).get("state")
            else:
                state = status.get("state")
        if state == "open":
            connectivity_score += 10
        elif state:
            connectivity_score += 5
    except Exception:
        pass

    return connectivity_score


async def _calcular_score_fila() -> int:
    """Calcula score da fila de mensagens (max 25 pontos)."""
    fila_score = 25
    try:
        from app.services.fila import fila_service

        fila_stats = await fila_service.obter_estatisticas_completas()
        pendentes = fila_stats.get("pendentes", 0)
        travadas = fila_stats.get("travadas", 0)
        erros = fila_stats.get("erros_ultima_hora", 0)

        if pendentes > 500:
            fila_score -= 15
        elif pendentes > 100:
            fila_score -= 5

        if travadas > 10:
            fila_score -= 10
        elif travadas > 0:
            fila_score -= 5

        if erros > 20:
            fila_score -= 10
        elif erros > 5:
            fila_score -= 5

        fila_score = max(0, fila_score)
    except Exception:
        fila_score = 0

    return fila_score


def _calcular_score_chips() -> int:
    """Calcula score do pool de chips (max 25 pontos)."""
    chips_score = 25
    try:
        result = (
            supabase.table("chips")
            .select("id, trust_score, evolution_connected")
            .eq("status", "active")
            .execute()
        )

        chips = result.data or []
        total = len(chips)

        if total == 0:
            chips_score = 0
        else:
            conectados = len([c for c in chips if c.get("evolution_connected")])
            saudaveis = len([c for c in chips if (c.get("trust_score") or 0) >= 60])

            taxa_conectados = conectados / total
            taxa_saudaveis = saudaveis / total

            if taxa_conectados < 0.5:
                chips_score -= 15
            elif taxa_conectados < 0.8:
                chips_score -= 5

            if taxa_saudaveis < 0.3:
                chips_score -= 10
            elif taxa_saudaveis < 0.5:
                chips_score -= 5

            chips_score = max(0, chips_score)
    except Exception:
        chips_score = 0

    return chips_score


def _calcular_score_circuits() -> int:
    """Calcula score dos circuit breakers (max 20 pontos)."""
    circuit_score = 20
    try:
        circuits = obter_status_circuits()
        for name, circuit in circuits.items():
            estado = circuit.get("estado")
            if estado == "open":
                circuit_score -= 8  # Circuit aberto eh grave
            elif estado == "half_open":
                circuit_score -= 3
        circuit_score = max(0, circuit_score)
    except Exception:
        circuit_score = 0

    return circuit_score
