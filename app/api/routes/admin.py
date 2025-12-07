"""
Endpoints administrativos para gestor avaliar conversas.
"""
from fastapi import APIRouter, Query
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import logging

from app.services.supabase import supabase

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)


@router.get("/conversas")
async def listar_conversas(
    status: Optional[str] = None,
    avaliada: Optional[bool] = None,
    limite: int = Query(default=20, le=100),
    offset: int = 0
):
    """
    Lista conversas para avaliação do gestor.

    Filtros:
    - status: active, completed, etc
    - avaliada: true/false (tem avaliação do gestor)
    """
    try:
        query = (
            supabase.table("conversations")
            .select("""
                *,
                clientes(primeiro_nome, telefone, especialidade_id),
                metricas_conversa(*),
                avaliacoes_qualidade(score_geral, avaliador)
            """)
            .order("created_at", desc=True)
            .range(offset, offset + limite - 1)
        )

        if status:
            query = query.eq("status", status)

        response = query.execute()
        conversas = response.data or []

        # Filtrar por avaliação se necessário
        if avaliada is not None:
            conversas = [
                c for c in conversas
                if any(
                    a.get("avaliador") == "gestor"
                    for a in (c.get("avaliacoes_qualidade") or [])
                ) == avaliada
            ]

        return {
            "conversas": conversas,
            "total": len(conversas),
            "offset": offset,
            "limite": limite
        }
    except Exception as e:
        logger.error(f"Erro ao listar conversas: {e}")
        return {
            "conversas": [],
            "total": 0,
            "offset": offset,
            "limite": limite,
            "erro": str(e)
        }


@router.get("/conversas/{conversa_id}")
async def obter_conversa_detalhada(conversa_id: str):
    """Retorna conversa com todas as interações."""
    try:
        conversa_response = (
            supabase.table("conversations")
            .select("*, clientes(*)")
            .eq("id", conversa_id)
            .single()
            .execute()
        )
        conversa = conversa_response.data

        interacoes_response = (
            supabase.table("interacoes")
            .select("*")
            .eq("conversation_id", conversa_id)
            .order("created_at")
            .execute()
        )
        interacoes = interacoes_response.data or []

        avaliacoes_response = (
            supabase.table("avaliacoes_qualidade")
            .select("*")
            .eq("conversa_id", conversa_id)
            .execute()
        )
        avaliacoes = avaliacoes_response.data or []

        return {
            "conversa": conversa,
            "interacoes": interacoes,
            "avaliacoes": avaliacoes
        }
    except Exception as e:
        logger.error(f"Erro ao obter conversa detalhada: {e}")
        return {
            "conversa": None,
            "interacoes": [],
            "avaliacoes": [],
            "erro": str(e)
        }


class AvaliacaoGestor(BaseModel):
    conversa_id: str
    naturalidade: int
    persona: int
    objetivo: int
    satisfacao: int
    notas: Optional[str] = None
    tags: Optional[List[str]] = []


@router.post("/avaliacoes")
async def criar_avaliacao_gestor(avaliacao: AvaliacaoGestor):
    """Salva avaliação do gestor."""
    try:
        score_geral = round((
            avaliacao.naturalidade +
            avaliacao.persona +
            avaliacao.objetivo +
            avaliacao.satisfacao
        ) / 4)

        response = (
            supabase.table("avaliacoes_qualidade")
            .insert({
                "conversa_id": avaliacao.conversa_id,
                "naturalidade": avaliacao.naturalidade,
                "persona": avaliacao.persona,
                "objetivo": avaliacao.objetivo,
                "satisfacao": avaliacao.satisfacao,
                "score_geral": score_geral,
                "notas": avaliacao.notas,
                "avaliador": "gestor",
                "tags": avaliacao.tags or []
            })
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Erro ao criar avaliação do gestor: {e}")
        return {"erro": str(e)}


@router.get("/conversas/por-tag/{tag}")
async def buscar_por_tag(tag: str, limite: int = 50):
    """Busca conversas que têm determinada tag."""
    try:
        avaliacoes_response = (
            supabase.table("avaliacoes_qualidade")
            .select("conversa_id")
            .contains("tags", [tag])
            .execute()
        )
        avaliacoes = avaliacoes_response.data or []

        conversa_ids = [a["conversa_id"] for a in avaliacoes]

        if not conversa_ids:
            return {"conversas": [], "total": 0}

        conversas_response = (
            supabase.table("conversations")
            .select("*, clientes(primeiro_nome)")
            .in_("id", conversa_ids)
            .limit(limite)
            .execute()
        )
        conversas = conversas_response.data or []

        return {"conversas": conversas, "total": len(conversas)}
    except Exception as e:
        logger.error(f"Erro ao buscar por tag: {e}")
        return {"conversas": [], "total": 0, "erro": str(e)}


class SugestaoPrompt(BaseModel):
    conversa_id: str
    avaliacao_id: Optional[str] = None
    tipo: str  # 'adicionar_regra', 'remover_regra', 'ajustar_tom', 'exemplo'
    descricao: str
    exemplo_ruim: Optional[str] = None
    exemplo_bom: Optional[str] = None


@router.post("/sugestoes")
async def criar_sugestao(sugestao: SugestaoPrompt):
    """Cria sugestão de melhoria do prompt."""
    try:
        response = (
            supabase.table("sugestoes_prompt")
            .insert(sugestao.dict())
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Erro ao criar sugestão: {e}")
        return {"erro": str(e)}


@router.get("/sugestoes")
async def listar_sugestoes(status: str = "pendente"):
    """Lista sugestões de melhoria."""
    try:
        response = (
            supabase.table("sugestoes_prompt")
            .select("*, conversations(clientes(primeiro_nome))")
            .eq("status", status)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.error(f"Erro ao listar sugestões: {e}")
        return []


@router.patch("/sugestoes/{sugestao_id}")
async def atualizar_sugestao(sugestao_id: str, status: str):
    """Atualiza status da sugestão."""
    try:
        atualizacao = {"status": status}
        if status == "implementada":
            atualizacao["implementada_em"] = datetime.utcnow().isoformat()

        response = (
            supabase.table("sugestoes_prompt")
            .update(atualizacao)
            .eq("id", sugestao_id)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Erro ao atualizar sugestão: {e}")
        return {"erro": str(e)}


@router.get("/sugestoes/agregadas")
async def obter_sugestoes_agregadas():
    """Retorna sugestões agrupadas por tipo."""
    try:
        from app.services.feedback import agregar_sugestoes
        return await agregar_sugestoes()
    except Exception as e:
        logger.error(f"Erro ao obter sugestões agregadas: {e}")
        return {}


@router.get("/tags")
async def obter_tags_predefinidas():
    """Retorna tags pré-definidas disponíveis."""
    from app.constants.tags import TAGS_PREDEFINIDAS
    return TAGS_PREDEFINIDAS

