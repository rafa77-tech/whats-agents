"""
Webhook Router para Z-API.

Sprint 27 - Suporte multi-provider (Z-API).

Recebe webhooks da Z-API e roteia para o processamento correto.
Docs: https://developer.z-api.io/en/webhooks
"""

import time
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
import logging
from datetime import datetime, timezone
from typing import Optional

from app.services.supabase import supabase
from app.services.redis import cache_get_json, cache_set_json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/zapi", tags=["zapi-webhook"])


@router.post("")
@router.post("/")
async def webhook_zapi(request: Request, background_tasks: BackgroundTasks):
    """
    Recebe webhooks da Z-API.

    Eventos suportados:
    - ReceivedCallback: Mensagem recebida
    - MessageStatusCallback: Status de mensagem (enviada, entregue, lida)
    - StatusInstanceCallback: Status da conexão

    Returns:
        {"status": "ok"} ou erro
    """
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"[WebhookZAPI] Erro ao parsear JSON: {e}")
        raise HTTPException(400, "Invalid JSON")

    # Z-API não envia um campo "event" como Evolution
    # Identificamos pelo conteúdo do payload
    event_type = _identificar_tipo_evento(payload)

    logger.info(f"[WebhookZAPI] Evento recebido: {event_type}")
    logger.debug(f"[WebhookZAPI] Payload: {payload}")

    # Buscar chip pelo instance_id
    instance_id = payload.get("instanceId")
    chip = await _obter_chip_por_zapi_instance(instance_id)

    if not chip:
        logger.warning(f"[WebhookZAPI] Instance desconhecida: {instance_id}")
        return {"status": "ignored", "reason": "unknown_instance"}

    # Rotear por tipo de evento
    if event_type == "received":
        return await processar_mensagem_recebida(chip, payload, background_tasks)

    elif event_type == "message_status":
        return await processar_status_mensagem(chip, payload)

    elif event_type == "connection_status":
        return await processar_conexao(chip, payload)

    elif event_type == "chat_presence":
        return await processar_presenca_chat(chip, payload)

    elif event_type == "delivery":
        return await processar_delivery(chip, payload)

    else:
        logger.debug(f"[WebhookZAPI] Evento ignorado: {event_type}")
        return {"status": "ignored", "event": event_type}


def _identificar_tipo_evento(payload: dict) -> str:
    """
    Identifica o tipo de evento Z-API pelo conteúdo do payload.

    Z-API não envia campo "event" - identificamos pela estrutura.
    Ou usa o campo "type" se presente (callbacks padronizados).
    """
    # Z-API callbacks padronizados usam campo "type"
    callback_type = payload.get("type", "")

    if callback_type == "ReceivedCallback":
        return "received"
    elif callback_type == "DeliveryCallback":
        return "delivery"
    elif callback_type == "MessageStatusCallback":
        return "message_status"
    elif callback_type == "PresenceChatCallback":
        return "chat_presence"
    elif callback_type == "DisconnectedCallback":
        return "connection_status"

    # Fallback: identificar pela estrutura do payload
    # Mensagem recebida tem phone e text/image/etc
    if payload.get("phone") and (
        payload.get("text") or
        payload.get("image") or
        payload.get("audio") or
        payload.get("video") or
        payload.get("document")
    ):
        # Verificar se é mensagem própria (enviada) ou recebida
        if payload.get("fromMe"):
            return "message_sent"
        return "received"

    # Status de mensagem tem status field
    if payload.get("status") and payload.get("id"):
        return "message_status"

    # Status de conexão tem connected field ou disconnected
    if "connected" in payload or "smartphoneConnected" in payload or payload.get("disconnected"):
        return "connection_status"

    return "unknown"


async def _obter_chip_por_zapi_instance(instance_id: str) -> Optional[dict]:
    """
    Busca chip pelo instance_id da Z-API.

    O instance_id está armazenado no campo zapi_instance_id.
    """
    if not instance_id:
        return None

    try:
        # Buscar por zapi_instance_id
        result = supabase.table("chips").select("*").eq(
            "zapi_instance_id", instance_id
        ).execute()

        if result.data:
            return result.data[0]

        # Fallback: buscar por provider z-api e verificar manualmente
        result = supabase.table("chips").select("*").eq(
            "provider", "z-api"
        ).execute()

        for chip in result.data or []:
            if chip.get("zapi_instance_id") == instance_id:
                return chip

        return None

    except Exception as e:
        logger.error(f"[WebhookZAPI] Erro ao buscar chip: {e}")
        return None


