"""
Supervisor Channel API - Chat privado supervisor-Julia.

Sprint 54 - Phase 4: Supervisor Channel

Endpoints:
- GET  /supervisor/channel/{conversation_id}/history - Historico do channel
- POST /supervisor/channel/{conversation_id}/message - Pergunta ao supervisor
- POST /supervisor/channel/{conversation_id}/instruct - Instrucao com preview
- POST /supervisor/channel/{conversation_id}/instruct/{id}/confirm - Confirma envio
- POST /supervisor/channel/{conversation_id}/instruct/{id}/reject - Rejeita preview
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.supabase import supabase
from app.services.llm import gerar_resposta
from app.services.chips.sender import enviar_via_chip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/supervisor/channel", tags=["supervisor-channel"])


# ============================================
# Request Models
# ============================================


class ChannelMessageRequest(BaseModel):
    """Request para mensagem no channel."""

    content: str


class InstructRequest(BaseModel):
    """Request para instrucao com preview."""

    instruction: str


# ============================================
# Helpers
# ============================================


async def _get_conversation_context(conversation_id: str) -> dict:
    """Monta contexto completo da conversa para Julia responder ao supervisor."""
    # Buscar conversa + cliente
    conv = (
        supabase.table("conversations")
        .select("*, clientes(id, nome, telefone, crm, especialidade, stage_jornada)")
        .eq("id", conversation_id)
        .single()
        .execute()
    )

    if not conv.data:
        raise HTTPException(404, "Conversa nao encontrada")

    # Buscar historico recente (ultimas 30 mensagens)
    interacoes = (
        supabase.table("interacoes")
        .select("tipo, conteudo, created_at")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=True)
        .limit(30)
        .execute()
    )

    historico_msgs = list(reversed(interacoes.data or []))

    # Buscar doctor_context (memorias)
    cliente_id = conv.data.get("cliente_id")
    memorias = []
    if cliente_id:
        mem_result = (
            supabase.table("doctor_context")
            .select("content, tipo")
            .eq("cliente_id", cliente_id)
            .eq("valido", True)
            .limit(15)
            .execute()
        )
        memorias = mem_result.data or []

    return {
        "conversation": conv.data,
        "cliente": conv.data.get("clientes", {}),
        "historico": historico_msgs,
        "memorias": memorias,
    }


def _build_supervisor_system_prompt(context: dict) -> str:
    """Monta system prompt para Julia responder ao supervisor."""
    cliente = context["cliente"]
    historico = context["historico"]
    memorias = context["memorias"]
    conversation = context["conversation"]

    historico_texto = "\n".join(
        [
            f"{'Medico' if m['tipo'] == 'entrada' else 'Julia'}: {m['conteudo']}"
            for m in historico[-20:]
        ]
    )

    memorias_texto = (
        "\n".join([f"- [{m.get('tipo', 'geral')}] {m['content']}" for m in memorias])
        if memorias
        else "Nenhuma memoria registrada."
    )

    return f"""Voce e Julia, escalista da Revoluna, respondendo ao seu supervisor sobre uma conversa com um medico.

CONTEXTO DA CONVERSA:
- Medico: {cliente.get("nome", "Desconhecido")}
- Especialidade: {cliente.get("especialidade", "N/A")}
- CRM: {cliente.get("crm", "N/A")}
- Stage: {cliente.get("stage_jornada", "N/A")}
- Status da conversa: {conversation.get("status", "N/A")}
- Controle: {conversation.get("controlled_by", "ai")}
- Pausada: {"Sim" if conversation.get("pausada_em") else "Nao"}

MEMORIAS DO MEDICO:
{memorias_texto}

HISTORICO DA CONVERSA:
{historico_texto}

REGRAS:
1. Responda de forma profissional e direta ao supervisor
2. NAO fale como se estivesse conversando com o medico
3. Use linguagem normal (sem abreviacoes de WhatsApp)
4. Analise a conversa e de insights uteis
5. Se o supervisor pedir para voce fazer algo, explique o que faria
6. Seja concisa mas completa nas respostas"""


def _build_instruction_system_prompt(context: dict, instruction: str) -> str:
    """Monta system prompt para gerar preview de mensagem com instrucao."""
    cliente = context["cliente"]
    historico = context["historico"]
    memorias = context["memorias"]

    historico_texto = "\n".join(
        [
            f"{'Medico' if m['tipo'] == 'entrada' else 'Julia'}: {m['conteudo']}"
            for m in historico[-20:]
        ]
    )

    memorias_texto = (
        "\n".join([f"- [{m.get('tipo', 'geral')}] {m['content']}" for m in memorias])
        if memorias
        else "Nenhuma memoria registrada."
    )

    return f"""Voce e Julia Mendes, escalista da Revoluna, de 27 anos.

Seu supervisor te deu uma instrucao especifica para seguir na proxima mensagem.

INSTRUCAO DO SUPERVISOR:
{instruction}

