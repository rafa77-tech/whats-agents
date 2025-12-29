"""
Testes do serviço de reconciliação de touches.

Sprint 24 P1: Checklist de aceite.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.touch_reconciliation import (
    reconciliar_touch,
    executar_reconciliacao,
    ReconciliationResult,
    _tentar_claim_log,
    _buscar_doctor_state,
)


class TestReconciliarTouch:
    """Testes da função reconciliar_touch."""

    @pytest.fixture
    def mensagem_valida(self):
        """Mensagem válida para reconciliação."""
        return {
            "id": "msg-123",
            "cliente_id": "cliente-456",
            "provider_message_id": "wa_abc123",
            "enviada_em": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "metadata": {"campanha_id": "100"},
        }

    @pytest.mark.asyncio
    @patch("app.services.touch_reconciliation._buscar_doctor_state")
    @patch("app.services.touch_reconciliation._atualizar_log")
    @patch("app.services.touch_reconciliation.supabase")
    async def test_reconcilia_quando_nao_tem_touch_anterior(
        self,
        mock_supabase,
        mock_atualizar_log,
        mock_buscar_state,
        mensagem_valida,
    ):
        """
        Checklist 2: Sem touch anterior, deve reconciliar.

        doctor_state.last_touch_at IS NULL → reconcilia
        """
        mock_buscar_state.return_value = None  # Sem state anterior
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock()
        mock_atualizar_log.return_value = None

        # skip_claim=True para testes unitários
        status = await reconciliar_touch(mensagem_valida, skip_claim=True)

        assert status == "ok"
        mock_supabase.table.assert_called_with("doctor_state")
        mock_atualizar_log.assert_called_once()
        call_args = mock_atualizar_log.call_args[1]
        assert call_args["status"] == "ok"

    @pytest.mark.asyncio
    @patch("app.services.touch_reconciliation._buscar_doctor_state")
    @patch("app.services.touch_reconciliation._atualizar_log")
    @patch("app.services.touch_reconciliation.supabase")
    async def test_reconcilia_quando_touch_anterior_mais_antigo(
        self,
        mock_supabase,
        mock_atualizar_log,
        mock_buscar_state,
        mensagem_valida,
    ):
        """
        Checklist 2: Touch anterior mais antigo, deve reconciliar.

        doctor_state.last_touch_at < enviada_em → reconcilia
        """
        # Touch anterior de 2 dias atrás
        touch_antigo = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        mock_buscar_state.return_value = {
            "last_touch_at": touch_antigo,
            "last_touch_campaign_id": 50,
        }
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock()
        mock_atualizar_log.return_value = None

        status = await reconciliar_touch(mensagem_valida, skip_claim=True)

        assert status == "ok"
        # Verifica que registrou o valor anterior
        call_args = mock_atualizar_log.call_args[1]
        assert call_args["previous_campaign_id"] == 50

    @pytest.mark.asyncio
    @patch("app.services.touch_reconciliation._buscar_doctor_state")
    @patch("app.services.touch_reconciliation._atualizar_log")
    async def test_nao_retrocede_quando_touch_mais_recente(
        self,
        mock_atualizar_log,
        mock_buscar_state,
        mensagem_valida,
    ):
        """
        Checklist 4: Não deve retroceder se touch atual é mais recente.

        doctor_state.last_touch_at > enviada_em → skip
        """
        # Touch atual mais recente que a mensagem
        touch_recente = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        mock_buscar_state.return_value = {
            "last_touch_at": touch_recente,
            "last_touch_campaign_id": 200,
        }
        mock_atualizar_log.return_value = None

        status = await reconciliar_touch(mensagem_valida, skip_claim=True)

        assert status == "skipped_already_newer"
        call_args = mock_atualizar_log.call_args[1]
        assert call_args["status"] == "skipped_already_newer"

    @pytest.mark.asyncio
    @patch("app.services.touch_reconciliation._buscar_doctor_state")
    @patch("app.services.touch_reconciliation._atualizar_log")
    async def test_skip_quando_valores_iguais(
        self,
        mock_atualizar_log,
        mock_buscar_state,
        mensagem_valida,
    ):
        """
        Não deve atualizar se valores já são iguais.
        """
        # Mesmo touch_at e campaign_id
        mock_buscar_state.return_value = {
            "last_touch_at": mensagem_valida["enviada_em"],
            "last_touch_campaign_id": 100,
        }
        mock_atualizar_log.return_value = None

        status = await reconciliar_touch(mensagem_valida, skip_claim=True)

        assert status == "skipped_no_change"


class TestClaimAtomico:
    """Testes do mecanismo de claim atômico para concorrência."""

    @pytest.mark.asyncio
    @patch("app.services.touch_reconciliation.supabase")
    async def test_claim_sucesso_retorna_true(self, mock_supabase):
        """
        Claim bem-sucedido deve retornar True.
        """
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        result = await _tentar_claim_log(
            provider_message_id="wa_123",
            mensagem_id="msg-1",
            cliente_id="cli-1",
            campaign_id=100,
            touch_at=datetime.now(timezone.utc),
        )

        assert result is True

    @pytest.mark.asyncio
    @patch("app.services.touch_reconciliation.supabase")
    async def test_claim_duplicado_retorna_false(self, mock_supabase):
        """
        Claim duplicado (PK conflict) deve retornar False.
        """
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception(
            "duplicate key value violates unique constraint"
        )

        result = await _tentar_claim_log(
            provider_message_id="wa_123",
            mensagem_id="msg-1",
            cliente_id="cli-1",
            campaign_id=100,
            touch_at=datetime.now(timezone.utc),
        )

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.touch_reconciliation._tentar_claim_log")
    @patch("app.services.touch_reconciliation._buscar_doctor_state")
    async def test_reconciliar_retorna_skipped_quando_claim_falha(
        self,
        mock_buscar_state,
        mock_tentar_claim,
    ):
        """
        Se claim falha, deve retornar skipped_already_processed.
        """
        mock_tentar_claim.return_value = False  # Outro worker já fez claim

        mensagem = {
            "id": "msg-123",
            "cliente_id": "cliente-456",
            "provider_message_id": "wa_abc123",
            "enviada_em": datetime.now(timezone.utc).isoformat(),
            "metadata": {"campanha_id": "100"},
        }

        status = await reconciliar_touch(mensagem, skip_claim=False)

        assert status == "skipped_already_processed"
        # Não deve buscar doctor_state se claim falhou
        mock_buscar_state.assert_not_called()


class TestExecutarReconciliacao:
    """Testes da função executar_reconciliacao."""

    @pytest.mark.asyncio
    @patch("app.services.touch_reconciliation.buscar_candidatos_reconciliacao")
    @patch("app.services.touch_reconciliation.reconciliar_touch")
    async def test_skip_ja_processados(
        self,
        mock_reconciliar,
        mock_buscar_candidatos,
    ):
        """
        Checklist 3: Rodar novamente deve pular processados.

        Candidatos já processados devem ser contados como skipped_already_processed.
        """
        mock_buscar_candidatos.return_value = [
            {"provider_message_id": "wa_1", "id": "1", "cliente_id": "c1", "enviada_em": "2024-01-01T00:00:00+00:00", "metadata": {"campanha_id": "100"}},
            {"provider_message_id": "wa_2", "id": "2", "cliente_id": "c2", "enviada_em": "2024-01-01T00:00:00+00:00", "metadata": {"campanha_id": "100"}},
        ]
        # wa_1 já foi processado (claim falha), wa_2 é novo
        mock_reconciliar.side_effect = ["skipped_already_processed", "ok"]

        result = await executar_reconciliacao(horas=24, limite=100)

        assert result.total_candidates == 2
        assert result.skipped_already_processed == 1
        assert result.reconciled == 1
        assert mock_reconciliar.call_count == 2

    @pytest.mark.asyncio
    @patch("app.services.touch_reconciliation.buscar_candidatos_reconciliacao")
    async def test_fila_vazia_retorna_zeros(self, mock_buscar):
        """Fila vazia deve retornar resultado com zeros."""
        mock_buscar.return_value = []

        result = await executar_reconciliacao()

        assert result.total_candidates == 0
        assert result.reconciled == 0


class TestContactCount:
    """
    Testes para garantir que contact_count_7d não é tocado.

    Checklist 5: contact_count_7d não deve ser incrementado pelo job.
    """

    @pytest.mark.asyncio
    @patch("app.services.touch_reconciliation._buscar_doctor_state")
    @patch("app.services.touch_reconciliation._atualizar_log")
    @patch("app.services.touch_reconciliation.supabase")
    async def test_upsert_nao_inclui_contact_count(
        self,
        mock_supabase,
        mock_atualizar_log,
        mock_buscar_state,
    ):
        """
        O upsert do doctor_state não deve incluir contact_count_7d.
        """
        mock_buscar_state.return_value = None
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock()
        mock_atualizar_log.return_value = None

        mensagem = {
            "id": "msg-123",
            "cliente_id": "cliente-456",
            "provider_message_id": "wa_abc123",
            "enviada_em": datetime.now(timezone.utc).isoformat(),
            "metadata": {"campanha_id": "100"},
        }

        await reconciliar_touch(mensagem, skip_claim=True)

        # Verificar que o upsert não inclui contact_count_7d
        upsert_call = mock_supabase.table.return_value.upsert.call_args[0][0]
        assert "contact_count_7d" not in upsert_call
        assert "last_touch_at" in upsert_call
        assert "last_touch_campaign_id" in upsert_call


class TestReconciliationResult:
    """Testes do dataclass ReconciliationResult."""

    def test_summary_format(self):
        """Summary deve ter formato correto para log/Slack."""
        result = ReconciliationResult(
            total_candidates=100,
            reconciled=50,
            skipped_already_processed=30,
            skipped_already_newer=10,
            skipped_no_change=5,
            failed=5,
        )

        summary = result.summary

        assert "reconciled=50" in summary
        assert "skipped=45" in summary  # 30 + 10 + 5
        assert "failed=5" in summary
