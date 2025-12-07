"""
Servico para gerenciamento de interacoes (mensagens).
"""
from typing import Optional, Literal
import logging

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


async def salvar_interacao(
    conversa_id: str,
    tipo: Literal["entrada", "saida"],
    conteudo: str,
    remetente: Literal["medico", "julia", "gestor"],
    message_id: Optional[str] = None
) -> Optional[dict]:
    """
    Salva uma interacao (mensagem) na conversa.

    Args:
        conversa_id: ID da conversa
        tipo: entrada (recebida) ou saida (enviada)
        conteudo: Texto da mensagem
        remetente: Quem enviou
        message_id: ID da mensagem no WhatsApp

    Returns:
        Dados da interacao salva
    """
    try:
        dados = {
            "conversation_id": conversa_id,
            "tipo": tipo,
            "conteudo": conteudo,
            "remetente": remetente,
        }

        if message_id:
            dados["whatsapp_message_id"] = message_id

        response = supabase.table("interacoes").insert(dados).execute()
        logger.debug(f"Interacao salva: {tipo} - {conteudo[:50]}...")
        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(f"Erro ao salvar interacao: {e}")
        return None


async def carregar_historico(
    conversa_id: str,
    limite: int = 10
) -> list[dict]:
    """
    Carrega ultimas interacoes da conversa.

    Args:
        conversa_id: ID da conversa
        limite: Maximo de interacoes a retornar

    Returns:
        Lista de interacoes ordenadas da mais antiga para mais recente
    """
    try:
        response = (
            supabase.table("interacoes")
            .select("*")
            .eq("conversation_id", conversa_id)
            .order("created_at", desc=True)
            .limit(limite)
            .execute()
        )

        # Inverter para ordem cronologica
        return list(reversed(response.data)) if response.data else []

    except Exception as e:
        logger.error(f"Erro ao carregar historico: {e}")
        return []


def formatar_historico_para_llm(interacoes: list[dict]) -> str:
    """
    Formata historico para incluir no prompt do LLM.

    Returns:
        String formatada com as mensagens
    """
    if not interacoes:
        return "Nenhuma mensagem anterior."

    linhas = []
    for i in interacoes:
        remetente = "Medico" if i["remetente"] == "medico" else "Julia"
        linhas.append(f"{remetente}: {i['conteudo']}")

    return "\n".join(linhas)


def converter_historico_para_messages(interacoes: list[dict]) -> list[dict]:
    """
    Converte historico para formato de messages do Claude.

    Returns:
        Lista no formato [{"role": "user/assistant", "content": "..."}]
    """
    messages = []
    for i in interacoes:
        role = "user" if i["remetente"] == "medico" else "assistant"
        messages.append({
            "role": role,
            "content": i["conteudo"]
        })
    return messages
