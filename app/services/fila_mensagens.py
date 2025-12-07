"""
Serviço para agendamento de mensagens.
"""
import logging
from datetime import datetime
from typing import Optional

from app.services.supabase import get_supabase
from app.services.timing import proximo_horario_comercial
from app.services.whatsapp import enviar_com_digitacao

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
    supabase = get_supabase()

    try:
        response = (
            supabase.table("mensagens_agendadas")
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


async def processar_mensagens_agendadas():
    """
    Job que processa mensagens agendadas.

    Executar via cron a cada minuto.
    """
    supabase = get_supabase()
    agora = datetime.now()

    try:
        # Buscar mensagens prontas para envio
        response = (
            supabase.table("mensagens_agendadas")
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

                if not telefone:
                    logger.warning(f"Telefone não encontrado para mensagem {msg.get('id')}")
                    continue

                # Enviar resposta
                await enviar_com_digitacao(
                    telefone=telefone,
                    texto=msg["resposta"]
                )

                # Marcar como enviada
                supabase.table("mensagens_agendadas").update({
                    "status": "enviada",
                    "enviada_em": datetime.now().isoformat()
                }).eq("id", msg["id"]).execute()

                logger.info(f"Mensagem agendada {msg['id']} enviada com sucesso")

            except Exception as e:
                logger.error(f"Erro ao enviar msg agendada {msg.get('id')}: {e}")

    except Exception as e:
        logger.error(f"Erro ao processar mensagens agendadas: {e}")

