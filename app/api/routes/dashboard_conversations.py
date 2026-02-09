"""
Dashboard Conversations API - Endpoints para envio de mensagens do dashboard.

Sprint 43 - UX & Operacao Unificada
Sprint 54 - Supervision Dashboard (pause, notes, feedback)

Endpoints para:
- Enviar mensagens de texto via WhatsApp
- Enviar midia (imagem, audio, documento) via WhatsApp
- Controle de conversas (handoff)
- Pausar/retomar Julia (Sprint 54)
- Notas do supervisor (Sprint 54)
- Feedback em mensagens (Sprint 54)
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.services.supabase import supabase
from app.services.chips.sender import enviar_via_chip, enviar_media_via_chip
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard/conversations", tags=["dashboard-conversations"])


class SendTextRequest(BaseModel):
    """Request para enviar mensagem de texto."""
    conversation_id: str
    message: str


class SendMediaRequest(BaseModel):
    """Request para enviar midia."""
    conversation_id: str
    media_url: str
    media_type: str  # image, audio, document, video
    caption: Optional[str] = None


class ControlRequest(BaseModel):
    """Request para alterar controle da conversa."""
    controlled_by: str  # ai ou human


class PauseRequest(BaseModel):
    """Request para pausar Julia na conversa."""
    motivo: Optional[str] = None


class NoteRequest(BaseModel):
    """Request para criar nota do supervisor."""
    content: str


class FeedbackRequest(BaseModel):
    """Request para feedback em mensagem."""
    interacao_id: int
    feedback_type: str  # positive ou negative
    comment: Optional[str] = None


async def _get_conversation_with_chip(conversation_id: str) -> dict:
    """
    Busca conversa com informacoes do chip associado.

    Returns:
        Dict com conversa, cliente e chip
    """
    # Buscar conversa
    conv_result = supabase.table("conversations").select(
        "*, clientes(*)"
    ).eq("id", conversation_id).single().execute()

    if not conv_result.data:
        raise HTTPException(404, "Conversa nao encontrada")

    conversation = conv_result.data
    cliente = conversation.get("clientes", {})

    # Buscar chip associado via conversation_chips
    # Nota: conversation_chips tem 2 FKs para chips (chip_id e migrated_from),
    # entao precisamos especificar qual usar.
    # A coluna eh 'conversa_id', nao 'conversation_id'.
    chip_result = supabase.table("conversation_chips").select(
        "chip_id, chips!conversation_chips_chip_id_fkey(*)"
    ).eq("conversa_id", conversation_id).eq(
        "active", True
    ).limit(1).execute()

    chip = None
    if chip_result.data and chip_result.data[0].get("chips"):
        chip = chip_result.data[0]["chips"]

    # Se nao tem chip associado, buscar um chip ativo
    if not chip:
        active_chip = supabase.table("chips").select("*").eq(
            "status", "active"
        ).limit(1).execute()

        if active_chip.data:
            chip = active_chip.data[0]

    if not chip:
        raise HTTPException(503, "Nenhum chip disponivel para envio")

    return {
        "conversation": conversation,
        "cliente": cliente,
        "chip": chip,
    }


async def _record_interaction(
    conversation_id: str,
    cliente_id: str,
    conteudo: str,
    tipo: str = "saida",
    tipo_midia: Optional[str] = None,
    media_url: Optional[str] = None,
) -> dict:
    """Registra interacao no banco."""
    data = {
        "conversation_id": conversation_id,
        "cliente_id": cliente_id,
        "origem": "dashboard",
        "tipo": tipo,
        "canal": "whatsapp",
        "conteudo": conteudo,
        "autor_nome": "Operador",
        "autor_tipo": "operador",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if tipo_midia:
        data["metadata"] = {
            "tipo_midia": tipo_midia,
            "media_url": media_url,
        }

    result = supabase.table("interacoes").insert(data).execute()
    return result.data[0] if result.data else {}


@router.post("/send-text")
async def send_text_message(request: SendTextRequest):
    """
    Envia mensagem de texto via WhatsApp.

    A mensagem e enviada pelo chip associado a conversa.
    """
    try:
        # Buscar conversa e chip
        data = await _get_conversation_with_chip(request.conversation_id)
        conversation = data["conversation"]
        cliente = data["cliente"]
        chip = data["chip"]

        # Verificar se esta em modo handoff
        if conversation.get("controlled_by") != "human":
            raise HTTPException(403, "Conversa nao esta em modo handoff")

        telefone = cliente.get("telefone")
        if not telefone:
            raise HTTPException(400, "Cliente sem telefone cadastrado")

        # Enviar via chip
        result = await enviar_via_chip(chip, telefone, request.message)

        if not result.success:
            logger.error(f"Falha ao enviar mensagem: {result.error}")
            raise HTTPException(500, f"Falha ao enviar: {result.error}")

        # Registrar interacao
        # Usar cliente_id da conversa diretamente, mais confiavel que o join
        cliente_id = conversation.get("cliente_id") or cliente.get("id")
        if not cliente_id:
            logger.error(f"cliente_id nao encontrado para conversa {request.conversation_id}")
            raise HTTPException(500, "Cliente nao encontrado para esta conversa")

        interacao = await _record_interaction(
            conversation_id=request.conversation_id,
            cliente_id=cliente_id,
            conteudo=request.message,
        )

        # Atualizar last_message_at
        supabase.table("conversations").update({
            "last_message_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", request.conversation_id).execute()

        logger.info(
            f"Mensagem enviada: conv={request.conversation_id}, "
            f"chip={chip.get('telefone', 'N/A')[-4:]}"
        )

        return {
            "success": True,
            "message_id": result.message_id,
            "interacao_id": interacao.get("id"),
            "chip_id": chip.get("id"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")


@router.post("/send-media")
async def send_media_message(request: SendMediaRequest):
    """
    Envia midia via WhatsApp.

    Tipos suportados: image, audio, document, video
    """
    try:
        # Buscar conversa e chip
        data = await _get_conversation_with_chip(request.conversation_id)
        conversation = data["conversation"]
        cliente = data["cliente"]
        chip = data["chip"]

        # Verificar se esta em modo handoff
        if conversation.get("controlled_by") != "human":
            raise HTTPException(403, "Conversa nao esta em modo handoff")

        telefone = cliente.get("telefone")
        if not telefone:
            raise HTTPException(400, "Cliente sem telefone cadastrado")

        # Enviar midia via chip
        result = await enviar_media_via_chip(
            chip=chip,
            telefone=telefone,
            media_url=request.media_url,
            caption=request.caption,
            media_type=request.media_type,
        )

        if not result.success:
            logger.error(f"Falha ao enviar midia: {result.error}")
            raise HTTPException(500, f"Falha ao enviar: {result.error}")

        # Registrar interacao
        # Usar cliente_id da conversa diretamente, mais confiavel que o join
        cliente_id = conversation.get("cliente_id") or cliente.get("id")
        if not cliente_id:
            logger.error(f"cliente_id nao encontrado para conversa {request.conversation_id}")
            raise HTTPException(500, "Cliente nao encontrado para esta conversa")

        conteudo = request.caption or f"[{request.media_type}]"
        interacao = await _record_interaction(
            conversation_id=request.conversation_id,
            cliente_id=cliente_id,
            conteudo=conteudo,
            tipo_midia=request.media_type,
            media_url=request.media_url,
        )

        # Atualizar last_message_at
        supabase.table("conversations").update({
            "last_message_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", request.conversation_id).execute()

        logger.info(
            f"Midia enviada: conv={request.conversation_id}, "
            f"tipo={request.media_type}, chip={chip.get('telefone', 'N/A')[-4:]}"
        )

        return {
            "success": True,
            "message_id": result.message_id,
            "interacao_id": interacao.get("id"),
            "chip_id": chip.get("id"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao enviar midia: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")


@router.post("/{conversation_id}/control")
async def change_control(conversation_id: str, request: ControlRequest):
    """
    Altera o controle da conversa entre AI e humano.
    """
    if request.controlled_by not in ("ai", "human"):
        raise HTTPException(400, "controlled_by deve ser 'ai' ou 'human'")

    try:
        result = supabase.table("conversations").update({
            "controlled_by": request.controlled_by,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", conversation_id).execute()

        if not result.data:
            raise HTTPException(404, "Conversa nao encontrada")

        logger.info(f"Controle alterado: conv={conversation_id}, para={request.controlled_by}")

        return {
            "success": True,
            "controlled_by": request.controlled_by,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao alterar controle: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")


@router.get("/{conversation_id}")
async def get_conversation_details(conversation_id: str):
    """
    Retorna detalhes da conversa incluindo chip associado.
    """
    try:
        data = await _get_conversation_with_chip(conversation_id)

        conversation = data["conversation"]
        cliente = data["cliente"]
        chip = data["chip"]

        # Buscar mensagens
        msgs = supabase.table("interacoes").select(
            "id, tipo, conteudo, created_at, metadata"
        ).eq(
            "cliente_id", cliente.get("id")
        ).order("created_at", desc=False).limit(100).execute()

        return {
            "id": conversation.get("id"),
            "status": conversation.get("status"),
            "controlled_by": conversation.get("controlled_by"),
            "cliente": {
                "id": cliente.get("id"),
                "nome": cliente.get("nome"),
                "telefone": cliente.get("telefone"),
            },
            "chip": {
                "id": chip.get("id"),
                "telefone": chip.get("telefone"),
                "instance_name": chip.get("instance_name"),
            } if chip else None,
            "messages": msgs.data or [],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar conversa: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")


# ============================================
# Sprint 54: Supervision Endpoints
# ============================================


@router.post("/{conversation_id}/pause")
async def pause_conversation(conversation_id: str, request: PauseRequest):
    """Pausa Julia na conversa."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        result = supabase.table("conversations").update({
            "pausada_em": now,
            "motivo_pausa": request.motivo,
            "updated_at": now,
        }).eq("id", conversation_id).execute()

        if not result.data:
            raise HTTPException(404, "Conversa nao encontrada")

        logger.info(f"Julia pausada: conv={conversation_id}, motivo={request.motivo}")
        return {"success": True, "pausada_em": now}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao pausar conversa: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")


