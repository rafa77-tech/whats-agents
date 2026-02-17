"""
Testes para auditoria de cobertura de eventos.

Sprint 18 - Cobertura de audit.py:
- Registro de log de auditoria com campos obrigatorios
- Busca por entidade e periodo
- Filtro por tipo de acao
- Propagacao de falha de persistencia
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

from app.services.business_events.audit import (
    CoverageSource,
    CoverageStatus,
    SourceCoverage,
    InvariantViolation,
    AuditResult,
    audit_pipeline_inbound,
    audit_outbound_coverage,
    audit_status_transitions,
    get_invariant_violations,
    run_full_audit,
)


# =============================================================================
# SourceCoverage
# =============================================================================


class TestSourceCoverage:
    """Testes para o dataclass SourceCoverage."""

    def test_from_row_status_ok(self):
        """Cobertura >= 98% gera status OK."""
        row = {
            "layer": "business_events",
            "notes": "pipeline deve gerar doctor_inbound",
            "expected_count": 100,
            "actual_count": 99,
            "coverage_pct": 99.0,
            "missing_ids": [],
        }
        coverage = SourceCoverage.from_row(row, CoverageSource.PIPELINE_INBOUND)

        assert coverage.status == CoverageStatus.OK
        assert coverage.source == CoverageSource.PIPELINE_INBOUND
        assert coverage.coverage_pct == 99.0
        assert coverage.expected_count == 100

    def test_from_row_status_warning(self):
        """Cobertura >= 90% e < 98% gera status WARNING."""
        row = {
            "layer": "business_events",
            "notes": "outbound cobertura parcial",
            "expected_count": 100,
            "actual_count": 93,
            "coverage_pct": 93.0,
            "missing_ids": ["id-1", "id-2"],
        }
        coverage = SourceCoverage.from_row(row, CoverageSource.AGENTE_OUTBOUND)

        assert coverage.status == CoverageStatus.WARNING

    def test_from_row_status_critical(self):
        """Cobertura < 90% gera status CRITICAL."""
        row = {
            "layer": "business_events",
            "notes": "muitos eventos ausentes",
            "expected_count": 100,
            "actual_count": 70,
            "coverage_pct": 70.0,
            "missing_ids": ["id-1", "id-2", "id-3"],
        }
        coverage = SourceCoverage.from_row(row, CoverageSource.HANDOFF)

        assert coverage.status == CoverageStatus.CRITICAL

    def test_from_row_campos_none(self):
        """Campos None no row sao tratados como zero."""
        row = {
            "layer": "business_events",
            "notes": None,
            "expected_count": None,
            "actual_count": None,
            "coverage_pct": None,
            "missing_ids": None,
        }
        coverage = SourceCoverage.from_row(row, CoverageSource.PIPELINE_INBOUND)

        assert coverage.expected_count == 0
        assert coverage.actual_count == 0
        assert coverage.coverage_pct == 0.0
        assert coverage.missing_ids == []
        assert coverage.status == CoverageStatus.CRITICAL


# =============================================================================
# audit_pipeline_inbound
# =============================================================================


class TestAuditPipelineInbound:
    """Testes para audit_pipeline_inbound."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.audit.supabase")
    async def test_retorna_coverages(self, mock_supabase):
        """Retorna lista de SourceCoverage a partir do RPC."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=24)

        mock_response = MagicMock()
        mock_response.data = [
            {
                "layer": "business_events",
                "notes": "inbound coverage",
                "expected_count": 50,
                "actual_count": 49,
                "coverage_pct": 98.0,
                "missing_ids": [],
            },
        ]
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        coverages = await audit_pipeline_inbound(start, now)

        assert len(coverages) == 1
        assert coverages[0].source == CoverageSource.PIPELINE_INBOUND
        assert coverages[0].status == CoverageStatus.OK

    @pytest.mark.asyncio
    @patch("app.services.business_events.audit.supabase")
    async def test_erro_retorna_lista_vazia(self, mock_supabase):
        """Erro no RPC retorna lista vazia."""
        mock_supabase.rpc.side_effect = Exception("DB error")

        coverages = await audit_pipeline_inbound(
            datetime.now(timezone.utc) - timedelta(hours=24),
            datetime.now(timezone.utc),
        )

        assert coverages == []


# =============================================================================
# audit_outbound_coverage
# =============================================================================


class TestAuditOutboundCoverage:
    """Testes para audit_outbound_coverage."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.audit.supabase")
    async def test_retorna_coverages(self, mock_supabase):
        """Retorna coverages de outbound."""
        mock_response = MagicMock()
        mock_response.data = [
            {
                "layer": "business_events",
                "notes": "outbound layer 1",
                "expected_count": 30,
                "actual_count": 28,
                "coverage_pct": 93.3,
                "missing_ids": ["id-1", "id-2"],
            },
        ]
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        coverages = await audit_outbound_coverage(
            datetime.now(timezone.utc) - timedelta(hours=24),
            datetime.now(timezone.utc),
        )

        assert len(coverages) == 1
        assert coverages[0].source == CoverageSource.AGENTE_OUTBOUND
        assert coverages[0].status == CoverageStatus.WARNING

    @pytest.mark.asyncio
    @patch("app.services.business_events.audit.supabase")
    async def test_erro_retorna_vazio(self, mock_supabase):
        """Erro retorna lista vazia."""
        mock_supabase.rpc.side_effect = Exception("timeout")

        coverages = await audit_outbound_coverage(
            datetime.now(timezone.utc) - timedelta(hours=24),
            datetime.now(timezone.utc),
        )

        assert coverages == []


