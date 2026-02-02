"""
Reconciliacao bidirecional DB vs Eventos.

Sprint 18 - E11: Data Integrity

Detecta divergencias nas duas direcoes:
- DB → Eventos esperados
- Eventos → DB esperado
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional
from dataclasses import dataclass
from uuid import uuid4

from app.core.timezone import agora_brasilia
from app.services.supabase import supabase
from app.services.slack import enviar_slack

logger = logging.getLogger(__name__)


@dataclass
class DataAnomaly:
    """Anomalia de dados detectada."""
    direction: str              # 'db_to_events' ou 'events_to_db'
    anomaly_type: str           # 'missing_event', 'state_mismatch', etc
    entity_type: str            # 'vaga', 'cliente', 'business_event'
    entity_id: str
    expected: str               # O que deveria existir
    found: Optional[str]        # O que foi encontrado
    details: dict
    severity: str = "warning"

    def to_insert_dict(self, run_id: str) -> dict:
        """Converte para insert no banco."""
        return {
            "anomaly_type": self.anomaly_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "expected": self.expected,
            "found": self.found,
            "severity": self.severity,
            "details": {**self.details, "direction": self.direction},
            "reconciliation_run_id": run_id,
        }


def _determine_severity(anomaly_type: str, entity_type: str) -> str:
    """Determina severidade da anomalia."""
    critical_patterns = [
        ("state_mismatch", "business_event"),  # Evento sem reflexo no DB
        ("missing_event", "vaga"),             # Vaga sem evento
    ]
    for pattern_type, pattern_entity in critical_patterns:
        if anomaly_type == pattern_type and entity_type == pattern_entity:
            return "critical"
    return "warning"


async def run_reconciliation(hours: int = 24) -> List[DataAnomaly]:
    """
    Executa reconciliacao bidirecional.

    Args:
        hours: Janela de tempo

    Returns:
        Lista de anomalias detectadas
    """
    try:
        response = supabase.rpc(
            "reconcile_all",
            {"p_hours": hours}
        ).execute()

        anomalies = []
        for row in response.data or []:
            anomaly = DataAnomaly(
                direction=row["direction"],
                anomaly_type=row["anomaly_type"],
                entity_type=row["entity_type"],
                entity_id=str(row["entity_id"]),
                expected=row["expected"],
                found=row.get("found"),
                details=row.get("details") or {},
            )
            anomaly.severity = _determine_severity(
                anomaly.anomaly_type,
                anomaly.entity_type
            )
            anomalies.append(anomaly)

        return anomalies

    except Exception as e:
        logger.error(f"Erro na reconciliacao: {e}")
        return []


async def persist_anomalies_with_dedup(
    anomalies: List[DataAnomaly],
    run_id: str
) -> dict:
    """
    Persiste anomalias com deduplicacao.

    Anomalias ja existentes (mesma entidade/tipo) tem count incrementado.
    Novas anomalias sao inseridas.

    Returns:
        {"inserted": N, "updated": M}
    """
    if not anomalies:
        return {"inserted": 0, "updated": 0}

    inserted = 0
    updated = 0

    for anomaly in anomalies:
        try:
            # Verificar se anomalia ja existe (nao resolvida)
            existing = (
                supabase.table("data_anomalies")
                .select("id, occurrence_count")
                .eq("anomaly_type", anomaly.anomaly_type)
                .eq("entity_type", anomaly.entity_type)
                .eq("entity_id", anomaly.entity_id)
                .eq("resolved", False)
                .limit(1)
                .execute()
            )

            now = datetime.now(timezone.utc).isoformat()

            if existing.data:
                # Atualizar existente (incrementar count)
                existing_id = existing.data[0]["id"]
                current_count = existing.data[0]["occurrence_count"] or 1
                supabase.table("data_anomalies").update({
                    "last_seen_at": now,
                    "occurrence_count": current_count + 1,
                    "details": {**anomaly.details, "direction": anomaly.direction},
                    "reconciliation_run_id": run_id,
                }).eq("id", existing_id).execute()
                updated += 1
            else:
                # Inserir nova
                insert_data = anomaly.to_insert_dict(run_id)
                insert_data["first_seen_at"] = now
                insert_data["last_seen_at"] = now
                insert_data["occurrence_count"] = 1

                supabase.table("data_anomalies").insert(insert_data).execute()
                inserted += 1

        except Exception as e:
            logger.error(f"Erro ao persistir anomalia {anomaly.entity_id}: {e}")

    return {"inserted": inserted, "updated": updated}


async def notify_anomalies_slack(
    anomalies: List[DataAnomaly],
    persist_result: dict
) -> bool:
    """Notifica anomalias no Slack com sumario."""
    if not anomalies:
        return True

    # Agrupar por direcao e tipo
    by_direction: dict = {"db_to_events": {}, "events_to_db": {}}
    for a in anomalies:
        direction = a.direction
        if a.anomaly_type not in by_direction[direction]:
            by_direction[direction][a.anomaly_type] = 0
        by_direction[direction][a.anomaly_type] += 1

    # Severidade geral
    has_critical = any(a.severity == "critical" for a in anomalies)
    color = "#FF0000" if has_critical else "#FFA500"
    emoji = "🚨" if has_critical else "⚠️"

    # Formatar campos
    fields = []

    # DB → Eventos
    if by_direction["db_to_events"]:
        db_items = [f"{k}: {v}" for k, v in by_direction["db_to_events"].items()]
        fields.append({
            "title": "DB → Eventos",
            "value": "\n".join(db_items),
            "short": True
        })

    # Eventos → DB
    if by_direction["events_to_db"]:
        ev_items = [f"{k}: {v}" for k, v in by_direction["events_to_db"].items()]
        fields.append({
            "title": "Eventos → DB",
            "value": "\n".join(ev_items),
            "short": True
        })

    # Persistencia
    fields.append({
        "title": "Persistencia",
        "value": f"Novas: {persist_result['inserted']}, Recorrentes: {persist_result['updated']}",
        "short": True
    })

    message = {
        "text": f"{emoji} Reconciliacao: {len(anomalies)} divergencia(s)",
        "attachments": [
            {
                "color": color,
                "title": "Resultado da Reconciliacao Bidirecional",
                "fields": fields,
                "footer": "Sprint 18 - Data Integrity",
                "ts": int(agora_brasilia().timestamp()),
            }
        ],
    }

    return await enviar_slack(message)


async def reconciliation_job() -> dict:
    """
    Job diario de reconciliacao bidirecional.

    Executa:
    1. Reconciliacao DB → Eventos
    2. Reconciliacao Eventos → DB
    3. Persiste com deduplicacao
    4. Notifica Slack
    """
    run_id = str(uuid4())
    logger.info(f"Iniciando reconciliacao bidirecional (run_id={run_id})...")

    try:
        # Executar reconciliacao
        anomalies = await run_reconciliation(hours=24)

        if anomalies:
            logger.warning(f"Detectadas {len(anomalies)} divergencias")

            # Persistir com deduplicacao
            persist_result = await persist_anomalies_with_dedup(anomalies, run_id)
            logger.info(
                f"Persistencia: {persist_result['inserted']} novas, "
                f"{persist_result['updated']} atualizadas"
            )

            # Notificar
            await notify_anomalies_slack(anomalies, persist_result)

            # Agrupar por direcao para retorno
            by_dir = {
                "db_to_events": sum(1 for a in anomalies if a.direction == "db_to_events"),
                "events_to_db": sum(1 for a in anomalies if a.direction == "events_to_db"),
            }

            return {
                "status": "warning",
                "run_id": run_id,
                "total_anomalies": len(anomalies),
                "by_direction": by_dir,
                "persist_result": persist_result,
            }
        else:
            logger.info("Nenhuma divergencia detectada")
            return {
                "status": "ok",
                "run_id": run_id,
                "total_anomalies": 0,
            }

    except Exception as e:
        logger.error(f"Erro no job de reconciliacao: {e}")
        return {
            "status": "error",
            "run_id": run_id,
            "error": str(e),
        }


async def listar_anomalias(
    days: int = 7,
    resolved: Optional[bool] = None,
    anomaly_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    severity: Optional[str] = None,
) -> dict:
    """
    Lista anomalias de dados detectadas.

    Returns:
        Dict com summary e lista de anomalias
    """
    try:
        from datetime import timedelta

        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        query = (
            supabase.table("data_anomalies")
            .select("*")
            .gte("last_seen_at", since)
            .order("last_seen_at", desc=True)
        )

        if resolved is not None:
            query = query.eq("resolved", resolved)
        if anomaly_type:
            query = query.eq("anomaly_type", anomaly_type)
        if entity_type:
            query = query.eq("entity_type", entity_type)
        if severity:
            query = query.eq("severity", severity)

        response = query.limit(100).execute()

        # Calcular sumario
        data = response.data or []
        summary: dict = {
            "total": len(data),
            "by_type": {},
            "by_entity": {},
            "by_severity": {"warning": 0, "critical": 0},
            "recurring": sum(1 for a in data if (a.get("occurrence_count") or 1) > 1),
        }
        for a in data:
            t = a.get("anomaly_type", "unknown")
            summary["by_type"][t] = summary["by_type"].get(t, 0) + 1
            e = a.get("entity_type", "unknown")
            summary["by_entity"][e] = summary["by_entity"].get(e, 0) + 1
            s = a.get("severity", "warning")
            summary["by_severity"][s] = summary["by_severity"].get(s, 0) + 1

        return {
            "period_days": days,
            "summary": summary,
            "anomalies": data,
        }

    except Exception as e:
        logger.error(f"Erro ao listar anomalias: {e}")
        return {"period_days": days, "summary": {}, "anomalies": [], "error": str(e)}


async def listar_anomalias_recorrentes(min_count: int = 3) -> dict:
    """
    Lista anomalias recorrentes (detectadas multiplas vezes).

    Util para identificar problemas sistematicos.
    """
    try:
        response = (
            supabase.table("data_anomalies")
            .select("*")
            .eq("resolved", False)
            .gte("occurrence_count", min_count)
            .order("occurrence_count", desc=True)
            .limit(50)
            .execute()
        )

        return {
            "min_count": min_count,
            "total": len(response.data or []),
            "anomalies": response.data or [],
        }

    except Exception as e:
        logger.error(f"Erro ao listar recorrentes: {e}")
        return {"min_count": min_count, "total": 0, "anomalies": [], "error": str(e)}


async def resolver_anomalia(
    anomaly_id: str,
    resolution_notes: str,
    resolved_by: str = "sistema",
) -> dict:
    """Marca anomalia como resolvida."""
    try:
        supabase.table("data_anomalies").update({
            "resolved": True,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "resolved_by": resolved_by,
            "resolution_notes": resolution_notes,
        }).eq("id", anomaly_id).execute()

        return {"status": "ok", "message": "Anomalia resolvida"}

    except Exception as e:
        logger.error(f"Erro ao resolver anomalia: {e}")
        return {"status": "error", "message": str(e)}