async def processar_mensagem_recebida(chip: dict, payload: dict, background_tasks: BackgroundTasks) -> dict:
    """
    Processa mensagem recebida no chip via Z-API.

    Payload Z-API:
    {
        "phone": "5511999999999",
        "text": {"message": "Olá"},
        "fromMe": false,
        "momment": 1612345678,
        "messageId": "xxxxx",
        "instanceId": "xxxxx"
    }
    """
    # Ignorar mensagens próprias
    if payload.get("fromMe"):
        return {"status": "ignored", "reason": "from_me"}

    # Extrair telefone
    telefone = payload.get("phone", "").replace("@c.us", "")

    # Ignorar grupos
    if payload.get("isGroup"):
        return {"status": "ignored", "reason": "group"}

    # Extrair message_id para deduplicação
    message_id = payload.get("messageId")
    if message_id:
        # Verificar se já foi processado
        cached = await cache_get_json(f"zapi:msg:{message_id}")
        if cached:
            logger.debug(f"[WebhookZAPI] Mensagem {message_id} já processada, ignorando")
            return {"status": "ignored", "reason": "duplicate"}

        # Marcar como processada
        await cache_set_json(f"zapi:msg:{message_id}", {"processed": True}, ttl=300)

    # Extrair tipo de mídia e conteúdo
    tipo_midia = "text"
    texto_mensagem = ""

    if payload.get("text"):
        tipo_midia = "text"
        texto_mensagem = payload.get("text", {}).get("message", "")
    elif payload.get("image"):
        tipo_midia = "image"
        texto_mensagem = payload.get("image", {}).get("caption", "")
    elif payload.get("audio"):
        tipo_midia = "audio"
    elif payload.get("video"):
        tipo_midia = "video"
        texto_mensagem = payload.get("video", {}).get("caption", "")
    elif payload.get("document"):
        tipo_midia = "document"
    elif payload.get("sticker"):
        tipo_midia = "sticker"

    # Registrar métricas via RPC
    try:
        result = supabase.rpc(
            "chip_registrar_resposta",
            {
                "p_chip_id": chip["id"],
                "p_telefone_remetente": telefone,
            },
        ).execute()

        foi_bidirecional = result.data.get("foi_bidirecional", False) if result.data else False

        if foi_bidirecional:
            logger.info(
                f"[WebhookZAPI] Conversa bidirecional detectada: "
                f"chip={chip['telefone'][-4:]}, remetente={telefone[-4:]}"
            )

    except Exception as e:
        logger.warning(f"[WebhookZAPI] Erro ao registrar resposta via RPC: {e}")
        # Fallback: registrar manualmente
        try:
            supabase.table("chip_interactions").insert({
                "chip_id": chip["id"],
                "tipo": "msg_recebida",
                "remetente": telefone,
                "sucesso": True,
                "metadata": {"tipo_midia": tipo_midia, "provider": "zapi"},
            }).execute()
        except Exception as e2:
            logger.error(f"[WebhookZAPI] Erro no fallback de métricas: {e2}")

    # Verificar se chip está ativo para processamento
    if chip.get("status") not in ["active", "warming"]:
        logger.warning(
            f"[WebhookZAPI] Chip {chip['telefone']} não está ativo "
            f"(status={chip.get('status')})"
        )
        return {"status": "ok", "processed": False}

    logger.info(
        f"[WebhookZAPI] Mensagem de {telefone} recebida por chip {chip['telefone']}"
    )

    # Converter payload Z-API para formato Evolution (compatível com pipeline)
    evolution_data = _converter_para_formato_evolution(payload, chip)
    logger.debug(f"[WebhookZAPI] Payload convertido: {evolution_data}")

    # Rotear para o pipeline da Julia em background
    background_tasks.add_task(_processar_no_pipeline, evolution_data)
    logger.info(f"[WebhookZAPI] Mensagem '{texto_mensagem[:50]}...' agendada para pipeline")

    return {"status": "ok", "processed": True, "chip": chip["telefone"]}


