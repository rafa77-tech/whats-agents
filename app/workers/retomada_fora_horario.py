"""
Job para processar mensagens fora do horario.

Roda as 08:00 de dias uteis.

Sprint 22 - Responsividade Inteligente
"""
import logging
from datetime import datetime

from app.services.fora_horario import (
    buscar_mensagens_pendentes,
    marcar_processada,
    eh_horario_comercial,
    TZ_BRASIL,
)

logger = logging.getLogger(__name__)


async def processar_retomadas() -> dict:
    """
    Processa todas as mensagens fora do horario pendentes.

    Returns:
        Estatisticas de processamento
    """
    if not eh_horario_comercial():
        logger.info("Fora do horario comercial, pulando retomadas")
        return {"processadas": 0, "erro": 0, "motivo": "fora_horario"}

    pendentes = await buscar_mensagens_pendentes()

    if not pendentes:
        logger.info("Nenhuma mensagem fora do horario pendente")
        return {"processadas": 0, "erro": 0}

    logger.info(f"Processando {len(pendentes)} mensagens fora do horario")

    stats = {"processadas": 0, "erro": 0, "ignoradas": 0}

    for registro in pendentes:
        try:
            # Buscar dados do cliente
            cliente = registro.get("clientes", {})
            nome = cliente.get("nome", "").split()[0] if cliente.get("nome") else ""
            telefone = cliente.get("telefone")

            if not telefone:
                logger.warning(f"Registro {registro['id']} sem telefone, pulando")
                await marcar_processada(registro["id"], "ignorado: sem telefone")
                stats["ignoradas"] += 1
                continue

            # Formatar mensagem de retomada
            hora = datetime.now(TZ_BRASIL).hour
            saudacao = "Bom dia" if hora < 12 else "Boa tarde"

            mensagem_retomada = f"""{saudacao} Dr(a) {nome}!

Sobre sua mensagem de ontem, ja verifiquei aqui.

"""
            # Processar a mensagem original com contexto de retomada
            from app.services.agente import gerar_resposta_com_contexto

            contexto = registro.get("contexto", {})
            contexto["retomada"] = True
            contexto["mensagem_original"] = registro["mensagem"]
            contexto["prefixo_resposta"] = mensagem_retomada

            resposta = await gerar_resposta_com_contexto(
                cliente_id=registro["cliente_id"],
                mensagem=registro["mensagem"],
                contexto_extra=contexto
            )

            if resposta:
                # Enviar resposta via wrapper de guardrails
                from app.services.outbound import send_outbound_message
                from app.services.guardrails import (
                    OutboundContext,
                    OutboundMethod,
                    OutboundChannel,
                    ActorType,
                )

                resposta_final = mensagem_retomada + resposta

                ctx = OutboundContext(
                    cliente_id=registro["cliente_id"],
                    actor_type=ActorType.BOT,
                    channel=OutboundChannel.WHATSAPP,
                    method=OutboundMethod.REPLY,
                    is_proactive=False,
                    conversation_id=registro.get("conversation_id"),
                )

                result = await send_outbound_message(telefone, resposta_final, ctx)

                if result.success:
                    await marcar_processada(registro["id"], "sucesso")
                    stats["processadas"] += 1
                    logger.info(f"Retomada processada: {registro['id']}")
                else:
                    await marcar_processada(registro["id"], f"bloqueado: {result.outcome_reason_code}")
                    stats["ignoradas"] += 1
                    logger.warning(f"Retomada bloqueada: {registro['id']} - {result.outcome}")
            else:
                await marcar_processada(registro["id"], "sem_resposta")
                stats["ignoradas"] += 1

        except Exception as e:
            logger.error(f"Erro ao processar retomada {registro['id']}: {e}")
            await marcar_processada(registro["id"], f"erro: {str(e)[:100]}")
            stats["erro"] += 1

    logger.info(f"Retomadas concluidas: {stats}")
    return stats
