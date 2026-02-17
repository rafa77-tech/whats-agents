"""
Testes para reconciliacao bidirecional DB vs Eventos.

Sprint 18 - Cobertura de reconciliation.py:
- Detecta eventos duplicados
- Detecta eventos ausentes
- Dados consistentes: sem divergencias
- Geracao de relatorio de reconciliacao
- Persistencia com deduplicacao
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

from app.services.business_events.reconciliation import (
    DataAnomaly,
    _determine_severity,
    run_reconciliation,
    persist_anomalies_with_dedup,
    reconciliation_job,
    listar_anomalias,
    listar_anomalias_recorrentes,
    resolver_anomalia,
)


# =============================================================================
# DataAnomaly
# =============================================================================


class TestDataAnomaly:
    """Testes para o dataclass DataAnomaly."""

    def test_to_insert_dict(self):
        """Converte anomalia para formato de insercao no banco."""
        anomaly = DataAnomaly(
            direction="db_to_events",
            anomaly_type="missing_event",
            entity_type="vaga",
            entity_id="vaga-123",
            expected="offer_made event",
            found=None,
            details={"status": "reservada"},
            severity="critical",
        )

        d = anomaly.to_insert_dict("run-456")

        assert d["anomaly_type"] == "missing_event"
        assert d["entity_type"] == "vaga"
        assert d["entity_id"] == "vaga-123"
        assert d["expected"] == "offer_made event"
        assert d["found"] is None
        assert d["severity"] == "critical"
        assert d["reconciliation_run_id"] == "run-456"
        assert d["details"]["direction"] == "db_to_events"


# =============================================================================
# _determine_severity
# =============================================================================


class TestDetermineSeverity:
    """Testes para _determine_severity."""

    def test_state_mismatch_business_event_critical(self):
        """State mismatch em business_event eh critico."""
        assert _determine_severity("state_mismatch", "business_event") == "critical"

    def test_missing_event_vaga_critical(self):
        """Missing event em vaga eh critico."""
        assert _determine_severity("missing_event", "vaga") == "critical"

    def test_outros_sao_warning(self):
        """Combinacoes nao mapeadas sao warning."""
        assert _determine_severity("missing_event", "cliente") == "warning"
        assert _determine_severity("state_mismatch", "vaga") == "warning"
        assert _determine_severity("unknown_type", "unknown_entity") == "warning"


# =============================================================================
# run_reconciliation
# =============================================================================


class TestRunReconciliation:
    """Testes para run_reconciliation."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.reconciliation.supabase")
    async def test_detecta_anomalias(self, mock_supabase):
        """Detecta anomalias retornadas pelo RPC."""
        mock_response = MagicMock()
        mock_response.data = [
            {
                "direction": "db_to_events",
                "anomaly_type": "missing_event",
                "entity_type": "vaga",
                "entity_id": "vaga-123",
                "expected": "offer_made",
                "found": None,
                "details": {},
            },
            {
                "direction": "events_to_db",
                "anomaly_type": "state_mismatch",
                "entity_type": "business_event",
                "entity_id": "evt-456",
                "expected": "status reservada",
                "found": "status aberta",
                "details": {"db_status": "aberta"},
            },
        ]
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        anomalies = await run_reconciliation(hours=24)

        assert len(anomalies) == 2
        # Verifica severidade calculada
        assert anomalies[0].severity == "critical"  # missing_event + vaga
        assert anomalies[1].severity == "critical"  # state_mismatch + business_event

    @pytest.mark.asyncio
    @patch("app.services.business_events.reconciliation.supabase")
    async def test_sem_divergencias(self, mock_supabase):
        """Dados consistentes retornam lista vazia."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        anomalies = await run_reconciliation(hours=24)

        assert anomalies == []

    @pytest.mark.asyncio
    @patch("app.services.business_events.reconciliation.supabase")
    async def test_erro_retorna_vazio(self, mock_supabase):
        """Erro no RPC retorna lista vazia."""
        mock_supabase.rpc.side_effect = Exception("timeout")

        anomalies = await run_reconciliation(hours=24)

        assert anomalies == []

    @pytest.mark.asyncio
    @patch("app.services.business_events.reconciliation.supabase")
    async def test_response_data_none(self, mock_supabase):
        """Response com data=None retorna lista vazia."""
        mock_response = MagicMock()
        mock_response.data = None
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        anomalies = await run_reconciliation(hours=24)

        assert anomalies == []


# =============================================================================
# persist_anomalies_with_dedup
# =============================================================================


class TestPersistAnomaliesWithDedup:
    """Testes para persist_anomalies_with_dedup."""

    @pytest.mark.asyncio
    async def test_lista_vazia_retorna_zeros(self):
        """Lista vazia de anomalias retorna contadores zerados."""
        result = await persist_anomalies_with_dedup([], "run-123")

        assert result == {"inserted": 0, "updated": 0}

    @pytest.mark.asyncio
    @patch("app.services.business_events.reconciliation.supabase")
    async def test_insere_nova_anomalia(self, mock_supabase):
        """Anomalia nova eh inserida no banco."""
        # Simula que nao existe anomalia previa
        mock_select_response = MagicMock()
        mock_select_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = (
            mock_select_response
        )

        # Simula insert
        mock_insert_response = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.return_value = (
            mock_insert_response
        )

        anomaly = DataAnomaly(
            direction="db_to_events",
            anomaly_type="missing_event",
            entity_type="vaga",
            entity_id="vaga-123",
            expected="offer_made",
            found=None,
            details={},
        )

        result = await persist_anomalies_with_dedup([anomaly], "run-456")

        assert result["inserted"] == 1
        assert result["updated"] == 0

    @pytest.mark.asyncio
    @patch("app.services.business_events.reconciliation.supabase")
    async def test_atualiza_anomalia_existente(self, mock_supabase):
        """Anomalia ja existente incrementa occurrence_count."""
        # Simula que existe anomalia previa
        mock_select_response = MagicMock()
        mock_select_response.data = [{"id": "anomaly-existing", "occurrence_count": 3}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = (
            mock_select_response
        )

        # Simula update
        mock_update_response = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            mock_update_response
        )

        anomaly = DataAnomaly(
            direction="db_to_events",
            anomaly_type="missing_event",
            entity_type="vaga",
            entity_id="vaga-123",
            expected="offer_made",
            found=None,
            details={},
        )

        result = await persist_anomalies_with_dedup([anomaly], "run-456")

        assert result["inserted"] == 0
        assert result["updated"] == 1

    @pytest.mark.asyncio
    @patch("app.services.business_events.reconciliation.supabase")
    async def test_erro_persistencia_nao_propaga(self, mock_supabase):
        """Erro ao persistir uma anomalia nao impede as demais."""
        # Primeira anomalia: erro
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.side_effect = [
            Exception("DB error"),
            MagicMock(data=[]),
        ]

        # Segunda anomalia: sucesso no insert
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        anomalies = [
            DataAnomaly(
                direction="db_to_events",
                anomaly_type="missing_event",
                entity_type="vaga",
                entity_id="vaga-1",
                expected="event",
                found=None,
                details={},
            ),
            DataAnomaly(
                direction="db_to_events",
                anomaly_type="missing_event",
                entity_type="vaga",
                entity_id="vaga-2",
                expected="event",
                found=None,
                details={},
            ),
        ]

        result = await persist_anomalies_with_dedup(anomalies, "run-789")

        # Primeira falhou, segunda inserida
        assert result["inserted"] == 1


# =============================================================================
# reconciliation_job
# =============================================================================


class TestReconciliationJob:
    """Testes para reconciliation_job."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.reconciliation.notify_anomalies_slack", new_callable=AsyncMock)
    @patch("app.services.business_events.reconciliation.persist_anomalies_with_dedup", new_callable=AsyncMock)
    @patch("app.services.business_events.reconciliation.run_reconciliation", new_callable=AsyncMock)
    async def test_job_sem_anomalias(self, mock_recon, mock_persist, mock_notify):
        """Job sem anomalias retorna status ok."""
        mock_recon.return_value = []

        result = await reconciliation_job()

        assert result["status"] == "ok"
        assert result["total_anomalies"] == 0
        mock_persist.assert_not_called()
        mock_notify.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.business_events.reconciliation.notify_anomalies_slack", new_callable=AsyncMock)
    @patch("app.services.business_events.reconciliation.persist_anomalies_with_dedup", new_callable=AsyncMock)
    @patch("app.services.business_events.reconciliation.run_reconciliation", new_callable=AsyncMock)
    async def test_job_com_anomalias(self, mock_recon, mock_persist, mock_notify):
        """Job com anomalias persiste, notifica e retorna status warning."""
        anomalies = [
            DataAnomaly(
                direction="db_to_events",
                anomaly_type="missing_event",
                entity_type="vaga",
                entity_id="vaga-1",
                expected="event",
                found=None,
                details={},
            ),
        ]
        mock_recon.return_value = anomalies
        mock_persist.return_value = {"inserted": 1, "updated": 0}
        mock_notify.return_value = True

        result = await reconciliation_job()

        assert result["status"] == "warning"
        assert result["total_anomalies"] == 1
        assert result["by_direction"]["db_to_events"] == 1
        mock_persist.assert_called_once()
        mock_notify.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.business_events.reconciliation.run_reconciliation", new_callable=AsyncMock)
    async def test_job_erro_retorna_error(self, mock_recon):
        """Erro no job retorna status error."""
        mock_recon.side_effect = Exception("fatal error")

        result = await reconciliation_job()

        assert result["status"] == "error"
        assert "error" in result