CONTEXTO DA CONVERSA:
- Medico: {cliente.get("nome", "Desconhecido")}
- Especialidade: {cliente.get("especialidade", "N/A")}
- Stage: {cliente.get("stage_jornada", "N/A")}

MEMORIAS DO MEDICO:
{memorias_texto}

HISTORICO DA CONVERSA:
{historico_texto}

REGRAS:
1. Gere uma mensagem PARA O MEDICO seguindo a instrucao do supervisor
2. Mantenha o tom da Julia: informal, curta, usa "vc", "pra", "blz"
3. NAO use bullet points ou listas
4. Mensagem curta (1-3 linhas)
5. Siga a instrucao do supervisor fielmente
6. A mensagem deve fazer sentido no contexto da conversa"""


# ============================================
# Endpoints
# ============================================


@router.get("/{conversation_id}/history")
async def listar_historico_channel(conversation_id: str, limit: int = 50):
    """Retorna historico do supervisor channel."""
    try:
        result = (
            supabase.table("supervisor_channel")
            .select("id, role, content, metadata, created_at")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        messages = list(reversed(result.data or []))
        return {"messages": messages}

    except Exception as e:
        logger.error(f"Erro ao buscar historico channel: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")


@router.post("/{conversation_id}/message")
async def enviar_mensagem_channel(conversation_id: str, request: ChannelMessageRequest):
    """
    Envia pergunta do supervisor e recebe resposta da Julia.

    A Julia responde sobre a conversa, NAO como se estivesse
    conversando com o medico.
    """
    if not request.content.strip():
        raise HTTPException(400, "Conteudo obrigatorio")

    try:
        # 1. Salvar mensagem do supervisor
        supabase.table("supervisor_channel").insert(
            {
                "conversation_id": conversation_id,
                "role": "supervisor",
                "content": request.content,
                "metadata": {"type": "question"},
            }
        ).execute()

        # 2. Montar contexto
        context = await _get_conversation_context(conversation_id)
        system_prompt = _build_supervisor_system_prompt(context)

        # 3. Buscar historico do channel para contexto
        channel_history = (
            supabase.table("supervisor_channel")
            .select("role, content")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=False)
            .limit(20)
            .execute()
        )

        messages_history = []
        for msg in (channel_history.data or [])[:-1]:  # Excluir a msg que acabamos de salvar
            role = "user" if msg["role"] == "supervisor" else "assistant"
            messages_history.append({"role": role, "content": msg["content"]})

        # 4. Gerar resposta da Julia (usando Sonnet para qualidade)
        resposta = await gerar_resposta(
            mensagem=request.content,
            historico=messages_history,
            system_prompt=system_prompt,
            max_tokens=500,
        )

        # 5. Salvar resposta da Julia
        julia_msg = (
            supabase.table("supervisor_channel")
            .insert(
                {
                    "conversation_id": conversation_id,
                    "role": "julia",
                    "content": resposta,
                    "metadata": {"type": "response"},
                }
            )
            .execute()
        )

        logger.info(f"Channel msg: conv={conversation_id}")

        return {
            "supervisor_message": request.content,
            "julia_response": resposta,
            "message_id": julia_msg.data[0]["id"] if julia_msg.data else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no channel message: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")


@router.post("/{conversation_id}/instruct")
async def criar_instrucao_com_preview(conversation_id: str, request: InstructRequest):
    """
    Cria instrucao com preview.

    O supervisor escreve uma instrucao, Julia gera um preview
    da mensagem que enviaria ao medico. O supervisor pode
    confirmar, editar ou rejeitar.
    """
    if not request.instruction.strip():
        raise HTTPException(400, "Instrucao obrigatoria")

    try:
        # 1. Montar contexto
        context = await _get_conversation_context(conversation_id)

        # 2. Gerar preview usando o prompt com instrucao
        system_prompt = _build_instruction_system_prompt(context, request.instruction)

        # Converter historico para messages format
        historico_msgs = []
        for msg in context["historico"][-10:]:
            role = "user" if msg["tipo"] == "entrada" else "assistant"
            historico_msgs.append({"role": role, "content": msg["conteudo"]})

        preview = await gerar_resposta(
            mensagem="Gere a mensagem seguindo a instrucao do supervisor.",
            historico=historico_msgs,
            system_prompt=system_prompt,
            max_tokens=300,
        )

        # 3. Salvar instrucao no channel com status pending
        instruction_msg = (
            supabase.table("supervisor_channel")
            .insert(
                {
                    "conversation_id": conversation_id,
                    "role": "supervisor",
                    "content": request.instruction,
                    "metadata": {
                        "type": "instruction",
                        "status": "pending",
                        "preview": preview,
                    },
                }
            )
            .execute()
        )

        instruction_id = instruction_msg.data[0]["id"] if instruction_msg.data else None

        logger.info(f"Instrucao criada: conv={conversation_id}, id={instruction_id}")

        return {
            "id": instruction_id,
            "instruction": request.instruction,
            "preview_message": preview,
            "status": "pending",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar instrucao: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")


@router.post("/{conversation_id}/instruct/{instruction_id}/confirm")
async def confirmar_instrucao(conversation_id: str, instruction_id: str):
    """
    Confirma envio da mensagem gerada pela instrucao.

    Envia a mensagem ao medico via WhatsApp e registra interacao.
    """
    try:
        # 1. Buscar instrucao
        instr = (
            supabase.table("supervisor_channel")
            .select("id, metadata")
            .eq("id", instruction_id)
            .eq("conversation_id", conversation_id)
            .single()
            .execute()
        )

        if not instr.data:
            raise HTTPException(404, "Instrucao nao encontrada")

        metadata = instr.data.get("metadata", {})
        if metadata.get("status") != "pending":
            raise HTTPException(400, f"Instrucao ja processada: {metadata.get('status')}")

        preview_message = metadata.get("preview", "")
        if not preview_message:
            raise HTTPException(400, "Preview vazio")

        # 2. Buscar conversa + chip para envio
        conv = (
            supabase.table("conversations")
            .select("*, clientes(id, telefone)")
            .eq("id", conversation_id)
            .single()
            .execute()
        )

        if not conv.data:
            raise HTTPException(404, "Conversa nao encontrada")

        cliente = conv.data.get("clientes", {})
        telefone = cliente.get("telefone")

        if not telefone:
            raise HTTPException(400, "Cliente sem telefone")

        # Buscar chip associado
        chip_result = (
            supabase.table("conversation_chips")
            .select("chip_id, chips!conversation_chips_chip_id_fkey(*)")
            .eq("conversa_id", conversation_id)
            .eq("active", True)
            .limit(1)
            .execute()
        )

        chip = None
        if chip_result.data and chip_result.data[0].get("chips"):
            chip = chip_result.data[0]["chips"]

        if not chip:
            # Fallback: chip ativo qualquer
            active_chip = (
                supabase.table("chips").select("*").eq("status", "active").limit(1).execute()
            )
            if active_chip.data:
                chip = active_chip.data[0]

        if not chip:
            raise HTTPException(503, "Nenhum chip disponivel")

        # 3. Enviar mensagem via WhatsApp
        result = await enviar_via_chip(chip, telefone, preview_message)

        if not result.success:
            logger.error(f"Falha ao enviar instrucao: {result.error}")
            raise HTTPException(500, f"Falha ao enviar: {result.error}")

        # 4. Registrar interacao
        cliente_id = conv.data.get("cliente_id") or cliente.get("id")
        supabase.table("interacoes").insert(
            {
                "conversation_id": conversation_id,
                "cliente_id": cliente_id,
                "origem": "supervisor_instruction",
                "tipo": "saida",
                "canal": "whatsapp",
                "conteudo": preview_message,
                "autor_nome": "Julia (instruida)",
                "autor_tipo": "agente",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()

        # 5. Atualizar status da instrucao
        supabase.table("supervisor_channel").update(
            {
                "metadata": {**metadata, "status": "confirmed"},
            }
        ).eq("id", instruction_id).execute()

        # 6. Salvar confirmacao no channel
        supabase.table("supervisor_channel").insert(
            {
                "conversation_id": conversation_id,
                "role": "julia",
                "content": f"Mensagem enviada: {preview_message}",
                "metadata": {"type": "instruction_confirmed", "instruction_id": instruction_id},
            }
        ).execute()

        # 7. Atualizar last_message_at
        supabase.table("conversations").update(
            {
                "last_message_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", conversation_id).execute()

        logger.info(f"Instrucao confirmada e enviada: conv={conversation_id}")

        return {
            "success": True,
            "message_sent": preview_message,
            "message_id": result.message_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao confirmar instrucao: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")


@router.post("/{conversation_id}/instruct/{instruction_id}/reject")
async def rejeitar_instrucao(conversation_id: str, instruction_id: str):
    """Rejeita instrucao - nenhuma mensagem e enviada ao medico."""
    try:
        instr = (
            supabase.table("supervisor_channel")
            .select("id, metadata")
            .eq("id", instruction_id)
            .eq("conversation_id", conversation_id)
            .single()
            .execute()
        )

        if not instr.data:
            raise HTTPException(404, "Instrucao nao encontrada")

        metadata = instr.data.get("metadata", {})
        if metadata.get("status") != "pending":
            raise HTTPException(400, f"Instrucao ja processada: {metadata.get('status')}")

        # Atualizar status
        supabase.table("supervisor_channel").update(
            {
                "metadata": {**metadata, "status": "rejected"},
            }
        ).eq("id", instruction_id).execute()

        logger.info(f"Instrucao rejeitada: conv={conversation_id}, id={instruction_id}")

        return {"success": True, "status": "rejected"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao rejeitar instrucao: {e}")
        raise HTTPException(500, f"Erro interno: {str(e)}")
