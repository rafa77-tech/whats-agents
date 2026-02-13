"""
Gatilhos autonomos e validacao de telefones.

Sprint 58 - Epic 1: Decomposicao de jobs.py
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.timezone import agora_brasilia

from ._helpers import job_endpoint

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# Validacao de Telefones (Sprint 32 E04)
# =============================================================================


@router.post("/validar-telefones")
@job_endpoint("validar-telefones")
async def job_validar_telefones(limite: int = 50):
    """
    Job para validar telefones via checkNumberStatus.

    Valida numeros pendentes usando Evolution API para verificar
    se o WhatsApp existe no numero antes de tentar contato.

    Sprint 32 E04 - Validacao previa evita desperdicio de mensagens.

    Args:
        limite: Maximo de telefones a processar por execucao (default: 50)

    Schedule:
        A cada 5 minutos, das 8h as 20h (*/5 8-19 * * *)
    """
    # Verificar horario comercial (horario de Brasilia)
    hora_atual = agora_brasilia().hour
    if hora_atual < 8 or hora_atual >= 20:
        return JSONResponse(
            {
                "status": "skipped",
                "reason": "fora_horario",
                "message": "Validação só ocorre das 8h às 20h",
            }
        )

    from app.services.validacao_telefone import processar_lote_validacao

    stats = await processar_lote_validacao(limit=limite)

    return {
        "status": "ok",
        "processados": stats["processados"],
        "validados": stats["validados"],
        "invalidos": stats["invalidos"],
        "erros": stats["erros"],
        "skips": stats["skips"],
    }


@router.post("/resetar-telefones-travados")
@job_endpoint("resetar-telefones-travados")
async def job_resetar_telefones_travados(horas: int = 1):
    """
    Reseta telefones travados em status 'validando'.

    Util quando o processo e interrompido e deixa registros
    em estado intermediario.

    Args:
        horas: Considerar travado se em 'validando' ha mais de X horas
    """
    from app.services.validacao_telefone import resetar_telefones_travados

    resetados = await resetar_telefones_travados(horas=horas)

    return {
        "status": "ok",
        "message": f"{resetados} telefone(s) resetado(s)",
        "resetados": resetados,
    }


# =============================================================================
# Gatilhos Automaticos Julia (Sprint 32 E05-E07)
# =============================================================================


@router.post("/executar-gatilhos-autonomos")
@job_endpoint("executar-gatilhos-autonomos")
async def job_executar_gatilhos_autonomos():
    """
    Job para executar todos os gatilhos automaticos da Julia.

    Gatilhos incluidos:
    - Discovery: Medicos nao-enriquecidos
    - Oferta: Vagas urgentes (< 20 dias)
    - Reativacao: Medicos inativos (> 60 dias)
    - Feedback: Plantoes realizados recentemente

    IMPORTANTE: So executa se PILOT_MODE=False.

    Sprint 32 E05 - Gatilhos Automaticos.
    """
    from app.services.gatilhos_autonomos import executar_todos_gatilhos

    resultados = await executar_todos_gatilhos()

    if resultados.get("pilot_mode"):
        return JSONResponse(
            {
                "status": "skipped",
                "reason": "pilot_mode",
                "message": "Modo piloto ativo - gatilhos não executados",
            }
        )

    return {
        "status": "ok",
        "discovery": resultados.get("discovery", {}),
        "oferta": resultados.get("oferta", {}),
        "reativacao": resultados.get("reativacao", {}),
        "feedback": resultados.get("feedback", {}),
    }


@router.post("/executar-discovery-autonomo")
@job_endpoint("executar-discovery-autonomo")
async def job_executar_discovery_autonomo():
    """
    Job especifico para Discovery automatico.

    Busca medicos nao-enriquecidos (sem especialidade) e
    enfileira mensagens de Discovery para conhece-los.

    So executa se PILOT_MODE=False.

    Sprint 32 E05.
    """
    from app.services.gatilhos_autonomos import executar_discovery_automatico

    resultado = await executar_discovery_automatico()

    if resultado is None:
        return JSONResponse(
            {
                "status": "skipped",
                "reason": "pilot_mode",
                "message": "Modo piloto ativo - discovery não executado",
            }
        )

    return {"status": "ok", **resultado}


@router.post("/executar-oferta-autonoma")
@job_endpoint("executar-oferta-autonoma")
async def job_executar_oferta_autonoma():
    """
    Job especifico para Oferta automatica (furo de escala).

    Busca vagas com menos de 20 dias ate a data e sem medico
    confirmado. Seleciona medicos compativeis e enfileira ofertas.

    So executa se PILOT_MODE=False.

    Sprint 32 E05/E06.
    """
    from app.services.gatilhos_autonomos import executar_oferta_automatica

    resultado = await executar_oferta_automatica()

    if resultado is None:
        return JSONResponse(
            {
                "status": "skipped",
                "reason": "pilot_mode",
                "message": "Modo piloto ativo - oferta não executada",
            }
        )

    return {"status": "ok", **resultado}


@router.post("/executar-reativacao-autonoma")
@job_endpoint("executar-reativacao-autonoma")
async def job_executar_reativacao_autonoma():
    """
    Job especifico para Reativacao automatica.

    Busca medicos inativos ha mais de 60 dias e enfileira
    mensagens de reativacao para retomar contato.

    So executa se PILOT_MODE=False.

    Sprint 32 E05.
    """
    from app.services.gatilhos_autonomos import executar_reativacao_automatica

    resultado = await executar_reativacao_automatica()

    if resultado is None:
        return JSONResponse(
            {
                "status": "skipped",
                "reason": "pilot_mode",
                "message": "Modo piloto ativo - reativação não executada",
            }
        )

    return {"status": "ok", **resultado}


@router.post("/executar-feedback-autonomo")
@job_endpoint("executar-feedback-autonomo")
async def job_executar_feedback_autonomo():
    """
    Job especifico para Feedback automatico.

    Busca plantoes realizados nos ultimos 2 dias e enfileira
    solicitacoes de feedback para os medicos.

    So executa se PILOT_MODE=False.

    Sprint 32 E05.
    """
    from app.services.gatilhos_autonomos import executar_feedback_automatico

    resultado = await executar_feedback_automatico()

    if resultado is None:
        return JSONResponse(
            {
                "status": "skipped",
                "reason": "pilot_mode",
                "message": "Modo piloto ativo - feedback não executado",
            }
        )

    return {"status": "ok", **resultado}


@router.get("/estatisticas-gatilhos")
@job_endpoint("estatisticas-gatilhos")
async def job_estatisticas_gatilhos():
    """
    Retorna estatisticas atuais dos gatilhos automaticos.

    Util para dashboard e monitoramento.

    Sprint 32 E05.
    """
    from app.services.gatilhos_autonomos import obter_estatisticas_gatilhos
    from app.workers.pilot_mode import is_pilot_mode

    stats = await obter_estatisticas_gatilhos()

    return {
        "status": "ok",
        "pilot_mode": is_pilot_mode(),
        "gatilhos": stats,
    }
