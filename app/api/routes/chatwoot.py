"""
Endpoints de webhook para integracao Chatwoot.

IMPORTANTE: A integracao nativa Evolution API <-> Chatwoot ja faz
a sincronizacao de mensagens/contatos/conversas. Este webhook e
apenas para logica de negocio (handoff via labels).
"""

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import logging

from app.services.supabase import supabase
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
        labels = [label.get("title", label.get("name", "")) for label in labels]

    if not chatwoot_conversation_id:
        logger.warning(f"Payload sem conversation.id. Keys: {list(payload.keys())}")
        return

    logger.info(f"Conversa {chatwoot_conversation_id} atualizada, labels: {labels}")

    # Buscar nossa conversa pelo chatwoot_conversation_id
    response = (
        supabase.table("conversations")
        .select("*, clientes(*)")
        .eq("chatwoot_conversation_id", str(chatwoot_conversation_id))
        .execute()
    )

    if not response.data:
        logger.warning(f"Conversa nao encontrada para chatwoot_id: {chatwoot_conversation_id}")
        return

    conversa = response.data[0]
    controlled_by = conversa.get("controlled_by")

    # Label "humano" presente -> handoff
    if "humano" in labels:
        if controlled_by != "human":
            logger.info("Label 'humano' detectada, iniciando handoff...")
            await iniciar_handoff(
                conversa_id=conversa["id"],
                cliente_id=conversa["cliente_id"],
                motivo="Label 'humano' adicionada no Chatwoot",
                trigger_type="manual",
            )
        else:
            logger.debug("Conversa ja esta sob controle humano")

    # Label "humano" removida -> voltar para IA
    elif controlled_by == "human":
        logger.info("Label 'humano' removida, finalizando handoff...")
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


@router.get("/test-api")
async def chatwoot_test_api():
    """
    Testa conectividade com API do Chatwoot.

    Util para verificar se a API key esta funcionando.
    """
    import httpx
    from app.services.chatwoot import chatwoot_service

    if not chatwoot_service.configurado:
        return {"status": "error", "message": "Chatwoot nao configurado"}

    # Testar endpoint de profile (valida API key)
    url = f"{chatwoot_service.base_url}/api/v1/profile"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=chatwoot_service.headers)

            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "ok",
                    "api_key_valid": True,
                    "user": data.get("name", "Unknown"),
                    "email": data.get("email", "Unknown"),
                    "account_id": chatwoot_service.account_id,
                }
            elif response.status_code == 401:
                return {
                    "status": "error",
                    "api_key_valid": False,
                    "message": "API key invalida. Regenere em Profile Settings > Access Token no Chatwoot.",
                    "chatwoot_url": chatwoot_service.base_url,
                }
            else:
                return {
                    "status": "error",
                    "http_status": response.status_code,
                    "message": response.text,
                }
    except httpx.ConnectError:
        return {
            "status": "error",
            "message": f"Nao foi possivel conectar ao Chatwoot em {chatwoot_service.base_url}",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/sync/{telefone}")
async def chatwoot_sync_ids(telefone: str):
    """
    Sincroniza IDs do Chatwoot para um telefone.

    Util para testar se a sincronizacao esta funcionando apos
    corrigir a API key.

    Args:
        telefone: Telefone no formato 5511999999999
    """
    from app.services.chatwoot import sincronizar_ids_chatwoot

    # Buscar cliente pelo telefone
    response = (
        supabase.table("clientes")
        .select("id, telefone, primeiro_nome")
        .eq("telefone", telefone)
        .execute()
    )

    if not response.data:
        return {"status": "error", "message": f"Cliente nao encontrado com telefone {telefone}"}

    cliente = response.data[0]

    # Sincronizar IDs
    resultado = await sincronizar_ids_chatwoot(cliente["id"], telefone)

    return {
        "status": "ok" if resultado.get("chatwoot_conversation_id") else "partial",
        "cliente": {
            "id": cliente["id"],
            "nome": cliente.get("primeiro_nome", "N/A"),
            "telefone": telefone,
        },
        "chatwoot": resultado,
    }
