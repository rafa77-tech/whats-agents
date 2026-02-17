"""
Job de decaimento de temperatura.

Executa periodicamente para:
- Decair temperatura de médicos inativos
- Expirar cooling_off vencidos
- Resetar contact_count_7d semanal

Sprint 15 - Policy Engine
"""

import logging
from datetime import timedelta

from app.core.timezone import agora_utc
from app.services.supabase import supabase
from app.services.policy.state_update import StateUpdate
from app.services.policy.repository import (
    save_doctor_state_updates,
    buscar_states_para_decay,
    _row_to_state,
)

logger = logging.getLogger(__name__)


async def decay_all_temperatures(batch_size: int = 100) -> int:
    """
    Job principal: decai temperatura de médicos inativos.

    Usa last_decay_at para ser IDEMPOTENTE.
    Pode rodar múltiplas vezes sem efeito cumulativo errado.

    Args:
        batch_size: Número máximo de registros por batch

    Returns:
        Quantidade de médicos com decay aplicado
    """
    logger.info("Iniciando job de decay de temperatura...")

    now = agora_utc()

    try:
        # Buscar estados que precisam de decay
        states_to_decay = await buscar_states_para_decay(dias_minimo=1)
        logger.info(f"Encontrados {len(states_to_decay)} médicos para avaliar decay")

        state_updater = StateUpdate()
        decayed = 0

        for row in states_to_decay[:batch_size]:  # Limitar batch
            try:
                # Sprint 59 Epic 4.2: Converter row direto ao invés de load_doctor_state
                state = _row_to_state(row)
                updates = state_updater.decay_temperature(state, now)

                if updates:
                    await save_doctor_state_updates(row["cliente_id"], updates)
                    decayed += 1
                    logger.debug(
                        f"Decay aplicado: {row['cliente_id'][:8]}... "
                        f"temp={state.temperature} -> {updates.get('temperature')}"
                    )
            except Exception as e:
                logger.error(f"Erro ao decair {row['cliente_id']}: {e}")
                continue

        logger.info(f"Decay aplicado em {decayed} médicos")
        return decayed

    except Exception as e:
        logger.error(f"Erro no job de decay: {e}")
        raise


async def expire_cooling_off() -> int:
    """
    Expira cooling_off que passou do prazo.

    Médicos em cooling_off com prazo expirado voltam para 'active'.

    Returns:
        Quantidade de cooling_off expirados
    """
    logger.info("Verificando cooling_off expirados...")

    now = agora_utc().isoformat()

    try:
        response = (
            supabase.table("doctor_state")
            .update(
                {
                    "permission_state": "active",
                    "cooling_off_until": None,
                }
            )
            .eq("permission_state", "cooling_off")
            .lt("cooling_off_until", now)
            .execute()
        )

        expired = len(response.data or [])
        if expired:
            logger.info(f"Expirados {expired} cooling_off")
        else:
            logger.debug("Nenhum cooling_off expirado")

        return expired

    except Exception as e:
        logger.error(f"Erro ao expirar cooling_off: {e}")
        raise


async def reset_weekly_contact_count() -> int:
    """
    Reseta contact_count_7d semanalmente.

    Executar toda segunda-feira às 00:00.

    Returns:
        Quantidade de contadores resetados
    """
    logger.info("Resetando contact_count_7d...")

    try:
        response = (
            supabase.table("doctor_state")
            .update({"contact_count_7d": 0})
            .gt("contact_count_7d", 0)
            .execute()
        )

        reset = len(response.data or [])
        if reset:
            logger.info(f"Resetados {reset} contadores semanais")
        else:
            logger.debug("Nenhum contador para resetar")

        return reset

    except Exception as e:
        logger.error(f"Erro ao resetar contadores: {e}")
        raise


async def update_lifecycle_stages() -> int:
    """
    Atualiza lifecycle_stage baseado em inatividade.

    Médicos inativos por muito tempo podem virar 'churned'.

    Returns:
        Quantidade de stages atualizados
    """
    logger.info("Verificando lifecycle stages...")

    now = agora_utc()
    churned_cutoff = (now - timedelta(days=90)).isoformat()  # 90 dias sem atividade

    try:
        # Marcar como churned se:
        # - última mensagem recebida foi há mais de 90 dias
        # - não está em opted_out (já é terminal)
        # - não está em 'churned' já
        response = (
            supabase.table("doctor_state")
            .update({"lifecycle_stage": "churned"})
            .neq("permission_state", "opted_out")
            .neq("lifecycle_stage", "churned")
            .lt("last_inbound_at", churned_cutoff)
            .execute()
        )

        churned = len(response.data or [])
        if churned:
            logger.info(f"Marcados {churned} médicos como churned")

        return churned

    except Exception as e:
        logger.error(f"Erro ao atualizar lifecycle: {e}")
        raise


async def run_daily_maintenance() -> dict:
    """
    Job diário completo de manutenção do doctor_state.

    Executa:
    1. Decay de temperatura
    2. Expiração de cooling_off
    3. Atualização de lifecycle

    Returns:
        Dict com contagem de cada operação
    """
    logger.info("=== Iniciando manutenção diária de doctor_state ===")

    try:
        decayed = await decay_all_temperatures()
        expired = await expire_cooling_off()
        churned = await update_lifecycle_stages()

        result = {
            "decayed": decayed,
            "expired_cooling_off": expired,
            "churned": churned,
            "timestamp": agora_utc().isoformat(),
        }

        logger.info(
            f"=== Manutenção concluída: "
            f"{decayed} decay, {expired} cooling_off, {churned} churned ==="
        )

        return result

    except Exception as e:
        logger.error(f"Erro na manutenção diária: {e}")
        raise


async def run_weekly_maintenance() -> dict:
    """
    Job semanal completo.

    Executa:
    1. Tudo do daily
    2. Reset de contadores semanais

    Returns:
        Dict com contagem de cada operação
    """
    logger.info("=== Iniciando manutenção semanal de doctor_state ===")

    try:
        daily_result = await run_daily_maintenance()
        reset = await reset_weekly_contact_count()

        result = {
            **daily_result,
            "reset_contact_count": reset,
        }

        logger.info(f"=== Manutenção semanal concluída: {result} ===")

        return result

    except Exception as e:
        logger.error(f"Erro na manutenção semanal: {e}")
        raise
