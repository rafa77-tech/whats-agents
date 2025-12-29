"""
Endpoints de webhook para integracoes externas.
"""
import asyncio
import hashlib
import hmac
import time
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
import logging

from app.core.config import settings
from app.pipeline.setup import message_pipeline
from app.pipeline.base import ProcessorResult

router = APIRouter(prefix="/webhook", tags=["Webhooks"])
logger = logging.getLogger(__name__)

# Semaforo para limitar processamento simultaneo de mensagens
# Evita sobrecarga da Evolution API e timeouts em cascata
_semaforo_processamento = asyncio.Semaphore(2)  # Maximo 2 mensagens simultaneas


@router.post("/evolution")
async def evolution_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Recebe webhooks da Evolution API.

    Responde imediatamente com 200 e processa em background
    para nao bloquear a Evolution.
    """
    try:
        payload = await request.json()
        logger.info(f"Webhook Evolution recebido: {payload.get('event')}")

        event = payload.get("event")
        instance = payload.get("instance")
        data = payload.get("data")

        if not event or not instance:
            logger.warning(f"Payload invalido: {payload}")
            return JSONResponse({"status": "invalid_payload"}, status_code=400)

        if event == "messages.upsert":
            background_tasks.add_task(processar_mensagem_pipeline, data)
            logger.info("Mensagem agendada para processamento")

        elif event == "connection.update":
            logger.info(f"Status conexao: {data}")

        else:
            logger.debug(f"Evento ignorado: {event}")

        return JSONResponse({"status": "received"})

    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        return JSONResponse({"status": "error", "message": str(e)})


async def processar_mensagem_pipeline(data: dict):
    """
    Processa mensagem usando o pipeline modular.

    O pipeline processa a mensagem atraves de:
    1. Pre-processadores (parse, opt-out, media, handoff, etc)
    2. Core processor (LLM)
    3. Pos-processadores (timing, envio, salvamento, metricas)

    Se um pre-processador retorna uma resposta (ex: opt-out, media),
    a resposta e enviada diretamente sem passar pelo LLM.
    """
    async with _semaforo_processamento:
        try:
            # Adicionar tempo de inicio para calculo de metricas
            data["_tempo_inicio"] = time.time()

            result = await message_pipeline.process(data)

            if not result.success:
                logger.error(f"Pipeline falhou: {result.error}")
            elif result.response:
                logger.info("Pipeline concluido com resposta")
            else:
                logger.info("Pipeline concluido sem resposta")

        except Exception as e:
            logger.error(f"Erro no pipeline: {e}", exc_info=True)


# ============================================================
# SLACK WEBHOOK
# ============================================================

def _verificar_assinatura_slack(body: bytes, timestamp: str, signature: str) -> bool:
    """
    Verifica se a requisicao veio realmente do Slack.

    Usa HMAC SHA256 com o Signing Secret para validar.
    """
    if not settings.SLACK_SIGNING_SECRET:
        logger.warning("SLACK_SIGNING_SECRET nao configurado")
        return False

    # Verificar se timestamp nao e muito antigo (previne replay attacks)
    try:
        req_timestamp = int(timestamp)
        current_time = int(time.time())
        if abs(current_time - req_timestamp) > 60 * 5:  # 5 minutos
            logger.warning("Timestamp do Slack muito antigo")
            return False
    except ValueError:
        return False

    # Calcular assinatura esperada
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    my_signature = 'v0=' + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode('utf-8'),
        sig_basestring.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(my_signature, signature)


@router.post("/slack")
async def slack_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Recebe eventos do Slack (mencoes, comandos).

    Eventos suportados:
    - url_verification: Verificacao inicial do Slack
    - event_callback: Eventos de mensagens/mencoes
    """
    body = await request.body()

    # Verificar assinatura (exceto em verificacao inicial)
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Erro ao parsear JSON do Slack: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # URL Verification (handshake inicial do Slack)
    if payload.get("type") == "url_verification":
        challenge = payload.get("challenge", "")
        logger.info("Slack URL verification recebida")
        return PlainTextResponse(content=challenge)

    # Verificar assinatura para outros eventos
    if not _verificar_assinatura_slack(body, timestamp, signature):
        logger.warning("Assinatura Slack invalida")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Processar evento
    event_type = payload.get("type")

    if event_type == "event_callback":
        event = payload.get("event", {})
        event_subtype = event.get("type")

        logger.info(f"Evento Slack recebido: {event_subtype}")

        # Ignorar mensagens do proprio bot
        if event.get("bot_id"):
            return JSONResponse({"status": "ignored", "reason": "bot_message"})

        # Mencao ao bot (app_mention) ou mensagem direta
        if event_subtype in ["app_mention", "message"]:
            # Processar em background para responder rapido
            background_tasks.add_task(_processar_comando_slack, event)
            return JSONResponse({"status": "processing"})

    return JSONResponse({"status": "ok"})


