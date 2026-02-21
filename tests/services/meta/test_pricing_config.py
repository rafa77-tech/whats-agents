"""
Testes para configurações de pricing Meta (Sprint 67, Chunk 1).
"""

import pytest
from unittest.mock import patch


class TestMetaPricingConfig:
    """Testes das configurações de pricing e budget Meta."""

    def test_pricing_defaults(self):
        """Verifica que os defaults de pricing estão configurados corretamente."""
        from app.core.config import Settings

        s = Settings(
            SUPABASE_URL="https://test.supabase.co",
            SUPABASE_SERVICE_KEY="test-key",
        )
        assert s.META_PRICING_MARKETING_USD == 0.0625
        assert s.META_PRICING_UTILITY_USD == 0.0350
        assert s.META_PRICING_AUTHENTICATION_USD == 0.0315
        assert s.META_BUDGET_DIARIO_USD == 50.0
        assert s.META_BUDGET_ALERT_THRESHOLD == 0.8

    def test_pricing_override_via_env(self):
        """Verifica que os valores podem ser sobrescritos via variáveis de ambiente."""
        with patch.dict(
            "os.environ",
            {
                "META_PRICING_MARKETING_USD": "0.10",
                "META_PRICING_UTILITY_USD": "0.05",
                "META_PRICING_AUTHENTICATION_USD": "0.04",
                "META_BUDGET_DIARIO_USD": "100.0",
                "META_BUDGET_ALERT_THRESHOLD": "0.9",
            },
        ):
            from app.core.config import Settings

            s = Settings(
                SUPABASE_URL="https://test.supabase.co",
                SUPABASE_SERVICE_KEY="test-key",
            )
            assert s.META_PRICING_MARKETING_USD == 0.10
            assert s.META_PRICING_UTILITY_USD == 0.05
            assert s.META_PRICING_AUTHENTICATION_USD == 0.04
            assert s.META_BUDGET_DIARIO_USD == 100.0
            assert s.META_BUDGET_ALERT_THRESHOLD == 0.9