def _converter_para_formato_evolution(payload: dict, chip: dict) -> dict:
    """
    Converte payload Z-API para formato Evolution API.

    Isso permite reutilizar o pipeline existente que espera formato Evolution.
    """
    telefone = payload.get("phone", "").replace("@c.us", "")

    # Extrair texto da mensagem
    texto = ""
    if payload.get("text"):
        texto = payload.get("text", {}).get("message", "")
    elif payload.get("image"):
        texto = payload.get("image", {}).get("caption", "")
    elif payload.get("video"):
        texto = payload.get("video", {}).get("caption", "")

    # Validar message_id (obrigatório para o parser)
    message_id = payload.get("messageId", "")
    if not message_id:
        logger.warning(f"[WebhookZAPI] Payload sem messageId: {payload}")
        message_id = f"zapi_{int(time.time() * 1000)}"  # Gerar ID temporário

    # Converter timestamp: Z-API pode enviar em segundos ou milissegundos
    raw_timestamp = payload.get("momment", int(time.time()))
    # Se timestamp > 10^12, está em milissegundos - converter para segundos
    if raw_timestamp > 10**12:
        raw_timestamp = raw_timestamp // 1000

    # Formato Evolution esperado pelo pipeline
    evolution_data = {
        "key": {
            "remoteJid": f"{telefone}@s.whatsapp.net",
            "fromMe": payload.get("fromMe", False),
            "id": message_id,
        },
        "message": {
            "conversation": texto,
        },
        "messageTimestamp": raw_timestamp,
        # Nome do contato (obrigatório para o parser)
        "pushName": payload.get("senderName") or payload.get("chatName") or "",
        # Metadados extras para o pipeline saber que é Z-API
        "_evolution_instance": chip.get("instance_name", "zapi"),
        "_zapi_chip_id": chip.get("id"),
        "_zapi_telefone": chip.get("telefone"),
        "_provider": "zapi",
    }

    # Adicionar mídia se presente
    if payload.get("image"):
        evolution_data["message"]["imageMessage"] = {
            "url": payload.get("image", {}).get("imageUrl"),
            "caption": payload.get("image", {}).get("caption", ""),
        }
    elif payload.get("audio"):
        evolution_data["message"]["audioMessage"] = {
            "url": payload.get("audio", {}).get("audioUrl"),
            "ptt": payload.get("audio", {}).get("ptt", False),
        }
    elif payload.get("video"):
        evolution_data["message"]["videoMessage"] = {
            "url": payload.get("video", {}).get("videoUrl"),
            "caption": payload.get("video", {}).get("caption", ""),
        }
    elif payload.get("document"):
        evolution_data["message"]["documentMessage"] = {
            "url": payload.get("document", {}).get("documentUrl"),
            "fileName": payload.get("document", {}).get("fileName"),
        }

    return evolution_data


async def _processar_no_pipeline(data: dict):
    """
    Processa mensagem no pipeline da Julia.

    Importa o pipeline aqui para evitar circular imports.
    """
    from app.pipeline.setup import message_pipeline

    try:
        data["_tempo_inicio"] = time.time()
        result = await message_pipeline.process(data)

        if not result.success:
            logger.error(f"[WebhookZAPI] Pipeline falhou: {result.error}")
        elif result.response:
            logger.info("[WebhookZAPI] Pipeline concluído com resposta")
        else:
            logger.info("[WebhookZAPI] Pipeline concluído sem resposta")

    except Exception as e:
        logger.error(f"[WebhookZAPI] Erro no pipeline: {e}", exc_info=True)


