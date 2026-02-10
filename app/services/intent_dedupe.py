"""
Serviço de dedupe por intenção de mensagem.

Sprint 24 E02: Fingerprint determinístico para evitar spam semântico.

Evita cenários como:
- Campanha A: "Oi, tudo bem? Vi seu perfil..."
- Campanha B: "Dr, tudo certo? Pintou uma vaga..."
-> Textos diferentes, mesma intenção -> dedupe bloqueia

Fingerprint: sha256(cliente_id + intent_type + reference_id + day_bucket)
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, Tuple

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Tipos de intenção padronizados."""

    # Discovery
    DISCOVERY_FIRST = "discovery_first_touch"
    DISCOVERY_FOLLOWUP = "discovery_followup"

    # Oferta
    OFFER_ACTIVE = "offer_active"
    OFFER_REMINDER = "offer_reminder"

    # Reativação
    REACTIVATION_NUDGE = "reactivation_nudge"
    REACTIVATION_VALUE = "reactivation_value_prop"

    # Follow-up
    FOLLOWUP_SILENCE = "followup_silence"
    FOLLOWUP_DOCS = "followup_pending_docs"

    # Operacional
    SHIFT_REMINDER = "shift_reminder"
    HANDOFF_CONFIRM = "handoff_confirmation"


# Janelas de dedupe por intent (dias)
# Dentro da janela, mesma intenção é bloqueada
INTENT_WINDOWS: dict[str, int] = {
    "discovery_first_touch": 7,  # 1 discovery por semana
    "discovery_followup": 3,  # 1 followup a cada 3 dias
    "offer_active": 1,  # 1 oferta por dia (por vaga)
    "offer_reminder": 2,  # 1 reminder a cada 2 dias
    "reactivation_nudge": 7,  # 1 reativação por semana
    "reactivation_value_prop": 7,  # 1 value prop por semana
    "followup_silence": 3,  # 1 followup silêncio a cada 3 dias
    "followup_pending_docs": 2,  # 1 cobrança docs a cada 2 dias
    "shift_reminder": 1,  # 1 reminder por dia
    "handoff_confirmation": 1,  # 1 confirmação por dia
}
DEFAULT_WINDOW = 3


# Qual campo usar como reference_id para cada intent
# Determina a granularidade do dedupe
INTENT_REFERENCE_FIELD: dict[str, Optional[str]] = {
    "discovery_first_touch": "campaign_id",  # 1 por campanha
    "discovery_followup": "campaign_id",
    "offer_active": "vaga_id",  # 1 por vaga
    "offer_reminder": "vaga_id",
    "reactivation_nudge": None,  # global
    "reactivation_value_prop": None,
    "followup_silence": "conversation_id",  # 1 por conversa
    "followup_pending_docs": "conversation_id",
    "shift_reminder": "vaga_id",
    "handoff_confirmation": "vaga_id",
}


def _normalize_intent_type(intent_type) -> str:
    """Normaliza intent_type para string."""
    if isinstance(intent_type, IntentType):
        return intent_type.value
    return str(intent_type)


def gerar_intent_fingerprint(
    cliente_id: str,
    intent_type: str,
    reference_id: Optional[str] = None,
    window_days: Optional[int] = None,
) -> str:
    """
    Gera fingerprint determinístico para uma intenção.

    O fingerprint é único para:
    - cliente_id: quem recebe
    - intent_type: tipo de intenção
    - reference_id: contexto (vaga, campanha, conversa)
    - day_bucket: janela temporal (arredondada)

    Args:
        cliente_id: ID do médico
        intent_type: Tipo de intenção (enum ou string)
        reference_id: ID de referência (vaga, campanha, etc)
        window_days: Janela em dias (usa default do intent se None)

    Returns:
        Fingerprint SHA256 truncado (32 chars)
    """
    intent_str = _normalize_intent_type(intent_type)

    if window_days is None:
        window_days = INTENT_WINDOWS.get(intent_str, DEFAULT_WINDOW)

    # day_bucket: agrupa dias na mesma janela
    # Ex: window=7 -> dias 0-6 = bucket 0, dias 7-13 = bucket 1
    day_bucket = datetime.now(timezone.utc).toordinal() // window_days

    raw = f"{cliente_id}:{intent_str}:{reference_id or 'none'}:{day_bucket}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


