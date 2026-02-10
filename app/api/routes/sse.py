"""
SSE (Server-Sent Events) - Atualizacoes em tempo real.

Sprint 54 - Phase 4: Real-Time Updates

Endpoint:
- GET /dashboard/sse/conversations/{id} - Stream de eventos para uma conversa
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard/sse", tags=["sse"])

# Intervalo de polling em segundos
POLL_INTERVAL = 5


@router.get("/conversations/{conversation_id}")
async def stream_conversation(conversation_id: str):
    """
    Stream SSE de eventos para uma conversa.

    Eventos emitidos:
    - new_message: Nova mensagem na conversa
    - control_change: Mudanca de controle (ai/human)
    - pause_change: Conversa pausada/retomada
    - channel_message: Nova mensagem no supervisor channel

    O cliente deve se reconectar se a conexao cair.
    """

    async def event_generator():
        """Gera eventos SSE via polling do banco."""
        last_message_at = None
        last_control = None
        last_paused = None
        last_channel_at = None

        # Estado inicial
        try:
            conv = (
                supabase.table("conversations")
                .select("controlled_by, pausada_em, last_message_at")
                .eq("id", conversation_id)
                .single()
                .execute()
            )

            if conv.data:
                last_control = conv.data.get("controlled_by")
                last_paused = conv.data.get("pausada_em")
                last_message_at = conv.data.get("last_message_at")

            # Ultimo channel message
            ch = (
                supabase.table("supervisor_channel")
                .select("created_at")
                .eq("conversation_id", conversation_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            if ch.data:
                last_channel_at = ch.data[0].get("created_at")

        except Exception as e:
            logger.error(f"SSE init error: {e}")

        # Enviar evento de conexao
        yield f"event: connected\ndata: {json.dumps({'conversation_id': conversation_id})}\n\n"

        while True:
            try:
                await asyncio.sleep(POLL_INTERVAL)

                # Buscar estado atual
                conv = (
                    supabase.table("conversations")
                    .select("controlled_by, pausada_em, last_message_at")
                    .eq("id", conversation_id)
                    .single()
                    .execute()
                )

                if not conv.data:
                    yield f"event: error\ndata: {json.dumps({'error': 'conversation_not_found'})}\n\n"
                    break

                current = conv.data

                # Detectar nova mensagem
                current_msg_at = current.get("last_message_at")
                if current_msg_at and current_msg_at != last_message_at:
                    last_message_at = current_msg_at
                    yield f"event: new_message\ndata: {json.dumps({'last_message_at': current_msg_at})}\n\n"

                # Detectar mudanca de controle
                current_control = current.get("controlled_by")
                if current_control != last_control:
                    last_control = current_control
                    yield f"event: control_change\ndata: {json.dumps({'controlled_by': current_control})}\n\n"

                # Detectar mudanca de pausa
                current_paused = current.get("pausada_em")
                if current_paused != last_paused:
                    last_paused = current_paused
                    yield f"event: pause_change\ndata: {json.dumps({'pausada_em': current_paused})}\n\n"

                # Detectar nova mensagem no channel
                ch = (
                    supabase.table("supervisor_channel")
                    .select("created_at, role, content")
                    .eq("conversation_id", conversation_id)
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )

                if ch.data:
                    current_channel_at = ch.data[0].get("created_at")
                    if current_channel_at and current_channel_at != last_channel_at:
                        last_channel_at = current_channel_at
                        yield f"event: channel_message\ndata: {json.dumps({'role': ch.data[0].get('role'), 'content': ch.data[0].get('content', '')[:100]})}\n\n"

                # Heartbeat para manter conexao viva
                yield f": heartbeat {datetime.now(timezone.utc).isoformat()}\n\n"

            except asyncio.CancelledError:
                logger.info(f"SSE desconectado: {conversation_id}")
                break
            except Exception as e:
                logger.error(f"SSE poll error: {e}")
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                await asyncio.sleep(POLL_INTERVAL * 2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
