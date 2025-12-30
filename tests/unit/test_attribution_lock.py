"""
Testes para attribution lock.

Sprint 23 - Produção Ready: Protege last_touch quando há inbound recente.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app.services.campaign_attribution import (
    _check_attribution_lock,
    registrar_campaign_touch,
    ATTRIBUTION_LOCK_MINUTES,
    AttributionResult,
)


class TestCheckAttributionLock:
    """Testes para _check_attribution_lock."""

    @pytest.mark.asyncio
    async def test_sem_doctor_state_nao_bloqueia(self):
        """Sem doctor_state, não deve bloquear."""
        with patch("app.services.campaign_attribution.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data=None
            )

            result = await _check_attribution_lock("cliente-123")

            assert result is False

    @pytest.mark.asyncio
    async def test_sem_last_inbound_nao_bloqueia(self):
        """Sem last_inbound_at, não deve bloquear."""
        with patch("app.services.campaign_attribution.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"last_inbound_at": None}
            )

            result = await _check_attribution_lock("cliente-123")

            assert result is False

    @pytest.mark.asyncio
    async def test_inbound_recente_bloqueia(self):
        """Inbound recente (< LOCK_MINUTES) deve bloquear."""
        # Inbound há 30 minutos (dentro do lock de 60 min)
        inbound_at = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()

        with patch("app.services.campaign_attribution.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"last_inbound_at": inbound_at}
            )

            result = await _check_attribution_lock("cliente-123")

            assert result is True

    @pytest.mark.asyncio
    async def test_inbound_antigo_nao_bloqueia(self):
        """Inbound antigo (>= LOCK_MINUTES) não deve bloquear."""
        # Inbound há 90 minutos (fora do lock de 60 min)
        inbound_at = (datetime.now(timezone.utc) - timedelta(minutes=90)).isoformat()

        with patch("app.services.campaign_attribution.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"last_inbound_at": inbound_at}
            )

            result = await _check_attribution_lock("cliente-123")

            assert result is False

    @pytest.mark.asyncio
    async def test_erro_nao_bloqueia(self):
        """Em caso de erro, não deve bloquear (fail-open)."""
        with patch("app.services.campaign_attribution.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception(
                "DB error"
            )

            result = await _check_attribution_lock("cliente-123")

            assert result is False


class TestRegistrarCampaignTouchWithLock:
    """Testes de integração para registrar_campaign_touch com lock."""

    @pytest.mark.asyncio
    async def test_sem_lock_atualiza_last_touch(self):
        """Sem lock, deve atualizar last_touch normalmente."""
        with patch("app.services.campaign_attribution._check_attribution_lock") as mock_lock:
            mock_lock.return_value = False

            with patch("app.services.campaign_attribution.supabase") as mock_supabase:
                # Mock da query de conversa
                mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                    data={"first_touch_campaign_id": 100}
                )
                # Mock do update
                mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

                with patch("app.services.campaign_attribution.emit_event"):
                    result = await registrar_campaign_touch(
                        conversation_id="conv-123",
                        campaign_id=200,
                        touch_type="campaign",
                        cliente_id="cliente-123",
                    )

                    assert result.success is True
                    assert result.last_touch_updated is True
                    assert result.attribution_locked is False

                    # Verificar que update foi chamado com last_touch_*
                    update_call = mock_supabase.table.return_value.update.call_args
                    update_data = update_call[0][0]
                    assert "last_touch_campaign_id" in update_data
                    assert update_data["last_touch_campaign_id"] == 200

    @pytest.mark.asyncio
    async def test_com_lock_nao_atualiza_last_touch(self):
        """Com lock, NÃO deve atualizar last_touch."""
        with patch("app.services.campaign_attribution._check_attribution_lock") as mock_lock:
            mock_lock.return_value = True

            with patch("app.services.campaign_attribution.supabase") as mock_supabase:
                # Mock da query de conversa (já tem first_touch)
                mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                    data={"first_touch_campaign_id": 100}
                )
                # Mock do update
                mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

                with patch("app.services.campaign_attribution.emit_event"):
                    result = await registrar_campaign_touch(
                        conversation_id="conv-123",
                        campaign_id=200,
                        touch_type="campaign",
                        cliente_id="cliente-123",
                    )

                    assert result.success is True
                    assert result.last_touch_updated is False
                    assert result.attribution_locked is True

                    # Verificar que update NÃO foi chamado (nada para atualizar)
                    mock_supabase.table.return_value.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_com_lock_ainda_seta_first_touch(self):
        """Com lock, ainda deve setar first_touch se não existir."""
        with patch("app.services.campaign_attribution._check_attribution_lock") as mock_lock:
            mock_lock.return_value = True

            with patch("app.services.campaign_attribution.supabase") as mock_supabase:
                # Mock da query de conversa (sem first_touch)
                mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                    data={"first_touch_campaign_id": None}
                )
                # Mock do update
                mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

                with patch("app.services.campaign_attribution.emit_event"):
                    result = await registrar_campaign_touch(
                        conversation_id="conv-123",
                        campaign_id=200,
                        touch_type="campaign",
                        cliente_id="cliente-123",
                    )

                    assert result.success is True
                    assert result.first_touch_set is True
                    assert result.last_touch_updated is False
                    assert result.attribution_locked is True

                    # Verificar que update foi chamado apenas com first_touch_*
                    update_call = mock_supabase.table.return_value.update.call_args
                    update_data = update_call[0][0]
                    assert "first_touch_campaign_id" in update_data
                    assert "last_touch_campaign_id" not in update_data


class TestCenarioRealAttributionLock:
    """Testes para cenário real de roubo de crédito."""

    @pytest.mark.asyncio
    async def test_cenario_me_liga_amanha(self):
        """
        Cenário: Médico disse 'me liga amanhã' (inbound recente).
        Nova campanha NÃO deve roubar o crédito da campanha anterior.
        """
        # Médico respondeu há 30 min (dentro do lock)
        inbound_at = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()

        with patch("app.services.campaign_attribution.supabase") as mock_supabase:
            # Mock para _check_attribution_lock
            def mock_execute_side_effect(*args, **kwargs):
                # Primeira chamada: doctor_state (para lock)
                # Segunda chamada: conversations (para touch)
                return MagicMock(data={"last_inbound_at": inbound_at})

            # Configurar mocks
            mock_result_lock = MagicMock(data={"last_inbound_at": inbound_at})
            mock_result_conv = MagicMock(data={"first_touch_campaign_id": 100})

            # Mock encadeado
            mock_table = mock_supabase.table.return_value
            mock_select = mock_table.select.return_value
            mock_eq = mock_select.eq.return_value
            mock_single = mock_eq.single.return_value

            # Configurar retornos diferentes para cada chamada
            mock_single.execute.side_effect = [mock_result_lock, mock_result_conv]

            with patch("app.services.campaign_attribution.emit_event"):
                result = await registrar_campaign_touch(
                    conversation_id="conv-123",
                    campaign_id=200,  # Nova campanha tentando "roubar"
                    touch_type="campaign",
                    cliente_id="cliente-123",
                )

                # Campanha 200 NÃO deve ter atualizado last_touch
                assert result.attribution_locked is True
                assert result.last_touch_updated is False

                # O crédito permanece com a campanha anterior (100)


class TestLockMinutesConfig:
    """Testes para configuração do lock."""

    def test_lock_minutes_valor_padrao(self):
        """Lock deve ser 60 minutos por padrão."""
        assert ATTRIBUTION_LOCK_MINUTES == 60