async def verificar_intent(
    cliente_id: str,
    intent_type: str,
    reference_id: Optional[str] = None,
) -> Tuple[bool, str, Optional[str]]:
    """
    Verifica e reserva intent para esse médico.

    Usa UPSERT com ON CONFLICT DO NOTHING (sem exceção).
    Se inseriu, pode enviar. Se já existia, é duplicata.

    Args:
        cliente_id: ID do médico
        intent_type: Tipo de intenção
        reference_id: ID de referência (vaga, campanha, etc)

    Returns:
        Tuple (pode_enviar, fingerprint, motivo_se_bloqueado)
        - pode_enviar: True se pode enviar, False se duplicata
        - fingerprint: Hash gerado
        - motivo: String com motivo se bloqueado, None se pode enviar
    """
    intent_str = _normalize_intent_type(intent_type)
    window_days = INTENT_WINDOWS.get(intent_str, DEFAULT_WINDOW)

    fingerprint = gerar_intent_fingerprint(cliente_id, intent_str, reference_id, window_days)

    expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

    try:
        response = supabase.rpc(
            "inserir_intent_se_novo",
            {
                "p_fingerprint": fingerprint,
                "p_cliente_id": cliente_id,
                "p_intent_type": intent_str,
                "p_reference_id": reference_id,
                "p_expires_at": expires_at,
            },
        ).execute()

        if response.data and len(response.data) > 0:
            inserted = response.data[0].get("inserted", False)

            if inserted:
                logger.debug(
                    f"Intent registrado: {intent_str} para {cliente_id[:8]}... "
                    f"(ref={reference_id}, window={window_days}d)"
                )
                return (True, fingerprint, None)

        # Não inseriu = já existia = duplicata
        logger.info(
            f"Intent duplicado: {intent_str} para {cliente_id[:8]}... "
            f"(ref={reference_id}, window={window_days}d)"
        )
        return (False, fingerprint, f"intent_duplicate:{intent_str}")

    except Exception as e:
        logger.error(f"Erro ao verificar intent: {e}")
        # Fail open: permite envio em caso de erro
        return (True, fingerprint, None)


def obter_reference_id(intent_type: str, ctx) -> Optional[str]:
    """
    Obtém reference_id correto para o intent_type.

    Usa o mapeamento INTENT_REFERENCE_FIELD para determinar
    qual campo do contexto usar como reference.

    Args:
        intent_type: Tipo de intenção
        ctx: Contexto do envio (OutboundContext ou similar)

    Returns:
        ID de referência ou None se intent é global
    """
    field = INTENT_REFERENCE_FIELD.get(str(intent_type))

    if field is None:
        return None

    # Tenta obter do objeto ou do metadata
    ref = getattr(ctx, field, None)
    if ref is None and hasattr(ctx, "metadata"):
        ref = ctx.metadata.get(field)

    return str(ref) if ref else None


async def limpar_intents_expirados() -> int:
    """
    Remove intents expirados da tabela.

    Deve ser chamado via job diário no scheduler.

    Returns:
        Número de registros removidos
    """
    try:
        response = (
            supabase.table("intent_log")
            .delete()
            .lt("expires_at", datetime.now(timezone.utc).isoformat())
            .execute()
        )

        count = len(response.data) if response.data else 0
        logger.info(f"Intent cleanup: {count} registros expirados removidos")
        return count

    except Exception as e:
        logger.error(f"Erro no cleanup de intents: {e}")
        return 0
