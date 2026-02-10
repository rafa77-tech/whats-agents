"""
Router de Guardrails - Sprint 43.

Expõe funcionalidades de controle operacional:
- Feature flags
- Desbloqueio de chips/clientes
- Reset de circuit breakers
- Modo emergência
- Audit trail
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.services.sistema_guardrails import (
    FeatureFlag,
    obter_feature_flag,
    definir_feature_flag,
    listar_feature_flags,
    desbloquear_chip,
    desbloquear_cliente,
    resetar_circuit_breaker_global,
    ativar_modo_emergencia,
    desativar_modo_emergencia,
    buscar_audit_trail,
)
from app.services.circuit_breaker import (
    circuit_evolution,
    circuit_claude,
    circuit_supabase,
)

router = APIRouter(prefix="/guardrails", tags=["guardrails"])
logger = get_logger(__name__)


# ============================================================
# Schemas
# ============================================================


class FeatureFlagResponse(BaseModel):
    """Resposta com valor de uma feature flag."""

    flag: str
    enabled: bool


class FeatureFlagListResponse(BaseModel):
    """Lista de todas as feature flags."""

    flags: dict[str, bool]
    total: int


class FeatureFlagUpdateRequest(BaseModel):
    """Request para atualizar feature flag."""

    enabled: bool
    motivo: str = Field(..., min_length=3, description="Motivo da alteração")
    usuario: str = Field(default="dashboard", description="Usuário que alterou")


class FeatureFlagUpdateResponse(BaseModel):
    """Resposta após atualizar feature flag."""

    success: bool
    flag: str
    enabled: bool
    motivo: str


class DesbloqueioRequest(BaseModel):
    """Request para desbloquear entidade."""

    motivo: str = Field(..., min_length=3, description="Motivo do desbloqueio")
    usuario: str = Field(default="dashboard", description="Usuário que desbloqueou")


class DesbloqueioResponse(BaseModel):
    """Resposta de desbloqueio."""

    success: bool
    entidade: str
    entidade_id: str
    motivo: str


class CircuitBreakerStatus(BaseModel):
    """Status de um circuit breaker."""

    name: str
    state: str
    failures: int
    threshold: int
    last_failure: Optional[str] = None


class CircuitBreakerListResponse(BaseModel):
    """Lista de circuit breakers."""

    circuits: list[CircuitBreakerStatus]


class CircuitResetRequest(BaseModel):
    """Request para resetar circuit breaker."""

    motivo: str = Field(..., min_length=3, description="Motivo do reset")
    usuario: str = Field(default="dashboard", description="Usuário que resetou")


class CircuitResetResponse(BaseModel):
    """Resposta de reset de circuit."""

    success: bool
    circuit: str
    motivo: str


class EmergenciaRequest(BaseModel):
    """Request para modo emergência."""

    motivo: str = Field(..., min_length=3, description="Motivo da emergência")
    usuario: str = Field(default="dashboard", description="Usuário que acionou")


class EmergenciaResponse(BaseModel):
    """Resposta do modo emergência."""

    success: bool
    ativo: bool
    motivo: str


class EmergenciaStatusResponse(BaseModel):
    """Status do modo emergência."""

    ativo: bool
    flags_envio: dict[str, bool]


class AuditTrailEntry(BaseModel):
    """Entrada do audit trail."""

    id: str
    acao: str
    entidade: str
    entidade_id: Optional[str] = None
    detalhes: dict
    usuario: str
    created_at: str


class AuditTrailResponse(BaseModel):
    """Resposta do audit trail."""

    entries: list[AuditTrailEntry]
    total: int


# ============================================================
# Feature Flags
# ============================================================


@router.get("/flags", response_model=FeatureFlagListResponse)
async def listar_flags() -> FeatureFlagListResponse:
    """
    Lista todas as feature flags e seus estados.

    Returns:
        Dict com todas as flags e seus valores (True/False)
    """
    flags = await listar_feature_flags()
    return FeatureFlagListResponse(
        flags=flags,
        total=len(flags),
    )


@router.get("/flags/{flag_name}", response_model=FeatureFlagResponse)
async def obter_flag(
    flag_name: str = Path(..., description="Nome da feature flag"),
) -> FeatureFlagResponse:
    """
    Obtém o valor de uma feature flag específica.

    Args:
        flag_name: Nome da flag (ex: envio_prospeccao)

    Returns:
        Flag e seu valor atual
    """
    try:
        flag = FeatureFlag(flag_name)
    except ValueError:
        valid_flags = [f.value for f in FeatureFlag]
        raise HTTPException(
            status_code=400,
            detail=f"Flag inválida: {flag_name}. Válidas: {valid_flags}",
        )

    enabled = await obter_feature_flag(flag)
    return FeatureFlagResponse(flag=flag_name, enabled=enabled)


@router.post("/flags/{flag_name}", response_model=FeatureFlagUpdateResponse)
async def atualizar_flag(
    request: FeatureFlagUpdateRequest,
    flag_name: str = Path(..., description="Nome da feature flag"),
) -> FeatureFlagUpdateResponse:
    """
    Atualiza o valor de uma feature flag.

    Requer motivo obrigatório para audit trail.

    Args:
        flag_name: Nome da flag
        request: enabled, motivo, usuario

    Returns:
        Confirmação da alteração
    """
    try:
        flag = FeatureFlag(flag_name)
    except ValueError:
        valid_flags = [f.value for f in FeatureFlag]
        raise HTTPException(
            status_code=400,
            detail=f"Flag inválida: {flag_name}. Válidas: {valid_flags}",
        )

    success = await definir_feature_flag(
        flag=flag,
        habilitada=request.enabled,
        motivo=request.motivo,
        usuario=request.usuario,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Erro ao atualizar flag")

    action = "habilitada" if request.enabled else "desabilitada"
    logger.info(f"[guardrails] Flag {flag_name} {action} por {request.usuario}")

    return FeatureFlagUpdateResponse(
        success=True,
        flag=flag_name,
        enabled=request.enabled,
        motivo=request.motivo,
    )


# ============================================================
# Desbloqueio
# ============================================================


@router.post("/desbloquear/chip/{chip_id}", response_model=DesbloqueioResponse)
async def desbloquear_chip_endpoint(
    request: DesbloqueioRequest,
    chip_id: str = Path(..., description="ID do chip"),
) -> DesbloqueioResponse:
    """
    Desbloqueia um chip manualmente.

    Reseta circuit breaker, cooldown e contadores de erro.

    Args:
        chip_id: ID do chip
        request: motivo, usuario

    Returns:
        Confirmação do desbloqueio
    """
    success = await desbloquear_chip(
        chip_id=chip_id,
        motivo=request.motivo,
        usuario=request.usuario,
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Chip não encontrado ou erro ao desbloquear: {chip_id}",
        )

    logger.info(f"[guardrails] Chip {chip_id} desbloqueado por {request.usuario}")

    return DesbloqueioResponse(
        success=True,
        entidade="chip",
        entidade_id=chip_id,
        motivo=request.motivo,
    )


@router.post("/desbloquear/cliente/{cliente_id}", response_model=DesbloqueioResponse)
async def desbloquear_cliente_endpoint(
    request: DesbloqueioRequest,
    cliente_id: str = Path(..., description="ID do cliente"),
) -> DesbloqueioResponse:
    """
    Desbloqueia um cliente manualmente.

    Reseta rate limit, flags de bloqueio e contadores de erro.

    Args:
        cliente_id: ID do cliente
        request: motivo, usuario

    Returns:
        Confirmação do desbloqueio
    """
    success = await desbloquear_cliente(
        cliente_id=cliente_id,
        motivo=request.motivo,
        usuario=request.usuario,
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Cliente não encontrado ou erro ao desbloquear: {cliente_id}",
        )

    logger.info(f"[guardrails] Cliente {cliente_id} desbloqueado por {request.usuario}")

    return DesbloqueioResponse(
        success=True,
        entidade="cliente",
        entidade_id=cliente_id,
        motivo=request.motivo,
    )


# ============================================================
# Circuit Breakers
# ============================================================


@router.get("/circuits", response_model=CircuitBreakerListResponse)
async def listar_circuits() -> CircuitBreakerListResponse:
    """
    Lista todos os circuit breakers e seus estados.

    Returns:
        Lista de circuits com estado, falhas e threshold
    """
    circuits = [
        ("evolution", circuit_evolution),
        ("claude", circuit_claude),
        ("supabase", circuit_supabase),
    ]

    result = []
    for name, circuit in circuits:
        status = circuit.status()
        result.append(
            CircuitBreakerStatus(
                name=name,
                state=status.get("state", "unknown"),
                failures=status.get("failures", 0),
                threshold=status.get("threshold", 5),
                last_failure=status.get("last_failure"),
            )
        )

    return CircuitBreakerListResponse(circuits=result)


@router.post("/circuits/{circuit_name}/reset", response_model=CircuitResetResponse)
async def resetar_circuit(
    request: CircuitResetRequest,
    circuit_name: str = Path(..., description="Nome do circuit breaker"),
) -> CircuitResetResponse:
    """
    Reseta um circuit breaker manualmente.

    Zera contadores e muda estado para CLOSED.

    Args:
        circuit_name: Nome do circuit (evolution, claude, supabase)
        request: motivo, usuario

    Returns:
        Confirmação do reset
    """
    valid_circuits = ["evolution", "claude", "supabase"]
    if circuit_name not in valid_circuits:
        raise HTTPException(
            status_code=400,
            detail=f"Circuit inválido: {circuit_name}. Válidos: {valid_circuits}",
        )

    success = await resetar_circuit_breaker_global(
        circuit_name=circuit_name,
        motivo=request.motivo,
        usuario=request.usuario,
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao resetar circuit breaker: {circuit_name}",
        )

    logger.info(f"[guardrails] Circuit {circuit_name} resetado por {request.usuario}")

    return CircuitResetResponse(
        success=True,
        circuit=circuit_name,
        motivo=request.motivo,
    )


# ============================================================
# Modo Emergência
# ============================================================


@router.get("/emergencia/status", response_model=EmergenciaStatusResponse)
async def status_emergencia() -> EmergenciaStatusResponse:
    """
    Verifica status do modo emergência.

    O modo emergência está ativo quando flags de envio estão desabilitadas.

    Returns:
        Status atual e flags de envio
    """
    flags_envio = {
        "envio_prospeccao": await obter_feature_flag(FeatureFlag.ENVIO_PROSPECCAO),
        "envio_followup": await obter_feature_flag(FeatureFlag.ENVIO_FOLLOWUP),
        "envio_resposta": await obter_feature_flag(FeatureFlag.ENVIO_RESPOSTA),
        "envio_campanha": await obter_feature_flag(FeatureFlag.ENVIO_CAMPANHA),
    }

    # Emergência ativa se qualquer flag de envio estiver desabilitada
    ativo = not all(flags_envio.values())

    return EmergenciaStatusResponse(ativo=ativo, flags_envio=flags_envio)


@router.post("/emergencia/ativar", response_model=EmergenciaResponse)
async def ativar_emergencia(request: EmergenciaRequest) -> EmergenciaResponse:
    """
    Ativa modo de emergência.

    Desabilita todas as flags de envio de mensagens.

    Args:
        request: motivo, usuario

    Returns:
        Confirmação da ativação
    """
    success = await ativar_modo_emergencia(
        motivo=request.motivo,
        usuario=request.usuario,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Erro ao ativar modo emergência")

    logger.critical(f"[guardrails] EMERGÊNCIA ATIVADA por {request.usuario}: {request.motivo}")

    return EmergenciaResponse(
        success=True,
        ativo=True,
        motivo=request.motivo,
    )


@router.post("/emergencia/desativar", response_model=EmergenciaResponse)
async def desativar_emergencia(request: EmergenciaRequest) -> EmergenciaResponse:
    """
    Desativa modo de emergência.

    Reabilita todas as flags de envio de mensagens.

    Args:
        request: motivo, usuario

    Returns:
        Confirmação da desativação
    """
    success = await desativar_modo_emergencia(
        motivo=request.motivo,
        usuario=request.usuario,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Erro ao desativar modo emergência")

    logger.info(f"[guardrails] Emergência DESATIVADA por {request.usuario}: {request.motivo}")

    return EmergenciaResponse(
        success=True,
        ativo=False,
        motivo=request.motivo,
    )


# ============================================================
# Audit Trail
# ============================================================


@router.get("/audit", response_model=AuditTrailResponse)
async def buscar_audit(
    acao: Optional[str] = Query(None, description="Filtrar por tipo de ação"),
    entidade: Optional[str] = Query(None, description="Filtrar por tipo de entidade"),
    entidade_id: Optional[str] = Query(None, description="Filtrar por ID da entidade"),
    usuario: Optional[str] = Query(None, description="Filtrar por usuário"),
    horas: int = Query(24, ge=1, le=168, description="Período em horas (max 7 dias)"),
    limite: int = Query(100, ge=1, le=500, description="Máximo de registros"),
) -> AuditTrailResponse:
    """
    Busca registros no audit trail.

    Filtros disponíveis:
    - acao: Tipo de ação (feature_flag_change, chip_desbloqueado, etc)
    - entidade: Tipo de entidade (chip, cliente, circuit_breaker, etc)
    - entidade_id: ID específico
    - usuario: Quem executou
    - horas: Período (default 24h, max 168h/7dias)
    - limite: Máximo de registros (default 100, max 500)

    Returns:
        Lista de registros de auditoria
    """
    entries = await buscar_audit_trail(
        acao=acao,
        entidade=entidade,
        entidade_id=entidade_id,
        usuario=usuario,
        horas=horas,
        limite=limite,
    )

    result = [
        AuditTrailEntry(
            id=entry.get("id", ""),
            acao=entry.get("acao", ""),
            entidade=entry.get("entidade", ""),
            entidade_id=entry.get("entidade_id"),
            detalhes=entry.get("detalhes", {}),
            usuario=entry.get("usuario", ""),
            created_at=entry.get("created_at", ""),
        )
        for entry in entries
    ]

    return AuditTrailResponse(entries=result, total=len(result))
