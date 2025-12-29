"""
Serviço para agendamento de mensagens.
"""
import logging
from datetime import datetime
from typing import Optional

from app.services.supabase import supabase
from app.services.timing import proximo_horario_comercial
from app.services.outbound import send_outbound_message, criar_contexto_followup

logger = logging.getLogger(__name__)


async def agendar_resposta(
    conversa_id: str,
    mensagem: str,
    resposta: str,
    agendar_para: datetime
) -> Optional[dict]:
    """
    Agenda resposta para envio posterior.

    Args:
        conversa_id: ID da conversa
        mensagem: Mensagem original recebida
        resposta: Resposta gerada
        agendar_para: Data/hora para envio

    Returns:
        Dados da mensagem agendada ou None se erro
    """
    try:
        response = (
            supabase.table("fila_mensagens")
            .insert({
                "conversa_id": conversa_id,
                "mensagem_original": mensagem,
                "resposta": resposta,
                "agendar_para": agendar_para.isoformat(),
                "status": "pendente"
            })
            .execute()
        )

        if response.data:
            logger.info(f"Mensagem agendada para {agendar_para}")
            return response.data[0]
        return None

    except Exception as e:
        logger.error(f"Erro ao agendar mensagem: {e}")
        return None


async def processar_fila_mensagens():
    """
    Job que processa mensagens agendadas.

    Executar via cron a cada minuto.
    """
    agora = datetime.now()

    try:
        # Buscar mensagens prontas para envio
        response = (
            supabase.table("fila_mensagens")
            .select("*")
            .eq("status", "pendente")
            .lte("agendar_para", agora.isoformat())
            .execute()
        )

        if not response.data:
            return

        for msg in response.data:
            try:
                # Buscar conversa e cliente
                conversa_id = msg.get("conversa_id")
                if not conversa_id:
                    logger.warning(f"Conversa ID não encontrado para mensagem {msg.get('id')}")
                    continue

                conversa_response = (
                    supabase.table("conversations")
                    .select("*, clientes(*)")
                    .eq("id", conversa_id)
                    .single()
                    .execute()
                )

                if not conversa_response.data:
                    logger.warning(f"Conversa {conversa_id} não encontrada")
                    continue

                conversa = conversa_response.data
                cliente = conversa.get("clientes", {})
                telefone = cliente.get("telefone")
                cliente_id = cliente.get("id")

                if not telefone:
                    logger.warning(f"Telefone não encontrado para mensagem {msg.get('id')}")
                    continue

                if not cliente_id:
                    logger.warning(f"Cliente ID não encontrado para mensagem {msg.get('id')}")
                    continue

                # GUARDRAIL: Verificar ANTES de enviar (substitui check básico de opt-out)
                ctx = criar_contexto_followup(
                    cliente_id=cliente_id,
                    conversation_id=conversa_id,
                )
                result = await send_outbound_message(
                    telefone=telefone,
                    texto=msg["resposta"],
                    ctx=ctx,
                    simular_digitacao=True,
                )

                if result.blocked:
                    logger.info(f"Mensagem {msg['id']} bloqueada: {result.block_reason}")
                    supabase.table("fila_mensagens").update({
                        "status": "bloqueada",
                        "erro": f"Guardrail: {result.block_reason}"
                    }).eq("id", msg["id"]).execute()
                    continue

                if not result.success:
                    raise Exception(result.error)

                # Marcar como enviada
                supabase.table("fila_mensagens").update({
                    "status": "enviada",
                    "enviada_em": datetime.now().isoformat()
                }).eq("id", msg["id"]).execute()

                logger.info(f"Mensagem agendada {msg['id']} enviada com sucesso")

            except Exception as e:
                logger.error(f"Erro ao enviar msg agendada {msg.get('id')}: {e}")

    except Exception as e:
        logger.error(f"Erro ao processar mensagens agendadas: {e}")


# Alias para compatibilidade (nome antigo usado em jobs.py e scheduler)
processar_mensagens_agendadas = processar_fila_mensagens
