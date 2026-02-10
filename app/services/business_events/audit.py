"""
Auditoria de cobertura de eventos por fonte.

Sprint 18 - E10: Data Integrity
Audita expectativas DETERMINISTICAS, nao contagens abstratas.
"""

import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class CoverageSource(Enum):
    """Fonte de eventos."""

    PIPELINE_INBOUND = "pipeline_inbound"
    AGENTE_OUTBOUND = "agente_outbound"
    DB_TRIGGER_STATUS = "db_trigger_status"
    HANDOFF = "handoff"


class CoverageStatus(Enum):
    """Status da cobertura."""

    OK = "ok"  # >= 98%
    WARNING = "warning"  # >= 90%
    CRITICAL = "critical"  # < 90%


@dataclass
class SourceCoverage:
    """Cobertura de uma fonte especifica."""

    source: CoverageSource
    layer: str  # ex: "business_events", "policy_events"
    expectation: str  # O que deveria acontecer
    expected_count: int
    actual_count: int
    coverage_pct: float
    status: CoverageStatus
    missing_ids: List[str] = field(default_factory=list)
    notes: Optional[str] = None

    @classmethod
    def from_row(cls, row: dict, source: CoverageSource) -> "SourceCoverage":
        """Cria a partir de row do banco."""
        coverage = float(row.get("coverage_pct") or 0)
        status = (
            CoverageStatus.OK
            if coverage >= 98
            else CoverageStatus.WARNING
            if coverage >= 90
            else CoverageStatus.CRITICAL
        )
        return cls(
            source=source,
            layer=row.get("layer", "business_events"),
            expectation=row.get("notes", ""),
            expected_count=int(row.get("expected_count") or 0),
            actual_count=int(row.get("actual_count") or 0),
            coverage_pct=coverage,
            status=status,
            missing_ids=[str(x) for x in row.get("missing_ids") or []],
            notes=row.get("notes"),
        )


@dataclass
class InvariantViolation:
    """Violacao de invariante do funil."""

    invariant_name: str
    violation_type: str
    event_id: str
    vaga_id: Optional[str]
    cliente_id: Optional[str]
    event_ts: datetime
    details: dict


