"""
Health check do pool de chips.

Sprint 58 - Epic 3: Extraido de app/api/routes/health.py
Sprint 59 - Epic 5.1: Cache Redis de 30s
"""

import logging

from app.services.supabase import supabase
from app.services.redis import cache_get_json, cache_set_json

logger = logging.getLogger(__name__)

CACHE_KEY_CHIPS = "health:chips"
CACHE_TTL_CHIPS = 30  # 30 segundos


async def obter_saude_chips() -> dict:
    """
    Retorna status completo de todos os chips.

    Sprint 59 Epic 5.1: Cache Redis de 30s.

    Verifica:
    - Trust Score e nivel
    - Estado do circuit breaker
    - Permissoes (pode_prospectar, pode_followup, pode_responder)
    - Status de conexao Evolution

    Returns:
        dict com status, message, summary, capacidade e chips.
    """
    # Sprint 59 Epic 5.1: Tentar cache primeiro
    try:
        cached = await cache_get_json(CACHE_KEY_CHIPS)
        if cached:
            return cached
    except Exception:
        pass

    from app.services.chips.circuit_breaker import ChipCircuitBreaker, CircuitState

    try:
        result = (
            supabase.table("chips")
            .select("*")
            .eq("status", "active")
            .order("trust_score", desc=True)
            .execute()
        )

        chips = result.data or []
        chips_status = []
        chips_disponiveis = 0
        chips_com_circuit_aberto = 0
        chips_desconectados = 0
        chips_saudaveis = 0
        chips_atencao = 0
        chips_criticos = 0

        for chip in chips:
            chip_id = chip["id"]
            trust = chip.get("trust_score") or 50
            circuit = ChipCircuitBreaker.get_circuit(chip_id, chip.get("telefone", ""))
            circuit_state = circuit.estado.value
            evolution_connected = chip.get("evolution_connected", False)

            if trust >= 80:
                health = "saudavel"
                chips_saudaveis += 1
            elif trust >= 60:
                health = "atencao"
                chips_atencao += 1
            else:
                health = "critico"
                chips_criticos += 1

            is_available = circuit_state != CircuitState.OPEN.value and evolution_connected
            if is_available:
                chips_disponiveis += 1
            if circuit_state == CircuitState.OPEN.value:
                chips_com_circuit_aberto += 1
            if not evolution_connected:
                chips_desconectados += 1

            chips_status.append(
                {
                    "telefone": chip.get("telefone", "N/A")[-4:],
                    "trust_score": trust,
                    "trust_level": chip.get("trust_level", "unknown"),
                    "health": health,
                    "circuit_state": circuit_state,
                    "circuit_falhas": circuit.falhas_consecutivas,
                    "evolution_connected": evolution_connected,
                    "pode_prospectar": chip.get("pode_prospectar", False),
                    "pode_followup": chip.get("pode_followup", False),
                    "pode_responder": chip.get("pode_responder", False),
                    "msgs_hoje": chip.get("msgs_enviadas_hoje", 0),
                    "erros_24h": chip.get("erros_ultimas_24h", 0),
                    "is_available": is_available,
                }
            )

        total_chips = len(chips)
        if total_chips == 0:
            status = "critical"
            message = "Pool de chips vazio!"
        elif chips_disponiveis == 0:
            status = "critical"
            message = "Nenhum chip disponível (todos com circuit aberto ou desconectados)"
        elif chips_saudaveis < total_chips * 0.3:
            status = "degraded"
            message = f"Poucos chips saudáveis: {chips_saudaveis}/{total_chips}"
        elif chips_com_circuit_aberto > total_chips * 0.5:
            status = "degraded"
            message = f"Muitos chips com circuit aberto: {chips_com_circuit_aberto}/{total_chips}"
        else:
            status = "healthy"
            message = "Pool de chips saudável"

        podem_prospectar = len(
            [c for c in chips if c.get("pode_prospectar") and c.get("trust_score", 0) >= 60]
        )
        podem_followup = len(
            [c for c in chips if c.get("pode_followup") and c.get("trust_score", 0) >= 40]
        )
        podem_responder = len(
            [c for c in chips if c.get("pode_responder") and c.get("trust_score", 0) >= 20]
        )

        result = {
            "status": status,
            "message": message,
            "summary": {
                "total": total_chips,
                "disponiveis": chips_disponiveis,
                "saudaveis": chips_saudaveis,
                "atencao": chips_atencao,
                "criticos": chips_criticos,
                "circuit_aberto": chips_com_circuit_aberto,
                "desconectados": chips_desconectados,
                "trust_medio": round(sum(c.get("trust_score", 0) for c in chips) / total_chips, 1)
                if total_chips > 0
                else 0,
            },
            "capacidade": {
                "prospeccao": podem_prospectar,
                "followup": podem_followup,
                "resposta": podem_responder,
            },
            "chips": chips_status,
        }

        # Sprint 59 Epic 5.1: Salvar no cache
        try:
            await cache_set_json(CACHE_KEY_CHIPS, result, CACHE_TTL_CHIPS)
        except Exception:
            pass

        return result

    except Exception as e:
        logger.error(f"[health/chips] Error: {e}")
        return {
            "status": "error",
            "error": str(e),
        }
