"""
Testes para regras de auto-recovery e anti-flap de qualidade Meta.

Sprint 67 (R9, Chunk 3) — 5 testes.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone

from app.services.meta.quality_rules import (
    calcular_trust_recovery,
    verificar_anti_flap,
    deve_reativar_chip,
    deve_desativar_chip,
    TRUST_RED_TO_GREEN,
)


class TestCalcularTrustRecovery:
    """Testes de cálculo de trust após mudança de qualidade."""

    def test_red_to_green_trust_30(self):
        """RED → GREEN deve retornar trust = 30."""
        assert calcular_trust_recovery("RED", "GREEN", 0) == TRUST_RED_TO_GREEN
        assert calcular_trust_recovery("RED", "GREEN", 50) == TRUST_RED_TO_GREEN

    def test_yellow_to_green_trust_reduzido(self):
        """YELLOW → GREEN deve retornar trust * 0.8."""
        assert calcular_trust_recovery("YELLOW", "GREEN", 50) == 40
        assert calcular_trust_recovery("YELLOW", "GREEN", 100) == 80

    def test_any_to_red_trust_zero(self):
        """Qualquer transição para RED deve zerar trust."""
        assert calcular_trust_recovery("GREEN", "RED", 100) == 0
        assert calcular_trust_recovery("YELLOW", "RED", 50) == 0


class TestDeveReativarChip:
    """Testes de decisão de reativação."""

    def test_red_to_yellow_nao_reativa(self):
        """RED → YELLOW não deve reativar (ainda não confiável)."""
        assert deve_reativar_chip("RED", "YELLOW") is False

    def test_red_to_green_reativa(self):
        """RED → GREEN deve reativar."""
        assert deve_reativar_chip("RED", "GREEN") is True

    def test_yellow_to_green_reativa(self):
        """YELLOW → GREEN deve reativar."""
        assert deve_reativar_chip("YELLOW", "GREEN") is True


class TestAntiFlap:
    """Testes de anti-flap com mock de Supabase."""

    @pytest.mark.asyncio
    async def test_anti_flap_muitas_oscilacoes(self):
        """Chip com >3 oscilações em 24h deve entrar em cooldown."""
        now = datetime.now(timezone.utc)
        # 5 oscilações: GREEN → YELLOW → GREEN → RED → GREEN → YELLOW
        history = [
            {"id": 1, "quality_rating": "GREEN", "checked_at": (now - timedelta(hours=5)).isoformat()},
            {"id": 2, "quality_rating": "YELLOW", "checked_at": (now - timedelta(hours=4)).isoformat()},
            {"id": 3, "quality_rating": "GREEN", "checked_at": (now - timedelta(hours=3)).isoformat()},
            {"id": 4, "quality_rating": "RED", "checked_at": (now - timedelta(hours=2)).isoformat()},
            {"id": 5, "quality_rating": "GREEN", "checked_at": (now - timedelta(hours=1)).isoformat()},
            {"id": 6, "quality_rating": "YELLOW", "checked_at": now.isoformat()},
        ]

        mock_resp = MagicMock()
        mock_resp.data = history

        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.gte.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.execute.return_value = mock_resp

        with patch("app.services.meta.quality_rules.supabase") as mock_sb:
            mock_sb.table.return_value = mock_chain
            result = await verificar_anti_flap("chip-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_anti_flap_poucas_oscilacoes_ok(self):
        """Chip com ≤3 oscilações em 24h NÃO está em cooldown."""
        now = datetime.now(timezone.utc)
        # 2 oscilações: GREEN → YELLOW → GREEN
        history = [
            {"id": 1, "quality_rating": "GREEN", "checked_at": (now - timedelta(hours=3)).isoformat()},
            {"id": 2, "quality_rating": "YELLOW", "checked_at": (now - timedelta(hours=2)).isoformat()},
            {"id": 3, "quality_rating": "GREEN", "checked_at": (now - timedelta(hours=1)).isoformat()},
        ]

        mock_resp = MagicMock()
        mock_resp.data = history

        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.gte.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.execute.return_value = mock_resp

        with patch("app.services.meta.quality_rules.supabase") as mock_sb:
            mock_sb.table.return_value = mock_chain
            result = await verificar_anti_flap("chip-456")

        assert result is False