# =============================================================================
# audit_status_transitions
# =============================================================================


class TestAuditStatusTransitions:
    """Testes para audit_status_transitions."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.audit.supabase")
    async def test_retorna_transicoes(self, mock_supabase):
        """Retorna coverages de transicoes de status."""
        mock_response = MagicMock()
        mock_response.data = [
            {
                "status_from": "aberta",
                "status_to": "reservada",
                "expected_event": "offer_accepted",
                "db_transitions": 20,
                "events_found": 18,
                "coverage_pct": 90.0,
                "missing_vaga_ids": ["v-1", "v-2"],
            },
        ]
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        coverages = await audit_status_transitions(
            datetime.now(timezone.utc) - timedelta(hours=24),
            datetime.now(timezone.utc),
        )

        assert len(coverages) == 1
        assert coverages[0].source == CoverageSource.DB_TRIGGER_STATUS
        assert "aberta" in coverages[0].expectation
        assert "reservada" in coverages[0].expectation

    @pytest.mark.asyncio
    @patch("app.services.business_events.audit.supabase")
    async def test_erro_retorna_vazio(self, mock_supabase):
        """Erro retorna lista vazia."""
        mock_supabase.rpc.side_effect = Exception("connection error")

        coverages = await audit_status_transitions(
            datetime.now(timezone.utc) - timedelta(hours=24),
            datetime.now(timezone.utc),
        )

        assert coverages == []


# =============================================================================
# get_invariant_violations
# =============================================================================


class TestGetInvariantViolations:
    """Testes para get_invariant_violations."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.audit.supabase")
    async def test_retorna_violacoes(self, mock_supabase):
        """Retorna lista de violacoes de invariantes."""
        mock_response = MagicMock()
        mock_response.data = [
            {
                "invariant_name": "offer_before_accept",
                "violation_type": "missing_prerequisite",
                "event_id": "evt-123",
                "vaga_id": "vaga-456",
                "cliente_id": "cli-789",
                "event_ts": "2025-01-15T10:00:00+00:00",
                "details": {"note": "offer_accepted sem offer_made"},
            },
        ]
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        violations = await get_invariant_violations(days=7)

        assert len(violations) == 1
        assert violations[0].invariant_name == "offer_before_accept"
        assert violations[0].vaga_id == "vaga-456"

    @pytest.mark.asyncio
    @patch("app.services.business_events.audit.supabase")
    async def test_event_ts_none(self, mock_supabase):
        """Event_ts None usa datetime atual."""
        mock_response = MagicMock()
        mock_response.data = [
            {
                "invariant_name": "test",
                "violation_type": "test_type",
                "event_id": "evt-1",
                "vaga_id": None,
                "cliente_id": None,
                "event_ts": None,
                "details": {},
            },
        ]
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        violations = await get_invariant_violations(days=7)

        assert len(violations) == 1
        assert violations[0].event_ts is not None

    @pytest.mark.asyncio
    @patch("app.services.business_events.audit.supabase")
    async def test_erro_retorna_lista_vazia(self, mock_supabase):
        """Erro retorna lista vazia."""
        mock_supabase.rpc.side_effect = Exception("DB error")

        violations = await get_invariant_violations(days=7)

        assert violations == []


# =============================================================================
# run_full_audit
# =============================================================================


