"""
Replay offline de decisões do Policy Engine.

Sprint 16 - Observability
Permite reproduzir decisões passadas para:
- Auditoria
- Debug
- Validação de mudanças em regras
- Testes de regressão
"""
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .types import (
    DoctorState,
    PolicyDecision,
    PermissionState,
    TemperatureBand,
    TemperatureTrend,
    ObjectionSeverity,
    RiskTolerance,
    LifecycleStage,
)
from .decide import PolicyDecide
from .events_repository import get_decision_by_id

logger = logging.getLogger(__name__)


@dataclass
class ReplayResult:
    """Resultado do replay de uma decisão."""

    original_decision_id: str
    original_rule: str
    original_action: str
    replayed_rule: str
    replayed_action: str
    match: bool
    hash_match: bool
    original_snapshot_hash: str
    computed_snapshot_hash: str
    differences: list[str]


def _parse_datetime_from_iso(value: Optional[str]) -> Optional[datetime]:
    """Converte string ISO para datetime."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _state_from_input(state_input: dict) -> DoctorState:
    """
    Reconstrói DoctorState a partir do doctor_state_input serializado.

    Args:
        state_input: Dict salvo no policy_event

    Returns:
        DoctorState reconstruído
    """
    # Parse enums com fallback
    try:
        permission = PermissionState(state_input.get("permission_state", "none"))
    except ValueError:
        permission = PermissionState.NONE

    try:
        trend = TemperatureTrend(state_input.get("temperature_trend", "stable"))
    except ValueError:
        trend = TemperatureTrend.STABLE

    try:
        band = TemperatureBand(state_input.get("temperature_band", "warm"))
    except ValueError:
        band = TemperatureBand.WARM

    try:
        risk = RiskTolerance(state_input.get("risk_tolerance", "unknown"))
    except ValueError:
        risk = RiskTolerance.UNKNOWN

    try:
        lifecycle = LifecycleStage(state_input.get("lifecycle_stage", "novo"))
    except ValueError:
        lifecycle = LifecycleStage.NOVO

    severity = None
    if state_input.get("objection_severity"):
        try:
            severity = ObjectionSeverity(state_input["objection_severity"])
        except ValueError:
            pass

    return DoctorState(
        cliente_id=state_input.get("cliente_id", "unknown"),
        permission_state=permission,
        temperature=float(state_input.get("temperature", 0.5)),
        temperature_trend=trend,
        temperature_band=band,
        risk_tolerance=risk,
        active_objection=state_input.get("active_objection"),
        objection_severity=severity,
        contact_count_7d=state_input.get("contact_count_7d", 0),
        cooling_off_until=_parse_datetime_from_iso(state_input.get("cooling_off_until")),
        last_inbound_at=_parse_datetime_from_iso(state_input.get("last_inbound_at")),
        last_outbound_at=_parse_datetime_from_iso(state_input.get("last_outbound_at")),
        lifecycle_stage=lifecycle,
    )


def _compute_hash(state_input: dict) -> str:
    """Computa hash do state_input para verificação."""
    normalized = json.dumps(state_input, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


async def replay_decision(
    policy_decision_id: str,
    is_first_message: Optional[bool] = None,
    conversa_status: Optional[str] = None,
    flags_override: Optional[dict] = None,
) -> Optional[ReplayResult]:
    """
    Reproduz uma decisão passada e compara com o resultado original.

    Sprint 16 Fix: Usa flags_override para replay determinístico.
    Por padrão, desabilita kill switch e safe mode para testar apenas regras.

    Args:
        policy_decision_id: ID da decisão a reproduzir
        is_first_message: Override do flag (usa original se None)
        conversa_status: Override do status (usa original se None)
        flags_override: Override de flags (default: policy habilitado, sem safe mode)

    Returns:
        ReplayResult com comparação ou None se erro
    """
    try:
        # 1. Buscar decisão original
        event = await get_decision_by_id(policy_decision_id)
        if not event:
            logger.error(f"Decisão não encontrada: {policy_decision_id}")
            return None

        # 2. Extrair dados originais
        original_rule = event.get("rule_matched", "unknown")
        original_action = event.get("primary_action", "unknown")
        original_hash = event.get("snapshot_hash", "")
        state_input = event.get("doctor_state_input", {})

        # Usar valores originais se não fornecidos
        if is_first_message is None:
            is_first_message = event.get("is_first_message", False)
        if conversa_status is None:
            conversa_status = event.get("conversa_status", "active")

        # Sprint 16 Fix: Default flags para replay determinístico
        # Replay testa REGRAS, não estado atual de kill switch
        if flags_override is None:
            flags_override = {
                "policy_engine_enabled": True,  # Sempre habilitado no replay
                "safe_mode_active": False,       # Sem safe mode no replay
                "disabled_rules": [],            # Nenhuma regra desabilitada
            }

        # 3. Verificar integridade do state_input
        computed_hash = _compute_hash(state_input)
        hash_match = computed_hash == original_hash

        if not hash_match:
            logger.warning(
                f"Hash mismatch para {policy_decision_id}: "
                f"original={original_hash}, computed={computed_hash}"
            )

        # 4. Reconstruir state
        state = _state_from_input(state_input)

        # 5. Re-executar PolicyDecide com flags determinísticos
        policy = PolicyDecide()
        replayed_decision = await policy.decide(
            state,
            is_first_message=is_first_message,
            conversa_status=conversa_status,
            flags_override=flags_override,
        )

        # 6. Comparar resultados
        replayed_rule = replayed_decision.rule_id
        replayed_action = replayed_decision.primary_action.value

        match = (
            original_rule == replayed_rule and
            original_action == replayed_action
        )

        # 7. Identificar diferenças
        differences = []
        if original_rule != replayed_rule:
            differences.append(f"rule: {original_rule} → {replayed_rule}")
        if original_action != replayed_action:
            differences.append(f"action: {original_action} → {replayed_action}")
        if event.get("tone") != replayed_decision.tone.value:
            differences.append(f"tone: {event.get('tone')} → {replayed_decision.tone.value}")
        if event.get("requires_human") != replayed_decision.requires_human:
            differences.append(
                f"requires_human: {event.get('requires_human')} → {replayed_decision.requires_human}"
            )

        return ReplayResult(
            original_decision_id=policy_decision_id,
            original_rule=original_rule,
            original_action=original_action,
            replayed_rule=replayed_rule,
            replayed_action=replayed_action,
            match=match,
            hash_match=hash_match,
            original_snapshot_hash=original_hash,
            computed_snapshot_hash=computed_hash,
            differences=differences,
        )

    except Exception as e:
        logger.error(f"Erro no replay de {policy_decision_id}: {e}")
        return None


async def replay_batch(
    decision_ids: list[str],
) -> dict:
    """
    Reproduz um lote de decisões.

    Útil para validar mudanças em regras antes de deploy.

    Args:
        decision_ids: Lista de IDs de decisões

    Returns:
        Dict com estatísticas do replay
    """
    import asyncio

    results = await asyncio.gather(
        *[replay_decision(did) for did in decision_ids],
        return_exceptions=True,
    )

    stats = {
        "total": len(decision_ids),
        "successful": 0,
        "match": 0,
        "mismatch": 0,
        "hash_mismatch": 0,
        "errors": 0,
        "mismatches": [],
    }

    for result in results:
        if isinstance(result, Exception):
            stats["errors"] += 1
        elif result is None:
            stats["errors"] += 1
        else:
            stats["successful"] += 1
            if result.match:
                stats["match"] += 1
            else:
                stats["mismatch"] += 1
                stats["mismatches"].append({
                    "decision_id": result.original_decision_id,
                    "differences": result.differences,
                })
            if not result.hash_match:
                stats["hash_mismatch"] += 1

    return stats


async def validate_rules_change(
    hours: int = 24,
    sample_size: int = 100,
) -> dict:
    """
    Valida impacto de mudanças em regras.

    Busca decisões recentes e faz replay para detectar
    mudanças no comportamento após alterações no código.

    Args:
        hours: Janela de tempo para buscar decisões
        sample_size: Quantidade de decisões a testar

    Returns:
        Dict com estatísticas de validação
    """
    from datetime import timezone, timedelta
    from app.services.supabase import supabase

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Buscar decisões recentes
        response = (
            supabase.table("policy_events")
            .select("policy_decision_id")
            .eq("event_type", "decision")
            .gte("ts", cutoff.isoformat())
            .limit(sample_size)
            .execute()
        )

        if not response.data:
            return {"error": "No decisions found", "total": 0}

        decision_ids = [d["policy_decision_id"] for d in response.data]

        # Executar replay
        return await replay_batch(decision_ids)

    except Exception as e:
        logger.error(f"Erro ao validar mudanças: {e}")
        return {"error": str(e)}
