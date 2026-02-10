"""
Serviço de reconciliação de touches.

Sprint 24 P1: Repair loop para consistência de doctor_state.last_touch_*.

Corrige inconsistências causadas por falhas no _finalizar_envio(),
garantindo que last_touch_* reflita o estado real dos envios.

Características:
- 100% determinístico (usa provider_message_id como chave)
- Idempotente (log com PK em provider_message_id)
- Monotônico (só avança, nunca retrocede)
- Usa enviada_em como touch_at real (não created_at)
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


@dataclass
class ReconciliationResult:
    """Resultado de uma execução de reconciliação."""

    total_candidates: int = 0
    reconciled: int = 0
    skipped_already_processed: int = 0
    skipped_already_newer: int = 0
    skipped_no_change: int = 0
    failed: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    @property
    def summary(self) -> str:
        """Resumo para log/Slack."""
        return (
            f"reconciled={self.reconciled}, "
            f"skipped={self.skipped_already_processed + self.skipped_already_newer + self.skipped_no_change}, "
            f"failed={self.failed}"
        )


async def buscar_candidatos_reconciliacao(
    horas: int = 72,
    limite: int = 1000,
) -> List[dict]:
    """
    Busca envios elegíveis para reconciliação.

    Critérios:
    - status = 'enviada'
    - outcome IN ('SENT', 'BYPASS')
    - provider_message_id IS NOT NULL
    - metadata->>'campanha_id' IS NOT NULL
    - enviada_em >= now() - interval X hours

    Args:
        horas: Janela de busca em horas (default 72h)
        limite: Máximo de registros

    Returns:
        Lista de mensagens elegíveis
    """
    desde = (datetime.now(timezone.utc) - timedelta(hours=horas)).isoformat()

    response = supabase.rpc(
        "buscar_candidatos_touch_reconciliation",
        {
            "p_desde": desde,
            "p_limite": limite,
        },
    ).execute()

    return response.data or []


async def _buscar_doctor_state(cliente_id: str) -> Optional[dict]:
    """Busca estado atual do doctor_state."""
    response = (
        supabase.table("doctor_state")
        .select("last_touch_at, last_touch_campaign_id")
        .eq("cliente_id", cliente_id)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


async def _tentar_claim_log(
    provider_message_id: str,
    mensagem_id: str,
    cliente_id: str,
    campaign_id: int,
    touch_at: datetime,
) -> bool:
    """
    Tenta fazer claim do provider_message_id via INSERT.

    Usa INSERT com status='processing' para garantir atomicidade.
    Se inserir, retorna True (pode processar).
    Se conflitar (PK), retorna False (outro worker já processou).
    """
    try:
        supabase.table("touch_reconciliation_log").insert(
            {
                "provider_message_id": provider_message_id,
                "mensagem_id": mensagem_id,
                "cliente_id": cliente_id,
                "campaign_id": campaign_id,
                "touch_at": touch_at.isoformat() if isinstance(touch_at, datetime) else touch_at,
                "status": "processing",  # Claim inicial
            }
        ).execute()
        return True
    except Exception as e:
        # PK conflict = outro worker já fez claim
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
            return False
        raise


async def _atualizar_log(
    provider_message_id: str,
    status: str,
    previous_touch_at: Optional[datetime] = None,
    previous_campaign_id: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    """Atualiza o log após processamento."""
    update_data = {
        "status": status,
        "previous_touch_at": previous_touch_at.isoformat() if previous_touch_at else None,
        "previous_campaign_id": previous_campaign_id,
        "error": error,
    }
    supabase.table("touch_reconciliation_log").update(update_data).eq(
        "provider_message_id", provider_message_id
    ).execute()


async def reconciliar_touch(
    mensagem: dict,
    skip_claim: bool = False,
) -> str:
    """
    Reconcilia um único touch.

    Lógica:
    1. Faz claim atômico via INSERT no log (evita race condition)
    2. Verifica monotonicidade (só avança, nunca retrocede)
    3. Atualiza doctor_state se necessário
    4. Atualiza log com status final

    Args:
        mensagem: Dict com dados da fila_mensagens
        skip_claim: Se True, pula o claim (usado em testes)

    Returns:
        Status: 'ok', 'skipped_already_newer', 'skipped_no_change',
                'skipped_already_processed', 'failed'
    """
    provider_message_id = mensagem["provider_message_id"]
    cliente_id = mensagem["cliente_id"]
    campaign_id = int(mensagem["metadata"]["campanha_id"])

    # Parse enviada_em
    enviada_em_str = mensagem["enviada_em"]
    if isinstance(enviada_em_str, str):
        enviada_em = datetime.fromisoformat(enviada_em_str.replace("Z", "+00:00"))
    else:
        enviada_em = enviada_em_str

    # 1. Tentar claim atômico (INSERT com status='processing')
    if not skip_claim:
        claimed = await _tentar_claim_log(
            provider_message_id=provider_message_id,
            mensagem_id=mensagem["id"],
            cliente_id=cliente_id,
            campaign_id=campaign_id,
            touch_at=enviada_em,
        )
        if not claimed:
            # Outro worker já processou/está processando
            return "skipped_already_processed"

    # 2. Buscar estado atual
    state = await _buscar_doctor_state(cliente_id)
    previous_touch_at = None
    previous_campaign_id = None

    if state:
        previous_touch_at_str = state.get("last_touch_at")
        if previous_touch_at_str:
            if isinstance(previous_touch_at_str, str):
                previous_touch_at = datetime.fromisoformat(
                    previous_touch_at_str.replace("Z", "+00:00")
                )
            else:
                previous_touch_at = previous_touch_at_str
        previous_campaign_id = state.get("last_touch_campaign_id")

    # 3. Verificar se precisa atualizar (valores iguais = no change)
    if previous_touch_at == enviada_em and previous_campaign_id == campaign_id:
        await _atualizar_log(
            provider_message_id=provider_message_id,
            status="skipped_no_change",
            previous_touch_at=previous_touch_at,
            previous_campaign_id=previous_campaign_id,
        )
        return "skipped_no_change"

    # 4. Verificar monotonicidade (só retrocede se touch atual é MAIS recente)
    if previous_touch_at and previous_touch_at > enviada_em:
        # Já tem touch mais recente, não retroceder
        await _atualizar_log(
            provider_message_id=provider_message_id,
            status="skipped_already_newer",
            previous_touch_at=previous_touch_at,
            previous_campaign_id=previous_campaign_id,
        )
        return "skipped_already_newer"

    # 5. Atualizar doctor_state
    try:
        supabase.table("doctor_state").upsert(
            {
                "cliente_id": cliente_id,
                "last_touch_at": enviada_em.isoformat(),
                "last_touch_method": "campaign",
                "last_touch_campaign_id": campaign_id,
            },
            on_conflict="cliente_id",
        ).execute()

        await _atualizar_log(
            provider_message_id=provider_message_id,
            status="ok",
            previous_touch_at=previous_touch_at,
            previous_campaign_id=previous_campaign_id,
        )

        logger.info(
            f"Touch reconciliado: cliente={cliente_id[:8]}..., "
            f"campaign={campaign_id}, touch_at={enviada_em.isoformat()}"
        )
        return "ok"

    except Exception as e:
        await _atualizar_log(
            provider_message_id=provider_message_id,
            status="failed",
            previous_touch_at=previous_touch_at,
            previous_campaign_id=previous_campaign_id,
            error=str(e)[:500],
        )
        logger.error(f"Erro ao reconciliar touch: {e}")
        return "failed"


async def executar_reconciliacao(
    horas: int = 72,
    limite: int = 1000,
) -> ReconciliationResult:
    """
    Executa reconciliação de touches.

    Processa envios elegíveis e corrige doctor_state.last_touch_*.
    Usa claim atômico (INSERT) para evitar race conditions entre workers.

    Args:
        horas: Janela de busca em horas
        limite: Máximo de registros por execução

    Returns:
        ReconciliationResult com estatísticas
    """
    result = ReconciliationResult()

    try:
        # Buscar candidatos (RPC já exclui os já processados via NOT EXISTS)
        candidatos = await buscar_candidatos_reconciliacao(horas, limite)
        result.total_candidates = len(candidatos)

        logger.info(f"Reconciliação: {len(candidatos)} candidatos encontrados")

        for mensagem in candidatos:
            provider_message_id = mensagem.get("provider_message_id")

            if not provider_message_id:
                continue

            # Reconciliar (claim atômico é feito internamente)
            try:
                status = await reconciliar_touch(mensagem)

                if status == "ok":
                    result.reconciled += 1
                elif status == "skipped_already_newer":
                    result.skipped_already_newer += 1
                elif status == "skipped_no_change":
                    result.skipped_no_change += 1
                elif status == "skipped_already_processed":
                    result.skipped_already_processed += 1
                elif status == "failed":
                    result.failed += 1

            except Exception as e:
                result.failed += 1
                result.errors.append(f"{provider_message_id}: {str(e)[:100]}")
                logger.error(f"Erro ao processar {provider_message_id}: {e}")

        logger.info(f"Reconciliação concluída: {result.summary}")

    except Exception as e:
        logger.error(f"Erro na reconciliação: {e}", exc_info=True)
        result.errors.append(f"Erro geral: {str(e)}")

    return result


async def limpar_logs_antigos(dias: int = 30) -> int:
    """
    Remove logs de reconciliação antigos.

    Args:
        dias: Manter logs dos últimos X dias

    Returns:
        Número de registros removidos
    """
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()

    try:
        response = (
            supabase.table("touch_reconciliation_log").delete().lt("processed_at", desde).execute()
        )
        count = len(response.data) if response.data else 0
        logger.info(f"Logs de reconciliação removidos: {count}")
        return count

    except Exception as e:
        logger.error(f"Erro ao limpar logs: {e}")
        return 0


@dataclass
class ReclaimResult:
    """Resultado de reclaim de processing travado."""

    found: int = 0
    reclaimed: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


async def reclamar_processing_travado(
    minutos_timeout: int = 15,
) -> ReclaimResult:
    """
    P1.2: Reclama entries travadas em status='processing'.

    Se um worker crashar entre claim e atualização final,
    a entry fica em 'processing' eternamente. Esta função
    marca essas entries como 'abandoned' para permitir
    reprocessamento ou auditoria.

    Args:
        minutos_timeout: Minutos após os quais 'processing' é considerado travado

    Returns:
        ReclaimResult com estatísticas
    """
    result = ReclaimResult()
    timeout_threshold = (
        datetime.now(timezone.utc) - timedelta(minutes=minutos_timeout)
    ).isoformat()

    try:
        # Buscar processing travados
        response = (
            supabase.table("touch_reconciliation_log")
            .select("provider_message_id, processed_at")
            .eq("status", "processing")
            .lt("processed_at", timeout_threshold)
            .execute()
        )

        stuck = response.data or []
        result.found = len(stuck)

        if not stuck:
            logger.info("Nenhum processing travado encontrado")
            return result

        logger.warning(f"Encontrados {len(stuck)} processing travados")

        # Marcar como abandoned
        for entry in stuck:
            try:
                supabase.table("touch_reconciliation_log").update(
                    {
                        "status": "abandoned",
                        "error": f"Timeout após {minutos_timeout}min sem finalização",
                    }
                ).eq("provider_message_id", entry["provider_message_id"]).execute()
                result.reclaimed += 1
            except Exception as e:
                result.errors.append(f"{entry['provider_message_id']}: {str(e)[:100]}")
                logger.error(f"Erro ao reclamar {entry['provider_message_id']}: {e}")

        logger.info(
            f"Reclaim concluído: found={result.found}, "
            f"reclaimed={result.reclaimed}, errors={len(result.errors)}"
        )

    except Exception as e:
        logger.error(f"Erro no reclaim: {e}", exc_info=True)
        result.errors.append(f"Erro geral: {str(e)}")

    return result


async def contar_processing_stuck(minutos_timeout: int = 15) -> int:
    """
    Conta entries em status='processing' que passaram do timeout.

    Útil para métricas/alertas sem fazer reclaim.

    Args:
        minutos_timeout: Minutos após os quais considerar stuck

    Returns:
        Contagem de entries stuck
    """
    timeout_threshold = (
        datetime.now(timezone.utc) - timedelta(minutes=minutos_timeout)
    ).isoformat()

    try:
        response = (
            supabase.table("touch_reconciliation_log")
            .select("provider_message_id", count="exact")
            .eq("status", "processing")
            .lt("processed_at", timeout_threshold)
            .execute()
        )
        return response.count or 0
    except Exception:
        return -1  # Indica erro
