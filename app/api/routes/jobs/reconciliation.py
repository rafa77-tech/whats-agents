"""
Jobs de reconciliacao de touches e handoffs (Sprints 20, 22, 24).

Sprint 58 - Epic 1: Decomposicao de jobs.py
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ._helpers import job_endpoint

router = APIRouter()


@router.post("/processar-handoffs")
@job_endpoint("processar-handoffs")
async def job_processar_handoffs():
    """
    Job para processar handoffs pendentes (follow-up e expiracao).

    Executa a cada 10 minutos:
    - Envia follow-ups (2h, 24h, 36h)
    - Expira handoffs vencidos (48h)
    - Libera vagas expiradas
    - Notifica medicos

    Sprint 20 - E07.
    """
    from app.workers.handoff_processor import processar_handoffs_pendentes

    stats = await processar_handoffs_pendentes()

    return {
        "status": "ok",
        "message": f"Processados {stats['total_processados']} handoffs",
        **stats,
    }


@router.post("/processar-retomadas")
@job_endpoint("processar-retomadas")
async def job_processar_retomadas():
    """
    Job para processar mensagens fora do horario pendentes.

    Executa as 08:00 de dias uteis.
    Retoma conversas com contexto preservado.

    Sprint 22 - Responsividade Inteligente.
    """
    from app.workers.retomada_fora_horario import processar_retomadas

    stats = await processar_retomadas()

    return {
        "status": "ok",
        "message": f"Processadas {stats.get('processadas', 0)} retomadas",
        **stats,
    }


@router.post("/reconcile-touches")
@job_endpoint("reconcile-touches")
async def job_reconcile_touches(horas: int = 72, limite: int = 1000):
    """
    Job de reconciliacao de doctor_state.last_touch_*.

    Sprint 24 P1: Repair loop para consistencia.

    Corrige inconsistencias causadas por falhas no _finalizar_envio(),
    garantindo que last_touch_* reflita o estado real dos envios.

    Caracteristicas:
    - 100% deterministico (usa provider_message_id como chave)
    - Idempotente (log com PK em provider_message_id)
    - Monotonico (so avanca, nunca retrocede)
    - Usa enviada_em como touch_at real (nao created_at)

    Args:
        horas: Janela de busca em horas (default 72h)
        limite: Maximo de registros por execucao (default 1000)

    Executar:
    - A cada 10-15 minutos (frequencia recomendada)
    - Manualmente via Slack quando necessario
    """
    from app.services.touch_reconciliation import executar_reconciliacao

    result = await executar_reconciliacao(horas=horas, limite=limite)

    return {
        "status": "ok",
        "message": result.summary,
        "stats": {
            "total_candidates": result.total_candidates,
            "reconciled": result.reconciled,
            "skipped_already_processed": result.skipped_already_processed,
            "skipped_already_newer": result.skipped_already_newer,
            "skipped_no_change": result.skipped_no_change,
            "failed": result.failed,
        },
        "errors": result.errors[:10] if result.errors else [],
    }


@router.post("/limpar-logs-reconciliacao")
@job_endpoint("limpar-logs-reconciliacao")
async def job_limpar_logs_reconciliacao(dias: int = 30):
    """
    Job para limpar logs antigos de reconciliacao.

    Mantem logs dos ultimos N dias para auditoria.

    Args:
        dias: Manter logs dos ultimos X dias (default 30)
    """
    from app.services.touch_reconciliation import limpar_logs_antigos

    removidos = await limpar_logs_antigos(dias=dias)

    return {
        "status": "ok",
        "message": f"{removidos} log(s) removido(s)",
        "removidos": removidos,
    }


@router.post("/reclamar-processing-travado")
@job_endpoint("reclamar-processing-travado")
async def job_reclamar_processing_travado(minutos_timeout: int = 15):
    """
    P1.2: Reclama entries travadas em status='processing'.

    Se um worker crashar entre claim e atualizacao final,
    a entry fica em 'processing' eternamente. Este job
    marca essas entries como 'abandoned'.

    Args:
        minutos_timeout: Minutos apos os quais 'processing' e considerado travado (default 15)
    """
    from app.services.touch_reconciliation import reclamar_processing_travado

    result = await reclamar_processing_travado(minutos_timeout=minutos_timeout)

    return {
        "status": "ok",
        "message": f"found={result.found}, reclaimed={result.reclaimed}",
        "stats": {
            "found": result.found,
            "reclaimed": result.reclaimed,
        },
        "errors": result.errors[:10] if result.errors else [],
    }


@router.get("/reconciliacao-status")
@job_endpoint("reconciliacao-status")
async def job_reconciliacao_status(minutos_timeout: int = 15):
    """
    Retorna status de saude do job de reconciliacao.

    Util para monitoramento/alertas.

    Returns:
        - processing_stuck: Entries travadas em 'processing'
    """
    from app.services.touch_reconciliation import contar_processing_stuck

    stuck_count = await contar_processing_stuck(minutos_timeout=minutos_timeout)

    status = "healthy" if stuck_count == 0 else "warning" if stuck_count < 10 else "critical"

    return JSONResponse(
        {
            "status": status,
            "processing_stuck": stuck_count,
            "timeout_minutes": minutos_timeout,
        }
    )
