"""
Detector de recusa de ofertas.

Sprint 17 - E05

Detecta quando médico recusa uma oferta e emite offer_declined.
Abordagem conservadora baseada em padrões de texto (sem LLM).
"""
import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.services.supabase import supabase
from .repository import emit_event
from .types import BusinessEvent, EventType, EventSource
from .rollout import should_emit_event

logger = logging.getLogger(__name__)


@dataclass
class RecusaResult:
    """Resultado da detecção de recusa."""
    is_recusa: bool
    confianca: float  # 0.0 a 1.0
    padrao_matched: Optional[str] = None
    tipo: Optional[str] = None  # "explicita", "desculpa", None


# Padrões de recusa explícita (alta confiança 0.9)
RECUSA_EXPLICITA = [
    r"n[aã]o\s+tenho\s+interesse",
    r"n[aã]o\s+quero",
    r"n[aã]o\s+(vou\s+)?poder",
    r"n[aã]o\s+d[aá]\s+(pra|para)\s+mim",
    r"pass[oa]\s+essa",
    r"n[aã]o\s+me\s+interessa",
    r"declino",
    r"recuso",
    r"n[aã]o\s+aceito",
    r"dispenso",
    r"obrigad[oa]\s*,?\s*mas\s+n[aã]o",
]

# Padrões de desculpas (média confiança 0.6)
DESCULPAS = [
    r"j[aá]\s+tenho\s+compromisso",
    r"tenho\s+outro\s+plant[aã]o",
    r"j[aá]\s+estou\s+escalad[oa]",
    r"viagem\s+marcada",
    r"estou\s+de\s+f[eé]rias",
    r"n[aã]o\s+trabalho\s+nesse\s+dia",
    r"n[aã]o\s+fa[cç]o\s+noturno",
    r"n[aã]o\s+fa[cç]o\s+final\s+de\s+semana",
    r"muito\s+longe",
    r"valor\s+baixo",
    r"n[aã]o\s+compensa",
    r"hor[aá]rio\s+ruim",
    r"n[aã]o\s+fa[cç]o\s+(urg[eê]ncia|emerg[eê]ncia|uti|ps)",
    r"n[aã]o\s+atendo\s+(crian[cç]a|pediatria|adulto)",
]

# Padrões que NÃO são recusa (evitar falso positivo)
NAO_RECUSA = [
    r"n[aã]o\s+entendi",
    r"n[aã]o\s+recebi",
    r"pode\s+me\s+explicar",
    r"qual\s+o\s+valor",
    r"onde\s+fica",
    r"me\s+fala\s+mais",
    r"pode\s+repetir",
    r"n[aã]o\s+vi\s+a\s+mensagem",
    r"n[aã]o\s+sei\s+se",
    r"me\s+manda\s+mais\s+(detalhes|informa)",
    r"preciso\s+pensar",
    r"vou\s+ver",
    r"deixa\s+eu\s+ver",
]


def detectar_recusa(mensagem: str) -> RecusaResult:
    """
    Detecta se mensagem indica recusa de oferta.

    Args:
        mensagem: Texto da mensagem do médico

    Returns:
        RecusaResult com is_recusa, confianca e detalhes
    """
    if not mensagem:
        return RecusaResult(is_recusa=False, confianca=0.5)

    texto = mensagem.lower().strip()

    # Primeiro, verificar se NÃO é recusa (evitar falso positivo)
    for pattern in NAO_RECUSA:
        if re.search(pattern, texto):
            return RecusaResult(is_recusa=False, confianca=0.9)

    # Verificar recusa explícita (alta confiança)
    for pattern in RECUSA_EXPLICITA:
        match = re.search(pattern, texto)
        if match:
            return RecusaResult(
                is_recusa=True,
                confianca=0.9,
                padrao_matched=match.group(),
                tipo="explicita",
            )

    # Verificar desculpas (média confiança)
    for pattern in DESCULPAS:
        match = re.search(pattern, texto)
        if match:
            return RecusaResult(
                is_recusa=True,
                confianca=0.6,
                padrao_matched=match.group(),
                tipo="desculpa",
            )

    # Nenhum padrão encontrado
    return RecusaResult(is_recusa=False, confianca=0.5)


async def buscar_ultima_oferta(
    cliente_id: str,
    max_horas: int = 48,
) -> Optional[dict]:
    """
    Busca a última oferta feita ao médico.

    Args:
        cliente_id: UUID do cliente/médico
        max_horas: Janela de tempo para considerar (default 48h)

    Returns:
        Dados da última oferta ou None
    """
    since = (datetime.now(timezone.utc) - timedelta(hours=max_horas)).isoformat()

    try:
        response = (
            supabase.table("business_events")
            .select("*")
            .eq("cliente_id", cliente_id)
            .eq("event_type", "offer_made")
            .gte("ts", since)
            .order("ts", desc=True)
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0]
        return None

    except Exception as e:
        logger.error(f"Erro ao buscar última oferta: {e}")
        return None


def _calcular_horas_desde(ts_str: str) -> float:
    """Calcula horas desde um timestamp ISO."""
    if not ts_str:
        return 0.0
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        now = datetime.now(ts.tzinfo)
        delta = now - ts
        return delta.total_seconds() / 3600
    except Exception:
        return 0.0


async def processar_possivel_recusa(
    cliente_id: str,
    mensagem: str,
    conversation_id: str = None,
    interaction_id: int = None,
) -> bool:
    """
    Processa mensagem verificando se é recusa.

    Args:
        cliente_id: UUID do médico
        mensagem: Texto da mensagem
        conversation_id: UUID da conversa
        interaction_id: ID da interação

    Returns:
        True se detectou e emitiu offer_declined
    """
    # Verificar rollout
    should_emit = await should_emit_event(cliente_id, "offer_declined")
    if not should_emit:
        return False

    # Detectar recusa
    result = detectar_recusa(mensagem)

    if not result.is_recusa or result.confianca < 0.6:
        return False

    # Buscar última oferta
    ultima_oferta = await buscar_ultima_oferta(cliente_id)

    if not ultima_oferta:
        logger.info(f"Recusa detectada mas sem oferta recente: {cliente_id[:8]}")
        return False

    # Emitir evento
    try:
        await emit_event(BusinessEvent(
            event_type=EventType.OFFER_DECLINED,
            source=EventSource.HEURISTIC,
            cliente_id=cliente_id,
            vaga_id=ultima_oferta.get("vaga_id"),
            hospital_id=ultima_oferta.get("hospital_id"),
            conversation_id=conversation_id,
            interaction_id=interaction_id,
            event_props={
                "tipo_recusa": result.tipo,
                "confianca": result.confianca,
                "padrao_matched": result.padrao_matched,
                "offer_made_event_id": ultima_oferta.get("id"),
                "horas_desde_oferta": _calcular_horas_desde(ultima_oferta.get("ts")),
            },
        ))

        logger.info(
            f"offer_declined emitido: cliente={cliente_id[:8]} "
            f"vaga={ultima_oferta.get('vaga_id', '')[:8] if ultima_oferta.get('vaga_id') else 'N/A'} "
            f"confianca={result.confianca}"
        )
        return True

    except Exception as e:
        logger.error(f"Erro ao emitir offer_declined: {e}")
        return False