class TestRunFullAudit:
    """Testes para run_full_audit."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.audit.get_invariant_violations")
    @patch("app.services.business_events.audit.audit_status_transitions")
    @patch("app.services.business_events.audit.audit_outbound_coverage")
    @patch("app.services.business_events.audit.audit_pipeline_inbound")
    async def test_audit_completa_sem_problemas(
        self, mock_inbound, mock_outbound, mock_transitions, mock_violations
    ):
        """Auditoria sem problemas retorna status OK."""
        mock_inbound.return_value = [
            SourceCoverage(
                source=CoverageSource.PIPELINE_INBOUND,
                layer="business_events",
                expectation="test",
                expected_count=100,
                actual_count=100,
                coverage_pct=100.0,
                status=CoverageStatus.OK,
            )
        ]
        mock_outbound.return_value = []
        mock_transitions.return_value = []
        mock_violations.return_value = []

        result = await run_full_audit(hours=24)

        assert result.overall_status == CoverageStatus.OK
        assert result.summary["sources_audited"] == 1
        assert result.summary["sources_ok"] == 1
        assert result.summary["violations_total"] == 0

    @pytest.mark.asyncio
    @patch("app.services.business_events.audit.get_invariant_violations")
    @patch("app.services.business_events.audit.audit_status_transitions")
    @patch("app.services.business_events.audit.audit_outbound_coverage")
    @patch("app.services.business_events.audit.audit_pipeline_inbound")
    async def test_audit_com_critical(
        self, mock_inbound, mock_outbound, mock_transitions, mock_violations
    ):
        """Fonte CRITICAL faz status geral ser CRITICAL."""
        mock_inbound.return_value = [
            SourceCoverage(
                source=CoverageSource.PIPELINE_INBOUND,
                layer="business_events",
                expectation="test",
                expected_count=100,
                actual_count=70,
                coverage_pct=70.0,
                status=CoverageStatus.CRITICAL,
            )
        ]
        mock_outbound.return_value = []
        mock_transitions.return_value = []
        mock_violations.return_value = []

        result = await run_full_audit(hours=24)

        assert result.overall_status == CoverageStatus.CRITICAL

    @pytest.mark.asyncio
    @patch("app.services.business_events.audit.get_invariant_violations")
    @patch("app.services.business_events.audit.audit_status_transitions")
    @patch("app.services.business_events.audit.audit_outbound_coverage")
    @patch("app.services.business_events.audit.audit_pipeline_inbound")
    async def test_audit_muitas_violacoes_eh_critical(
        self, mock_inbound, mock_outbound, mock_transitions, mock_violations
    ):
        """Mais de 10 violacoes faz status geral ser CRITICAL."""
        mock_inbound.return_value = []
        mock_outbound.return_value = []
        mock_transitions.return_value = []
        # 11 violacoes
        mock_violations.return_value = [
            InvariantViolation(
                invariant_name=f"test_{i}",
                violation_type="test",
                event_id=f"evt-{i}",
                vaga_id=None,
                cliente_id=None,
                event_ts=datetime.now(timezone.utc),
                details={},
            )
            for i in range(11)
        ]

        result = await run_full_audit(hours=24)

        assert result.overall_status == CoverageStatus.CRITICAL

    def test_audit_result_to_dict(self):
        """Serializa AuditResult para dicionario."""
        now = datetime.now(timezone.utc)
        result = AuditResult(
            timestamp=now,
            period_start=now - timedelta(hours=24),
            period_end=now,
            overall_status=CoverageStatus.OK,
            coverage_by_source=[],
            invariant_violations=[],
            summary={
                "sources_audited": 0,
                "sources_ok": 0,
                "sources_warning": 0,
                "sources_critical": 0,
                "violations_total": 0,
            },
        )

        d = result.to_dict()

        assert d["overall_status"] == "ok"
        assert "period" in d
        assert d["violations"]["count"] == 0
        assert "summary" in d

    def test_audit_result_group_violations(self):
        """Agrupa violacoes por tipo no to_dict."""
        now = datetime.now(timezone.utc)
        violations = [
            InvariantViolation(
                invariant_name="test",
                violation_type="missing_prerequisite",
                event_id="evt-1",
                vaga_id="v-1",
                cliente_id=None,
                event_ts=now,
                details={},
            ),
            InvariantViolation(
                invariant_name="test",
                violation_type="missing_prerequisite",
                event_id="evt-2",
                vaga_id="v-2",
                cliente_id=None,
                event_ts=now,
                details={},
            ),
            InvariantViolation(
                invariant_name="test",
                violation_type="state_mismatch",
                event_id="evt-3",
                vaga_id="v-3",
                cliente_id=None,
                event_ts=now,
                details={},
            ),
        ]
        result = AuditResult(
            timestamp=now,
            period_start=now - timedelta(hours=24),
            period_end=now,
            overall_status=CoverageStatus.WARNING,
            coverage_by_source=[],
            invariant_violations=violations,
            summary={
                "sources_audited": 0,
                "sources_ok": 0,
                "sources_warning": 0,
                "sources_critical": 0,
                "violations_total": 3,
            },
        )

        d = result.to_dict()

        assert d["violations"]["by_type"]["missing_prerequisite"] == 2
        assert d["violations"]["by_type"]["state_mismatch"] == 1
