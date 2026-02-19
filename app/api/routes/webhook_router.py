"""
Webhook Router - Roteamento multi-chip.

Sprint 26 - E03
Sprint 36 - T08.2: Registrar resposta recebida por chip

Recebe webhooks de multiplas instancias Evolution
e roteia para o processamento correto.
"""

from fastapi import APIRouter, Request, HTTPException, Header
import logging
from datetime import datetime, timezone
from typing import Optional

from app.services.supabase import supabase
from app.services.chips.selector import chip_selector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/evolution", tags=["evolution-multichip"])


@router.post("/{instance_name}")
async def webhook_evolution(instance_name: str, request: Request):
    """
    Recebe webhook de uma instancia Evolution.

    O instance_name identifica qual chip recebeu a mensagem.

    Args:
        instance_name: Nome da instancia (ex: julia-99999999)
        request: Request com payload do evento

    Returns:
        {"status": "ok"} ou erro
    """
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"[WebhookRouter] Erro ao parsear JSON: {e}")
        raise HTTPException(400, "Invalid JSON")

    event_type = payload.get("event")

    logger.debug(f"[WebhookRouter] {instance_name}: {event_type}")

    # Buscar chip pelo instance_name
    chip = await chip_selector.obter_chip_por_instance(instance_name)

    if not chip:
        logger.warning(f"[WebhookRouter] Instancia desconhecida: {instance_name}")
        # Nao retornar erro para nao quebrar Evolution
        return {"status": "ignored", "reason": "unknown_instance"}

    # Verificar se chip esta em status valido
    if chip["status"] not in ["active", "warming"]:
        logger.warning(
            f"[WebhookRouter] Chip {instance_name} nao esta ativo "
            f"(status={chip['status']}). Evento sera ignorado para processamento."
        )
        # Ainda atualiza metricas mas nao processa para Julia
        chip["_ignore_processing"] = True

    # Rotear por tipo de evento
    if event_type == "messages.upsert":
        return await processar_mensagem_recebida(chip, payload)

    elif event_type == "connection.update":
        return await processar_conexao(chip, payload)

    elif event_type == "messages.update":
        return await processar_status_mensagem(chip, payload)

    elif event_type == "qrcode.updated":
        return await processar_qr_code(chip, payload)

    else:
        logger.debug(f"[WebhookRouter] Evento ignorado: {event_type}")
        return {"status": "ignored", "event": event_type}


@router.post("/")
async def webhook_evolution_unified(
    request: Request,
    x_instance_name: Optional[str] = Header(None, alias="X-Instance-Name"),
):
    """
    Endpoint unificado que recebe de qualquer instancia.

    A instancia e identificada pelo header X-Instance-Name.
    """
    if not x_instance_name:
        raise HTTPException(400, "Missing X-Instance-Name header")

    # Reutilizar logica do endpoint com path
    return await webhook_evolution(x_instance_name, request)


async def processar_mensagem_recebida(chip: dict, payload: dict) -> dict:
    """
    Processa mensagem recebida no chip.

    Sprint 36 - T08.2: Usa RPC para registrar métricas e conversas bidirecionais.

    Fluxo:
    1. Extrair dados da mensagem
    2. Registrar resposta via RPC (atualiza métricas + conversas bidirecionais)
    3. Se chip ativo, enviar para pipeline Julia
    """
    data = payload.get("data", {})
    message = data.get("message", {})
    key = data.get("key", {})

    # Ignorar mensagens proprias
    if key.get("fromMe"):
        return {"status": "ignored", "reason": "from_me"}

    # Extrair telefone
    remote_jid = key.get("remoteJid", "")
    telefone = remote_jid.split("@")[0]

    # Ignorar broadcasts
    if "@broadcast" in remote_jid:
        return {"status": "ignored", "reason": "broadcast"}

    # Interceptar mensagens de grupo para extração de vagas
    if "@g.us" in remote_jid:
        try:
            from app.services.parser import parsear_mensagem
            from app.services.grupos.ingestor import ingerir_mensagem_grupo

            mensagem = parsear_mensagem(data)
            if mensagem:
                mensagem_id = await ingerir_mensagem_grupo(
                    mensagem, data, instance_name=chip["instance_name"]
                )
                logger.info(
                    f"[WebhookRouter] Grupo ingerido via chip {chip['telefone']}: {mensagem_id}"
                )
        except Exception as e:
            logger.error(f"[WebhookRouter] Erro ingestão grupo: {e}", exc_info=True)

        return {"status": "ok", "reason": "group_ingested"}

    # Extrair tipo de midia
    tipo_midia = "text"
    if message.get("imageMessage"):
        tipo_midia = "image"
    elif message.get("audioMessage"):
        tipo_midia = "audio"
    elif message.get("videoMessage"):
        tipo_midia = "video"
    elif message.get("documentMessage"):
        tipo_midia = "document"
    elif message.get("stickerMessage"):
        tipo_midia = "sticker"

    # Sprint 36 - T08.2: Usar RPC para registrar métricas e conversas bidirecionais
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
                f"[WebhookRouter] Conversa bidirecional detectada: "
                f"chip={chip['telefone'][-4:]}, remetente={telefone[-4:]}"
            )

    except Exception as e:
        logger.warning(f"[WebhookRouter] Erro ao registrar resposta via RPC: {e}")
        # Fallback: registrar manualmente
        try:
            supabase.table("chip_interactions").insert(
                {
                    "chip_id": chip["id"],
                    "tipo": "msg_recebida",
                    "remetente": telefone,
                    "metadata": {"tipo_midia": tipo_midia},
                }
            ).execute()

            # Atualizar contadores manualmente
            chip_data = (
                supabase.table("chips")
                .select("msgs_recebidas_total")
                .eq("id", chip["id"])
                .single()
                .execute()
            )

            if chip_data.data:
                supabase.table("chips").update(
                    {
                        "msgs_recebidas_total": (chip_data.data.get("msgs_recebidas_total") or 0)
                        + 1,
                    }
                ).eq("id", chip["id"]).execute()
        except Exception as e2:
            logger.error(f"[WebhookRouter] Erro no fallback de métricas: {e2}")

    # Se chip nao deve processar, parar aqui
    if chip.get("_ignore_processing"):
        return {"status": "ok", "processed": False}

    # Para chips ativos, delegar ao pipeline principal
    # O payload original segue para /webhook/evolution existente
    # Aqui apenas registramos metricas e adicionamos contexto

    logger.info(f"[WebhookRouter] Mensagem de {telefone} recebida por chip {chip['telefone']}")

    return {"status": "ok", "processed": True, "chip": chip["telefone"]}


