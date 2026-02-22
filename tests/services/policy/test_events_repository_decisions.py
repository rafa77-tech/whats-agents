"""Testes do metodo listar_decisoes_por_cliente.

Sprint 72 - Epic 02
"""

import pytest
from unittest.mock import patch

from app.services.policy.events_repository import listar_decisoes_por_cliente


PATCH_TARGET = "app.services.policy.events_repository.supabase"


class TestListarDecisoesPorCliente:
    """Testes do metodo listar_decisoes_por_cliente."""

    @pytest.mark.asyncio
    async def test_retorna_decisoes(self):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_data = [
                {
                    "event_id": "evt-1",
                    "event_type": "decision",
                    "cliente_id": "cli-123",
                    "rule_matched": "R01",
                    "primary_action": "respond",
                    "ts": "2026-02-21T10:00:00+00:00",
                },
                {
                    "event_id": "evt-2",
                    "event_type": "decision",
                    "cliente_id": "cli-123",
                    "rule_matched": "R03",
                    "primary_action": "wait",
                    "ts": "2026-02-21T09:00:00+00:00",
                },
            ]
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = mock_data

            result = await listar_decisoes_por_cliente("cli-123", horas=24, limite=50)

            assert len(result) == 2
            assert result[0]["rule_matched"] == "R01"
            mock_supabase.table.assert_called_with("policy_events")

    @pytest.mark.asyncio
    async def test_retorna_vazio_sem_dados(self):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = []

            result = await listar_decisoes_por_cliente("cli-999")

            assert result == []

    @pytest.mark.asyncio
    async def test_erro_retorna_vazio(self):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.side_effect = Exception(
                "DB error"
            )

            result = await listar_decisoes_por_cliente("cli-123")

            assert result == []

    @pytest.mark.asyncio
    async def test_parametros_custom(self):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = []

            await listar_decisoes_por_cliente("cli-123", horas=48, limite=100)

            # Verifica que limit foi chamado com o valor correto
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.limit.assert_called_with(100)
