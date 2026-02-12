"""
Testes da finalização centralizada de envio outbound.

Sprint 24 E03: Centralização da Finalização.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

from app.services.outbound import (
    _atualizar_last_touch,
    _finalizar_envio,
    send_outbound_message,
    OutboundResult,
)
from app.services.guardrails import (
    OutboundContext,
    OutboundChannel,
    OutboundMethod,
    ActorType,
    SendOutcome,
)


class TestAtualizarLastTouch:
    """Testes da função _atualizar_last_touch."""

    @pytest.mark.asyncio
    @patch("app.services.supabase.supabase")
    async def test_atualiza_campos_basicos(self, mock_supabase):
        """Deve atualizar last_touch_at e last_touch_method."""
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock()

        await _atualizar_last_touch(
            cliente_id="uuid-123",
            method="campaign",
            campaign_id="456",
        )

        mock_supabase.table.assert_called_once_with("doctor_state")
        call_args = mock_supabase.table.return_value.upsert.call_args[0][0]

        assert call_args["cliente_id"] == "uuid-123"
        assert call_args["last_touch_method"] == "campaign"
        assert call_args["last_touch_campaign_id"] == "456"
        assert "last_touch_at" in call_args

    @pytest.mark.asyncio
    @patch("app.services.supabase.supabase")
    async def test_limpa_campaign_id_se_nao_campanha(self, mock_supabase):
        """Deve limpar campaign_id se método não for campanha."""
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock()

        await _atualizar_last_touch(
            cliente_id="uuid-123",
            method="followup",
            campaign_id=None,
        )

        call_args = mock_supabase.table.return_value.upsert.call_args[0][0]
        assert call_args["last_touch_campaign_id"] is None

    @pytest.mark.asyncio
    @patch("app.services.supabase.supabase")
    async def test_erro_nao_propaga(self, mock_supabase):
        """Erro no update não deve propagar exceção."""
        mock_supabase.table.return_value.upsert.return_value.execute.side_effect = Exception("DB error")

        # Não deve lançar exceção
        await _atualizar_last_touch(
            cliente_id="uuid-123",
            method="campaign",
        )


class TestFinalizarEnvio:
    """Testes da função _finalizar_envio."""

    @pytest.fixture
    def ctx_campanha(self):
        return OutboundContext(
            cliente_id="uuid-123",
            actor_type=ActorType.SYSTEM,
            channel=OutboundChannel.JOB,
            method=OutboundMethod.CAMPAIGN,
            is_proactive=True,
            campaign_id="456",
            conversation_id="conv-789",
        )

    @pytest.fixture
    def ctx_followup(self):
        return OutboundContext(
            cliente_id="uuid-123",
            actor_type=ActorType.BOT,
            channel=OutboundChannel.WHATSAPP,
            method=OutboundMethod.FOLLOWUP,
            is_proactive=True,
            conversation_id="conv-789",
        )

    @pytest.mark.asyncio
    @patch("app.services.outbound._atualizar_last_touch")
    @patch("app.services.campaign_attribution.registrar_campaign_touch")
    @patch("app.services.campaign_cooldown.registrar_envio_campanha")
    async def test_sent_atualiza_last_touch(
        self,
        mock_cooldown,
        mock_attribution,
        mock_last_touch,
        ctx_campanha,
    ):
        """SENT deve atualizar last_touch_*."""
        mock_last_touch.return_value = None
        mock_attribution.return_value = None
        mock_cooldown.return_value = True

        await _finalizar_envio(
            ctx=ctx_campanha,
            outcome=SendOutcome.SENT,
        )

        mock_last_touch.assert_called_once()
        call_args = mock_last_touch.call_args[1]
        assert call_args["cliente_id"] == "uuid-123"
        assert call_args["method"] == "campaign"
        assert call_args["campaign_id"] == "456"

    @pytest.mark.asyncio
    @patch("app.services.outbound._atualizar_last_touch")
    @patch("app.services.campaign_attribution.registrar_campaign_touch")
    @patch("app.services.campaign_cooldown.registrar_envio_campanha")
    async def test_bypass_atualiza_last_touch(
        self,
        mock_cooldown,
        mock_attribution,
        mock_last_touch,
        ctx_campanha,
    ):
        """BYPASS deve atualizar last_touch_*."""
        mock_last_touch.return_value = None
        mock_attribution.return_value = None
        mock_cooldown.return_value = True

        await _finalizar_envio(
            ctx=ctx_campanha,
            outcome=SendOutcome.BYPASS,
        )

        mock_last_touch.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.outbound._atualizar_last_touch")
    async def test_blocked_nao_atualiza(self, mock_last_touch, ctx_campanha):
        """BLOCKED não deve atualizar last_touch_*."""
        await _finalizar_envio(
            ctx=ctx_campanha,
            outcome=SendOutcome.BLOCKED_OPTED_OUT,
        )

        mock_last_touch.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.outbound._atualizar_last_touch")
    async def test_deduped_nao_atualiza(self, mock_last_touch, ctx_campanha):
        """DEDUPED não deve atualizar last_touch_*."""
        await _finalizar_envio(
            ctx=ctx_campanha,
            outcome=SendOutcome.DEDUPED,
        )

        mock_last_touch.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.outbound._atualizar_last_touch")
    async def test_failed_nao_atualiza(self, mock_last_touch, ctx_campanha):
        """FAILED não deve atualizar last_touch_*."""
        await _finalizar_envio(
            ctx=ctx_campanha,
            outcome=SendOutcome.FAILED_PROVIDER,
        )

        mock_last_touch.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.outbound._atualizar_last_touch")
    @patch("app.services.campaign_attribution.registrar_campaign_touch")
    @patch("app.services.campaign_cooldown.registrar_envio_campanha")
    async def test_sent_com_campanha_registra_attribution(
        self,
        mock_cooldown,
        mock_attribution,
        mock_last_touch,
        ctx_campanha,
    ):
        """SENT com campaign_id deve registrar attribution."""
        mock_last_touch.return_value = None
        mock_attribution.return_value = None
        mock_cooldown.return_value = True

        await _finalizar_envio(
            ctx=ctx_campanha,
            outcome=SendOutcome.SENT,
        )

        mock_attribution.assert_called_once()
        call_args = mock_attribution.call_args[1]
        assert call_args["campaign_id"] == 456
        assert call_args["cliente_id"] == "uuid-123"

    @pytest.mark.asyncio
    @patch("app.services.outbound._atualizar_last_touch")
    async def test_followup_nao_registra_cooldown(self, mock_last_touch, ctx_followup):
        """Followup não tem campaign_id, não registra cooldown."""
        mock_last_touch.return_value = None

        # Não deve chamar campaign_cooldown (não tem campaign_id)
        await _finalizar_envio(
            ctx=ctx_followup,
            outcome=SendOutcome.SENT,
        )

        mock_last_touch.assert_called_once()
        call_args = mock_last_touch.call_args[1]
        assert call_args["campaign_id"] is None


class TestSendOutboundMessageTryFinally:
    """Testes do padrão try/finally em send_outbound_message."""

    @pytest.fixture
    def ctx(self):
        return OutboundContext(
            cliente_id="uuid-123",
            actor_type=ActorType.SYSTEM,
            channel=OutboundChannel.JOB,
            method=OutboundMethod.CAMPAIGN,
            is_proactive=True,
            campaign_id="456",
        )

    @pytest.mark.asyncio
    @patch("app.services.outbound._is_multi_chip_enabled")
    @patch("app.services.outbound._verificar_dev_allowlist")
    @patch("app.services.outbound._finalizar_envio")
    @patch("app.services.outbound.verificar_e_reservar")
    @patch("app.services.outbound.check_outbound_guardrails")
    @patch("app.services.outbound.evolution")
    @patch("app.services.outbound.marcar_enviado")
    async def test_sucesso_chama_finalizacao(
        self,
        mock_marcar,
        mock_evolution,
        mock_guardrails,
        mock_dedupe,
        mock_finalizar,
        mock_dev_allowlist,
        mock_multi_chip,
        ctx,
    ):
        """Envio bem-sucedido deve chamar _finalizar_envio."""
        mock_multi_chip.return_value = False
        mock_dev_allowlist.return_value = (True, None)  # Bypass DEV guardrail
        mock_dedupe.return_value = (True, "key-123", None)
        mock_guardrails.return_value = MagicMock(is_blocked=False, human_bypass=False)
        mock_evolution.enviar_mensagem = AsyncMock(return_value={"key": {"id": "msg-1"}})
        mock_marcar.return_value = None
        mock_finalizar.return_value = None

        result = await send_outbound_message("5511999999999", "Oi", ctx)

        mock_finalizar.assert_called_once()
        assert result.outcome == SendOutcome.SENT

    @pytest.mark.asyncio
    @patch("app.services.outbound._is_multi_chip_enabled")
    @patch("app.services.outbound._verificar_dev_allowlist")
    @patch("app.services.outbound._finalizar_envio")
    @patch("app.services.outbound.verificar_e_reservar")
    @patch("app.services.outbound.check_outbound_guardrails")
    @patch("app.services.outbound.evolution")
    @patch("app.services.outbound.marcar_falha")
    async def test_falha_provider_chama_finalizacao(
        self,
        mock_marcar_falha,
        mock_evolution,
        mock_guardrails,
        mock_dedupe,
        mock_finalizar,
        mock_dev_allowlist,
        mock_multi_chip,
        ctx,
    ):
        """Falha no provider deve chamar _finalizar_envio."""
        mock_multi_chip.return_value = False  # Forçar caminho Evolution
        mock_dev_allowlist.return_value = (True, None)  # Bypass DEV guardrail
        mock_dedupe.return_value = (True, "key-123", None)
        mock_guardrails.return_value = MagicMock(is_blocked=False, human_bypass=False)
        mock_evolution.enviar_mensagem = AsyncMock(side_effect=Exception("API Error"))
        mock_marcar_falha.return_value = None
        mock_finalizar.return_value = None

        result = await send_outbound_message("5511999999999", "Oi", ctx)

        mock_finalizar.assert_called_once()
        assert result.outcome == SendOutcome.FAILED_PROVIDER

    @pytest.mark.asyncio
    @patch("app.services.outbound._verificar_dev_allowlist")
    @patch("app.services.outbound._finalizar_envio")
    @patch("app.services.outbound.verificar_e_reservar")
    async def test_dedupe_nao_chama_finalizacao(
        self,
        mock_dedupe,
        mock_finalizar,
        mock_dev_allowlist,
        ctx,
    ):
        """Deduplicação não deve chamar _finalizar_envio (retorno antecipado)."""
        mock_dev_allowlist.return_value = (True, None)  # Bypass DEV guardrail
        mock_dedupe.return_value = (False, "key-123", "duplicado")

        result = await send_outbound_message("5511999999999", "Oi", ctx)

        mock_finalizar.assert_not_called()
        assert result.outcome == SendOutcome.DEDUPED

    @pytest.mark.asyncio
    @patch("app.services.outbound._verificar_dev_allowlist")
    @patch("app.services.outbound._finalizar_envio")
    @patch("app.services.outbound.verificar_e_reservar")
    @patch("app.services.outbound.check_outbound_guardrails")
    async def test_guardrail_block_nao_chama_finalizacao(
        self,
        mock_guardrails,
        mock_dedupe,
        mock_finalizar,
        mock_dev_allowlist,
        ctx,
    ):
        """Bloqueio por guardrail não deve chamar _finalizar_envio."""
        mock_dev_allowlist.return_value = (True, None)  # Bypass DEV guardrail
        mock_dedupe.return_value = (True, "key-123", None)
        mock_guardrails.return_value = MagicMock(
            is_blocked=True,
            reason_code="opted_out",
            human_bypass=False,
        )

        result = await send_outbound_message("5511999999999", "Oi", ctx)

        mock_finalizar.assert_not_called()
        assert result.outcome.is_blocked

    @pytest.mark.asyncio
    @patch("app.services.outbound._is_multi_chip_enabled")
    @patch("app.services.outbound._verificar_dev_allowlist")
    @patch("app.services.outbound._finalizar_envio")
    @patch("app.services.outbound.verificar_e_reservar")
    @patch("app.services.outbound.check_outbound_guardrails")
    @patch("app.services.outbound.evolution")
    @patch("app.services.outbound.marcar_enviado")
    async def test_finalizacao_recebe_outcome_correto(
        self,
        mock_marcar,
        mock_evolution,
        mock_guardrails,
        mock_dedupe,
        mock_finalizar,
        mock_dev_allowlist,
        mock_multi_chip,
        ctx,
    ):
        """_finalizar_envio deve receber outcome correto."""
        mock_multi_chip.return_value = False
        mock_dev_allowlist.return_value = (True, None)  # Bypass DEV guardrail
        mock_dedupe.return_value = (True, "key-123", None)
        mock_guardrails.return_value = MagicMock(is_blocked=False, human_bypass=False)
        mock_evolution.enviar_mensagem = AsyncMock(return_value={"key": {"id": "msg-1"}})
        mock_marcar.return_value = None
        mock_finalizar.return_value = None

        await send_outbound_message("5511999999999", "Oi", ctx)

        call_args = mock_finalizar.call_args[1]
        assert call_args["outcome"] == SendOutcome.SENT
        assert call_args["ctx"] == ctx


class TestDevAllowlistGuardrail:
    """Testes para o guardrail DEV allowlist (R-2: fail-closed)."""

    @pytest.fixture
    def ctx(self):
        """Contexto de teste para envio de campanha."""
        return OutboundContext(
            cliente_id="123",
            actor_type=ActorType.SYSTEM,
            channel=OutboundChannel.JOB,
            method=OutboundMethod.CAMPAIGN,
            is_proactive=True,
            campaign_id="456",
        )

    @pytest.mark.asyncio
    async def test_dev_allowlist_empty_blocks_all(self, ctx):
        """Allowlist vazia em DEV deve bloquear TODOS os envios (fail-closed)."""
        # Não mockar _verificar_dev_allowlist para testar comportamento real
        # O teste roda em DEV com allowlist vazia por padrão
        result = await send_outbound_message("5511999999999", "Oi", ctx)

        assert result.outcome == SendOutcome.BLOCKED_DEV_ALLOWLIST
        assert result.blocked is True
        assert "dev_allowlist" in result.outcome_reason_code

    @pytest.mark.asyncio
    @patch("app.services.outbound.settings")
    async def test_dev_allowlist_blocks_number_not_in_list(
        self,
        mock_settings,
        ctx,
    ):
        """Número fora da allowlist deve ser bloqueado em DEV."""
        mock_settings.is_production = False
        mock_settings.APP_ENV = "dev"
        mock_settings.outbound_allowlist_numbers = {"5511888888888"}

        result = await send_outbound_message("5511999999999", "Oi", ctx)

        assert result.outcome == SendOutcome.BLOCKED_DEV_ALLOWLIST
        assert result.blocked is True

    @pytest.mark.asyncio
    @patch("app.services.outbound._is_multi_chip_enabled")
    @patch("app.services.outbound._verificar_dev_allowlist")
    @patch("app.services.outbound.verificar_e_reservar")
    @patch("app.services.outbound.check_outbound_guardrails")
    @patch("app.services.outbound.evolution")
    @patch("app.services.outbound.marcar_enviado")
    async def test_dev_allowlist_allows_number_in_list(
        self,
        mock_marcar,
        mock_evolution,
        mock_guardrails,
        mock_dedupe,
        mock_dev_allowlist,
        mock_multi_chip,
        ctx,
    ):
        """Número na allowlist deve passar em DEV."""
        mock_multi_chip.return_value = False
        mock_dev_allowlist.return_value = (True, None)  # Simula número na allowlist
        mock_dedupe.return_value = (True, "key-123", None)
        mock_guardrails.return_value = MagicMock(is_blocked=False, human_bypass=False)
        mock_evolution.enviar_mensagem = AsyncMock(return_value={"key": {"id": "msg-1"}})
        mock_marcar.return_value = None

        result = await send_outbound_message("5511999999999", "Oi", ctx)

        assert result.outcome == SendOutcome.SENT
        assert result.blocked is False

    @pytest.mark.asyncio
    @patch("app.services.outbound._is_multi_chip_enabled")
    @patch("app.services.outbound.settings")
    @patch("app.services.outbound.verificar_e_reservar")
    @patch("app.services.outbound.check_outbound_guardrails")
    @patch("app.services.outbound.evolution")
    @patch("app.services.outbound.marcar_enviado")
    async def test_production_bypasses_dev_allowlist(
        self,
        mock_marcar,
        mock_evolution,
        mock_guardrails,
        mock_dedupe,
        mock_settings,
        mock_multi_chip,
        ctx,
    ):
        """Em produção, DEV allowlist não é verificada."""
        mock_multi_chip.return_value = False
        mock_settings.is_production = True
        mock_settings.APP_ENV = "production"
        mock_settings.outbound_allowlist_numbers = set()  # Vazio, mas não importa em PROD
        mock_dedupe.return_value = (True, "key-123", None)
        mock_guardrails.return_value = MagicMock(is_blocked=False, human_bypass=False)
        mock_evolution.enviar_mensagem = AsyncMock(return_value={"key": {"id": "msg-1"}})
        mock_marcar.return_value = None

        result = await send_outbound_message("5511999999999", "Oi", ctx)

        assert result.outcome == SendOutcome.SENT
        assert result.blocked is False