async def processar_conexao(chip: dict, payload: dict) -> dict:
    """
    Atualiza status de conexao do chip.
    """
    state = payload.get("data", {}).get("state")
    connected = state == "open"

    supabase.table("chips").update(
        {
            "evolution_connected": connected,
        }
    ).eq("id", chip["id"]).execute()

    if not connected:
        logger.warning(f"[WebhookRouter] Chip desconectado: {chip['telefone']}")

        # Criar alerta
        supabase.table("chip_alerts").insert(
            {
                "chip_id": chip["id"],
                "severity": "warning",
                "tipo": "connection_lost",
                "message": f"Chip {chip['telefone']} desconectado",
            }
        ).execute()

    else:
        logger.info(f"[WebhookRouter] Chip conectado: {chip['telefone']}")

        # Resolver alertas de conexao
        supabase.table("chip_alerts").update(
            {
                "resolved": True,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
                "resolved_by": "auto",
            }
        ).eq("chip_id", chip["id"]).eq("tipo", "connection_lost").eq("resolved", False).execute()

    return {"status": "ok", "connected": connected}


async def processar_status_mensagem(chip: dict, payload: dict) -> dict:
    """
    Processa atualizacao de status de mensagem (entregue, lido, etc).

    Sprint 41: Atualiza delivery_status na tabela interacoes.
    """
    from app.services.delivery_status import atualizar_delivery_status

    data = payload.get("data", {})
    status = data.get("status")
    key = data.get("key", {})

    # Extrair telefone e message_id
    remote_jid = key.get("remoteJid", "")
    telefone = remote_jid.split("@")[0]
    message_id = key.get("id")

    if status == "DELIVERY_ACK":
        # Mensagem entregue
        supabase.table("chip_interactions").insert(
            {
                "chip_id": chip["id"],
                "tipo": "msg_entregue",
                "destinatario": telefone,
            }
        ).execute()

        # Sprint 41: Atualizar delivery_status na interação
        if message_id:
            await atualizar_delivery_status(
                provider_message_id=message_id,
                status="delivered",
                chip_id=chip["id"],
            )

    elif status == "READ":
        # Mensagem lida
        supabase.table("chip_interactions").insert(
            {
                "chip_id": chip["id"],
                "tipo": "msg_lida",
                "destinatario": telefone,
            }
        ).execute()

        # Sprint 41: Atualizar delivery_status na interação
        if message_id:
            await atualizar_delivery_status(
                provider_message_id=message_id,
                status="read",
                chip_id=chip["id"],
            )

    return {"status": "ok", "message_status": status}


async def processar_qr_code(chip: dict, payload: dict) -> dict:
    """
    Processa QR Code atualizado (para conexao inicial).
    """
    qr = payload.get("data", {}).get("qrcode", {}).get("base64")

    if qr:
        supabase.table("chips").update(
            {
                "evolution_qr_code": qr,
            }
        ).eq("id", chip["id"]).execute()

        logger.info(f"[WebhookRouter] QR Code atualizado para {chip['telefone']}")

    return {"status": "ok"}