@router.post("/{conversation_id}/resume")
async def resume_conversation(conversation_id: str):
    """Retoma Julia na conversa."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        result = supabase.table("conversations").update({
            "pausada_em": None,
            "motivo_pausa": None,
            "updated_at": now,
        }).eq("id", conversation_id).execute()

        if not result.data:
            raise HTTPException(404, "Conversa nao encontrada")

        logger.info(f"Julia retomada: conv={conversation_id}")
        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao retomar conversa: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")


@router.get("/{conversation_id}/notes")
async def list_notes(conversation_id: str):
    """Lista notas do supervisor para a conversa."""
    try:
        result = supabase.table("supervisor_notes").select(
            "id, content, created_at, user_id"
        ).eq(
            "conversation_id", conversation_id
        ).order("created_at", desc=True).limit(50).execute()

        return {"notes": result.data or []}

    except Exception as e:
        logger.error(f"Erro ao listar notas: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")


@router.post("/{conversation_id}/notes")
async def create_note(conversation_id: str, request: NoteRequest):
    """Cria nota do supervisor."""
    try:
        # Buscar cliente_id da conversa
        conv = supabase.table("conversations").select(
            "cliente_id"
        ).eq("id", conversation_id).single().execute()

        if not conv.data:
            raise HTTPException(404, "Conversa nao encontrada")

        note_data = {
            "id": str(uuid4()),
            "conversation_id": conversation_id,
            "cliente_id": conv.data["cliente_id"],
            "content": request.content,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        result = supabase.table("supervisor_notes").insert(note_data).execute()

        logger.info(f"Nota criada: conv={conversation_id}")
        return {"success": True, "note": result.data[0] if result.data else note_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar nota: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")


@router.post("/{conversation_id}/feedback")
async def create_feedback(conversation_id: str, request: FeedbackRequest):
    """Registra feedback em mensagem da Julia."""
    if request.feedback_type not in ("positive", "negative"):
        raise HTTPException(400, "feedback_type deve ser 'positive' ou 'negative'")

    try:
        feedback_data = {
            "id": str(uuid4()),
            "interacao_id": request.interacao_id,
            "conversation_id": conversation_id,
            "feedback_type": request.feedback_type,
            "comment": request.comment,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        result = supabase.table("message_feedback").insert(feedback_data).execute()

        logger.info(
            f"Feedback registrado: conv={conversation_id}, "
            f"interacao={request.interacao_id}, tipo={request.feedback_type}"
        )
        return {"success": True, "feedback": result.data[0] if result.data else feedback_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao registrar feedback: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")
