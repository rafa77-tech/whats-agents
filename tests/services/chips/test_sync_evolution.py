"""
Tests for sync_evolution.py — Issue #90.

Validates chip synchronization with Evolution API instances.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

_MOD = "app.services.chips.sync_evolution"


def _make_instance(name, state="open", phone="5511999999999"):
    """Build an Evolution API instance dict."""
    return {
        "name": name,
        "connectionStatus": state,
        "ownerJid": f"{phone}@s.whatsapp.net" if phone else None,
    }


def _make_chip(
    chip_id, instance_name, status="active", connected=True, provider=None
):
    """Build a chip row dict."""
    return {
        "id": chip_id,
        "instance_name": instance_name,
        "status": status,
        "evolution_connected": connected,
        "provider": provider,
    }


def _mock_supabase_select(chips: list[dict]):
    """Return a supabase mock whose .table('chips').select(...).neq(...).execute()
    returns the given chip list."""
    mock_sb = MagicMock()
    mock_response = MagicMock()
    mock_response.data = chips

    chain = mock_sb.table("chips").select.return_value.neq.return_value
    chain.execute.return_value = mock_response
    return mock_sb


class TestSincronizarChipsComEvolution:
    """Tests for sincronizar_chips_com_evolution."""

    @pytest.mark.asyncio
    async def test_happy_path_atualiza_chips(self):
        """Evolution returns instances → chips updated, stats correct."""
        instances = [_make_instance("julia-01", "open"), _make_instance("julia-02", "close")]
        chips = [
            _make_chip("c1", "julia-01", status="active", connected=False),
            _make_chip("c2", "julia-02", status="active", connected=True),
        ]
        mock_sb = _mock_supabase_select(chips)

        with patch(f"{_MOD}.listar_instancias_evolution", new_callable=AsyncMock, return_value=instances), \
             patch(f"{_MOD}.supabase", mock_sb):

            from app.services.chips.sync_evolution import sincronizar_chips_com_evolution

            stats = await sincronizar_chips_com_evolution()

        assert stats["instancias_evolution"] == 2
        assert stats["chips_atualizados"] == 2
        assert stats["chips_criados"] == 0
        assert stats["erros"] == 0

    @pytest.mark.asyncio
    async def test_zapi_chips_nao_tocados(self):
        """Query uses .neq('provider', 'z-api') — z-api chips excluded."""
        mock_sb = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []

        select_chain = mock_sb.table("chips").select.return_value
        neq_chain = select_chain.neq.return_value
        neq_chain.execute.return_value = mock_response

        instances = [_make_instance("julia-01")]

        with patch(f"{_MOD}.listar_instancias_evolution", new_callable=AsyncMock, return_value=instances), \
             patch(f"{_MOD}.supabase", mock_sb):

            from app.services.chips.sync_evolution import sincronizar_chips_com_evolution

            await sincronizar_chips_com_evolution()

        # Verify the .neq call filters z-api
        select_chain.neq.assert_called_once_with("provider", "z-api")

    @pytest.mark.asyncio
    async def test_nova_instancia_cria_chip_warming(self):
        """Instance not in DB → creates chip with status='warming' if connected."""
        instances = [_make_instance("julia-new", "open", phone="5511888888888")]
        mock_sb = _mock_supabase_select([])  # no existing chips

        with patch(f"{_MOD}.listar_instancias_evolution", new_callable=AsyncMock, return_value=instances), \
             patch(f"{_MOD}.supabase", mock_sb):

            from app.services.chips.sync_evolution import sincronizar_chips_com_evolution

            stats = await sincronizar_chips_com_evolution()

        assert stats["chips_criados"] == 1
        # Verify inserted data
        insert_call = mock_sb.table("chips").insert
        insert_call.assert_called_once()
        inserted = insert_call.call_args[0][0]
        assert inserted["status"] == "warming"
        assert inserted["instance_name"] == "julia-new"
        assert inserted["telefone"] == "5511888888888"

    @pytest.mark.asyncio
    async def test_instancia_ausente_marca_desconectado(self):
        """Chip in DB not in Evolution → evolution_connected=False."""
        instances = []  # no instances returned but we still want chip processing
        chips = [_make_chip("c1", "julia-gone", status="active", connected=True)]

        # Need at least 1 instance to not early-return, so use a dummy
        instances = [_make_instance("julia-other", "open")]
        mock_sb = _mock_supabase_select(chips)

        with patch(f"{_MOD}.listar_instancias_evolution", new_callable=AsyncMock, return_value=instances), \
             patch(f"{_MOD}.supabase", mock_sb):

            from app.services.chips.sync_evolution import sincronizar_chips_com_evolution

            stats = await sincronizar_chips_com_evolution()

        # julia-gone is not in instances → should be marked disconnected
        assert stats["chips_desconectados"] >= 1
        # Verify update was called for the missing chip
        update_calls = mock_sb.table("chips").update.call_args_list
        # Find the call that sets evolution_connected=False for chip c1
        found = any(
            call[0][0].get("evolution_connected") is False
            for call in update_calls
        )
        assert found, "Expected update setting evolution_connected=False"

    @pytest.mark.asyncio
    async def test_pending_para_warming_quando_conectado(self):
        """pending + connected → warming."""
        instances = [_make_instance("julia-pending", "open")]
        chips = [_make_chip("c1", "julia-pending", status="pending", connected=False)]
        mock_sb = _mock_supabase_select(chips)

        with patch(f"{_MOD}.listar_instancias_evolution", new_callable=AsyncMock, return_value=instances), \
             patch(f"{_MOD}.supabase", mock_sb):

            from app.services.chips.sync_evolution import sincronizar_chips_com_evolution

            stats = await sincronizar_chips_com_evolution()

        assert stats["chips_atualizados"] == 1
        update_calls = mock_sb.table("chips").update.call_args_list
        found = any(
            call[0][0].get("status") == "warming"
            for call in update_calls
        )
        assert found, "Expected chip status transition pending → warming"

    @pytest.mark.asyncio
    async def test_active_para_pending_quando_desconectado(self):
        """active + disconnected → pending."""
        instances = [_make_instance("julia-disc", "close")]
        chips = [_make_chip("c1", "julia-disc", status="active", connected=True)]
        mock_sb = _mock_supabase_select(chips)

        with patch(f"{_MOD}.listar_instancias_evolution", new_callable=AsyncMock, return_value=instances), \
             patch(f"{_MOD}.supabase", mock_sb):

            from app.services.chips.sync_evolution import sincronizar_chips_com_evolution

            stats = await sincronizar_chips_com_evolution()

        assert stats["chips_atualizados"] == 1
        update_calls = mock_sb.table("chips").update.call_args_list
        found = any(
            call[0][0].get("status") == "pending"
            for call in update_calls
        )
        assert found, "Expected chip status transition active → pending"

    @pytest.mark.asyncio
    async def test_evolution_api_erro_retorna_stats_vazio(self):
        """API error → empty stats, no crash."""
        with patch(f"{_MOD}.listar_instancias_evolution", new_callable=AsyncMock, return_value=[]):

            from app.services.chips.sync_evolution import sincronizar_chips_com_evolution

            stats = await sincronizar_chips_com_evolution()

        assert stats["instancias_evolution"] == 0
        assert stats["chips_atualizados"] == 0
        assert stats["chips_criados"] == 0
        assert stats["erros"] == 0

    @pytest.mark.asyncio
    async def test_provider_null_tratado_como_evolution(self):
        """provider=NULL chips are included in sync (not filtered by .neq('provider', 'z-api'))."""
        instances = [_make_instance("julia-null", "open")]
        # Chip with provider=None should still be selected
        chips = [_make_chip("c1", "julia-null", status="active", connected=False, provider=None)]
        mock_sb = _mock_supabase_select(chips)

        with patch(f"{_MOD}.listar_instancias_evolution", new_callable=AsyncMock, return_value=instances), \
             patch(f"{_MOD}.supabase", mock_sb):

            from app.services.chips.sync_evolution import sincronizar_chips_com_evolution

            stats = await sincronizar_chips_com_evolution()

        # Chip with provider=NULL should be updated (not skipped)
        assert stats["chips_atualizados"] == 1
