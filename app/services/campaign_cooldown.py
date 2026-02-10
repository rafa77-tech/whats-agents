"""
Servico de cooldown entre campanhas.

Sprint 23 E05 - Evita que medico receba campanhas diferentes em janela curta.

Regras:
- R5a: Nao enviar 2 campanhas diferentes em 3 dias
- R5b: Se respondeu, suspender campanhas por 7 dias
- R5c: Reply e atendimento NUNCA sao bloqueados
- R5d: Bypass via Slack permitido (com log)

IMPORTANTE: Este modulo so afeta method=CAMPAIGN.
Reply e followup NAO passam por estas regras.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from dataclasses import dataclass

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# Configuracoes de cooldown (podem ser movidas para feature_flags)
CAMPAIGN_COOLDOWN_DAYS = 3  # Entre campanhas diferentes
RESPONSE_COOLDOWN_DAYS = 7  # Apos medico responder


@dataclass
class CooldownResult:
    """Resultado da verificacao de cooldown."""

    is_blocked: bool
    reason: Optional[str] = None
    details: Optional[dict] = None


@dataclass
class LastCampaignInfo:
    """Info da ultima campanha enviada."""

    campaign_id: int
    campaign_type: str
    sent_at: datetime


async def registrar_envio_campanha(
    cliente_id: str,
    campaign_id: int,
    campaign_type: str,
) -> bool:
    """
    Registra envio de campanha no historico.

    Chamado quando outbound com outcome=SENT e campaign_id != null.

    Args:
        cliente_id: ID do cliente
        campaign_id: ID da campanha
        campaign_type: Tipo da campanha

    Returns:
        True se registrou com sucesso
    """
    try:
        supabase.table("campaign_contact_history").upsert(
            {
                "cliente_id": cliente_id,
                "campaign_id": campaign_id,
                "campaign_type": campaign_type,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="cliente_id,campaign_id",
        ).execute()

        logger.debug(
            f"Envio de campanha registrado: cliente={cliente_id[:8]}, "
            f"campanha={campaign_id}, tipo={campaign_type}"
        )
        return True

    except Exception as e:
        logger.error(f"Erro ao registrar envio de campanha: {e}")
        return False


async def buscar_ultima_campanha_enviada(
    cliente_id: str,
) -> Optional[LastCampaignInfo]:
    """
    Busca a ultima campanha enviada para um cliente.

    Args:
        cliente_id: ID do cliente

    Returns:
        LastCampaignInfo ou None se nunca recebeu campanha
    """
    response = (
        supabase.table("campaign_contact_history")
        .select("campaign_id, campaign_type, sent_at")
        .eq("cliente_id", cliente_id)
        .order("sent_at", desc=True)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    row = response.data[0]
    return LastCampaignInfo(
        campaign_id=row["campaign_id"],
        campaign_type=row["campaign_type"],
        sent_at=datetime.fromisoformat(row["sent_at"].replace("Z", "+00:00")),
    )


async def medico_respondeu_recentemente(
    cliente_id: str,
    dias: int = RESPONSE_COOLDOWN_DAYS,
) -> bool:
    """
    Verifica se medico respondeu nos ultimos X dias.

    Args:
        cliente_id: ID do cliente
        dias: Janela de tempo em dias

    Returns:
        True se respondeu recentemente
    """
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()

    response = (
        supabase.table("interacoes")
        .select("id", count="exact")
        .eq("cliente_id", cliente_id)
        .eq("origem", "medico")  # Inbound do medico
        .gte("created_at", desde)
        .limit(1)
        .execute()
    )

    return (response.count or 0) > 0


async def tem_conversa_ativa_com_oferta(
    cliente_id: str,
) -> bool:
    """
    Verifica se cliente tem conversa ativa com oferta em andamento.

    Uma conversa ativa e aquela onde:
    - status != 'fechada'
    - Houve interacao nos ultimos 7 dias

    Returns:
        True se tem conversa ativa
    """
    desde = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    response = (
        supabase.table("conversations")
        .select("id", count="exact")
        .eq("cliente_id", cliente_id)
        .neq("status", "fechada")
        .gte("updated_at", desde)
        .limit(1)
        .execute()
    )

    return (response.count or 0) > 0


async def check_campaign_cooldown(
    cliente_id: str,
    campaign_id: int,
) -> CooldownResult:
    """
    Verifica se cliente esta em cooldown para campanhas.

    Regras verificadas:
    - R5a: Ultima campanha diferente foi ha menos de 3 dias?
    - R5b: Medico respondeu nos ultimos 7 dias?

    Args:
        cliente_id: ID do cliente
        campaign_id: ID da campanha atual

    Returns:
        CooldownResult indicando se esta bloqueado
    """
    now = datetime.now(timezone.utc)

    # R5a: Verificar campanhas diferentes em janela curta
    ultima = await buscar_ultima_campanha_enviada(cliente_id)

    if ultima and ultima.campaign_id != campaign_id:
        dias_desde = (now - ultima.sent_at).days

        if dias_desde < CAMPAIGN_COOLDOWN_DAYS:
            logger.info(
                f"Cooldown R5a: cliente={cliente_id[:8]} recebeu campanha "
                f"{ultima.campaign_id} ha {dias_desde} dias"
            )
            return CooldownResult(
                is_blocked=True,
                reason="different_campaign_recent",
                details={
                    "last_campaign_id": ultima.campaign_id,
                    "last_campaign_type": ultima.campaign_type,
                    "days_since": dias_desde,
                    "cooldown_days": CAMPAIGN_COOLDOWN_DAYS,
                },
            )

    # R5b: Verificar se respondeu recentemente
    if await medico_respondeu_recentemente(cliente_id, RESPONSE_COOLDOWN_DAYS):
        # Exceto se tem conversa ativa (pode estar negociando)
        if not await tem_conversa_ativa_com_oferta(cliente_id):
            logger.info(
                f"Cooldown R5b: cliente={cliente_id[:8]} respondeu nos ultimos "
                f"{RESPONSE_COOLDOWN_DAYS} dias"
            )
            return CooldownResult(
                is_blocked=True,
                reason="responded_recently",
                details={
                    "cooldown_days": RESPONSE_COOLDOWN_DAYS,
                },
            )

    return CooldownResult(is_blocked=False)


async def get_cooldown_config() -> dict:
    """
    Retorna configuracao atual de cooldown.

    Pode ser extendido para ler de feature_flags.
    """
    return {
        "campaign_cooldown_days": CAMPAIGN_COOLDOWN_DAYS,
        "response_cooldown_days": RESPONSE_COOLDOWN_DAYS,
    }
