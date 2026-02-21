"""
Jobs de confirmacao de plantao (Sprint 17).

Sprint 58 - Epic 1: Decomposicao de jobs.py
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ._helpers import job_endpoint

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/processar-confirmacao-plantao")
@job_endpoint("processar-confirmacao-plantao")
async def job_processar_confirmacao_plantao(buffer_horas: int = 2):
    """
    Job horario para transicionar vagas vencidas.

    Regra: reservada -> pendente_confirmacao quando fim_plantao <= now() - buffer

    Args:
        buffer_horas: Horas apos fim do plantao para considerar vencido (default: 2)
    """
    from app.services.confirmacao_plantao import processar_vagas_vencidas

    resultado = await processar_vagas_vencidas(buffer_horas=buffer_horas)

    return {
        "status": "ok",
        "processadas": resultado["processadas"],
        "erros": resultado["erros"],
        "vagas": resultado["vagas"],
    }


@router.post("/backfill-confirmacao-plantao")
@job_endpoint("backfill-confirmacao-plantao")
async def job_backfill_confirmacao_plantao():
    """
    Job unico para backfill de vagas reservadas antigas.

    Move vagas reservadas vencidas para pendente_confirmacao com source='backfill'.
    """
    from app.services.confirmacao_plantao import processar_vagas_vencidas

    resultado = await processar_vagas_vencidas(buffer_horas=2, is_backfill=True)

    return {
        "status": "ok",
        "message": f"Backfill concluído: {resultado['processadas']} vagas transicionadas",
        "processadas": resultado["processadas"],
        "erros": resultado["erros"],
    }


@router.get("/pendentes-confirmacao")
@job_endpoint("pendentes-confirmacao")
async def listar_pendentes_confirmacao():
    """
    Lista vagas aguardando confirmacao.

    Retorna vagas em pendente_confirmacao para exibicao/acao.
    """
    from app.services.confirmacao_plantao import listar_pendentes_confirmacao

    vagas = await listar_pendentes_confirmacao()

    return {
        "status": "ok",
        "total": len(vagas),
        "vagas": [
            {
                "id": v.id,
                "data": v.data,
                "horario": f"{v.hora_inicio} - {v.hora_fim}",
                "valor": v.valor,
                "hospital": v.hospital_nome,
                "especialidade": v.especialidade_nome,
                "medico": v.cliente_nome,
                "telefone": v.cliente_telefone,
            }
            for v in vagas
        ],
    }


@router.post("/enviar-otp-confirmacao/{vaga_id}")
async def enviar_otp_confirmacao(vaga_id: str):
    """
    Sprint 72: Envia OTP via Meta AUTHENTICATION template para confirmar plantão.

    Busca o médico associado à vaga e envia código OTP via WhatsApp.
    """
    try:
        from app.services.supabase import supabase
        from app.services.meta.otp_confirmation import otp_confirmation

        # Buscar vaga com dados do médico
        vaga = (
            supabase.table("vagas")
            .select("id, status, cliente_id, clientes(telefone)")
            .eq("id", vaga_id)
            .single()
            .execute()
        )

        if not vaga.data:
            return JSONResponse(
                {"status": "error", "message": "Vaga não encontrada"},
                status_code=404,
            )

        if vaga.data.get("status") != "pendente_confirmacao":
            return JSONResponse(
                {"status": "error", "message": "Vaga não está pendente de confirmação"},
                status_code=400,
            )

        telefone = (vaga.data.get("clientes") or {}).get("telefone")
        if not telefone:
            return JSONResponse(
                {"status": "error", "message": "Telefone do médico não encontrado"},
                status_code=400,
            )

        resultado = await otp_confirmation.enviar_confirmacao_plantao(
            telefone=telefone,
            plantao_id=vaga_id,
        )

        return JSONResponse({"status": "ok", **resultado})

    except Exception as e:
        logger.error(f"Erro ao enviar OTP para vaga {vaga_id}: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/verificar-otp-confirmacao")
async def verificar_otp_confirmacao(telefone: str, codigo: str):
    """
    Sprint 72: Verifica código OTP e confirma plantão se válido.
    """
    try:
        from app.services.meta.otp_confirmation import otp_confirmation
        from app.services.confirmacao_plantao import confirmar_plantao_realizado

        resultado = await otp_confirmation.verificar_codigo_otp(telefone, codigo)

        if not resultado.get("valido"):
            return JSONResponse(
                {"status": "error", "message": resultado.get("motivo", "Código inválido")},
                status_code=400,
            )

        # OTP válido — confirmar plantão
        plantao_id = resultado["plantao_id"]
        confirmacao = await confirmar_plantao_realizado(plantao_id, "otp_meta")

        return JSONResponse({
            "status": "ok",
            "plantao_id": plantao_id,
            "confirmado": confirmacao.sucesso,
        })

    except Exception as e:
        logger.error(f"Erro ao verificar OTP: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/confirmar-plantao/{vaga_id}")
async def confirmar_plantao(vaga_id: str, realizado: bool, confirmado_por: str = "api"):
    """
    Confirma status de um plantao.

    Args:
        vaga_id: UUID da vaga
        realizado: True = realizado, False = nao ocorreu
        confirmado_por: Identificador de quem confirmou
    """
    try:
        from app.services.confirmacao_plantao import (
            confirmar_plantao_realizado,
            confirmar_plantao_nao_ocorreu,
        )

        if realizado:
            resultado = await confirmar_plantao_realizado(vaga_id, confirmado_por)
        else:
            resultado = await confirmar_plantao_nao_ocorreu(vaga_id, confirmado_por)

        if resultado.sucesso:
            return JSONResponse(
                {
                    "status": "ok",
                    "vaga_id": vaga_id,
                    "novo_status": resultado.status_novo,
                    "confirmado_por": confirmado_por,
                }
            )
        else:
            return JSONResponse({"status": "error", "message": resultado.erro}, status_code=400)
    except Exception as e:
        logger.error(f"Erro ao confirmar plantão {vaga_id}: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