async def processar_conexao(chip: dict, payload: dict) -> dict:
    """
    Atualiza status de conexão do chip via Z-API.

    Payload Z-API:
    {
        "connected": true,
        "smartphoneConnected": true,
        "instanceId": "xxxxx"
    }
    """
    connected = payload.get("connected", False)
    smartphone_connected = payload.get("smartphoneConnected", False)

    # Ambos precisam estar true para considerar conectado
    is_connected = connected and smartphone_connected

    try:
        supabase.table("chips").update({
            "evolution_connected": is_connected,  # Reutiliza campo existente
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", chip["id"]).execute()

        if not is_connected:
            logger.warning(f"[WebhookZAPI] Chip desconectado: {chip['telefone']}")

            # Criar alerta
            supabase.table("chip_alerts").insert({
                "chip_id": chip["id"],
                "severity": "warning",
                "tipo": "connection_lost",
                "message": f"Chip {chip['telefone']} desconectado (Z-API)",
            }).execute()

        else:
            logger.info(f"[WebhookZAPI] Chip conectado: {chip['telefone']}")

            # Resolver alertas de conexão
            supabase.table("chip_alerts").update({
                "resolved": True,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
                "resolved_by": "auto",
            }).eq(
                "chip_id", chip["id"]
            ).eq(
                "tipo", "connection_lost"
            ).eq(
                "resolved", False
            ).execute()

    except Exception as e:
        logger.error(f"[WebhookZAPI] Erro ao atualizar conexão: {e}")

    return {"status": "ok", "connected": is_connected}


async def processar_status_mensagem(chip: dict, payload: dict) -> dict:
    """
    Processa atualização de status de mensagem (entregue, lido, etc) via Z-API.

    Payload Z-API:
    {
        "id": "message_id",
        "status": "DELIVERED" | "READ" | "PLAYED",
        "phone": "5511999999999",
        "instanceId": "xxxxx"
    }
    """
    status = payload.get("status", "").upper()
    telefone = payload.get("phone", "").replace("@c.us", "")
    message_id = payload.get("id")

    try:
        if status in ["DELIVERED", "DELIVERY_ACK"]:
            supabase.table("chip_interactions").insert({
                "chip_id": chip["id"],
                "tipo": "msg_entregue",
                "destinatario": telefone,
                "metadata": {"message_id": message_id, "provider": "zapi"},
            }).execute()

        elif status in ["READ", "VIEWED"]:
            supabase.table("chip_interactions").insert({
                "chip_id": chip["id"],
                "tipo": "msg_lida",
                "destinatario": telefone,
                "metadata": {"message_id": message_id, "provider": "zapi"},
            }).execute()

        elif status == "PLAYED":
            # Áudio/vídeo reproduzido
            supabase.table("chip_interactions").insert({
                "chip_id": chip["id"],
                "tipo": "msg_reproduzida",
                "destinatario": telefone,
                "metadata": {"message_id": message_id, "provider": "zapi"},
            }).execute()

    except Exception as e:
        logger.error(f"[WebhookZAPI] Erro ao registrar status: {e}")

    return {"status": "ok", "message_status": status}


async def processar_presenca_chat(chip: dict, payload: dict) -> dict:
    """
    Processa presença no chat (digitando, online, etc) via Z-API.

    Payload Z-API:
    {
        "type": "PresenceChatCallback",
        "phone": "5511999999999",
        "status": "COMPOSING" | "AVAILABLE" | "UNAVAILABLE" | "PAUSED" | "RECORDING",
        "lastSeen": null,
        "instanceId": "xxxxx"
    }

    Status:
    - AVAILABLE: Usuário está no chat
    - UNAVAILABLE: Usuário saiu do chat
    - COMPOSING: Usuário está digitando
    - PAUSED: Parou de digitar (multi-device beta)
    - RECORDING: Gravando áudio (multi-device beta)
    """
    status = payload.get("status", "").upper()
    telefone = payload.get("phone", "").replace("@c.us", "")

    logger.debug(
        f"[WebhookZAPI] Presença: {telefone} -> {status} "
        f"(chip={chip['telefone'][-4:]})"
    )

    # Registrar presença se for digitando ou gravando (indicativo de engajamento)
    if status in ["COMPOSING", "RECORDING"]:
        try:
            supabase.table("chip_interactions").insert({
                "chip_id": chip["id"],
                "tipo": "presenca_digitando" if status == "COMPOSING" else "presenca_gravando",
                "remetente": telefone,
                "metadata": {"status": status, "provider": "zapi"},
            }).execute()
        except Exception as e:
            logger.debug(f"[WebhookZAPI] Erro ao registrar presença: {e}")

    return {"status": "ok", "presence": status}


async def processar_delivery(chip: dict, payload: dict) -> dict:
    """
    Processa confirmação de envio de mensagem via Z-API.

    Payload Z-API:
    {
        "type": "DeliveryCallback",
        "phone": "5511999999999",
        "zaapId": "A20DA9C0183A2D35A260F53F5D2B9244",
        "messageId": "A20DA9C0183A2D35A260F53F5D2B9244",
        "instanceId": "xxxxx"
    }
    """
    telefone = payload.get("phone", "").replace("@c.us", "")
    message_id = payload.get("messageId")

    logger.debug(
        f"[WebhookZAPI] Delivery confirmado: {message_id} -> {telefone} "
        f"(chip={chip['telefone'][-4:]})"
    )

    try:
        supabase.table("chip_interactions").insert({
            "chip_id": chip["id"],
            "tipo": "msg_enviada_confirmada",
            "destinatario": telefone,
            "metadata": {"message_id": message_id, "provider": "zapi"},
        }).execute()
    except Exception as e:
        logger.debug(f"[WebhookZAPI] Erro ao registrar delivery: {e}")

    return {"status": "ok", "delivered": True}