# =============================================================================
# listar_anomalias
# =============================================================================


class TestListarAnomalias:
    """Testes para listar_anomalias."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.reconciliation.supabase")
    async def test_lista_com_filtros(self, mock_supabase):
        """Lista anomalias com filtros aplicados."""
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "a-1",
                "anomaly_type": "missing_event",
                "entity_type": "vaga",
                "severity": "critical",
                "occurrence_count": 5,
            },
        ]
        mock_supabase.table.return_value.select.return_value.gte.return_value.order.return_value.eq.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = (
            mock_response
        )

        result = await listar_anomalias(
            days=7,
            resolved=False,
            anomaly_type="missing_event",
            entity_type="vaga",
            severity="critical",
        )

        assert result["summary"]["total"] == 1
        assert result["summary"]["by_type"]["missing_event"] == 1
        assert result["summary"]["recurring"] == 1

    @pytest.mark.asyncio
    @patch("app.services.business_events.reconciliation.supabase")
    async def test_erro_retorna_vazio(self, mock_supabase):
        """Erro retorna estrutura vazia com mensagem de erro."""
        mock_supabase.table.side_effect = Exception("DB error")

        result = await listar_anomalias(days=7)

        assert result["anomalies"] == []
        assert "error" in result


# =============================================================================
# resolver_anomalia
# =============================================================================


class TestResolverAnomalia:
    """Testes para resolver_anomalia."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.reconciliation.supabase")
    async def test_resolve_com_sucesso(self, mock_supabase):
        """Resolve anomalia com sucesso."""
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            MagicMock()
        )

        result = await resolver_anomalia("anomaly-1", "Falso positivo", "admin")

        assert result["status"] == "ok"

    @pytest.mark.asyncio
    @patch("app.services.business_events.reconciliation.supabase")
    async def test_resolve_com_erro(self, mock_supabase):
        """Erro ao resolver retorna mensagem."""
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = (
            Exception("DB error")
        )

        result = await resolver_anomalia("anomaly-1", "test", "admin")

        assert result["status"] == "error"
