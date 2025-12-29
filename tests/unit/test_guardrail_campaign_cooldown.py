"""
Testes do guardrail campaign_cooldown.

Sprint 24 E04: Cooldown entre campanhas diferentes.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

from app.services.guardrails.check import (
    _check_campaign_cooldown_state,
    check_outbound_guardrails,
    CAMPAIGN_COOLDOWN_DAYS,
)
from app.services.guardrails import (
    OutboundContext,
    OutboundChannel,
    OutboundMethod,
    ActorType,
    GuardrailDecision,
)


@dataclass
class MockDoctorState:
    """Mock do DoctorState para testes."""
    permission_state: MagicMock = None
    last_touch_at: datetime = None
    last_touch_method: str = None
    last_touch_campaign_id: str = None
    cooling_off_until: datetime = None
    next_allowed_at: datetime = None
    contact_count_7d: int = 0

    def __post_init__(self):
        if self.permission_state is None:
            self.permission_state = MagicMock()
            self.permission_state.value = "active"


@pytest.fixture
def ctx_campanha_a():
    """Contexto para campanha A."""
    return OutboundContext(
        cliente_id="uuid-123",
        actor_type=ActorType.SYSTEM,
        channel=OutboundChannel.JOB,
        method=OutboundMethod.CAMPAIGN,
        is_proactive=True,
        campaign_id="100",
    )


@pytest.fixture
def ctx_campanha_b():
    """Contexto para campanha B."""
    return OutboundContext(
        cliente_id="uuid-123",
        actor_type=ActorType.SYSTEM,
        channel=OutboundChannel.JOB,
        method=OutboundMethod.CAMPAIGN,
        is_proactive=True,
        campaign_id="200",
    )


@pytest.fixture
def ctx_followup():
    """Contexto para followup."""
    return OutboundContext(
        cliente_id="uuid-123",
        actor_type=ActorType.BOT,
        channel=OutboundChannel.WHATSAPP,
        method=OutboundMethod.FOLLOWUP,
        is_proactive=True,
    )


@pytest.fixture
def ctx_reply():
    """Contexto para reply."""
    return OutboundContext(
        cliente_id="uuid-123",
        actor_type=ActorType.BOT,
        channel=OutboundChannel.WHATSAPP,
        method=OutboundMethod.REPLY,
        is_proactive=False,
        conversation_id="conv-1",
        inbound_interaction_id=123,
        last_inbound_at=datetime.now(timezone.utc).isoformat(),
    )


class TestCheckCampaignCooldownState:
    """Testes da função _check_campaign_cooldown_state."""

    def test_campanha_b_bloqueada_apos_campanha_a_2_dias(self, ctx_campanha_b):
        """Campanha B deve ser bloqueada se campanha A foi enviada há 2 dias."""
        state = MockDoctorState(
            last_touch_at=datetime.now(timezone.utc) - timedelta(days=2),
            last_touch_method="campaign",
            last_touch_campaign_id="100",  # Campanha A
        )

        result = _check_campaign_cooldown_state(ctx_campanha_b, state)

        assert result is not None
        assert result.is_blocked
        assert result.reason_code == "campaign_cooldown"
        assert result.details["days_since"] == 2
        assert result.details["required"] == CAMPAIGN_COOLDOWN_DAYS

    def test_mesma_campanha_followup_permitido(self):
        """Mesma campanha (followup) deve ser permitida."""
        # Criar contexto com campaign_id 100
        ctx = OutboundContext(
            cliente_id="uuid-123",
            actor_type=ActorType.SYSTEM,
            channel=OutboundChannel.JOB,
            method=OutboundMethod.CAMPAIGN,
            is_proactive=True,
            campaign_id="100",  # Mesma campanha
        )
        state = MockDoctorState(
            last_touch_at=datetime.now(timezone.utc) - timedelta(days=1),
            last_touch_method="campaign",
            last_touch_campaign_id="100",  # Mesma campanha
        )

        result = _check_campaign_cooldown_state(ctx, state)

        assert result is None  # Não bloqueia

    def test_reply_nao_afetado_por_cooldown(self, ctx_reply):
        """Reply não deve ser afetado pelo cooldown."""
        state = MockDoctorState(
            last_touch_at=datetime.now(timezone.utc) - timedelta(days=1),
            last_touch_method="campaign",
            last_touch_campaign_id="100",
        )

        result = _check_campaign_cooldown_state(ctx_reply, state)

        assert result is None  # Não afeta reply

    def test_followup_nao_afetado_por_cooldown(self, ctx_followup):
        """Followup não deve ser afetado pelo cooldown."""
        state = MockDoctorState(
            last_touch_at=datetime.now(timezone.utc) - timedelta(days=1),
            last_touch_method="campaign",
            last_touch_campaign_id="100",
        )

        result = _check_campaign_cooldown_state(ctx_followup, state)

        assert result is None  # Não afeta followup

    def test_cooldown_expirado_permite_envio(self, ctx_campanha_b):
        """Cooldown expirado (>= 3 dias) deve permitir envio."""
        state = MockDoctorState(
            last_touch_at=datetime.now(timezone.utc) - timedelta(days=3),
            last_touch_method="campaign",
            last_touch_campaign_id="100",
        )

        result = _check_campaign_cooldown_state(ctx_campanha_b, state)

        assert result is None  # Permite

    def test_sem_last_touch_permite_envio(self, ctx_campanha_a):
        """Sem last_touch deve permitir envio."""
        state = MockDoctorState()  # Sem last_touch_*

        result = _check_campaign_cooldown_state(ctx_campanha_a, state)

        assert result is None  # Permite

    def test_last_touch_nao_campanha_permite(self, ctx_campanha_b):
        """last_touch de followup não deve bloquear campanha."""
        state = MockDoctorState(
            last_touch_at=datetime.now(timezone.utc) - timedelta(days=1),
            last_touch_method="followup",  # Não é campanha
            last_touch_campaign_id=None,
        )

        result = _check_campaign_cooldown_state(ctx_campanha_b, state)

        assert result is None  # Permite

    def test_state_none_permite_envio(self, ctx_campanha_a):
        """state=None deve permitir envio."""
        result = _check_campaign_cooldown_state(ctx_campanha_a, None)

        assert result is None  # Permite

    def test_details_contem_informacoes_corretas(self, ctx_campanha_b):
        """Details do bloqueio deve conter informações corretas."""
        state = MockDoctorState(
            last_touch_at=datetime.now(timezone.utc) - timedelta(days=2),
            last_touch_method="campaign",
            last_touch_campaign_id="100",
        )

        result = _check_campaign_cooldown_state(ctx_campanha_b, state)

        assert result.details["days_since"] == 2
        assert result.details["required"] == 3
        assert result.details["last_campaign_id"] == "100"
        assert result.details["current_campaign_id"] == "200"


class TestCheckOutboundGuardrailsCampaignCooldown:
    """Testes de integração do cooldown no pipeline de guardrails."""

    @pytest.mark.asyncio
    @patch("app.services.guardrails.check.load_doctor_state")
    @patch("app.services.guardrails.check.get_campaigns_flags")
    @patch("app.services.guardrails.check.is_safe_mode_active")
    @patch("app.services.guardrails.check._emit_guardrail_event")
    async def test_campanha_bloqueada_por_cooldown(
        self,
        mock_emit,
        mock_safe_mode,
        mock_flags,
        mock_load_state,
        ctx_campanha_b,
    ):
        """Campanha deve ser bloqueada se cooldown ativo."""
        mock_state = MockDoctorState(
            last_touch_at=datetime.now(timezone.utc) - timedelta(days=2),
            last_touch_method="campaign",
            last_touch_campaign_id="100",
        )
        mock_load_state.return_value = mock_state
        mock_flags.return_value = MagicMock(enabled=True)
        mock_safe_mode.return_value = False
        mock_emit.return_value = None

        result = await check_outbound_guardrails(ctx_campanha_b)

        assert result.is_blocked
        assert result.reason_code == "campaign_cooldown"
        mock_emit.assert_called()

    @pytest.mark.asyncio
    @patch("app.services.guardrails.check.load_doctor_state")
    @patch("app.services.guardrails.check.get_campaigns_flags")
    @patch("app.services.guardrails.check.is_safe_mode_active")
    async def test_manual_humano_nao_afetado_por_cooldown(
        self,
        mock_safe_mode,
        mock_flags,
        mock_load_state,
    ):
        """
        Envio MANUAL via Slack não é afetado por cooldown.

        Cooldown só aplica a method=CAMPAIGN.
        Humano pode usar method=MANUAL para contornar cooldown.
        """
        ctx = OutboundContext(
            cliente_id="uuid-123",
            actor_type=ActorType.HUMAN,
            channel=OutboundChannel.SLACK,
            method=OutboundMethod.MANUAL,  # MANUAL não é CAMPAIGN → cooldown não aplica
            is_proactive=True,
            actor_id="user-456",
        )

        mock_state = MockDoctorState(
            last_touch_at=datetime.now(timezone.utc) - timedelta(days=2),
            last_touch_method="campaign",
            last_touch_campaign_id="100",
        )
        mock_load_state.return_value = mock_state
        mock_flags.return_value = MagicMock(enabled=True)
        mock_safe_mode.return_value = False

        result = await check_outbound_guardrails(ctx)

        # MANUAL não é bloqueado por campaign_cooldown
        assert not result.is_blocked
        assert result.reason_code == "ok"

    @pytest.mark.asyncio
    @patch("app.services.guardrails.check.load_doctor_state")
    @patch("app.services.guardrails.check.get_campaigns_flags")
    @patch("app.services.guardrails.check.is_safe_mode_active")
    async def test_reply_nao_passa_por_cooldown(
        self,
        mock_safe_mode,
        mock_flags,
        mock_load_state,
        ctx_reply,
    ):
        """Reply válido não deve passar pelo check de cooldown."""
        mock_state = MockDoctorState(
            last_touch_at=datetime.now(timezone.utc) - timedelta(days=1),
            last_touch_method="campaign",
            last_touch_campaign_id="100",
        )
        mock_load_state.return_value = mock_state
        mock_flags.return_value = MagicMock(enabled=True)
        mock_safe_mode.return_value = False

        result = await check_outbound_guardrails(ctx_reply)

        # Reply válido é permitido (reason_code != campaign_cooldown)
        assert not result.is_blocked or result.reason_code != "campaign_cooldown"

    @pytest.mark.asyncio
    @patch("app.services.guardrails.check.load_doctor_state")
    @patch("app.services.guardrails.check.get_campaigns_flags")
    @patch("app.services.guardrails.check.is_safe_mode_active")
    async def test_campanha_sem_cooldown_permitida(
        self,
        mock_safe_mode,
        mock_flags,
        mock_load_state,
        ctx_campanha_a,
    ):
        """Campanha sem cooldown anterior deve ser permitida."""
        mock_state = MockDoctorState()  # Sem last_touch
        mock_load_state.return_value = mock_state
        mock_flags.return_value = MagicMock(enabled=True)
        mock_safe_mode.return_value = False

        result = await check_outbound_guardrails(ctx_campanha_a)

        assert not result.is_blocked
        assert result.reason_code == "ok"


class TestCooldownDays:
    """Testes de limites de dias."""

    def test_cooldown_dias_configurado(self):
        """CAMPAIGN_COOLDOWN_DAYS deve ser 3."""
        assert CAMPAIGN_COOLDOWN_DAYS == 3

    def test_bloqueio_no_dia_2(self, ctx_campanha_b):
        """Dia 2 deve bloquear."""
        state = MockDoctorState(
            last_touch_at=datetime.now(timezone.utc) - timedelta(days=2),
            last_touch_method="campaign",
            last_touch_campaign_id="100",
        )

        result = _check_campaign_cooldown_state(ctx_campanha_b, state)
        assert result is not None and result.is_blocked

    def test_bloqueio_no_dia_1(self, ctx_campanha_b):
        """Dia 1 deve bloquear."""
        state = MockDoctorState(
            last_touch_at=datetime.now(timezone.utc) - timedelta(days=1),
            last_touch_method="campaign",
            last_touch_campaign_id="100",
        )

        result = _check_campaign_cooldown_state(ctx_campanha_b, state)
        assert result is not None and result.is_blocked

    def test_liberacao_no_dia_3(self, ctx_campanha_b):
        """Dia 3 (exato) deve liberar."""
        state = MockDoctorState(
            last_touch_at=datetime.now(timezone.utc) - timedelta(days=3),
            last_touch_method="campaign",
            last_touch_campaign_id="100",
        )

        result = _check_campaign_cooldown_state(ctx_campanha_b, state)
        assert result is None  # Libera

    def test_liberacao_no_dia_4(self, ctx_campanha_b):
        """Dia 4 deve liberar."""
        state = MockDoctorState(
            last_touch_at=datetime.now(timezone.utc) - timedelta(days=4),
            last_touch_method="campaign",
            last_touch_campaign_id="100",
        )

        result = _check_campaign_cooldown_state(ctx_campanha_b, state)
        assert result is None  # Libera