async def _processar_comando_slack(event: dict):
    """
    Processa comando recebido via Slack.

    Comandos suportados:
    - @julia contata <telefone/CRM>
    - @julia bloqueia <telefone/CRM>
    - @julia status
    - @julia pausa
    - @julia retoma
    """
    from app.services.slack_comandos import processar_comando

    try:
        texto = event.get("text", "")
        channel = event.get("channel", "")
        user = event.get("user", "")

        logger.info(f"Processando comando Slack: {texto[:100]}")

        await processar_comando(
            texto=texto,
            channel=channel,
            user=user
        )

    except Exception as e:
        logger.error(f"Erro ao processar comando Slack: {e}", exc_info=True)


# =============================================================================
# Slack Interactivity (Botões)
# =============================================================================

@router.post("/slack/interactivity")
async def slack_interactivity(request: Request):
    """
    Recebe interações do Slack (cliques em botões).

    Usado para confirmação de plantões.
    """
    import json
    from urllib.parse import parse_qs

    body = await request.body()

    # Verificar assinatura
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    if not _verificar_assinatura_slack(body, timestamp, signature):
        logger.warning("Assinatura Slack invalida em interactivity")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Slack envia como form-urlencoded com payload JSON
    try:
        parsed = parse_qs(body.decode("utf-8"))
        payload_str = parsed.get("payload", ["{}"])[0]
        payload = json.loads(payload_str)
    except Exception as e:
        logger.error(f"Erro ao parsear payload de interactivity: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")

    # Processar ação
    action_type = payload.get("type")

    if action_type == "block_actions":
        actions = payload.get("actions", [])
        user = payload.get("user", {})
        response_url = payload.get("response_url", "")

        for action in actions:
            action_id = action.get("action_id")
            vaga_id = action.get("value")
            user_name = user.get("name", user.get("id", "unknown"))

            logger.info(f"Slack action: {action_id} para vaga {vaga_id} por {user_name}")

            if action_id == "confirmar_realizado":
                await _processar_confirmacao_plantao(
                    vaga_id=vaga_id,
                    realizado=True,
                    confirmado_por=user_name,
                    response_url=response_url
                )
            elif action_id == "confirmar_nao_ocorreu":
                await _processar_confirmacao_plantao(
                    vaga_id=vaga_id,
                    realizado=False,
                    confirmado_por=user_name,
                    response_url=response_url
                )

    # Responder imediatamente (Slack espera resposta em 3s)
    return JSONResponse({"status": "ok"})


async def _processar_confirmacao_plantao(
    vaga_id: str,
    realizado: bool,
    confirmado_por: str,
    response_url: str
):
    """
    Processa confirmação de plantão via Slack.

    1. Valida status da vaga (idempotência)
    2. Atualiza status + emite business_event
    3. Atualiza mensagem no Slack (remove botões)
    """
    from app.services.confirmacao_plantao import (
        confirmar_plantao_realizado,
        confirmar_plantao_nao_ocorreu
    )
    from app.services.slack import atualizar_mensagem_confirmada

    try:
        # Confirmar no banco + emitir evento
        if realizado:
            resultado = await confirmar_plantao_realizado(vaga_id, confirmado_por)
        else:
            resultado = await confirmar_plantao_nao_ocorreu(vaga_id, confirmado_por)

        if resultado.sucesso:
            logger.info(f"Plantão {vaga_id} confirmado como {'realizado' if realizado else 'não ocorreu'}")

            # Atualizar mensagem no Slack
            await atualizar_mensagem_confirmada(
                response_url=response_url,
                vaga_id=vaga_id,
                confirmado_por=confirmado_por,
                realizado=realizado
            )
        else:
            logger.warning(f"Erro ao confirmar plantão {vaga_id}: {resultado.erro}")

    except Exception as e:
        logger.error(f"Erro ao processar confirmação de plantão: {e}", exc_info=True)
