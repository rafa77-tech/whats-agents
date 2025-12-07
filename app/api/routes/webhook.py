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
from app.services.handoff_detector import detectar_trigger_handoff

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
        if mensagem.texto and detectar_optout(mensagem.texto)[0]:
            logger.info(f"🛑 Opt-out detectado para {mensagem.telefone[:8]}...")
            from app.services.optout import MENSAGEM_CONFIRMACAO_OPTOUT
            
            sucesso = await processar_optout(
                cliente_id=medico["id"],
                telefone=mensagem.telefone
            )
            if sucesso:
                await evolution.enviar_mensagem(
                    telefone=mensagem.telefone,
                    texto=MENSAGEM_CONFIRMACAO_OPTOUT,
                    verificar_rate_limit=False  # Confirmação não conta no rate limit
                )
                await salvar_interacao(
                    conversa_id=conversa["id"],
                    cliente_id=medico["id"],
                    tipo="saida",
                    conteudo=MENSAGEM_CONFIRMACAO_OPTOUT,
                    autor_tipo="julia",
                )
                logger.info("✓ Confirmação de opt-out enviada")
            return

        # 8.5. Tratar mensagens não-texto (áudio, imagem, documento, vídeo)
        from app.services.respostas_especiais import (
            obter_resposta_audio,
            obter_resposta_imagem,
            obter_resposta_documento,
            obter_resposta_video
        )
        from app.services.agente import enviar_resposta

        if mensagem.tipo == "audio":
            logger.info("🎤 Mensagem de áudio recebida")
            resposta = obter_resposta_audio()
            await enviar_resposta(mensagem.telefone, resposta)
            
            # Salvar interações
            await salvar_interacao(
                conversa_id=conversa["id"],
                cliente_id=medico["id"],
                tipo="entrada",
                conteudo="[Áudio recebido]",
                autor_tipo="medico",
                message_id=mensagem.message_id
            )
            await salvar_interacao(
                conversa_id=conversa["id"],
                cliente_id=medico["id"],
                tipo="saida",
                conteudo=resposta,
                autor_tipo="julia",
            )
            logger.info("✓ Resposta para áudio enviada")
            return

        if mensagem.tipo == "imagem":
            logger.info("🖼️ Mensagem de imagem recebida")
            caption = mensagem.texto or ""
            resposta = obter_resposta_imagem(caption)
            await enviar_resposta(mensagem.telefone, resposta)
            
            # Salvar interação
            conteudo_imagem = f"[Imagem: {caption}]" if caption else "[Imagem recebida]"
            await salvar_interacao(
                conversa_id=conversa["id"],
                cliente_id=medico["id"],
                tipo="entrada",
                conteudo=conteudo_imagem,
                autor_tipo="medico",
                message_id=mensagem.message_id
            )
            await salvar_interacao(
                conversa_id=conversa["id"],
                cliente_id=medico["id"],
                tipo="saida",
                conteudo=resposta,
                autor_tipo="julia",
            )
            logger.info("✓ Resposta para imagem enviada")
            return

        if mensagem.tipo == "documento":
            logger.info("📄 Mensagem de documento recebida")
            resposta = obter_resposta_documento()
            await enviar_resposta(mensagem.telefone, resposta)
            
            # Salvar interação
            await salvar_interacao(
                conversa_id=conversa["id"],
                cliente_id=medico["id"],
                tipo="entrada",
                conteudo=f"[Documento: {mensagem.texto or 'sem nome'}]",
                autor_tipo="medico",
                message_id=mensagem.message_id
            )
            await salvar_interacao(
                conversa_id=conversa["id"],
                cliente_id=medico["id"],
                tipo="saida",
                conteudo=resposta,
                autor_tipo="julia",
            )
            logger.info("✓ Resposta para documento enviada")
            return

        if mensagem.tipo == "video":
            logger.info("🎥 Mensagem de vídeo recebida")
            resposta = obter_resposta_video()
            await enviar_resposta(mensagem.telefone, resposta)
            
            # Salvar interação
            await salvar_interacao(
                conversa_id=conversa["id"],
                cliente_id=medico["id"],
                tipo="entrada",
                conteudo="[Vídeo recebido]",
                autor_tipo="medico",
                message_id=mensagem.message_id
            )
            await salvar_interacao(
                conversa_id=conversa["id"],
                cliente_id=medico["id"],
                tipo="saida",
                conteudo=resposta,
                autor_tipo="julia",
            )
            logger.info("✓ Resposta para vídeo enviada")
            return

        # 8.6. Tratar mensagens muito longas
        if mensagem.texto:
            from app.services.mensagem import tratar_mensagem_longa, RESPOSTA_MENSAGEM_LONGA
            
            texto_processado, acao = tratar_mensagem_longa(mensagem.texto)
            
            if acao == "pedir_resumo":
                logger.warning(f"📏 Mensagem muito longa ({len(mensagem.texto)} chars), pedindo resumo")
                await enviar_resposta(mensagem.telefone, RESPOSTA_MENSAGEM_LONGA)
                
                # Salvar interação de entrada (truncada)
                await salvar_interacao(
                    conversa_id=conversa["id"],
                    cliente_id=medico["id"],
                    tipo="entrada",
                    conteudo=texto_processado + "... [truncada]",
                    autor_tipo="medico",
                    message_id=mensagem.message_id
                )
                await salvar_interacao(
                    conversa_id=conversa["id"],
                    cliente_id=medico["id"],
                    tipo="saida",
                    conteudo=RESPOSTA_MENSAGEM_LONGA,
                    autor_tipo="julia",
                )
                return
            
            if acao == "truncada":
                logger.warning(
                    f"📏 Mensagem truncada de {len(mensagem.texto)} para {len(texto_processado)} chars"
                )
                mensagem.texto = texto_processado

        # 9. Verificar triggers de handoff ANTES de processar
        if mensagem.texto:
            from app.services.handoff import iniciar_handoff
            trigger = detectar_trigger_handoff(mensagem.texto)
            if trigger:
                logger.info(f"🚨 Trigger de handoff detectado: {trigger['tipo']}")
                await iniciar_handoff(
                    conversa_id=conversa["id"],
                    cliente_id=medico["id"],
                    motivo=trigger["motivo"],
                    trigger_type=trigger["tipo"]
                )
                return  # Não gera resposta automática

        # 10. Verificar se IA controla a conversa
        if conversa.get("controlled_by") != "ai":
            logger.info("⏸ Conversa sob controle humano, não gerando resposta")
            # Sincronizar mensagem recebida com Chatwoot para gestor ver
            from app.services.chatwoot import chatwoot_service
            if conversa.get("chatwoot_conversation_id") and chatwoot_service.configurado:
                try:
                    await chatwoot_service.enviar_mensagem(
                        conversation_id=conversa["chatwoot_conversation_id"],
                        content=mensagem.texto or "[mídia]",
                        message_type="incoming"
                    )
                except Exception as e:
                    logger.warning(f"Erro ao sincronizar mensagem com Chatwoot: {e}")
            return

        # 10.5. Verificar horário comercial
        from app.services.timing import esta_em_horario_comercial, proximo_horario_comercial
        from app.services.fila_mensagens import agendar_resposta
        
        if not esta_em_horario_comercial():
            # Gerar resposta mas agendar para depois
            resposta = await processar_mensagem_completo(
                mensagem_texto=mensagem.texto or "",
                medico=medico,
                conversa=conversa,
                vagas=None
            )
            
            if resposta:
                proximo_horario = proximo_horario_comercial()
                await agendar_resposta(
                    conversa_id=conversa["id"],
                    mensagem=mensagem.texto or "",
                    resposta=resposta,
                    agendar_para=proximo_horario
                )
                
                logger.info(
                    f"⏰ Mensagem agendada para {proximo_horario} "
                    f"(fora do horário comercial)"
                )
            return

        # 11. Registrar mensagem do médico nas métricas
        from app.services.metricas import metricas_service
        await metricas_service.registrar_mensagem(
            conversa_id=conversa["id"],
            origem="medico"
        )

        # 12. Calcular delay humanizado ANTES de processar
        from app.services.timing import calcular_delay_resposta, log_timing
        import time
        
        tempo_inicio = time.time()
        delay = calcular_delay_resposta(mensagem.texto or "")
        logger.info(f"⏳ Delay calculado: {delay:.1f}s")

        # 13. Gerar resposta (enquanto "lê" a mensagem)
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

        # 14. Calcular tempo restante de delay
        tempo_processamento = time.time() - tempo_inicio
        delay_restante = max(0, delay - tempo_processamento)
        
        # Log timing
        log_timing(mensagem.texto or "", delay, tempo_processamento)

        # 15. Aguardar delay restante (simulando "pensar")
        if delay_restante > 5:
            # Mostrar "digitando" antes de enviar
            await asyncio.sleep(delay_restante - 5)
            await mostrar_digitando(mensagem.telefone)
            await asyncio.sleep(5)
        else:
            await asyncio.sleep(delay_restante)
            await mostrar_digitando(mensagem.telefone)

        # 16. Enviar resposta com timing humanizado (quebra mensagens longas)
        from app.services.agente import enviar_resposta
        resultado = await enviar_resposta(
            telefone=mensagem.telefone,
            resposta=resposta
        )

        if resultado:
            logger.info(f"✓ Mensagem enviada para {mensagem.telefone[:8]}...")

            # 17. Registrar resposta da Júlia nas métricas (com tempo de resposta)
            await metricas_service.registrar_mensagem(
                conversa_id=conversa["id"],
                origem="ai",
                tempo_resposta_segundos=tempo_processamento
            )

            # 18. Salvar interação de saída
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
