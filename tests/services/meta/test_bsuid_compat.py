"""
Testes para BsuidCompat.

Sprint 70+ — Chunk 30.
"""

import pytest


class TestBsuidCompat:

    @pytest.mark.asyncio
    async def test_resolver_bsuid_passthrough(self):
        from app.services.meta.bsuid_compat import BsuidCompat

        compat = BsuidCompat()
        result = await compat.resolver_bsuid("5511999999999", "waba_1")
        assert result == "5511999999999"

    @pytest.mark.asyncio
    async def test_resolver_telefone_passthrough(self):
        from app.services.meta.bsuid_compat import BsuidCompat

        compat = BsuidCompat()
        result = await compat.resolver_telefone("5511999999999", "waba_1")
        assert result == "5511999999999"

    @pytest.mark.asyncio
    async def test_migrar_para_bsuid_noop(self):
        from app.services.meta.bsuid_compat import BsuidCompat

        compat = BsuidCompat()
        result = await compat.migrar_para_bsuid("waba_1")
        assert result["success"] is True
        assert result["migrated"] == 0

    def test_eh_bsuid_false_v1(self):
        from app.services.meta.bsuid_compat import BsuidCompat

        compat = BsuidCompat()
        assert compat.eh_bsuid("5511999999999") is False
        assert compat.eh_bsuid("bsuid_abc123") is False

    def test_normalizar_identificador_telefone(self):
        from app.services.meta.bsuid_compat import BsuidCompat

        compat = BsuidCompat()
        assert compat.normalizar_identificador("+55 (11) 99999-9999") == "5511999999999"
        assert compat.normalizar_identificador("5511999") == "5511999"
