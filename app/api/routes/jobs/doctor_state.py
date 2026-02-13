"""
Jobs de manutencao do doctor_state (Sprint 15).

Sprint 58 - Epic 1: Decomposicao de jobs.py
"""

from fastapi import APIRouter

from ._helpers import job_endpoint

router = APIRouter()


@router.post("/doctor-state-manutencao-diaria")
@job_endpoint("doctor-state-manutencao-diaria")
async def job_doctor_state_manutencao_diaria():
    """
    Job diario de manutencao do doctor_state.

    Executa:
    - Decay de temperatura por inatividade
    - Expiracao de cooling_off vencidos
    - Atualizacao de lifecycle stages
    """
    from app.workers.temperature_decay import run_daily_maintenance

    result = await run_daily_maintenance()
    return {"status": "ok", "message": "Manutenção diária concluída", "result": result}


@router.post("/doctor-state-manutencao-semanal")
@job_endpoint("doctor-state-manutencao-semanal")
async def job_doctor_state_manutencao_semanal():
    """
    Job semanal de manutencao do doctor_state.

    Executa tudo do diario + reset de contadores semanais.
    """
    from app.workers.temperature_decay import run_weekly_maintenance

    result = await run_weekly_maintenance()
    return {"status": "ok", "message": "Manutenção semanal concluída", "result": result}


@router.post("/doctor-state-decay")
@job_endpoint("doctor-state-decay")
async def job_doctor_state_decay(batch_size: int = 100):
    """
    Job especifico de decay de temperatura.

    Decai temperatura de medicos inativos.
    Idempotente: usa last_decay_at para evitar decay duplo.
    """
    from app.workers.temperature_decay import decay_all_temperatures

    decayed = await decay_all_temperatures(batch_size)
    return {
        "status": "ok",
        "message": f"Decay aplicado em {decayed} médicos",
        "decayed": decayed,
    }


@router.post("/doctor-state-expire-cooling")
@job_endpoint("doctor-state-expire-cooling")
async def job_doctor_state_expire_cooling():
    """
    Job especifico para expirar cooling_off vencidos.

    Medicos com cooling_off expirado voltam para 'active'.
    """
    from app.workers.temperature_decay import expire_cooling_off

    expired = await expire_cooling_off()
    return {
        "status": "ok",
        "message": f"{expired} cooling_off expirado(s)",
        "expired": expired,
    }
