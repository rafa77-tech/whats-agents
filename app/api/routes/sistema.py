"""
Endpoints de configuracao do sistema.

Sprint 32 - E20: Toggle Modo Piloto via Dashboard
"""
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger
from app.services.supabase import supabase

router = APIRouter(prefix="/sistema", tags=["sistema"])
logger = get_logger(__name__)


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
                "updated_at": datetime.utcnow().isoformat(),
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
