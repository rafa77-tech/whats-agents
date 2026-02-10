"""
Endpoints de configuracao do sistema.

Sprint 32 - E20: Toggle Modo Piloto via Dashboard
Sprint 35: Controle granular de features autonomas
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel

from app.core.config import settings
from app.core.timezone import agora_utc
from app.core.logging import get_logger
from app.services.supabase import supabase

router = APIRouter(prefix="/sistema", tags=["sistema"])
logger = get_logger(__name__)

# Tipos validos de feature
FeatureType = Literal[
    "discovery_automatico",
    "oferta_automatica",
    "reativacao_automatica",
    "feedback_automatico",
]

# Mapeamento feature -> atributo do settings
FEATURE_TO_SETTING = {
    "discovery_automatico": "DISCOVERY_AUTOMATICO_ENABLED",
    "oferta_automatica": "OFERTA_AUTOMATICA_ENABLED",
    "reativacao_automatica": "REATIVACAO_AUTOMATICA_ENABLED",
    "feedback_automatico": "FEEDBACK_AUTOMATICO_ENABLED",
}


class StatusResponse(BaseModel):
    """Resposta com status do sistema."""

    pilot_mode: bool
    autonomous_features: dict[str, bool]
    last_changed_by: str | None = None
    last_changed_at: str | None = None


class PilotModeRequest(BaseModel):
    """Request para alterar modo piloto."""

    pilot_mode: bool
    changed_by: str | None = None


class PilotModeResponse(BaseModel):
    """Resposta da alteracao de modo piloto."""

    success: bool
    pilot_mode: bool
    autonomous_features: dict[str, bool]


class FeatureToggleRequest(BaseModel):
    """Request para alterar feature individual."""

    enabled: bool
    changed_by: str | None = None


class FeatureToggleResponse(BaseModel):
    """Resposta da alteracao de feature."""

    success: bool
    feature: str
    enabled: bool
    pilot_mode: bool
    autonomous_features: dict[str, bool]


@router.get("/status", response_model=StatusResponse)
async def get_sistema_status() -> StatusResponse:
    """
    Retorna status atual do sistema.

    Inclui:
    - pilot_mode: se esta em modo piloto
    - autonomous_features: status de cada feature autonoma
    - last_changed_by: quem alterou por ultimo
    - last_changed_at: quando foi alterado
    """
    # Buscar ultima alteracao do banco
    last_changed_by = None
    last_changed_at = None

    try:
        config_resp = (
            supabase.table("system_config")
            .select("updated_at, updated_by")
            .eq("key", "PILOT_MODE")
            .single()
            .execute()
        )
        if config_resp.data:
            last_changed_by = config_resp.data.get("updated_by")
            last_changed_at = config_resp.data.get("updated_at")
    except Exception:
        # Se tabela nao existe, ignora
        pass

    return StatusResponse(
        pilot_mode=settings.is_pilot_mode,
        autonomous_features=settings.autonomous_features_status,
        last_changed_by=last_changed_by,
        last_changed_at=last_changed_at,
    )


@router.post("/pilot-mode", response_model=PilotModeResponse)
async def set_pilot_mode(request: PilotModeRequest) -> PilotModeResponse:
    """
    Altera modo piloto.

    Quando pilot_mode=True:
    - Desabilita acoes autonomas (Discovery, Oferta, Reativacao, Feedback)
    - Mantem funcionando campanhas manuais e respostas inbound

    Quando pilot_mode=False:
    - Habilita todas as acoes autonomas
    - Julia age proativamente

    A configuracao persiste em system_config e atualiza settings em memoria.
    """
    try:
        # Salvar em tabela de configuracao
        supabase.table("system_config").upsert(
            {
                "key": "PILOT_MODE",
                "value": str(request.pilot_mode).lower(),
                "updated_at": agora_utc().isoformat(),
                "updated_by": request.changed_by,
            },
            on_conflict="key",
        ).execute()

        # Atualizar settings em memoria
        # NOTA: Isso funciona porque Settings nao usa @property para PILOT_MODE
        settings.PILOT_MODE = request.pilot_mode

        action = "ativado" if request.pilot_mode else "desativado"
        logger.info(f"Modo piloto {action} por {request.changed_by}")

        return PilotModeResponse(
            success=True,
            pilot_mode=request.pilot_mode,
            autonomous_features=settings.autonomous_features_status,
        )

    except Exception as e:
        logger.error(f"Erro ao alterar modo piloto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/features/{feature}", response_model=FeatureToggleResponse)
async def set_feature_status(
    request: FeatureToggleRequest,
    feature: FeatureType = Path(..., description="Nome da feature autonoma"),
) -> FeatureToggleResponse:
    """
    Altera status de uma feature autonoma individual.

    Sprint 35: Controle granular de features autonomas.

    IMPORTANTE: Se PILOT_MODE=True, a feature nao sera executada mesmo se habilitada.
    O PILOT_MODE funciona como master switch.

    Features disponiveis:
    - discovery_automatico: Conhecer medicos nao-enriquecidos
    - oferta_automatica: Ofertar vagas com furo de escala
    - reativacao_automatica: Retomar contato com inativos
    - feedback_automatico: Pedir feedback pos-plantao

    Args:
        feature: Nome da feature (path parameter)
        request: enabled (bool) e changed_by (str opcional)

    Returns:
        Status atualizado com todas as features
    """
    if feature not in FEATURE_TO_SETTING:
        raise HTTPException(
            status_code=400,
            detail=f"Feature invalida: {feature}. Validas: {list(FEATURE_TO_SETTING.keys())}",
        )

    setting_name = FEATURE_TO_SETTING[feature]

    try:
        # Salvar em tabela de configuracao
        config_key = setting_name  # Ex: DISCOVERY_AUTOMATICO_ENABLED
        supabase.table("system_config").upsert(
            {
                "key": config_key,
                "value": str(request.enabled).lower(),
                "updated_at": agora_utc().isoformat(),
                "updated_by": request.changed_by,
            },
            on_conflict="key",
        ).execute()

        # Atualizar settings em memoria
        setattr(settings, setting_name, request.enabled)

        action = "habilitada" if request.enabled else "desabilitada"
        logger.info(f"Feature {feature} {action} por {request.changed_by}")

        return FeatureToggleResponse(
            success=True,
            feature=feature,
            enabled=request.enabled,
            pilot_mode=settings.is_pilot_mode,
            autonomous_features=settings.autonomous_features_status,
        )

    except Exception as e:
        logger.error(f"Erro ao alterar feature {feature}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
