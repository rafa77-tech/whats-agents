"""
Deduplicação de mensagens outbound.

Sprint 18.1 - C1: Evita duplicatas em timeout/retry.

Nível 1 (simples):
- Gera dedupe_key determinística
- Verifica no banco antes de enviar
- Marca como sent/failed após envio
- Emite OUTBOUND_DEDUPED para auditoria
"""
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

from app.core.tasks import safe_create_task
from app.services.supabase import supabase
from app.services.business_events import emit_event, BusinessEvent, EventType, EventSource

logger = logging.getLogger(__name__)


# Janela de deduplicação por método
DEDUPE_WINDOWS = {
    "campaign": 60,       # 60 minutos (campanhas são únicas por hora)
    "followup": 60,       # 60 minutos
    "reactivation": 120,  # 2 horas
    "reply": 5,           # 5 minutos (replies podem ser rápidos)
    "button": 5,          # 5 minutos
    "command": 5,         # 5 minutos
    "manual": 10,         # 10 minutos
}

DEFAULT_WINDOW = 30  # 30 minutos padrão


def gerar_dedupe_key(
    cliente_id: str,
    method: str,
    content_hash: str = None,
    template_ref: str = None,
) -> str:
    """
    Gera chave de deduplicação determinística.

    A chave inclui:
    - cliente_id: quem recebe
    - method: tipo de envio (campaign, reply, etc)
    - content_hash ou template_ref: identificador do conteúdo
    - window_bucket: janela temporal para permitir retry legítimo depois

    Args:
        cliente_id: UUID do cliente
        method: Método de envio
        content_hash: Hash do conteúdo (opcional)
        template_ref: Referência do template/vaga (opcional)

    Returns:
        Hash SHA256 truncado (32 chars)
    """
    window_minutes = DEDUPE_WINDOWS.get(method, DEFAULT_WINDOW)
    now = datetime.now(timezone.utc)

    # Bucket temporal: arredonda para janela
    bucket_minutes = (now.hour * 60 + now.minute) // window_minutes * window_minutes
    window_bucket = f"{now.strftime('%Y%m%d')}{bucket_minutes:04d}"

    # Conteúdo identificador
    content_id = content_hash or template_ref or "none"

    raw = f"{cliente_id}:{method}:{content_id}:{window_bucket}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


async def verificar_e_reservar(
    cliente_id: str,
    method: str,
    conversation_id: str = None,
    content_hash: str = None,
    template_ref: str = None,
) -> Tuple[bool, str, Optional[str]]:
    """
    Verifica se pode enviar e reserva slot se disponível.

    Tenta inserir no banco com dedupe_key único.
    Se já existe, é duplicata.

    Args:
        cliente_id: UUID do cliente
        method: Método de envio
        conversation_id: UUID da conversa (opcional)
        content_hash: Hash do conteúdo (opcional)
        template_ref: Referência do template (opcional)

    Returns:
        Tuple (pode_enviar, dedupe_key, motivo_se_bloqueado)
    """
    dedupe_key = gerar_dedupe_key(
        cliente_id=cliente_id,
        method=method,
        content_hash=content_hash,
        template_ref=template_ref,
    )

    try:
        # Tentar inserir - falha se duplicata (unique constraint)
        response = supabase.table("outbound_dedupe").insert({
            "dedupe_key": dedupe_key,
            "cliente_id": cliente_id,
            "conversation_id": conversation_id,
            "method": method,
            "status": "queued",
        }).execute()

        if response.data:
            logger.debug(f"Dedupe reservado: {dedupe_key[:16]}... para {method}")
            return True, dedupe_key, None

        # Inserção falhou sem exception - verificar motivo
        return False, dedupe_key, "insert_failed"

    except Exception as e:
        error_str = str(e).lower()

        # Violação de unique constraint = duplicata
        if "unique" in error_str or "duplicate" in error_str or "23505" in error_str:
            logger.info(
                f"Dedupe detectou duplicata: {dedupe_key[:16]}... para cliente {cliente_id[:8]}",
                extra={
                    "event": "outbound_deduped",
                    "dedupe_key": dedupe_key,
                    "cliente_id": cliente_id,
                    "method": method,
                }
            )

            # Registrar como deduped para métricas
            try:
                await _registrar_deduped(dedupe_key)
            except Exception:
                pass

            # Emitir business_event para auditoria (Sprint 18.1)
            safe_create_task(
                emit_event(BusinessEvent(
                    event_type=EventType.OUTBOUND_DEDUPED,
                    source=EventSource.BACKEND,
                    cliente_id=cliente_id,
                    conversation_id=conversation_id,
                    dedupe_key=f"deduped:{cliente_id}:{dedupe_key[:16]}",
                    event_props={
                        "dedupe_key": dedupe_key,
                        "method": method,
                        "reason": "duplicate_within_window",
                    },
                )),
                name="emit_outbound_deduped"
            )

            return False, dedupe_key, "duplicata"

        # Outro erro - loga mas permite envio (fail-open)
        logger.warning(f"Erro no dedupe, permitindo envio: {e}")
        return True, dedupe_key, None


async def marcar_enviado(dedupe_key: str) -> None:
    """
    Marca entrada como enviada com sucesso.

    Args:
        dedupe_key: Chave de deduplicação
    """
    try:
        supabase.table("outbound_dedupe").update({
            "status": "sent",
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }).eq("dedupe_key", dedupe_key).execute()
    except Exception as e:
        logger.warning(f"Erro ao marcar dedupe como enviado: {e}")


async def marcar_falha(dedupe_key: str, error: str) -> None:
    """
    Marca entrada como falha.

    Args:
        dedupe_key: Chave de deduplicação
        error: Mensagem de erro
    """
    try:
        supabase.table("outbound_dedupe").update({
            "status": "failed",
            "error": error[:500],  # Truncar erro longo
        }).eq("dedupe_key", dedupe_key).execute()
    except Exception as e:
        logger.warning(f"Erro ao marcar dedupe como falha: {e}")


async def _registrar_deduped(dedupe_key: str) -> None:
    """Atualiza entrada existente para registrar tentativa de duplicata."""
    try:
        # Incrementar contador ou atualizar timestamp
        supabase.table("outbound_dedupe").update({
            "status": "deduped",
        }).eq("dedupe_key", dedupe_key).eq("status", "sent").execute()
    except Exception:
        pass


async def limpar_entradas_antigas() -> int:
    """
    Remove entradas antigas (> 24h) para manter tabela leve.

    Returns:
        Número de entradas removidas
    """
    try:
        response = supabase.rpc("cleanup_old_dedupe_entries").execute()
        logger.info("Limpeza de dedupe executada")
        return 0  # RPC não retorna count
    except Exception as e:
        logger.warning(f"Erro ao limpar dedupe: {e}")
        return 0
