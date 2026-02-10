"""
Servico de deteccao de mencoes a bot/IA.

Registra e monitora quando medicos percebem que estao falando com uma IA.
Meta: taxa de deteccao < 5% (docs/METRICAS_MVP.md)
"""

import re
import logging
from datetime import datetime, timedelta, timezone

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


# =============================================================================
# PADROES DE DETECCAO
# =============================================================================

# Padroes que indicam deteccao como bot
PADROES_DETECCAO = [
    # Mencoes diretas
    r"\bbot\b",
    r"\brob[oô]\b",
    r"\bia\b",
    r"\bintelig[eê]ncia artificial\b",
    r"\bautom[aá]tico\b",
    r"\bm[aá]quina\b",
    r"\balgoritmo\b",
    r"\bchatbot\b",
    r"\bchat bot\b",
    r"\bgpt\b",
    r"\bchatgpt\b",
    r"\brobozinho\b",
    r"\brobozinha\b",
    r"\bsistema automatizado\b",
    # Perguntas suspeitas
    r"isso [eé] autom[aá]tico",
    r"[eé] um? bot",
    r"[eé] uma? ia",
    r"t[oô] falando com (uma? )?(m[aá]quina|rob[oô]|bot)",
    r"voc[eê] [eé] (uma? )?(m[aá]quina|rob[oô]|bot|ia)",
    r"[eé] (uma? )?pessoa (real|de verdade)",
    r"tem (algu[eé]m|gente) a[ií]",
    r"falar com (uma? )?pessoa",
    r"atendente (humano|real|de verdade)",
    r"resposta autom[aá]tica",
    r"mensagem autom[aá]tica",
    r"parece (um )?rob[oô]",
    r"parece autom[aá]tico",
    r"parece (uma )?ia",
    r"isso [eé] (um )?rob[oô]",
    r"vc [eé] (um )?rob[oô]",
    r"ce [eé] (um )?rob[oô]",
    r"conversar com (uma? )?pessoa",
    r"pessoa de verdade",
    r"humano de verdade",
    r"nao [eé] pessoa",
    r"n[aã]o [eé] humano",
]

# Compilar regex para performance
_padroes_compilados = [re.compile(p, re.IGNORECASE) for p in PADROES_DETECCAO]


# =============================================================================
# FUNCOES DE DETECCAO
# =============================================================================


def detectar_mencao_bot(mensagem: str) -> dict:
    """
    Detecta se mensagem indica que medico percebeu que e bot.

    Args:
        mensagem: Texto da mensagem do medico

    Returns:
        dict com:
        - detectado: bool
        - padrao: str (qual padrao matchou)
        - trecho: str (parte da mensagem que matchou)
    """
    if not mensagem:
        return {"detectado": False, "padrao": None, "trecho": None}

    mensagem_limpa = mensagem.lower().strip()

    for padrao in _padroes_compilados:
        match = padrao.search(mensagem_limpa)
        if match:
            return {"detectado": True, "padrao": padrao.pattern, "trecho": match.group(0)}

    return {"detectado": False, "padrao": None, "trecho": None}


