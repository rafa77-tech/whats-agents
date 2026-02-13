"""
Testes de caracterizacao para app/services/outbound/

Sprint 58 - Epic 0: Safety Net
Captura o comportamento atual de send_outbound_message e helpers.

Foca em:
- Contratos de OutboundResult (shape, campos)
- Fluxos de decisao: dev allowlist -> dedupe -> guardrails -> envio
- Factories de contexto (criar_contexto_*)
- DEV guardrail behavior

Sprint 58 E04: Patch paths atualizados para package structure.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def ctx_campanha():
    from app.services.guardrails import (
        OutboundContext,
        OutboundChannel,
        OutboundMethod,
        ActorType,
    )

    return OutboundContext(
        cliente_id=str(uuid4()),
        actor_type=ActorType.SYSTEM,
        channel=OutboundChannel.JOB,
        method=OutboundMethod.CAMPAIGN,
        is_proactive=True,
        campaign_id="camp-123",
        conversation_id=str(uuid4()),
    )


@pytest.fixture
def ctx_reply():
    from app.services.guardrails import (
        OutboundContext,
        OutboundChannel,
        OutboundMethod,
        ActorType,
    )

    return OutboundContext(
        cliente_id=str(uuid4()),
        actor_type=ActorType.BOT,
        channel=OutboundChannel.WHATSAPP,
        method=OutboundMethod.REPLY,
        is_proactive=False,
        conversation_id=str(uuid4()),
        inbound_interaction_id=42,
        last_inbound_at="2025-01-15T10:00:00Z",
    )


# =============================================================================
# OutboundResult
# =============================================================================


class TestOutboundResult:
    """Testa shape do OutboundResult."""

    def test_outbound_result_sucesso(self):
        from app.services.outbound import OutboundResult
        from app.services.guardrails import SendOutcome

        result = OutboundResult(
            success=True,
            outcome=SendOutcome.SENT,
            outcome_reason_code="ok",
            outcome_at=datetime.now(timezone.utc),
            provider_message_id="msg-123",
        )
        assert result.success is True
        assert result.blocked is False
        assert result.deduped is False
        assert result.provider_message_id == "msg-123"
        assert result.block_reason == "ok"  # Alias

    def test_outbound_result_bloqueado(self):
        from app.services.outbound import OutboundResult
        from app.services.guardrails import SendOutcome

        result = OutboundResult(
            success=False,
            outcome=SendOutcome.BLOCKED_OPTED_OUT,
            outcome_reason_code="opted_out",
            blocked=True,
        )
        assert result.success is False
        assert result.blocked is True
        assert result.deduped is False

    def test_outbound_result_deduped(self):
        from app.services.outbound import OutboundResult
        from app.services.guardrails import SendOutcome

        result = OutboundResult(
            success=False,
            outcome=SendOutcome.DEDUPED,
            outcome_reason_code="content_hash_window:duplicate",
            blocked=False,
            deduped=True,
            dedupe_key="dk-123",
        )
        assert result.deduped is True
        assert result.blocked is False

    def test_outbound_result_chip_id(self):
        from app.services.outbound import OutboundResult
        from app.services.guardrails import SendOutcome

        result = OutboundResult(
            success=True,
            outcome=SendOutcome.SENT,
            chip_id="chip-abc",
        )
        assert result.chip_id == "chip-abc"


# =============================================================================
# send_outbound_message paths
# =============================================================================


class TestSendOutboundMessage:
    """Testa send_outbound_message - caminhos principais."""

    @pytest.mark.asyncio
    async def test_dev_allowlist_bloqueia(self, ctx_campanha):
        from app.services.outbound import send_outbound_message
        from app.services.guardrails import SendOutcome

        with patch(
            "app.services.outbound.sender._verificar_dev_allowlist",
            return_value=(False, "dev_allowlist"),
        ):
            result = await send_outbound_message(
                telefone="5511999999999",
                texto="Oi!",
                ctx=ctx_campanha,
            )
            assert result.success is False
            assert result.outcome == SendOutcome.BLOCKED_DEV_ALLOWLIST
            assert result.blocked is True

    @pytest.mark.asyncio
    async def test_deduplicacao_bloqueia(self, ctx_campanha):
        from app.services.outbound import send_outbound_message
        from app.services.guardrails import SendOutcome

        with (
            patch(
                "app.services.outbound.sender._verificar_dev_allowlist",
                return_value=(True, None),
            ),
            patch(
                "app.services.outbound.sender.verificar_e_reservar",
                new_callable=AsyncMock,
                return_value=(False, "dk-123", "duplicate"),
            ),
        ):
            result = await send_outbound_message(
                telefone="5511999999999",
                texto="Oi!",
                ctx=ctx_campanha,
            )
            assert result.success is False
            assert result.outcome == SendOutcome.DEDUPED
            assert result.deduped is True
            assert result.blocked is False

    @pytest.mark.asyncio
    async def test_guardrail_bloqueia(self, ctx_campanha):
        from app.services.outbound import send_outbound_message
        from app.services.guardrails import SendOutcome

        mock_guardrail_result = MagicMock()
        mock_guardrail_result.is_blocked = True
        mock_guardrail_result.reason_code = "opted_out"
        mock_guardrail_result.human_bypass = False

        with (
            patch(
                "app.services.outbound.sender._verificar_dev_allowlist",
                return_value=(True, None),
            ),
            patch(
                "app.services.outbound.sender.verificar_e_reservar",
                new_callable=AsyncMock,
                return_value=(True, "dk-123", None),
            ),
            patch(
                "app.services.outbound.sender.check_outbound_guardrails",
                new_callable=AsyncMock,
                return_value=mock_guardrail_result,
            ),
        ):
            result = await send_outbound_message(
                telefone="5511999999999",
                texto="Oi!",
                ctx=ctx_campanha,
            )
            assert result.success is False
            assert result.blocked is True

    @pytest.mark.asyncio
    async def test_envio_sucesso(self, ctx_reply):
        from app.services.outbound import send_outbound_message
        from app.services.guardrails import SendOutcome

        mock_guardrail_result = MagicMock()
        mock_guardrail_result.is_blocked = False
        mock_guardrail_result.human_bypass = False
        mock_guardrail_result.reason_code = None

        with (
            patch(
                "app.services.outbound.sender._verificar_dev_allowlist",
                return_value=(True, None),
            ),
            patch(
                "app.services.outbound.sender.verificar_e_reservar",
                new_callable=AsyncMock,
                return_value=(True, "dk-123", None),
            ),
            patch(
                "app.services.outbound.sender.check_outbound_guardrails",
                new_callable=AsyncMock,
                return_value=mock_guardrail_result,
            ),
            patch(
                "app.services.outbound.sender._is_multi_chip_enabled",
                return_value=False,
            ),
            patch(
                "app.services.outbound.sender.evolution.enviar_mensagem",
                new_callable=AsyncMock,
                return_value={"key": {"id": "msg-abc"}},
            ),
            patch(
                "app.services.outbound.sender.marcar_enviado",
                new_callable=AsyncMock,
            ),
            patch(
                "app.services.outbound.sender._finalizar_envio",
                new_callable=AsyncMock,
            ),
        ):
            result = await send_outbound_message(
                telefone="5511999999999",
                texto="Oi!",
                ctx=ctx_reply,
            )
            assert result.success is True
            assert result.outcome == SendOutcome.SENT
            assert result.provider_message_id == "msg-abc"

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, ctx_campanha):
        from app.services.outbound import send_outbound_message
        from app.services.guardrails import SendOutcome

        mock_guardrail_result = MagicMock()
        mock_guardrail_result.is_blocked = False
        mock_guardrail_result.human_bypass = False

        with (
            patch(
                "app.services.outbound.sender._verificar_dev_allowlist",
                return_value=(True, None),
            ),
            patch(
                "app.services.outbound.sender.verificar_e_reservar",
                new_callable=AsyncMock,
                return_value=(True, "dk-123", None),
            ),
            patch(
                "app.services.outbound.sender.check_outbound_guardrails",
                new_callable=AsyncMock,
                return_value=mock_guardrail_result,
            ),
            patch(
                "app.services.outbound.sender._is_multi_chip_enabled",
                return_value=False,
            ),
            patch(
                "app.services.outbound.sender.evolution.enviar_mensagem",
                new_callable=AsyncMock,
                side_effect=__import__("app.services.whatsapp", fromlist=["RateLimitError"]).RateLimitError(
                    "Rate limit exceeded"
                ),
            ),
            patch("app.services.outbound.sender.marcar_falha", new_callable=AsyncMock),
            patch("app.services.outbound.sender._finalizar_envio", new_callable=AsyncMock),
        ):
            result = await send_outbound_message(
                telefone="5511999999999",
                texto="Oi!",
                ctx=ctx_campanha,
            )
            assert result.success is False
            assert result.outcome == SendOutcome.FAILED_RATE_LIMIT


# =============================================================================
# DEV Allowlist
# =============================================================================


class TestDevAllowlist:
    """Testa _verificar_dev_allowlist."""

    def test_producao_permite_tudo(self):
        from app.services.outbound import _verificar_dev_allowlist

        with patch("app.services.outbound.dev_guardrails.settings") as mock_settings:
            mock_settings.is_production = True
            pode, reason = _verificar_dev_allowlist("5511999999999")
            assert pode is True
            assert reason is None

    def test_dev_sem_allowlist_bloqueia(self):
        from app.services.outbound import _verificar_dev_allowlist

        with patch("app.services.outbound.dev_guardrails.settings") as mock_settings:
            mock_settings.is_production = False
            mock_settings.outbound_allowlist_numbers = []
            pode, reason = _verificar_dev_allowlist("5511999999999")
            assert pode is False
            assert reason == "dev_allowlist_empty"

    def test_dev_numero_na_allowlist(self):
        from app.services.outbound import _verificar_dev_allowlist

        with patch("app.services.outbound.dev_guardrails.settings") as mock_settings:
            mock_settings.is_production = False
            mock_settings.outbound_allowlist_numbers = ["5511999999999"]
            pode, reason = _verificar_dev_allowlist("5511999999999")
            assert pode is True
            assert reason is None

    def test_dev_numero_fora_allowlist(self):
        from app.services.outbound import _verificar_dev_allowlist

        with patch("app.services.outbound.dev_guardrails.settings") as mock_settings:
            mock_settings.is_production = False
            mock_settings.outbound_allowlist_numbers = ["5511888888888"]
            pode, reason = _verificar_dev_allowlist("5511999999999")
            assert pode is False
            assert reason == "dev_allowlist"


# =============================================================================
# Context Factories
# =============================================================================


class TestContextFactories:
    """Testa helpers para criar contexto."""

    def test_criar_contexto_campanha(self):
        from app.services.outbound import criar_contexto_campanha
        from app.services.guardrails import OutboundMethod, ActorType

        ctx = criar_contexto_campanha(
            cliente_id="cli-123",
            campaign_id="camp-456",
            conversation_id="conv-789",
        )
        assert ctx.cliente_id == "cli-123"
        assert ctx.campaign_id == "camp-456"
        assert ctx.method == OutboundMethod.CAMPAIGN
        assert ctx.actor_type == ActorType.SYSTEM
        assert ctx.is_proactive is True

    def test_criar_contexto_followup(self):
        from app.services.outbound import criar_contexto_followup
        from app.services.guardrails import OutboundMethod

        ctx = criar_contexto_followup(
            cliente_id="cli-123",
            conversation_id="conv-789",
            policy_decision_id="pd-123",
        )
        assert ctx.method == OutboundMethod.FOLLOWUP
        assert ctx.is_proactive is True
        assert ctx.policy_decision_id == "pd-123"

    def test_criar_contexto_reativacao(self):
        from app.services.outbound import criar_contexto_reativacao
        from app.services.guardrails import OutboundMethod

        ctx = criar_contexto_reativacao(cliente_id="cli-123")
        assert ctx.method == OutboundMethod.REACTIVATION
        assert ctx.is_proactive is True

    def test_criar_contexto_reply(self):
        from app.services.outbound import criar_contexto_reply
        from app.services.guardrails import OutboundMethod

        ctx = criar_contexto_reply(
            cliente_id="cli-123",
            conversation_id="conv-789",
            inbound_interaction_id=42,
            last_inbound_at="2025-01-15T10:00:00Z",
        )
        assert ctx.method == OutboundMethod.REPLY
        assert ctx.is_proactive is False
        assert ctx.inbound_interaction_id == 42

    def test_criar_contexto_manual_slack(self):
        from app.services.outbound import criar_contexto_manual_slack
        from app.services.guardrails import ActorType, OutboundChannel

        ctx = criar_contexto_manual_slack(
            cliente_id="cli-123",
            actor_id="user-abc",
            bypass_reason="Teste manual",
        )
        assert ctx.actor_type == ActorType.HUMAN
        assert ctx.channel == OutboundChannel.SLACK
        assert ctx.bypass_reason == "Teste manual"


# =============================================================================
# Helpers internos
# =============================================================================


class TestHelpers:
    """Testa helpers internos."""

    def test_gerar_content_hash(self):
        from app.services.outbound import _gerar_content_hash

        hash1 = _gerar_content_hash("Oi!")
        hash2 = _gerar_content_hash("Oi!")
        hash3 = _gerar_content_hash("Tchau!")

        assert hash1 == hash2  # Deterministico
        assert hash1 != hash3  # Diferente para conteudos diferentes
        assert len(hash1) == 16  # Truncado em 16 chars

    def test_determinar_tipo_mensagem(self):
        from app.services.outbound import _determinar_tipo_mensagem
        from app.services.guardrails import (
            OutboundContext,
            OutboundChannel,
            OutboundMethod,
            ActorType,
        )

        # Reply -> resposta
        ctx = OutboundContext(
            cliente_id="c",
            actor_type=ActorType.BOT,
            channel=OutboundChannel.WHATSAPP,
            method=OutboundMethod.REPLY,
            is_proactive=False,
        )
        assert _determinar_tipo_mensagem(ctx) == "resposta"

        # Campaign proativo -> prospeccao
        ctx = OutboundContext(
            cliente_id="c",
            actor_type=ActorType.SYSTEM,
            channel=OutboundChannel.JOB,
            method=OutboundMethod.CAMPAIGN,
            is_proactive=True,
        )
        assert _determinar_tipo_mensagem(ctx) == "prospeccao"

        # Followup -> followup
        ctx = OutboundContext(
            cliente_id="c",
            actor_type=ActorType.BOT,
            channel=OutboundChannel.WHATSAPP,
            method=OutboundMethod.FOLLOWUP,
            is_proactive=True,
        )
        assert _determinar_tipo_mensagem(ctx) == "followup"

    def test_is_multi_chip_enabled(self):
        from app.services.outbound import _is_multi_chip_enabled

        with patch("app.services.outbound.multi_chip.settings") as mock_settings:
            mock_settings.MULTI_CHIP_ENABLED = True
            assert _is_multi_chip_enabled() is True

            mock_settings.MULTI_CHIP_ENABLED = False
            assert _is_multi_chip_enabled() is False
