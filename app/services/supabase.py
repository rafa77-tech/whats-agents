"""
Cliente Supabase para operacoes de banco de dados.
"""
from supabase import create_client, Client
from functools import lru_cache
from datetime import datetime, timezone
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache()
def get_supabase_client() -> Client:
    """
    Retorna cliente Supabase cacheado.
    Usa service key para acesso completo.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_URL e SUPABASE_SERVICE_KEY sao obrigatorios")

    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY
    )


# Instancia global (use via dependency injection quando possivel)
supabase = get_supabase_client()


# Funcoes auxiliares para operacoes comuns
async def get_medico_by_telefone(telefone: str) -> dict | None:
    """Busca medico pelo telefone."""
    response = supabase.table("clientes").select("*").eq("telefone", telefone).execute()
    return response.data[0] if response.data else None


async def get_medico_by_id(medico_id: str) -> dict | None:
    """Busca medico pelo ID."""
    response = supabase.table("clientes").select("*").eq("id", medico_id).execute()
    return response.data[0] if response.data else None


async def get_or_create_medico(telefone: str, primeiro_nome: Optional[str] = None) -> dict:
    """Busca ou cria medico."""
    medico = await get_medico_by_telefone(telefone)
    if not medico:
        data = {
            "telefone": telefone,
            "primeiro_nome": primeiro_nome,
            "stage_jornada": "novo",
            "status": "novo"
        }
        response = supabase.table("clientes").insert(data).execute()
        logger.info(f"Novo medico criado: {telefone[:8]}...")
        return response.data[0]
    return medico


async def get_vagas_disponiveis(especialidade_id: str = None, limit: int = 10) -> list:
    """Busca vagas abertas para uma especialidade."""
    query = (
        supabase.table("vagas")
        .select("*, hospitais(*), periodos(*), setores(*), especialidades(*)")
        .eq("status", "aberta")
        .gte("data", datetime.now(timezone.utc).date().isoformat())
        .order("data")
        .limit(limit)
    )

    if especialidade_id:
        query = query.eq("especialidade_id", especialidade_id)

    response = query.execute()
    return response.data


async def get_conversa_ativa(cliente_id: str) -> dict | None:
    """Busca conversa ativa do cliente."""
    response = (
        supabase.table("conversations")
        .select("*")
        .eq("cliente_id", cliente_id)
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


async def criar_conversa(cliente_id: str, origem: str = "prospeccao") -> dict:
    """Cria nova conversa para um medico."""
    response = (
        supabase.table("conversations")
        .insert({
            "cliente_id": cliente_id,
            "status": "active",
            "controlled_by": "ai",
            "instance_id": settings.EVOLUTION_INSTANCE,
        })
        .execute()
    )
    return response.data[0] if response.data else None


async def salvar_interacao(
    conversa_id: str,
    cliente_id: str,
    direcao: str,
    conteudo: str,
    tipo: str = "texto"
) -> dict:
    """Salva uma interacao (mensagem) na conversa."""
    origem = "medico" if direcao == "entrada" else "julia"
    autor_tipo = "medico" if direcao == "entrada" else "ai"

    response = (
        supabase.table("interacoes")
        .insert({
            "conversation_id": conversa_id,
            "cliente_id": cliente_id,
            "origem": origem,
            "tipo": tipo,
            "conteudo": conteudo,
            "canal": "whatsapp",
            "autor_tipo": autor_tipo,
        })
        .execute()
    )
    return response.data[0] if response.data else None


async def get_historico(conversa_id: str, limit: int = 20) -> list:
    """Busca historico de mensagens da conversa."""
    response = (
        supabase.table("interacoes")
        .select("*")
        .eq("conversation_id", conversa_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return list(reversed(response.data)) if response.data else []
