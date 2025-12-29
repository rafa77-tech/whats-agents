"""
Service para processamento de fila de mensagens.

Sprint 10 - S10.E3.1
"""
import logging
from dataclasses import dataclass, field

from app.services.supabase import supabase
from app.services.fila import fila_service
from app.services.interacao import salvar_interacao
from app.services.outbound import send_outbound_message, criar_contexto_followup

logger = logging.getLogger(__name__)


@dataclass
class StatsFilaMensagens:
    """Estatisticas do processamento da fila."""
    processadas: int = 0
    enviadas: int = 0
    bloqueadas_optout: int = 0
    erros: int = 0


async def processar_fila(limite: int = 20) -> StatsFilaMensagens:
    """
    Processa mensagens pendentes na fila.

    Args:
        limite: Numero maximo de mensagens a processar

    Returns:
        StatsFilaMensagens com estatisticas
    """
    stats = StatsFilaMensagens()

    for _ in range(limite):
        # Obter proxima mensagem
        mensagem = await fila_service.obter_proxima()
        if not mensagem:
            break

        stats.processadas += 1
        resultado = await _processar_mensagem(mensagem)

        if resultado == "enviada":
            stats.enviadas += 1
        elif resultado == "optout":
            stats.bloqueadas_optout += 1
        else:
            stats.erros += 1

    return stats


async def _processar_mensagem(mensagem: dict) -> str:
    """
    Processa uma mensagem individual da fila.

    Args:
        mensagem: Dados da mensagem

    Returns:
        Status: 'enviada', 'optout', 'erro'
    """
    cliente = mensagem.get("clientes", {})
    telefone = cliente.get("telefone")
    cliente_id = mensagem.get("cliente_id")
    mensagem_id = mensagem["id"]

    # Validar telefone
    if not telefone:
        logger.warning(f"Telefone nao encontrado para mensagem {mensagem_id}")
        await fila_service.marcar_erro(mensagem_id, "Telefone nao encontrado")
        return "erro"

    if not cliente_id:
        logger.warning(f"Cliente ID nao encontrado para mensagem {mensagem_id}")
        await fila_service.marcar_erro(mensagem_id, "Cliente ID nao encontrado")
        return "erro"

    # Enviar mensagem com GUARDRAIL
    try:
        ctx = criar_contexto_followup(
            cliente_id=cliente_id,
            conversation_id=mensagem.get("conversa_id"),
        )
        result = await send_outbound_message(
            telefone=telefone,
            texto=mensagem["conteudo"],
            ctx=ctx,
            simular_digitacao=True,
        )

        if result.blocked:
            logger.info(f"Mensagem {mensagem_id} bloqueada: {result.block_reason}")
            await fila_service.marcar_erro(mensagem_id, f"Guardrail: {result.block_reason}")
            return "optout" if result.block_reason == "opted_out" else "erro"

        if not result.success:
            logger.error(f"Erro ao enviar mensagem {mensagem_id}: {result.error}")
            await fila_service.marcar_erro(mensagem_id, result.error)
            return "erro"

        await fila_service.marcar_enviada(mensagem_id)

        # Salvar interacao se tiver conversa
        if mensagem.get("conversa_id"):
            await salvar_interacao(
                conversa_id=mensagem["conversa_id"],
                cliente_id=cliente_id,
                tipo="saida",
                conteudo=mensagem["conteudo"],
                autor_tipo="julia"
            )

        logger.info(f"Mensagem {mensagem_id} enviada para {telefone}")
        return "enviada"

    except Exception as e:
        logger.error(f"Erro ao enviar mensagem {mensagem_id}: {e}")
        await fila_service.marcar_erro(mensagem_id, str(e))
        return "erro"


async def _verificar_optout_cliente(cliente_id: str) -> bool:
    """Verifica se cliente fez opt-out."""
    cliente_resp = (
        supabase.table("clientes")
        .select("opted_out")
        .eq("id", cliente_id)
        .single()
        .execute()
    )
    return cliente_resp.data and cliente_resp.data.get("opted_out", False)


async def _cancelar_mensagem_optout(mensagem_id: str) -> None:
    """Cancela mensagem por opt-out."""
    supabase.table("fila_mensagens").update({
        "status": "cancelada",
        "erro": "Cliente fez opt-out"
    }).eq("id", mensagem_id).execute()
