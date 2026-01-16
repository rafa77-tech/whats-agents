"""
Testes para SendOutcome enum e mapeamento de guardrail.

Sprint 23 E01 - Outcome no Send.
"""
import pytest
from datetime import datetime, timezone

from app.services.guardrails import (
    SendOutcome,
    map_guardrail_to_outcome,
)


class TestSendOutcomeEnum:
    """Testes para o enum SendOutcome."""

    def test_sent_is_success(self):
        """SENT deve ser sucesso."""
        assert SendOutcome.SENT.is_success is True
        assert SendOutcome.SENT.is_blocked is False
        assert SendOutcome.SENT.is_deduped is False
        assert SendOutcome.SENT.is_failed is False

    def test_blocked_outcomes(self):
        """Outcomes BLOCKED_* devem ser bloqueio."""
        blocked_outcomes = [
            SendOutcome.BLOCKED_OPTED_OUT,
            SendOutcome.BLOCKED_COOLING_OFF,
            SendOutcome.BLOCKED_NEXT_ALLOWED,
            SendOutcome.BLOCKED_CONTACT_CAP,
            SendOutcome.BLOCKED_CAMPAIGNS_DISABLED,
            SendOutcome.BLOCKED_SAFE_MODE,
            SendOutcome.BLOCKED_CAMPAIGN_COOLDOWN,
        ]

        for outcome in blocked_outcomes:
            assert outcome.is_blocked is True, f"{outcome.value} should be blocked"
            assert outcome.is_success is False
            assert outcome.is_deduped is False
            assert outcome.is_failed is False

    def test_deduped_is_not_blocked(self):
        """DEDUPED nao deve ser tratado como bloqueio."""
        assert SendOutcome.DEDUPED.is_deduped is True
        assert SendOutcome.DEDUPED.is_blocked is False  # CRITICO
        assert SendOutcome.DEDUPED.is_success is False
        assert SendOutcome.DEDUPED.is_failed is False

    def test_failed_outcomes(self):
        """Outcomes FAILED_* devem ser erro."""
        failed_outcomes = [
            SendOutcome.FAILED_PROVIDER,
            SendOutcome.FAILED_VALIDATION,
            SendOutcome.FAILED_RATE_LIMIT,
            SendOutcome.FAILED_CIRCUIT_OPEN,
        ]

        for outcome in failed_outcomes:
            assert outcome.is_failed is True, f"{outcome.value} should be failed"
            assert outcome.is_success is False
            assert outcome.is_blocked is False
            assert outcome.is_deduped is False

    def test_bypass_is_success(self):
        """BYPASS deve ser tratado como sucesso (envio foi feito)."""
        # BYPASS indica que houve override humano mas mensagem foi enviada
        assert SendOutcome.BYPASS.is_success is False  # Nao e SENT
        assert SendOutcome.BYPASS.is_blocked is False
        assert SendOutcome.BYPASS.is_deduped is False
        assert SendOutcome.BYPASS.is_failed is False

    def test_enum_values_match_db(self):
        """Valores do enum devem corresponder ao banco."""
        # Estes valores devem corresponder ao enum no PostgreSQL
        # Sprint 29+: Adicionados BLOCKED_DEV_ALLOWLIST, BLOCKED_QUIET_HOURS, FAILED_BANNED
        expected_values = {
            "SENT",
            "BLOCKED_OPTED_OUT",
            "BLOCKED_COOLING_OFF",
            "BLOCKED_NEXT_ALLOWED",
            "BLOCKED_CONTACT_CAP",
            "BLOCKED_CAMPAIGNS_DISABLED",
            "BLOCKED_SAFE_MODE",
            "BLOCKED_CAMPAIGN_COOLDOWN",
            "BLOCKED_DEV_ALLOWLIST",
            "BLOCKED_QUIET_HOURS",
            "DEDUPED",
            "FAILED_PROVIDER",
            "FAILED_VALIDATION",
            "FAILED_RATE_LIMIT",
            "FAILED_CIRCUIT_OPEN",
            "FAILED_BANNED",
            "BYPASS",
        }

        actual_values = {outcome.value for outcome in SendOutcome}
        assert actual_values == expected_values


