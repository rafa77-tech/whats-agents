"""
Endpoints de webhook para integrações externas.
"""
import asyncio
import random
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import logging

from app.services.parser import parsear_mensagem, deve_processar
from app.services.whatsapp import evolution, mostrar_online, mostrar_digitando
from app.services.medico import buscar_ou_criar_medico
from app.services.conversa import buscar_ou_criar_conversa
from app.services.interacao import salvar_interacao
from app.services.agente import processar_mensagem_completo
from app.services.optout import detectar_optout, processar_optout

router = APIRouter(prefix="/webhook", tags=["Webhooks"])
logger = logging.getLogger(__name__)


@router.post("/evolution")
async def evolution_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Recebe webhooks da Evolution API.

    Responde imediatamente com 200 e processa em background
    para não bloquear a Evolution.
    """
    try:
        # Parsear payload
        payload = await request.json()
        logger.info(f"Webhook Evolution recebido: {payload.get('event')}")

        # Validar estrutura básica
        event = payload.get("event")
        instance = payload.get("instance")
        data = payload.get("data")

        if not event or not instance:
            logger.warning(f"Payload inválido: {payload}")
            return JSONResponse({"status": "invalid_payload"}, status_code=400)

        # Processar por tipo de evento
        if event == "messages.upsert":
            # Agendar processamento em background
            background_tasks.add_task(processar_mensagem, data)
            logger.info("Mensagem agendada para processamento")

        elif event == "connection.update":
            logger.info(f"Status conexão: {data}")

        else:
            logger.debug(f"Evento ignorado: {event}")

        return JSONResponse({"status": "received"})

    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        # Ainda retorna 200 para não causar retry da Evolution
        return JSONResponse({"status": "error", "message": str(e)})


async def processar_mensagem(data: dict):
    """Processa mensagem recebida."""
    # Parsear mensagem
    mensagem = parsear_mensagem(data)

    if not mensagem:
        logger.warning("Mensagem não pôde ser parseada")
        return

    # Verificar se deve processar
    if not deve_processar(mensagem):
        if mensagem.from_me:
            logger.debug("Ignorando mensagem própria")
        elif mensagem.is_grupo:
            logger.debug("Ignorando mensagem de grupo")
        elif mensagem.is_status:
            logger.debug("Ignorando status")
        return

    logger.info(
        f"Mensagem parseada: "
        f"tel={mensagem.telefone}, "
        f"tipo={mensagem.tipo}, "
        f"from_me={mensagem.from_me}, "
        f"texto={mensagem.texto[:50] if mensagem.texto else 'N/A'}..."
    )

    try:
        # 1. Marcar como lida
        await evolution.marcar_como_lida(
            mensagem.telefone,
            mensagem.message_id
        )
        logger.info(f"✓ Mensagem {mensagem.message_id[:8]}... marcada como lida")

        # 2. Mostrar online
        await mostrar_online(mensagem.telefone)
        logger.info(f"✓ Presença 'online' enviada para {mensagem.telefone[:8]}...")

        # 3. Pequena pausa (simula leitura)
        await asyncio.sleep(1)

        # 4. Mostrar digitando
        await mostrar_digitando(mensagem.telefone)
        logger.info(f"✓ Presença 'digitando' enviada para {mensagem.telefone[:8]}...")

        # 5. Buscar ou criar médico
        medico = await buscar_ou_criar_medico(
            telefone=mensagem.telefone,
            nome_whatsapp=mensagem.nome_contato
        )
        if not medico:
            logger.error("Erro ao buscar/criar médico")
            return

        logger.info(f"✓ Médico: {medico.get('primeiro_nome', 'Novo')} ({medico['id'][:8]}...)")

        # 6. Buscar ou criar conversa
        conversa = await buscar_ou_criar_conversa(cliente_id=medico["id"])
        if not conversa:
            logger.error("Erro ao buscar/criar conversa")
            return

        logger.info(f"✓ Conversa: {conversa['id'][:8]}... (controlled_by={conversa['controlled_by']})")

        # 7. Salvar interação de entrada
        await salvar_interacao(
            conversa_id=conversa["id"],
            cliente_id=medico["id"],
            tipo="entrada",
            conteudo=mensagem.texto or "[mídia]",
            autor_tipo="medico",
            message_id=mensagem.message_id
        )
        logger.info("✓ Interação de entrada salva")

        # 8. Verificar opt-out ANTES de gerar resposta
        if mensagem.texto and detectar_optout(mensagem.texto):
            logger.info(f"🛑 Opt-out detectado para {mensagem.telefone[:8]}...")
            resposta_optout = await processar_optout(
                cliente_id=medico["id"],
                telefone=mensagem.telefone
            )
            if resposta_optout:
                await evolution.enviar_mensagem(
                    telefone=mensagem.telefone,
                    texto=resposta_optout,
                    verificar_rate_limit=False  # Confirmação não conta no rate limit
                )
                await salvar_interacao(
                    conversa_id=conversa["id"],
                    cliente_id=medico["id"],
                    tipo="saida",
                    conteudo=resposta_optout,
                    autor_tipo="julia",
                )
                logger.info("✓ Confirmação de opt-out enviada")
            return

        # 9. Verificar se IA controla a conversa
        if conversa.get("controlled_by") != "ai":
            logger.info("⏸ Conversa sob controle humano, não gerando resposta")
            return

        # 10. Delay humano (simula leitura + digitação)
        delay = random.uniform(2, 5)  # 2-5 segundos
        logger.info(f"⏳ Delay humano: {delay:.1f}s")
        await asyncio.sleep(delay)

        # 11. Manter digitando
        await mostrar_digitando(mensagem.telefone)

        # 12. Gerar resposta da Julia
        resposta = await processar_mensagem_completo(
            mensagem_texto=mensagem.texto or "",
            medico=medico,
            conversa=conversa,
            vagas=None  # TODO: Buscar vagas relevantes
        )

        if not resposta:
            logger.warning("Julia não gerou resposta")
            return

        logger.info(f"✓ Resposta gerada: {resposta[:50]}...")

        # 13. Enviar resposta via WhatsApp (sem verificar rate limit para respostas)
        resultado = await evolution.enviar_mensagem(
            telefone=mensagem.telefone,
            texto=resposta,
            verificar_rate_limit=False  # Respostas a mensagens recebidas não contam
        )

        if resultado:
            logger.info(f"✓ Mensagem enviada para {mensagem.telefone[:8]}...")

            # 14. Salvar interação de saída
            await salvar_interacao(
                conversa_id=conversa["id"],
                cliente_id=medico["id"],
                tipo="saida",
                conteudo=resposta,
                autor_tipo="julia",
                message_id=resultado.get("key", {}).get("id")
            )
            logger.info("✓ Interação de saída salva")
        else:
            logger.error("Falha ao enviar mensagem")

    except Exception as e:
        logger.error(f"Erro ao processar: {e}", exc_info=True)