async def registrar_deteccao_bot(
    cliente_id: str, conversa_id: str, mensagem: str, padrao: str, trecho: str
):
    """
    Registra deteccao de bot na tabela de metricas.

    Args:
        cliente_id: ID do medico
        conversa_id: ID da conversa
        mensagem: Mensagem completa do medico
        padrao: Padrao regex que matchou
        trecho: Trecho especifico que indicou deteccao
    """
    try:
        supabase.table("metricas_deteccao_bot").insert(
            {
                "cliente_id": cliente_id,
                "conversa_id": conversa_id,
                "mensagem": mensagem[:500],  # Limitar tamanho
                "padrao_detectado": padrao,
                "trecho": trecho,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()

        logger.warning(f"DETECCAO BOT: cliente={cliente_id[:8]}..., trecho='{trecho}'")

    except Exception as e:
        logger.error(f"Erro ao registrar deteccao bot: {e}")


async def calcular_taxa_deteccao(dias: int = 7) -> dict:
    """
    Calcula taxa de deteccao como bot nos ultimos N dias.

    Args:
        dias: Numero de dias para calcular (default: 7)

    Returns:
        dict com:
        - total_conversas: int
        - deteccoes: int
        - taxa_percentual: float
        - periodo_dias: int
    """
    desde = datetime.now(timezone.utc) - timedelta(days=dias)

    try:
        # Total de conversas no periodo
        conversas_resp = (
            supabase.table("conversations")
            .select("id", count="exact")
            .gte("created_at", desde.isoformat())
            .execute()
        )

        # Total de deteccoes no periodo (conversas unicas)
        deteccoes_resp = (
            supabase.table("metricas_deteccao_bot")
            .select("conversa_id")
            .gte("created_at", desde.isoformat())
            .execute()
        )
        # Contar conversas unicas com deteccao
        conversas_com_deteccao = len(
            set(d["conversa_id"] for d in deteccoes_resp.data or [] if d.get("conversa_id"))
        )

        total = conversas_resp.count or 0
        taxa = (conversas_com_deteccao / total * 100) if total > 0 else 0

        return {
            "total_conversas": total,
            "deteccoes": conversas_com_deteccao,
            "taxa_percentual": round(taxa, 2),
            "periodo_dias": dias,
        }

    except Exception as e:
        logger.error(f"Erro ao calcular taxa de deteccao: {e}")
        return {"total_conversas": 0, "deteccoes": 0, "taxa_percentual": 0, "periodo_dias": dias}


async def calcular_taxa_deteccao_periodo(inicio: datetime, fim: datetime) -> dict:
    """
    Calcula taxa de deteccao como bot em um periodo especifico.

    Args:
        inicio: Data/hora de inicio
        fim: Data/hora de fim

    Returns:
        dict com:
        - total_conversas: int
        - deteccoes: int
        - taxa_percentual: float
    """
    try:
        # Total de conversas no periodo
        conversas_resp = (
            supabase.table("conversations")
            .select("id", count="exact")
            .gte("created_at", inicio.isoformat())
            .lte("created_at", fim.isoformat())
            .execute()
        )

        # Total de deteccoes no periodo (conversas unicas)
        deteccoes_resp = (
            supabase.table("metricas_deteccao_bot")
            .select("conversa_id")
            .gte("created_at", inicio.isoformat())
            .lte("created_at", fim.isoformat())
            .execute()
        )
        # Contar conversas unicas com deteccao
        conversas_com_deteccao = len(
            set(d["conversa_id"] for d in deteccoes_resp.data or [] if d.get("conversa_id"))
        )

        total = conversas_resp.count or 0
        taxa = (conversas_com_deteccao / total * 100) if total > 0 else 0

        return {
            "total_conversas": total,
            "deteccoes": conversas_com_deteccao,
            "taxa_percentual": round(taxa, 2),
        }

    except Exception as e:
        logger.error(f"Erro ao calcular taxa de deteccao do periodo: {e}")
        return {"total_conversas": 0, "deteccoes": 0, "taxa_percentual": 0}


async def listar_deteccoes_recentes(limite: int = 10) -> list:
    """
    Lista deteccoes recentes para revisao.

    Args:
        limite: Numero maximo de deteccoes

    Returns:
        Lista de deteccoes com dados do cliente
    """
    try:
        response = (
            supabase.table("metricas_deteccao_bot")
            .select("*, clientes(primeiro_nome, telefone)")
            .order("created_at", desc=True)
            .limit(limite)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao listar deteccoes: {e}")
        return []


async def marcar_falso_positivo(deteccao_id: str, revisor: str):
    """
    Marca uma deteccao como falso positivo.

    Args:
        deteccao_id: ID da deteccao
        revisor: Nome/email de quem revisou
    """
    try:
        supabase.table("metricas_deteccao_bot").update(
            {"falso_positivo": True, "revisado_por": revisor}
        ).eq("id", deteccao_id).execute()

        logger.info(f"Deteccao {deteccao_id} marcada como falso positivo por {revisor}")

    except Exception as e:
        logger.error(f"Erro ao marcar falso positivo: {e}")