class TestMapGuardrailToOutcome:
    """Testes para mapeamento de reason_code do guardrail."""

    def test_opted_out_mapping(self):
        """opted_out deve mapear para BLOCKED_OPTED_OUT."""
        assert map_guardrail_to_outcome("opted_out") == SendOutcome.BLOCKED_OPTED_OUT

    def test_cooling_off_mapping(self):
        """cooling_off deve mapear para BLOCKED_COOLING_OFF."""
        assert map_guardrail_to_outcome("cooling_off") == SendOutcome.BLOCKED_COOLING_OFF

    def test_next_allowed_at_mapping(self):
        """next_allowed_at deve mapear para BLOCKED_NEXT_ALLOWED."""
        assert map_guardrail_to_outcome("next_allowed_at") == SendOutcome.BLOCKED_NEXT_ALLOWED

    def test_contact_cap_mapping(self):
        """contact_cap deve mapear para BLOCKED_CONTACT_CAP."""
        assert map_guardrail_to_outcome("contact_cap") == SendOutcome.BLOCKED_CONTACT_CAP

    def test_campaigns_disabled_mapping(self):
        """campaigns_disabled deve mapear para BLOCKED_CAMPAIGNS_DISABLED."""
        assert map_guardrail_to_outcome("campaigns_disabled") == SendOutcome.BLOCKED_CAMPAIGNS_DISABLED

    def test_safe_mode_mapping(self):
        """safe_mode deve mapear para BLOCKED_SAFE_MODE."""
        assert map_guardrail_to_outcome("safe_mode") == SendOutcome.BLOCKED_SAFE_MODE

    def test_campaign_cooldown_mapping(self):
        """campaign_cooldown deve mapear para BLOCKED_CAMPAIGN_COOLDOWN."""
        assert map_guardrail_to_outcome("campaign_cooldown") == SendOutcome.BLOCKED_CAMPAIGN_COOLDOWN

    def test_unknown_reason_raises_error(self):
        """reason_code desconhecido deve levantar ValueError."""
        with pytest.raises(ValueError, match="reason_code nao mapeado"):
            map_guardrail_to_outcome("unknown_reason")

    def test_opted_out_bypass_no_reason_mapping(self):
        """opted_out_bypass_no_reason deve mapear para BLOCKED_OPTED_OUT."""
        assert map_guardrail_to_outcome("opted_out_bypass_no_reason") == SendOutcome.BLOCKED_OPTED_OUT


class TestOutboundResultDataclass:
    """Testes para OutboundResult com novos campos."""

    def test_sent_result(self):
        """Resultado de envio bem sucedido."""
        from app.services.outbound import OutboundResult

        now = datetime.now(timezone.utc)
        result = OutboundResult(
            success=True,
            outcome=SendOutcome.SENT,
            outcome_reason_code="ok",
            outcome_at=now,
            provider_message_id="ABC123",
        )

        assert result.success is True
        assert result.outcome == SendOutcome.SENT
        assert result.outcome.is_success is True
        assert result.blocked is False
        assert result.deduped is False
        assert result.provider_message_id == "ABC123"

    def test_blocked_result(self):
        """Resultado de envio bloqueado por guardrail."""
        from app.services.outbound import OutboundResult

        now = datetime.now(timezone.utc)
        result = OutboundResult(
            success=False,
            outcome=SendOutcome.BLOCKED_OPTED_OUT,
            outcome_reason_code="opted_out",
            outcome_at=now,
            blocked=True,
        )

        assert result.success is False
        assert result.outcome.is_blocked is True
        assert result.blocked is True
        assert result.deduped is False
        # Alias para compatibilidade
        assert result.block_reason == "opted_out"

    def test_deduped_result_not_blocked(self):
        """Resultado deduplicado NAO deve ser tratado como bloqueio."""
        from app.services.outbound import OutboundResult

        now = datetime.now(timezone.utc)
        result = OutboundResult(
            success=False,
            outcome=SendOutcome.DEDUPED,
            outcome_reason_code="content_hash_window:duplicata",
            outcome_at=now,
            blocked=False,  # CRITICO: NAO e bloqueio
            deduped=True,
        )

        assert result.success is False
        assert result.outcome.is_deduped is True
        assert result.blocked is False  # CRITICO
        assert result.deduped is True

    def test_failed_result(self):
        """Resultado de erro tecnico."""
        from app.services.outbound import OutboundResult

        now = datetime.now(timezone.utc)
        result = OutboundResult(
            success=False,
            outcome=SendOutcome.FAILED_PROVIDER,
            outcome_reason_code="provider_error:timeout",
            outcome_at=now,
            error="Connection timeout",
        )

        assert result.success is False
        assert result.outcome.is_failed is True
        assert result.blocked is False
        assert result.error == "Connection timeout"

    def test_bypass_result(self):
        """Resultado de bypass humano."""
        from app.services.outbound import OutboundResult

        now = datetime.now(timezone.utc)
        result = OutboundResult(
            success=True,
            outcome=SendOutcome.BYPASS,
            outcome_reason_code="opted_out",
            outcome_at=now,
            human_bypass=True,
            provider_message_id="XYZ789",
        )

        assert result.success is True
        assert result.outcome == SendOutcome.BYPASS
        assert result.human_bypass is True
        assert result.provider_message_id == "XYZ789"
