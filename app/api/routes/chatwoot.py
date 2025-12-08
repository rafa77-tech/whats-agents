"""
Endpoints de webhook para integracao Chatwoot.

IMPORTANTE: A integracao nativa Evolution API <-> Chatwoot ja faz
a sincronizacao de mensagens/contatos/conversas. Este webhook e
apenas para logica de negocio (handoff via labels).
"""
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import logging

from app.services.supabase import get_supabase
from app.services.handoff import iniciar_handoff, finalizar_handoff

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chatwoot", tags=["Chatwoot"])


@router.post("/webhook")
async def chatwoot_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Recebe webhooks do Chatwoot.

    Eventos processados:
    - conversation_updated: Detecta label "humano" para handoff

    NOTA: Mensagens e contatos sao sincronizados pela integracao
    nativa Evolution API <-> Chatwoot. Este webhook e apenas para
    logica de negocio (handoff).
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON invalido")

    event = payload.get("event")
    logger.info(f"Webhook Chatwoot recebido: {event}")

    if event == "conversation_updated":
        background_tasks.add_task(processar_conversation_updated, payload)

    return JSONResponse({"status": "ok"})


async def processar_conversation_updated(payload: dict):
    """
    Processa atualizacao de conversa.

    - Label "humano" adicionada -> iniciar handoff
    - Label "humano" removida -> finalizar handoff
    """
    # Log payload para debug (INFO temporariamente para diagnostico)
    logger.info(f"Payload conversation_updated keys: {list(payload.keys())}")

    # Chatwoot pode enviar como "conversation" ou diretamente no payload
    conversation = payload.get("conversation") or payload
    labels = conversation.get("labels", [])
    chatwoot_conversation_id = conversation.get("id")

    # Extrair labels (pode vir como lista de strings ou objetos)
    if labels and isinstance(labels[0], dict):
        labels = [l.get("title", l.get("name", "")) for l in labels]

    if not chatwoot_conversation_id:
        logger.warning(f"Payload sem conversation.id. Keys: {list(payload.keys())}")
        return

    logger.info(
        f"Conversa {chatwoot_conversation_id} atualizada, labels: {labels}"
    )

    supabase = get_supabase()

    # Buscar nossa conversa pelo chatwoot_conversation_id
    response = (
        supabase.table("conversations")
        .select("*, clientes(*)")
        .eq("chatwoot_conversation_id", str(chatwoot_conversation_id))
        .execute()
    )

    if not response.data:
        logger.warning(
            f"Conversa nao encontrada para chatwoot_id: {chatwoot_conversation_id}"
        )
        return

    conversa = response.data[0]
    controlled_by = conversa.get("controlled_by")

    # Label "humano" presente -> handoff
    if "humano" in labels:
        if controlled_by != "human":
            logger.info(f"Label 'humano' detectada, iniciando handoff...")
            await iniciar_handoff(
                conversa_id=conversa["id"],
                cliente_id=conversa["cliente_id"],
                motivo="Label 'humano' adicionada no Chatwoot",
                trigger_type="manual"
            )
        else:
            logger.debug("Conversa ja esta sob controle humano")

    # Label "humano" removida -> voltar para IA
    elif controlled_by == "human":
        logger.info(f"Label 'humano' removida, finalizando handoff...")
        await finalizar_handoff(conversa["id"])


@router.get("/status")
async def chatwoot_status():
    """Verifica status da integracao Chatwoot."""
    from app.services.chatwoot import chatwoot_service

    return {
        "configurado": chatwoot_service.configurado,
        "base_url": chatwoot_service.base_url if chatwoot_service.configurado else None,
        "account_id": chatwoot_service.account_id if chatwoot_service.configurado else None,
    }