@dataclass
class AuditResult:
    """Resultado completo da auditoria."""

    timestamp: datetime
    period_start: datetime
    period_end: datetime
    overall_status: CoverageStatus
    coverage_by_source: List[SourceCoverage]
    invariant_violations: List[InvariantViolation]
    summary: Dict[str, int]

    def to_dict(self) -> dict:
        """Serializa para JSON."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat(),
            },
            "overall_status": self.overall_status.value,
            "coverage": [
                {
                    "source": c.source.value,
                    "layer": c.layer,
                    "expectation": c.expectation,
                    "expected": c.expected_count,
                    "actual": c.actual_count,
                    "coverage_pct": c.coverage_pct,
                    "status": c.status.value,
                    "missing_sample": c.missing_ids[:5],  # Amostra
                }
                for c in self.coverage_by_source
            ],
            "violations": {
                "count": len(self.invariant_violations),
                "by_type": self._group_violations(),
                "sample": [
                    {
                        "type": v.violation_type,
                        "event_id": v.event_id,
                        "vaga_id": v.vaga_id,
                    }
                    for v in self.invariant_violations[:10]
                ],
            },
            "summary": self.summary,
        }

    def _group_violations(self) -> dict:
        """Agrupa violacoes por tipo."""
        grouped: Dict[str, int] = {}
        for v in self.invariant_violations:
            grouped[v.violation_type] = grouped.get(v.violation_type, 0) + 1
        return grouped


async def audit_pipeline_inbound(start: datetime, end: datetime) -> List[SourceCoverage]:
    """Audita cobertura do pipeline inbound."""
    try:
        response = supabase.rpc(
            "audit_pipeline_inbound_coverage",
            {"p_start": start.isoformat(), "p_end": end.isoformat()},
        ).execute()

        return [
            SourceCoverage.from_row(row, CoverageSource.PIPELINE_INBOUND)
            for row in response.data or []
        ]
    except Exception as e:
        logger.error(f"Erro ao auditar pipeline inbound: {e}")
        return []


async def audit_outbound_coverage(start: datetime, end: datetime) -> List[SourceCoverage]:
    """Audita cobertura de outbound (2 layers)."""
    try:
        response = supabase.rpc(
            "audit_outbound_coverage", {"p_start": start.isoformat(), "p_end": end.isoformat()}
        ).execute()

        return [
            SourceCoverage.from_row(row, CoverageSource.AGENTE_OUTBOUND)
            for row in response.data or []
        ]
    except Exception as e:
        logger.error(f"Erro ao auditar outbound: {e}")
        return []


async def audit_status_transitions(start: datetime, end: datetime) -> List[SourceCoverage]:
    """Audita cobertura de transicoes de status."""
    try:
        response = supabase.rpc(
            "audit_status_transition_coverage",
            {"p_start": start.isoformat(), "p_end": end.isoformat()},
        ).execute()

        coverages = []
        for row in response.data or []:
            coverage = float(row.get("coverage_pct") or 0)
            status = (
                CoverageStatus.OK
                if coverage >= 98
                else CoverageStatus.WARNING
                if coverage >= 90
                else CoverageStatus.CRITICAL
            )
            coverages.append(
                SourceCoverage(
                    source=CoverageSource.DB_TRIGGER_STATUS,
                    layer="business_events",
                    expectation=f"{row['status_from']} → {row['status_to']} gera {row['expected_event']}",
                    expected_count=int(row["db_transitions"] or 0),
                    actual_count=int(row["events_found"] or 0),
                    coverage_pct=coverage,
                    status=status,
                    missing_ids=[str(x) for x in row.get("missing_vaga_ids") or []],
                )
            )
        return coverages
    except Exception as e:
        logger.error(f"Erro ao auditar transicoes: {e}")
        return []


async def get_invariant_violations(days: int = 7) -> List[InvariantViolation]:
    """Obtem violacoes de invariantes do funil."""
    try:
        response = supabase.rpc("get_funnel_invariant_violations", {"p_days": days}).execute()

        violations = []
        for row in response.data or []:
            event_ts = row.get("event_ts")
            if isinstance(event_ts, str):
                event_ts = datetime.fromisoformat(event_ts.replace("Z", "+00:00"))
            elif event_ts is None:
                event_ts = datetime.now(timezone.utc)

            violations.append(
                InvariantViolation(
                    invariant_name=row["invariant_name"],
                    violation_type=row["violation_type"],
                    event_id=str(row["event_id"]),
                    vaga_id=str(row["vaga_id"]) if row.get("vaga_id") else None,
                    cliente_id=str(row["cliente_id"]) if row.get("cliente_id") else None,
                    event_ts=event_ts,
                    details=row.get("details") or {},
                )
            )
        return violations
    except Exception as e:
        logger.error(f"Erro ao obter violacoes: {e}")
        return []


async def run_full_audit(hours: int = 24) -> AuditResult:
    """
    Executa auditoria completa de cobertura.

    Args:
        hours: Janela de tempo em horas

    Returns:
        AuditResult com todas as metricas
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)

    # Coletar todas as coberturas
    all_coverage: List[SourceCoverage] = []

    # 1. Pipeline inbound
    inbound = await audit_pipeline_inbound(start, now)
    all_coverage.extend(inbound)

    # 2. Outbound (2 layers)
    outbound = await audit_outbound_coverage(start, now)
    all_coverage.extend(outbound)

    # 3. Transicoes de status
    transitions = await audit_status_transitions(start, now)
    all_coverage.extend(transitions)

    # 4. Violacoes de invariantes
    violations = await get_invariant_violations(days=7)

    # Calcular status geral
    has_critical = any(c.status == CoverageStatus.CRITICAL for c in all_coverage)
    has_warning = any(c.status == CoverageStatus.WARNING for c in all_coverage)

    if has_critical or len(violations) > 10:
        overall = CoverageStatus.CRITICAL
    elif has_warning or len(violations) > 0:
        overall = CoverageStatus.WARNING
    else:
        overall = CoverageStatus.OK

    # Sumario
    summary = {
        "sources_audited": len(all_coverage),
        "sources_ok": sum(1 for c in all_coverage if c.status == CoverageStatus.OK),
        "sources_warning": sum(1 for c in all_coverage if c.status == CoverageStatus.WARNING),
        "sources_critical": sum(1 for c in all_coverage if c.status == CoverageStatus.CRITICAL),
        "violations_total": len(violations),
    }

    return AuditResult(
        timestamp=now,
        period_start=start,
        period_end=now,
        overall_status=overall,
        coverage_by_source=all_coverage,
        invariant_violations=violations,
        summary=summary,
    )
