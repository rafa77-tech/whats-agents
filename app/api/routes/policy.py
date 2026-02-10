"""
Router de Policy Engine - Sprint 43.

Expõe funcionalidades do Policy Engine:
- Status e flags
- Safe mode
- Regras
- Métricas
- Decisões
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.services.policy.flags import (
    is_policy_engine_enabled,
    is_safe_mode_active,
    get_safe_mode_action,
    are_campaigns_enabled,
    get_disabled_rules,
    enable_policy_engine,
    disable_policy_engine,
    enable_safe_mode,
    disable_safe_mode,
    enable_rule,
    disable_rule,
)
from app.services.policy.metrics import (
    get_decisions_count,
    get_decisions_by_rule,
    get_decisions_by_action,
    get_decisions_per_hour,
    get_orphan_decisions,
    get_policy_summary,
)
from app.services.policy.rules import RULES_IN_ORDER

router = APIRouter(prefix="/policy", tags=["policy"])
logger = get_logger(__name__)


# ============================================================
# Schemas
# ============================================================


class PolicyStatusResponse(BaseModel):
    """Status geral do Policy Engine."""

    enabled: bool
    safe_mode: bool
    safe_mode_action: str
    campaigns_enabled: bool
    disabled_rules: list[str]


class PolicyToggleRequest(BaseModel):
    """Request para habilitar/desabilitar."""

    usuario: str = Field(default="dashboard", description="Usuário que alterou")


class PolicyToggleResponse(BaseModel):
    """Resposta de toggle."""

    success: bool
    enabled: bool


class SafeModeRequest(BaseModel):
    """Request para safe mode."""

    mode: str = Field(default="wait", pattern="^(wait|handoff)$", description="wait ou handoff")
    usuario: str = Field(default="dashboard", description="Usuário que alterou")


class SafeModeResponse(BaseModel):
    """Resposta do safe mode."""

    success: bool
    enabled: bool
    mode: str


class SafeModeStatusResponse(BaseModel):
    """Status do safe mode."""

    enabled: bool
    mode: str


class RuleInfo(BaseModel):
    """Informação de uma regra."""

    id: str
    name: str
    description: str
    enabled: bool


class RulesListResponse(BaseModel):
    """Lista de regras."""

    rules: list[RuleInfo]
    total: int
    disabled_count: int


class RuleToggleRequest(BaseModel):
    """Request para toggle de regra."""

    usuario: str = Field(default="dashboard", description="Usuário que alterou")


class RuleToggleResponse(BaseModel):
    """Resposta de toggle de regra."""

    success: bool
    rule_id: str
    enabled: bool


class MetricsSummaryResponse(BaseModel):
    """Resumo de métricas."""

    period_hours: int
    total_decisions: int
    total_handoffs: int
    handoff_rate: float
    decisions_by_rule: list[dict]
    decisions_by_action: list[dict]
    effects_by_type: list[dict]


class DecisionsCountResponse(BaseModel):
    """Contagem de decisões."""

    count: int
    period_hours: int


class DecisionsByRuleResponse(BaseModel):
    """Decisões agrupadas por regra."""

    data: list[dict]
    period_hours: int


class DecisionsByHourResponse(BaseModel):
    """Decisões por hora."""

    data: list[dict]
    period_hours: int


class OrphanDecisionsResponse(BaseModel):
    """Decisões órfãs."""

    orphans: list[dict]
    count: int
    period_hours: int


class DecisionDetailResponse(BaseModel):
    """Detalhe de uma decisão."""

    decision_id: str
    cliente_id: str
    rule_matched: str
    primary_action: str
    requires_human: bool
    ts: str
    detalhes: dict


# ============================================================
# Status e Flags
# ============================================================


@router.get("/status", response_model=PolicyStatusResponse)
async def get_policy_status() -> PolicyStatusResponse:
    """
    Retorna status geral do Policy Engine.

    Inclui:
    - enabled: se engine está habilitado
    - safe_mode: se modo seguro está ativo
    - safe_mode_action: ação do safe mode (wait/handoff)
    - campaigns_enabled: se campanhas estão habilitadas
    - disabled_rules: lista de regras desabilitadas
    """
    disabled_rules_flags = await get_disabled_rules()

    return PolicyStatusResponse(
        enabled=await is_policy_engine_enabled(),
        safe_mode=await is_safe_mode_active(),
        safe_mode_action=await get_safe_mode_action(),
        campaigns_enabled=await are_campaigns_enabled(),
        disabled_rules=disabled_rules_flags.rules,
    )


@router.post("/enable", response_model=PolicyToggleResponse)
async def enable_policy(request: PolicyToggleRequest) -> PolicyToggleResponse:
    """
    Habilita o Policy Engine.

    Args:
        request: usuario

    Returns:
        Confirmação
    """
    success = await enable_policy_engine(updated_by=request.usuario)

    if not success:
        raise HTTPException(status_code=500, detail="Erro ao habilitar Policy Engine")

    logger.info(f"[policy] Policy Engine HABILITADO por {request.usuario}")

    return PolicyToggleResponse(success=True, enabled=True)


@router.post("/disable", response_model=PolicyToggleResponse)
async def disable_policy(request: PolicyToggleRequest) -> PolicyToggleResponse:
    """
    Desabilita o Policy Engine.

    ATENÇÃO: Isso desliga todo o engine de decisões!

    Args:
        request: usuario

    Returns:
        Confirmação
    """
    success = await disable_policy_engine(updated_by=request.usuario)

    if not success:
        raise HTTPException(status_code=500, detail="Erro ao desabilitar Policy Engine")

    logger.warning(f"[policy] Policy Engine DESABILITADO por {request.usuario}")

    return PolicyToggleResponse(success=True, enabled=False)


# ============================================================
# Safe Mode
# ============================================================


@router.get("/safe-mode", response_model=SafeModeStatusResponse)
async def get_safe_mode_status() -> SafeModeStatusResponse:
    """
    Retorna status do modo seguro.

    Returns:
        enabled: se está ativo
        mode: "wait" (não responde) ou "handoff" (escala humano)
    """
    return SafeModeStatusResponse(
        enabled=await is_safe_mode_active(),
        mode=await get_safe_mode_action(),
    )


@router.post("/safe-mode/enable", response_model=SafeModeResponse)
async def enable_safe_mode_endpoint(request: SafeModeRequest) -> SafeModeResponse:
    """
    Ativa modo seguro.

    Modos disponíveis:
    - wait: Julia não responde (mensagens ficam pendentes)
    - handoff: Julia escala para humano automaticamente

    Args:
        request: mode (wait/handoff), usuario

    Returns:
        Confirmação
    """
    success = await enable_safe_mode(mode=request.mode, updated_by=request.usuario)

    if not success:
        raise HTTPException(status_code=500, detail="Erro ao ativar safe mode")

    logger.warning(f"[policy] Safe Mode ATIVADO ({request.mode}) por {request.usuario}")

    return SafeModeResponse(success=True, enabled=True, mode=request.mode)


@router.post("/safe-mode/disable", response_model=SafeModeResponse)
async def disable_safe_mode_endpoint(request: PolicyToggleRequest) -> SafeModeResponse:
    """
    Desativa modo seguro.

    Args:
        request: usuario

    Returns:
        Confirmação
    """
    success = await disable_safe_mode(updated_by=request.usuario)

    if not success:
        raise HTTPException(status_code=500, detail="Erro ao desativar safe mode")

    logger.info(f"[policy] Safe Mode DESATIVADO por {request.usuario}")

    return SafeModeResponse(success=True, enabled=False, mode="wait")


# ============================================================
# Regras
# ============================================================


@router.get("/rules", response_model=RulesListResponse)
async def list_rules() -> RulesListResponse:
    """
    Lista todas as regras do Policy Engine.

    Inclui status (habilitada/desabilitada) de cada regra.

    Returns:
        Lista de regras com info e status
    """
    disabled_rules_flags = await get_disabled_rules()
    disabled_set = set(disabled_rules_flags.rules)

    # Extrair info das regras do código
    rules = []
    for rule_func in RULES_IN_ORDER:
        rule_id = rule_func.__name__
        rules.append(
            RuleInfo(
                id=rule_id,
                name=rule_id.replace("rule_", "").replace("_", " ").title(),
                description=rule_func.__doc__.strip().split("\n")[0] if rule_func.__doc__ else "",
                enabled=rule_id not in disabled_set,
            )
        )

    # Adicionar rule_default (sempre presente)
    rules.append(
        RuleInfo(
            id="rule_default",
            name="Default",
            description="Regra padrão conservadora (fallback)",
            enabled=True,  # Default nunca é desabilitada
        )
    )

    disabled_count = len(disabled_set)

    return RulesListResponse(
        rules=rules,
        total=len(rules),
        disabled_count=disabled_count,
    )


@router.post("/rules/{rule_id}/enable", response_model=RuleToggleResponse)
async def enable_rule_endpoint(
    request: RuleToggleRequest,
    rule_id: str = Path(..., description="ID da regra"),
) -> RuleToggleResponse:
    """
    Habilita uma regra específica.

    Args:
        rule_id: ID da regra (ex: rule_grave_objection)
        request: usuario

    Returns:
        Confirmação
    """
    success = await enable_rule(rule_id=rule_id, updated_by=request.usuario)

    if not success:
        raise HTTPException(status_code=500, detail=f"Erro ao habilitar regra: {rule_id}")

    logger.info(f"[policy] Regra {rule_id} HABILITADA por {request.usuario}")

    return RuleToggleResponse(success=True, rule_id=rule_id, enabled=True)


@router.post("/rules/{rule_id}/disable", response_model=RuleToggleResponse)
async def disable_rule_endpoint(
    request: RuleToggleRequest,
    rule_id: str = Path(..., description="ID da regra"),
) -> RuleToggleResponse:
    """
    Desabilita uma regra específica.

    ATENÇÃO: Desabilitar regras críticas pode causar comportamento indesejado!

    Args:
        rule_id: ID da regra (ex: rule_grave_objection)
        request: usuario

    Returns:
        Confirmação
    """
    # Não permitir desabilitar rule_default
    if rule_id == "rule_default":
        raise HTTPException(
            status_code=400,
            detail="Não é possível desabilitar a regra default",
        )

    success = await disable_rule(rule_id=rule_id, updated_by=request.usuario)

    if not success:
        raise HTTPException(status_code=500, detail=f"Erro ao desabilitar regra: {rule_id}")

    logger.warning(f"[policy] Regra {rule_id} DESABILITADA por {request.usuario}")

    return RuleToggleResponse(success=True, rule_id=rule_id, enabled=False)


# ============================================================
# Métricas
# ============================================================


@router.get("/metrics", response_model=MetricsSummaryResponse)
async def get_metrics_summary(
    horas: int = Query(24, ge=1, le=168, description="Período em horas (max 7 dias)"),
) -> MetricsSummaryResponse:
    """
    Retorna resumo de métricas do Policy Engine.

    Inclui:
    - Total de decisões
    - Total de handoffs
    - Taxa de handoff
    - Decisões por regra
    - Decisões por ação
    - Efeitos por tipo

    Args:
        horas: Período (default 24h, max 168h/7dias)

    Returns:
        Resumo de métricas
    """
    summary = await get_policy_summary(hours=horas)

    return MetricsSummaryResponse(
        period_hours=summary.get("period_hours", horas),
        total_decisions=summary.get("total_decisions", 0),
        total_handoffs=summary.get("total_handoffs", 0),
        handoff_rate=summary.get("handoff_rate", 0.0),
        decisions_by_rule=summary.get("decisions_by_rule", []),
        decisions_by_action=summary.get("decisions_by_action", []),
        effects_by_type=summary.get("effects_by_type", []),
    )


@router.get("/metrics/decisions", response_model=DecisionsCountResponse)
async def get_decisions_count_endpoint(
    horas: int = Query(24, ge=1, le=168, description="Período em horas"),
    cliente_id: Optional[str] = Query(None, description="Filtrar por cliente"),
) -> DecisionsCountResponse:
    """
    Conta total de decisões no período.

    Args:
        horas: Período em horas
        cliente_id: Filtrar por cliente (opcional)

    Returns:
        Contagem de decisões
    """
    count = await get_decisions_count(hours=horas, cliente_id=cliente_id)

    return DecisionsCountResponse(count=count, period_hours=horas)


@router.get("/metrics/rules", response_model=DecisionsByRuleResponse)
async def get_decisions_by_rule_endpoint(
    horas: int = Query(24, ge=1, le=168, description="Período em horas"),
) -> DecisionsByRuleResponse:
    """
    Agrupa decisões por regra.

    Mostra qual regra está disparando mais.

    Args:
        horas: Período em horas

    Returns:
        Decisões agrupadas por regra
    """
    data = await get_decisions_by_rule(hours=horas)

    return DecisionsByRuleResponse(data=data, period_hours=horas)


@router.get("/metrics/actions", response_model=DecisionsByRuleResponse)
async def get_decisions_by_action_endpoint(
    horas: int = Query(24, ge=1, le=168, description="Período em horas"),
) -> DecisionsByRuleResponse:
    """
    Agrupa decisões por ação primária.

    Mostra distribuição de ações (followup, wait, handoff, etc).

    Args:
        horas: Período em horas

    Returns:
        Decisões agrupadas por ação
    """
    data = await get_decisions_by_action(hours=horas)

    return DecisionsByRuleResponse(data=data, period_hours=horas)


@router.get("/metrics/hourly", response_model=DecisionsByHourResponse)
async def get_decisions_per_hour_endpoint(
    horas: int = Query(24, ge=1, le=168, description="Período em horas"),
) -> DecisionsByHourResponse:
    """
    Decisões agrupadas por hora.

    Útil para visualizar volume ao longo do tempo.

    Args:
        horas: Período em horas

    Returns:
        Decisões por hora
    """
    data = await get_decisions_per_hour(hours=horas)

    return DecisionsByHourResponse(data=data, period_hours=horas)


@router.get("/metrics/orphans", response_model=OrphanDecisionsResponse)
async def get_orphan_decisions_endpoint(
    horas: int = Query(24, ge=1, le=168, description="Período em horas"),
    limite: int = Query(100, ge=1, le=500, description="Máximo de resultados"),
) -> OrphanDecisionsResponse:
    """
    Encontra decisões órfãs (sem efeitos correspondentes).

    Decisões órfãs podem indicar bugs no pipeline, erros de rede ou timeouts.

    Args:
        horas: Período em horas
        limite: Máximo de resultados

    Returns:
        Lista de decisões órfãs
    """
    orphans = await get_orphan_decisions(hours=horas, limit=limite)

    return OrphanDecisionsResponse(
        orphans=orphans,
        count=len(orphans),
        period_hours=horas,
    )


# ============================================================
# Decisões (Debug)
# ============================================================


@router.get("/decisions/cliente/{cliente_id}")
async def get_decisions_by_cliente(
    cliente_id: str = Path(..., description="ID do cliente"),
    horas: int = Query(24, ge=1, le=168, description="Período em horas"),
    limite: int = Query(50, ge=1, le=200, description="Máximo de resultados"),
) -> dict:
    """
    Lista decisões de um cliente específico.

    Útil para debug de comportamento do Policy Engine.

    Args:
        cliente_id: ID do cliente (médico)
        horas: Período em horas
        limite: Máximo de resultados

    Returns:
        Lista de decisões do cliente
    """
    from datetime import datetime, timedelta, timezone
    from app.services.supabase import supabase

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=horas)

        response = (
            supabase.table("policy_events")
            .select("*")
            .eq("event_type", "decision")
            .eq("cliente_id", cliente_id)
            .gte("ts", cutoff.isoformat())
            .order("ts", desc=True)
            .limit(limite)
            .execute()
        )

        return {
            "cliente_id": cliente_id,
            "decisions": response.data or [],
            "count": len(response.data or []),
            "period_hours": horas,
        }

    except Exception as e:
        logger.error(f"Erro ao buscar decisões do cliente {cliente_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
