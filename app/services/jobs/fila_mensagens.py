"""
Service para processamento de fila de mensagens.

Sprint 10 - S10.E3.1
"""
import logging
from dataclasses import dataclass, field

from app.services.supabase import supabase
from app.services.fila import fila_service
from app.services.whatsapp import enviar_com_digitacao
from app.services.interacao import salvar_interacao

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

    # Verificar opt-out
    if await _verificar_optout_cliente(cliente_id):
        logger.info(f"Cliente {cliente_id} fez opt-out, cancelando mensagem {mensagem_id}")
        await _cancelar_mensagem_optout(mensagem_id)
        return "optout"

    # Enviar mensagem
    try:
        await enviar_com_digitacao(
            telefone=telefone,
            texto=mensagem["conteudo"]
        )

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
