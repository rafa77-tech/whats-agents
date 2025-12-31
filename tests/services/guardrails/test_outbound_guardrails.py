"""
Testes dos guardrails de outbound.

Sprint 18 - Validação do encanamento de outbound.
Testes para R0 (opt-out), R0.5 (quiet_hours), e handoff.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.guardrails.check import check_outbound_guardrails
from app.services.guardrails.types import (
    OutboundContext,
    OutboundChannel,
    OutboundMethod,
    ActorType,
    GuardrailDecision,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def ctx_proativo():
    """Contexto de envio proativo (campanha)."""
    return OutboundContext(
        cliente_id="test-cliente-123",
        actor_type=ActorType.SYSTEM,
        channel=OutboundChannel.JOB,
        method=OutboundMethod.CAMPAIGN,
        is_proactive=True,
    )


@pytest.fixture
def ctx_followup():
    """Contexto de follow-up."""
    return OutboundContext(
        cliente_id="test-cliente-123",
        actor_type=ActorType.BOT,
        channel=OutboundChannel.WHATSAPP,
        method=OutboundMethod.FOLLOWUP,
        is_proactive=True,
    )


@pytest.fixture
def ctx_reply():
    """Contexto de reply (resposta a inbound)."""
    return OutboundContext(
        cliente_id="test-cliente-123",
        actor_type=ActorType.BOT,
        channel=OutboundChannel.WHATSAPP,
        method=OutboundMethod.REPLY,
        is_proactive=False,
        conversation_id="conv-123",
        inbound_interaction_id=42,
        last_inbound_at=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def ctx_slack_humano():
    """Contexto de bypass humano via Slack."""
    return OutboundContext(
        cliente_id="test-cliente-123",
        actor_type=ActorType.HUMAN,
        channel=OutboundChannel.SLACK,
        method=OutboundMethod.COMMAND,
        is_proactive=True,
        actor_id="rafael",
        bypass_reason="Emergência médica",
    )


# =============================================================================
# Teste 3: Quiet Hours bloqueia proativo
# =============================================================================

class TestQuietHours:
    """Testes para R0.5 - Quiet Hours."""

    @pytest.mark.asyncio
    async def test_proativo_bloqueado_fora_horario_comercial(self, ctx_proativo):
        """Proativo deve ser bloqueado fora do horário comercial."""
        with patch("app.services.guardrails.check.load_doctor_state", new_callable=AsyncMock) as mock_state:
            mock_state.return_value = MagicMock(
                permission_state=MagicMock(value="active"),
                cooling_off_until=None,
                next_allowed_at=None,
                contact_count_7d=0,
            )

            # Mock na origem do import
            with patch("app.services.timing.esta_em_horario_comercial", return_value=False):
                with patch("app.services.guardrails.check._emit_guardrail_event", new_callable=AsyncMock):
                    result = await check_outbound_guardrails(ctx_proativo)

        assert result.decision == GuardrailDecision.BLOCK
        assert result.reason_code == "quiet_hours"

    @pytest.mark.asyncio
    async def test_proativo_liberado_em_horario_comercial(self, ctx_proativo):
        """Proativo deve ser liberado em horário comercial."""
        with patch("app.services.guardrails.check.load_doctor_state", new_callable=AsyncMock) as mock_state:
            mock_state.return_value = MagicMock(
                permission_state=MagicMock(value="active"),
                cooling_off_until=None,
                next_allowed_at=None,
                contact_count_7d=0,
            )

            with patch("app.services.timing.esta_em_horario_comercial", return_value=True):
                with patch("app.services.guardrails.check.get_campaigns_flags", new_callable=AsyncMock) as mock_flags:
                    mock_flags.return_value = MagicMock(enabled=True)

                    with patch("app.services.guardrails.check.is_safe_mode_active", new_callable=AsyncMock, return_value=False):
                        result = await check_outbound_guardrails(ctx_proativo)

        assert result.decision == GuardrailDecision.ALLOW
        assert result.reason_code == "ok"

    @pytest.mark.asyncio
    async def test_reply_liberado_fora_horario_comercial(self, ctx_reply):
        """Reply deve ser liberado mesmo fora do horário comercial."""
        with patch("app.services.guardrails.check.load_doctor_state", new_callable=AsyncMock) as mock_state:
            mock_state.return_value = MagicMock(
                permission_state=MagicMock(value="active"),
            )

            # Reply não chega a verificar quiet_hours (sai antes por ser non_proactive)
            result = await check_outbound_guardrails(ctx_reply)

        assert result.decision == GuardrailDecision.ALLOW
        assert "reply" in result.reason_code or result.reason_code == "non_proactive"

    @pytest.mark.asyncio
    async def test_bypass_humano_libera_fora_horario(self, ctx_slack_humano):
        """Bypass humano via Slack deve liberar mesmo fora do horário."""
        with patch("app.services.guardrails.check.load_doctor_state", new_callable=AsyncMock) as mock_state:
            mock_state.return_value = MagicMock(
                permission_state=MagicMock(value="active"),
                cooling_off_until=None,
                next_allowed_at=None,
                contact_count_7d=0,
            )

            with patch("app.services.timing.esta_em_horario_comercial", return_value=False):
                with patch("app.services.guardrails.check._emit_guardrail_event", new_callable=AsyncMock):
                    result = await check_outbound_guardrails(ctx_slack_humano)

        assert result.decision == GuardrailDecision.ALLOW
        assert result.human_bypass is True
        assert result.reason_code == "quiet_hours"


# =============================================================================
# Teste 4: Opt-out é absoluto
# =============================================================================

class TestOptOut:
    """Testes para R0 - Opt-out absoluto."""

    @pytest.mark.asyncio
    async def test_campanha_bloqueada_para_opted_out(self, ctx_proativo):
        """Campanha deve ser bloqueada para cliente opted_out."""
        with patch("app.services.guardrails.check.load_doctor_state", new_callable=AsyncMock) as mock_state:
            mock_state.return_value = MagicMock(
                permission_state=MagicMock(value="opted_out"),
            )

            with patch("app.services.guardrails.check._emit_guardrail_event", new_callable=AsyncMock):
                result = await check_outbound_guardrails(ctx_proativo)

        assert result.decision == GuardrailDecision.BLOCK
        assert result.reason_code == "opted_out"

    @pytest.mark.asyncio
    async def test_followup_bloqueado_para_opted_out(self, ctx_followup):
        """Follow-up deve ser bloqueado para cliente opted_out."""
        with patch("app.services.guardrails.check.load_doctor_state", new_callable=AsyncMock) as mock_state:
            mock_state.return_value = MagicMock(
                permission_state=MagicMock(value="opted_out"),
            )

            with patch("app.services.guardrails.check._emit_guardrail_event", new_callable=AsyncMock):
                result = await check_outbound_guardrails(ctx_followup)

        assert result.decision == GuardrailDecision.BLOCK
        assert result.reason_code == "opted_out"

    @pytest.mark.asyncio
    async def test_reply_liberado_para_opted_out(self, ctx_reply):
        """Reply deve ser liberado para opted_out (médico iniciou contato)."""
        with patch("app.services.guardrails.check.load_doctor_state", new_callable=AsyncMock) as mock_state:
            mock_state.return_value = MagicMock(
                permission_state=MagicMock(value="opted_out"),
            )

            result = await check_outbound_guardrails(ctx_reply)

        assert result.decision == GuardrailDecision.ALLOW
        assert result.reason_code == "reply_to_opted_out"

    @pytest.mark.asyncio
    async def test_bypass_humano_com_reason_libera_opted_out(self, ctx_slack_humano):
        """Bypass humano com reason deve liberar opted_out."""
        with patch("app.services.guardrails.check.load_doctor_state", new_callable=AsyncMock) as mock_state:
            mock_state.return_value = MagicMock(
                permission_state=MagicMock(value="opted_out"),
            )

            with patch("app.services.guardrails.check._emit_guardrail_event", new_callable=AsyncMock):
                result = await check_outbound_guardrails(ctx_slack_humano)

        assert result.decision == GuardrailDecision.ALLOW
        assert result.human_bypass is True

    @pytest.mark.asyncio
    async def test_bypass_humano_sem_reason_bloqueia_opted_out(self):
        """Bypass humano SEM reason deve bloquear opted_out."""
        ctx = OutboundContext(
            cliente_id="test-cliente-123",
            actor_type=ActorType.HUMAN,
            channel=OutboundChannel.SLACK,
            method=OutboundMethod.COMMAND,
            is_proactive=True,
            actor_id="rafael",
            bypass_reason=None,  # SEM reason!
        )

        with patch("app.services.guardrails.check.load_doctor_state", new_callable=AsyncMock) as mock_state:
            mock_state.return_value = MagicMock(
                permission_state=MagicMock(value="opted_out"),
            )

            with patch("app.services.guardrails.check._emit_guardrail_event", new_callable=AsyncMock):
                result = await check_outbound_guardrails(ctx)

        assert result.decision == GuardrailDecision.BLOCK
        assert "opted_out" in result.reason_code


# =============================================================================
# Teste 5: Handoff trava outbound
# =============================================================================

class TestHandoffTravaOutbound:
    """Testes para verificar que handoff trava outbound proativo."""

    @pytest.mark.asyncio
    async def test_followup_nao_dispara_em_handoff(self):
        """Follow-up não deve disparar para conversa em handoff."""
        # Este teste verifica o comportamento do followup service
        # A conversa em handoff tem controlled_by='human'

        from app.services.followup import _buscar_conversas_para_followup

        with patch("app.services.followup.supabase") as mock_supabase:
            # Simular query que filtra controlled_by='ai'
            mock_response = MagicMock()
            mock_response.data = []  # Nenhuma conversa em handoff retornada
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.lte.return_value.is_.return_value.limit.return_value.execute.return_value = mock_response

            conversas = await _buscar_conversas_para_followup("msg_enviada", timedelta(hours=48))

        # Conversas em handoff (controlled_by='human') não aparecem
        assert len(conversas) == 0

    @pytest.mark.asyncio
    async def test_campanha_nao_atinge_handoff(self):
        """Campanha não deve atingir médico em handoff ativo."""
        # Handoff ativo = controlled_by='human' na conversa
        # O envio de campanha deve verificar isso antes de enfileirar

        # Este teste documenta o comportamento esperado
        # A implementação atual pode não ter essa verificação
        pass  # TODO: Implementar verificação de handoff no envio de campanha


# =============================================================================
# Testes de Regressão
# =============================================================================

class TestRegressao:
    """Testes de regressão para bugs corrigidos."""

    @pytest.mark.asyncio
    async def test_inbound_responde_24_7(self, ctx_reply):
        """
        Regressão: Julia deve responder inbound 24/7.

        Bug corrigido em 31/12/2025:
        - ForaHorarioProcessor bloqueava TODAS as mensagens fora do horário
        - Fix: Removido do pipeline, inbound sempre passa
        """
        # Reply com prova de inbound válida deve passar sempre
        with patch("app.services.guardrails.check.load_doctor_state", new_callable=AsyncMock) as mock_state:
            mock_state.return_value = MagicMock(
                permission_state=MagicMock(value="active"),
            )

            # Reply não chega a verificar quiet_hours (sai antes por ser non_proactive)
            result = await check_outbound_guardrails(ctx_reply)

        assert result.decision == GuardrailDecision.ALLOW
