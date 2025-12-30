"""
Testes para classificador de erros de provider.

Sprint 23 - Produção Ready: Distinguir FAILED_VALIDATION de FAILED_PROVIDER.
"""
import pytest

from app.services.guardrails.error_classifier import (
    classify_provider_error,
    classify_error_string,
    ClassifiedError,
)
from app.services.guardrails.types import SendOutcome


class TestClassifyProviderError:
    """Testes para classify_provider_error."""

    def test_numero_invalido_retorna_validation(self):
        """Número inválido deve retornar FAILED_VALIDATION."""
        error = Exception("invalid number format: 123")
        result = classify_provider_error(error)

        assert result.outcome == SendOutcome.FAILED_VALIDATION
        assert result.provider_error_code == "invalid_number"

    def test_numero_nao_registrado_retorna_validation(self):
        """Número não registrado no WhatsApp deve retornar FAILED_VALIDATION."""
        error = Exception("The phone number is not registered on WhatsApp")
        result = classify_provider_error(error)

        assert result.outcome == SendOutcome.FAILED_VALIDATION
        assert result.provider_error_code == "not_on_whatsapp"

    def test_jid_invalido_retorna_validation(self):
        """JID inválido deve retornar FAILED_VALIDATION."""
        error = Exception("invalid jid: 5511999@s.whatsapp.net")
        result = classify_provider_error(error)

        assert result.outcome == SendOutcome.FAILED_VALIDATION
        assert result.provider_error_code == "invalid_jid"

    def test_numero_nao_encontrado_retorna_validation(self):
        """Número não encontrado deve retornar FAILED_VALIDATION."""
        error = Exception("404: number not found")
        result = classify_provider_error(error)

        assert result.outcome == SendOutcome.FAILED_VALIDATION
        assert result.provider_error_code == "number_not_found"

    def test_bloqueado_por_usuario_retorna_banned(self):
        """Bloqueado pelo usuário deve retornar FAILED_BANNED."""
        error = Exception("Message blocked by user privacy settings")
        result = classify_provider_error(error)

        assert result.outcome == SendOutcome.FAILED_BANNED
        # "blocked by user" é detectado primeiro, então retorna blocked_by_user
        assert result.provider_error_code in ("privacy_settings", "blocked_by_user")

    def test_usuario_banido_retorna_banned(self):
        """Conta banida deve retornar FAILED_BANNED."""
        error = Exception("This account has been banned for spam")
        result = classify_provider_error(error)

        assert result.outcome == SendOutcome.FAILED_BANNED
        assert result.provider_error_code in ("banned", "spam_detected")

    def test_conta_restrita_retorna_banned(self):
        """Conta restrita deve retornar FAILED_BANNED."""
        error = Exception("Account is restricted")
        result = classify_provider_error(error)

        assert result.outcome == SendOutcome.FAILED_BANNED
        assert result.provider_error_code == "account_restricted"

    def test_timeout_retorna_provider(self):
        """Timeout deve retornar FAILED_PROVIDER."""
        error = Exception("Connection timeout after 30s")
        result = classify_provider_error(error)

        assert result.outcome == SendOutcome.FAILED_PROVIDER
        assert result.provider_error_code == "timeout"

    def test_erro_rede_retorna_provider(self):
        """Erro de rede deve retornar FAILED_PROVIDER."""
        error = Exception("Network connection refused")
        result = classify_provider_error(error)

        assert result.outcome == SendOutcome.FAILED_PROVIDER
        assert result.provider_error_code == "network_error"

    def test_erro_5xx_retorna_provider(self):
        """Erro 5xx deve retornar FAILED_PROVIDER."""
        error = Exception("502 Bad Gateway")
        result = classify_provider_error(error)

        assert result.outcome == SendOutcome.FAILED_PROVIDER
        assert result.provider_error_code == "server_error"

    def test_erro_desconhecido_retorna_provider(self):
        """Erro desconhecido deve retornar FAILED_PROVIDER como fallback."""
        error = Exception("Something completely unexpected happened")
        result = classify_provider_error(error)

        assert result.outcome == SendOutcome.FAILED_PROVIDER
        assert result.provider_error_code == "unknown"

    def test_trunca_erro_raw(self):
        """Erro raw deve ser truncado para storage."""
        long_error = "x" * 500
        error = Exception(long_error)
        result = classify_provider_error(error)

        assert len(result.provider_error_raw) <= 200


class TestClassifyErrorString:
    """Testes para classify_error_string (versão simplificada)."""

    def test_retorna_tuple(self):
        """Deve retornar tuple de (outcome, code)."""
        outcome, code = classify_error_string("invalid number")

        assert outcome == SendOutcome.FAILED_VALIDATION
        assert isinstance(code, str)

    def test_banned_patterns(self):
        """Deve detectar padrões de banimento."""
        patterns = [
            "blocked by user",
            "user blocked",
            "spam detected",
            "account restricted",
            "privacy settings",
        ]

        for pattern in patterns:
            outcome, _ = classify_error_string(pattern)
            assert outcome == SendOutcome.FAILED_BANNED, f"Falhou para: {pattern}"

    def test_validation_patterns(self):
        """Deve detectar padrões de validação."""
        patterns = [
            "invalid number",
            "not registered",
            "does not exist",
            "not on whatsapp",
            "invalid jid",
        ]

        for pattern in patterns:
            outcome, _ = classify_error_string(pattern)
            assert outcome == SendOutcome.FAILED_VALIDATION, f"Falhou para: {pattern}"


class TestErrorCodeExtraction:
    """Testes para extração de código de erro."""

    def test_not_on_whatsapp_code(self):
        """Deve extrair código específico para 'not on whatsapp'."""
        error = Exception("Number is not on WhatsApp")
        result = classify_provider_error(error)

        assert result.provider_error_code == "not_on_whatsapp"

    def test_blocked_by_user_code(self):
        """Deve extrair código específico para 'blocked by user'."""
        error = Exception("Message was blocked by user")
        result = classify_provider_error(error)

        assert result.provider_error_code == "blocked_by_user"

    def test_timeout_code(self):
        """Deve extrair código específico para timeout."""
        error = Exception("Request timeout")
        result = classify_provider_error(error)

        assert result.provider_error_code == "timeout"
