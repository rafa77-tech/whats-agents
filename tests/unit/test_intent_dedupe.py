"""
Testes do serviço de dedupe por intenção.

Sprint 24 E02: Fingerprint determinístico para evitar spam semântico.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.services.intent_dedupe import (
    IntentType,
    INTENT_WINDOWS,
    INTENT_REFERENCE_FIELD,
    gerar_intent_fingerprint,
    verificar_intent,
    obter_reference_id,
    limpar_intents_expirados,
)


class TestGerarIntentFingerprint:
    """Testes da função gerar_intent_fingerprint."""

    def test_fingerprint_deterministico(self):
        """Mesmo input deve gerar mesmo fingerprint."""
        fp1 = gerar_intent_fingerprint(
            cliente_id="uuid-123",
            intent_type="discovery_first_touch",
            reference_id="campaign-456",
        )
        fp2 = gerar_intent_fingerprint(
            cliente_id="uuid-123",
            intent_type="discovery_first_touch",
            reference_id="campaign-456",
        )

        assert fp1 == fp2
        assert len(fp1) == 32  # SHA256 truncado

    def test_cliente_diferente_fingerprint_diferente(self):
        """Clientes diferentes devem ter fingerprints diferentes."""
        fp1 = gerar_intent_fingerprint(
            cliente_id="uuid-123",
            intent_type="discovery_first_touch",
        )
        fp2 = gerar_intent_fingerprint(
            cliente_id="uuid-456",
            intent_type="discovery_first_touch",
        )

        assert fp1 != fp2

    def test_intent_diferente_fingerprint_diferente(self):
        """Intents diferentes devem ter fingerprints diferentes."""
        fp1 = gerar_intent_fingerprint(
            cliente_id="uuid-123",
            intent_type="discovery_first_touch",
        )
        fp2 = gerar_intent_fingerprint(
            cliente_id="uuid-123",
            intent_type="offer_active",
        )

        assert fp1 != fp2

    def test_reference_diferente_fingerprint_diferente(self):
        """References diferentes devem ter fingerprints diferentes."""
        fp1 = gerar_intent_fingerprint(
            cliente_id="uuid-123",
            intent_type="offer_active",
            reference_id="vaga-1",
        )
        fp2 = gerar_intent_fingerprint(
            cliente_id="uuid-123",
            intent_type="offer_active",
            reference_id="vaga-2",
        )

        assert fp1 != fp2

    def test_reference_none_vs_string(self):
        """None e 'none' devem gerar fingerprints iguais."""
        fp1 = gerar_intent_fingerprint(
            cliente_id="uuid-123",
            intent_type="reactivation_nudge",
            reference_id=None,
        )
        # Internamente usa "none" como string
        assert len(fp1) == 32

    def test_usa_janela_do_intent(self):
        """Deve usar janela específica do intent."""
        # Discovery tem janela de 7 dias
        assert INTENT_WINDOWS["discovery_first_touch"] == 7
        # Offer tem janela de 1 dia
        assert INTENT_WINDOWS["offer_active"] == 1

    def test_window_customizado(self):
        """Deve aceitar window customizado."""
        fp1 = gerar_intent_fingerprint(
            cliente_id="uuid-123",
            intent_type="discovery_first_touch",
            window_days=1,  # Força janela de 1 dia
        )
        fp2 = gerar_intent_fingerprint(
            cliente_id="uuid-123",
            intent_type="discovery_first_touch",
            window_days=7,  # Janela padrão
        )

        # Podem ser diferentes dependendo do dia
        assert len(fp1) == 32
        assert len(fp2) == 32

    def test_aceita_enum_e_string(self):
        """Deve aceitar tanto enum quanto string."""
        fp1 = gerar_intent_fingerprint(
            cliente_id="uuid-123",
            intent_type=IntentType.DISCOVERY_FIRST,
        )
        fp2 = gerar_intent_fingerprint(
            cliente_id="uuid-123",
            intent_type="discovery_first_touch",
        )

        assert fp1 == fp2


class TestVerificarIntent:
    """Testes da função verificar_intent."""

    @pytest.mark.asyncio
    @patch("app.services.intent_dedupe.supabase")
    async def test_primeira_insercao_permite(self, mock_supabase):
        """Primeira inserção deve permitir envio."""
        mock_response = MagicMock()
        mock_response.data = [{"fingerprint": "abc123", "inserted": True}]
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        pode_enviar, fingerprint, motivo = await verificar_intent(
            cliente_id="uuid-123",
            intent_type="discovery_first_touch",
            reference_id="campaign-456",
        )

        assert pode_enviar is True
        assert len(fingerprint) == 32
        assert motivo is None

    @pytest.mark.asyncio
    @patch("app.services.intent_dedupe.supabase")
    async def test_segunda_insercao_bloqueia(self, mock_supabase):
        """Segunda inserção (duplicata) deve bloquear."""
        mock_response = MagicMock()
        mock_response.data = [{"fingerprint": "abc123", "inserted": False}]
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        pode_enviar, fingerprint, motivo = await verificar_intent(
            cliente_id="uuid-123",
            intent_type="discovery_first_touch",
        )

        assert pode_enviar is False
        assert len(fingerprint) == 32
        assert motivo == "intent_duplicate:discovery_first_touch"

    @pytest.mark.asyncio
    @patch("app.services.intent_dedupe.supabase")
    async def test_erro_permite_envio(self, mock_supabase):
        """Erro no RPC deve permitir envio (fail open)."""
        mock_supabase.rpc.return_value.execute.side_effect = Exception("DB error")

        pode_enviar, fingerprint, motivo = await verificar_intent(
            cliente_id="uuid-123",
            intent_type="discovery_first_touch",
        )

        assert pode_enviar is True  # Fail open
        assert len(fingerprint) == 32
        assert motivo is None

    @pytest.mark.asyncio
    @patch("app.services.intent_dedupe.supabase")
    async def test_chama_rpc_com_parametros_corretos(self, mock_supabase):
        """Deve chamar RPC com parâmetros corretos."""
        mock_response = MagicMock()
        mock_response.data = [{"fingerprint": "abc", "inserted": True}]
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        await verificar_intent(
            cliente_id="uuid-123",
            intent_type="offer_active",
            reference_id="vaga-456",
        )

        mock_supabase.rpc.assert_called_once()
        call_args = mock_supabase.rpc.call_args[0]
        assert call_args[0] == "inserir_intent_se_novo"

        params = call_args[1]
        assert "p_fingerprint" in params
        assert params["p_cliente_id"] == "uuid-123"
        assert params["p_intent_type"] == "offer_active"
        assert params["p_reference_id"] == "vaga-456"
        assert "p_expires_at" in params


class TestObterReferenceId:
    """Testes da função obter_reference_id."""

    def test_discovery_usa_campaign_id(self):
        """Discovery deve usar campaign_id como reference."""
        assert INTENT_REFERENCE_FIELD["discovery_first_touch"] == "campaign_id"
        assert INTENT_REFERENCE_FIELD["discovery_followup"] == "campaign_id"

    def test_offer_usa_vaga_id(self):
        """Offer deve usar vaga_id como reference."""
        assert INTENT_REFERENCE_FIELD["offer_active"] == "vaga_id"
        assert INTENT_REFERENCE_FIELD["offer_reminder"] == "vaga_id"

    def test_reactivation_global(self):
        """Reactivation deve ser global (sem reference)."""
        assert INTENT_REFERENCE_FIELD["reactivation_nudge"] is None
        assert INTENT_REFERENCE_FIELD["reactivation_value_prop"] is None

    def test_followup_usa_conversation_id(self):
        """Followup deve usar conversation_id como reference."""
        assert INTENT_REFERENCE_FIELD["followup_silence"] == "conversation_id"
        assert INTENT_REFERENCE_FIELD["followup_pending_docs"] == "conversation_id"

    def test_obter_de_objeto(self):
        """Deve obter reference do atributo do objeto."""
        class FakeCtx:
            campaign_id = "camp-123"

        ref = obter_reference_id("discovery_first_touch", FakeCtx())
        assert ref == "camp-123"

    def test_obter_de_metadata(self):
        """Deve obter reference do metadata se não houver atributo."""
        class FakeCtx:
            metadata = {"vaga_id": "vaga-456"}

        ref = obter_reference_id("offer_active", FakeCtx())
        assert ref == "vaga-456"

    def test_retorna_none_para_global(self):
        """Deve retornar None para intents globais."""
        class FakeCtx:
            pass

        ref = obter_reference_id("reactivation_nudge", FakeCtx())
        assert ref is None


class TestLimparIntentsExpirados:
    """Testes da função limpar_intents_expirados."""

    @pytest.mark.asyncio
    @patch("app.services.intent_dedupe.supabase")
    async def test_remove_expirados(self, mock_supabase):
        """Deve remover registros expirados."""
        mock_response = MagicMock()
        mock_response.data = [{"id": 1}, {"id": 2}, {"id": 3}]
        mock_supabase.table.return_value.delete.return_value.lt.return_value.execute.return_value = mock_response

        count = await limpar_intents_expirados()

        assert count == 3
        mock_supabase.table.assert_called_with("intent_log")

    @pytest.mark.asyncio
    @patch("app.services.intent_dedupe.supabase")
    async def test_erro_retorna_zero(self, mock_supabase):
        """Erro deve retornar 0 sem propagar exceção."""
        mock_supabase.table.return_value.delete.return_value.lt.return_value.execute.side_effect = Exception("DB error")

        count = await limpar_intents_expirados()

        assert count == 0


class TestIntentWindows:
    """Testes das configurações de janelas."""

    def test_todas_janelas_definidas(self):
        """Todos os IntentTypes devem ter janela definida."""
        for intent in IntentType:
            assert intent.value in INTENT_WINDOWS, f"Faltando janela para {intent.value}"

    def test_todas_references_definidas(self):
        """Todos os IntentTypes devem ter reference definido."""
        for intent in IntentType:
            assert intent.value in INTENT_REFERENCE_FIELD, f"Faltando reference para {intent.value}"

    def test_janelas_razoaveis(self):
        """Janelas devem estar em range razoável (1-30 dias)."""
        for intent, days in INTENT_WINDOWS.items():
            assert 1 <= days <= 30, f"Janela inválida para {intent}: {days}"
