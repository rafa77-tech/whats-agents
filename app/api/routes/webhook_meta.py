"""
Webhook Router para Meta WhatsApp Cloud API.

Sprint 66 — Recebe webhooks da Meta e roteia para o pipeline Julia.

Segue o padrão exato do webhook_zapi.py:
- Converte payload Meta para formato Evolution
- Processa em background via pipeline
- Atualiza delivery status
"""

import hashlib
import hmac
import time
import logging
from typing import Optional

from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse

from app.core.config import settings
from app.services.supabase import supabase
from app.services.redis import cache_get_json, cache_set_json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/meta", tags=["meta-webhook"])


@router.get("")
@router.get("/")
async def verificar_webhook(request: Request):
    """
    Verificação de webhook (challenge) da Meta.

    Meta envia GET com hub.mode, hub.verify_token, hub.challenge.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.META_WEBHOOK_VERIFY_TOKEN:
        logger.info("[WebhookMeta] Webhook verificado com sucesso")
        return PlainTextResponse(challenge)

    logger.warning(f"[WebhookMeta] Verificação falhou: mode={mode}")
    return PlainTextResponse("Verification failed", status_code=403)


@router.post("")
@router.post("/")
async def webhook_meta(request: Request, background_tasks: BackgroundTasks):
    """
    Recebe webhooks da Meta Cloud API.

    Eventos suportados:
    - messages: Mensagem recebida
    - statuses: Status de mensagem (sent, delivered, read, failed)
    - message_template_status_update: Atualização de template
    """
    # 1. Validar signature
    body = await request.body()
    if not _validar_signature(request, body):
        logger.warning("[WebhookMeta] Signature inválida")
        return PlainTextResponse("Invalid signature", status_code=403)

    # 2. Parse payload
    try:
        import json

        payload = json.loads(body)
    except Exception as e:
        logger.error(f"[WebhookMeta] Erro ao parsear JSON: {e}")
        return {"status": "ok"}  # Retornar 200 para não gerar retries

    # 3. Ignorar se não for whatsapp_business_account
    if payload.get("object") != "whatsapp_business_account":
        return {"status": "ignored", "reason": "not_whatsapp"}

    # 4. Processar cada entry/change
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            field = change.get("field")
            value = change.get("value", {})

            if field == "messages":
                await _processar_messages_field(value, background_tasks)
            elif field == "message_template_status_update":
                await _processar_template_status(value)
            else:
                logger.debug(f"[WebhookMeta] Campo ignorado: {field}")

    return {"status": "ok"}


def _validar_signature(request: Request, body: bytes) -> bool:
    """
    Valida X-Hub-Signature-256 usando HMAC SHA256.

    Args:
        request: FastAPI Request
        body: Body raw da requisição

    Returns:
        True se signature válida ou se META_APP_SECRET não configurado
    """
    app_secret = settings.META_APP_SECRET
    if not app_secret:
        # Se não configurado, aceitar (desenvolvimento)
        logger.warning(
            "[WebhookMeta] META_APP_SECRET não configurado — "
            "signature validation desabilitada. Configurar em produção!"
        )
        return True

    signature_header = request.headers.get("X-Hub-Signature-256", "")
    if not signature_header.startswith("sha256="):
        return False

    expected_signature = signature_header[7:]  # Remove "sha256="
    computed = hmac.new(
        app_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed, expected_signature)


async def _processar_messages_field(
    value: dict, background_tasks: BackgroundTasks
) -> None:
    """
    Processa campo 'messages' do webhook (mensagens e status).

    Value contém:
    - metadata: {phone_number_id, display_phone_number}
    - messages: lista de mensagens recebidas
    - statuses: lista de atualizações de status
    """
    metadata = value.get("metadata", {})
    phone_number_id = metadata.get("phone_number_id")

    # Buscar chip
    chip = await _obter_chip_por_meta_phone_number_id(phone_number_id)
    if not chip:
        logger.debug(
            f"[WebhookMeta] Phone number ID desconhecido: {phone_number_id}"
        )
        return

    # Processar mensagens recebidas
    for message in value.get("messages", []):
        contacts = value.get("contacts", [])
        await _processar_mensagem_recebida(
            chip, message, contacts, background_tasks
        )

    # Processar status updates
    for status in value.get("statuses", []):
        await _processar_status_mensagem(chip, status)


async def _obter_chip_por_meta_phone_number_id(
    phone_number_id: str,
) -> Optional[dict]:
    """Busca chip pelo meta_phone_number_id."""
    if not phone_number_id:
        return None

    try:
        result = (
            supabase.table("chips")
            .select("*")
            .eq("meta_phone_number_id", phone_number_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"[WebhookMeta] Erro ao buscar chip: {e}")
        return None


async def _processar_mensagem_recebida(
    chip: dict,
    message: dict,
    contacts: list,
    background_tasks: BackgroundTasks,
) -> None:
    """
    Processa mensagem recebida e envia para pipeline Julia.

    Converte payload Meta para formato Evolution (padrão do pipeline).
    """
    message_id = message.get("id")
    telefone = message.get("from", "")
    msg_type = message.get("type", "text")

    # Deduplicação via cache
    if message_id:
        cached = await cache_get_json(f"meta:msg:{message_id}")
        if cached:
            logger.debug(f"[WebhookMeta] Mensagem {message_id} já processada")
            return
        await cache_set_json(
            f"meta:msg:{message_id}", {"processed": True}, ttl=300
        )

    # Registrar métricas via RPC
    try:
        supabase.rpc(
            "chip_registrar_resposta",
            {
                "p_chip_id": chip["id"],
                "p_telefone_remetente": telefone,
            },
        ).execute()
    except Exception as e:
        logger.warning(f"[WebhookMeta] Erro ao registrar resposta via RPC: {e}")

    # Abrir/renovar janela de conversa 24h
    try:
        from app.services.meta.window_tracker import window_tracker

        await window_tracker.abrir_janela(chip["id"], telefone, "user_initiated")
    except Exception as e:
        logger.warning(f"[WebhookMeta] Erro ao abrir janela: {e}")

    # Verificar se chip está ativo para processamento
    if chip.get("status") not in ["active", "warming"]:
        logger.warning(
            f"[WebhookMeta] Chip {chip.get('telefone')} não ativo "
            f"(status={chip.get('status')})"
        )
        return

    # Converter para formato Evolution e processar
    evolution_data = _converter_meta_para_formato_evolution(
        message, contacts, chip
    )

    background_tasks.add_task(_processar_no_pipeline, evolution_data)

    # Extrair texto para log
    texto = _extrair_texto_mensagem(message)
    logger.info(
        f"[WebhookMeta] Mensagem de {telefone[-4:]} ({msg_type}) "
        f"agendada para pipeline: '{texto[:50]}...'"
    )


def _extrair_texto_mensagem(message: dict) -> str:
    """Extrai texto de qualquer tipo de mensagem Meta."""
    msg_type = message.get("type", "text")

    if msg_type == "text":
        return message.get("text", {}).get("body", "")
    elif msg_type == "image":
        return message.get("image", {}).get("caption", "[imagem]")
    elif msg_type == "video":
        return message.get("video", {}).get("caption", "[video]")
    elif msg_type == "audio":
        return "[audio]"
    elif msg_type == "document":
        return message.get("document", {}).get("caption", "[documento]")
    elif msg_type == "interactive":
        interactive = message.get("interactive", {})
        itype = interactive.get("type")
        if itype == "button_reply":
            return interactive.get("button_reply", {}).get("title", "")
        elif itype == "list_reply":
            return interactive.get("list_reply", {}).get("title", "")
    elif msg_type == "reaction":
        return message.get("reaction", {}).get("emoji", "")

    return f"[{msg_type}]"


def _converter_meta_para_formato_evolution(
    message: dict, contacts: list, chip: dict
) -> dict:
    """
    Converte payload Meta para formato Evolution API (compatível com pipeline).

    Segue o padrão exato do _converter_para_formato_evolution do webhook_zapi.
    """
    telefone = message.get("from", "")
    message_id = message.get("id", f"meta_{int(time.time() * 1000)}")
    timestamp = int(message.get("timestamp", time.time()))
    msg_type = message.get("type", "text")

    # Nome do contato
    push_name = ""
    if contacts:
        push_name = contacts[0].get("profile", {}).get("name", "")

    # Texto da mensagem
    texto = ""
    if msg_type == "text":
        texto = message.get("text", {}).get("body", "")
    elif msg_type == "image":
        texto = message.get("image", {}).get("caption", "")
    elif msg_type == "video":
        texto = message.get("video", {}).get("caption", "")
    elif msg_type == "interactive":
        interactive = message.get("interactive", {})
        itype = interactive.get("type")
        if itype == "button_reply":
            texto = interactive.get("button_reply", {}).get("title", "")
        elif itype == "list_reply":
            texto = interactive.get("list_reply", {}).get("title", "")

    # Formato Evolution esperado pelo pipeline
    evolution_data = {
        "key": {
            "remoteJid": f"{telefone}@s.whatsapp.net",
            "fromMe": False,
            "id": message_id,
        },
        "message": {
            "conversation": texto,
        },
        "messageTimestamp": timestamp,
        "pushName": push_name,
        # Metadados para identificar origem Meta
        "_evolution_instance": chip.get("instance_name", "meta"),
        "_meta_chip_id": chip.get("id"),
        "_meta_telefone": chip.get("telefone"),
        "_provider": "meta",
    }

    # Adicionar mídia se presente
    if msg_type == "image":
        evolution_data["message"]["imageMessage"] = {
            "id": message.get("image", {}).get("id"),
            "caption": message.get("image", {}).get("caption", ""),
            "mime_type": message.get("image", {}).get("mime_type"),
        }
    elif msg_type == "audio":
        evolution_data["message"]["audioMessage"] = {
            "id": message.get("audio", {}).get("id"),
            "mime_type": message.get("audio", {}).get("mime_type"),
            "ptt": msg_type == "audio",  # Assume voice note
        }
    elif msg_type == "video":
        evolution_data["message"]["videoMessage"] = {
            "id": message.get("video", {}).get("id"),
            "caption": message.get("video", {}).get("caption", ""),
            "mime_type": message.get("video", {}).get("mime_type"),
        }
    elif msg_type == "document":
        evolution_data["message"]["documentMessage"] = {
            "id": message.get("document", {}).get("id"),
            "fileName": message.get("document", {}).get("filename"),
            "mime_type": message.get("document", {}).get("mime_type"),
        }

    return evolution_data


async def _processar_no_pipeline(data: dict) -> None:
    """Processa mensagem no pipeline da Julia."""
    from app.pipeline.setup import message_pipeline

    try:
        data["_tempo_inicio"] = time.time()
        result = await message_pipeline.process(data)

        if not result.success:
            logger.error(f"[WebhookMeta] Pipeline falhou: {result.error}")
        elif result.response:
            logger.info("[WebhookMeta] Pipeline concluído com resposta")
        else:
            logger.info("[WebhookMeta] Pipeline concluído sem resposta")

    except Exception as e:
        logger.error(f"[WebhookMeta] Erro no pipeline: {e}", exc_info=True)


async def _processar_status_mensagem(chip: dict, status_data: dict) -> None:
    """
    Processa atualização de status de mensagem (sent/delivered/read/failed).

    Atualiza delivery_status na tabela interações.
    """
    from app.services.delivery_status import atualizar_delivery_status

    status = status_data.get("status", "")
    message_id = status_data.get("id")
    telefone = status_data.get("recipient_id", "")

    if not message_id:
        return

    try:
        if status in ("sent", "delivered", "read"):
            await atualizar_delivery_status(
                provider_message_id=message_id,
                status=status,
                chip_id=chip["id"],
            )

        elif status == "failed":
            errors = status_data.get("errors", [])
            error_msg = errors[0].get("message", "Unknown") if errors else "Unknown"
            error_code = errors[0].get("code", 0) if errors else 0

            logger.warning(
                f"[WebhookMeta] Envio falhou: {message_id[:12]}... "
                f"code={error_code}, msg={error_msg}"
            )

            await atualizar_delivery_status(
                provider_message_id=message_id,
                status="failed",
                chip_id=chip["id"],
            )

    except Exception as e:
        logger.error(f"[WebhookMeta] Erro ao processar status: {e}")

    logger.debug(
        f"[WebhookMeta] Status: {message_id[:12]}... -> {status} "
        f"(chip={chip.get('telefone', 'N/A')[-4:]})"
    )


async def _processar_template_status(value: dict) -> None:
    """
    Processa atualização de status de template (APPROVED, REJECTED, etc).

    Atualiza tabela meta_templates.
    """
    event = value.get("event")
    template_name = value.get("message_template_name")
    template_language = value.get("message_template_language", "pt_BR")
    template_id = value.get("message_template_id")

    if not template_name:
        return

    logger.info(
        f"[WebhookMeta] Template status: {template_name} -> {event}"
    )

    try:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        update_data = {
            "status": event,
            "updated_at": now,
        }

        if template_id:
            update_data["meta_template_id"] = str(template_id)

        if event == "APPROVED":
            update_data["approved_at"] = now
        elif event == "REJECTED":
            update_data["rejected_at"] = now
            reason = value.get("reason")
            if reason:
                update_data["rejection_reason"] = reason

        supabase.table("meta_templates").update(update_data).eq(
            "template_name", template_name
        ).eq("language", template_language).execute()

    except Exception as e:
        logger.error(
            f"[WebhookMeta] Erro ao atualizar template status: {e}"
        )
