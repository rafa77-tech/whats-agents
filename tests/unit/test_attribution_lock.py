"""
Testes para attribution lock dinâmico.

Sprint 23 - Produção Ready: Lock 30/60 min baseado em sinais de continuidade.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.campaign_attribution import (
    _check_attribution_lock,
    _has_continuity_signal,
    _buscar_ultimo_inbound_texto,
    registrar_campaign_touch,
    LOCK_DEFAULT_MINUTES,
    LOCK_EXTENDED_MINUTES,
    LockInfo,
    AttributionResult,
)


class TestHasContinuitySignal:
    """Testes para detecção de sinais de continuidade."""

    def test_sem_texto_retorna_false(self):
        """Sem texto, não deve detectar continuidade."""
        has_signal, pattern = _has_continuity_signal("")
        assert has_signal is False
        assert pattern is None

    def test_me_liga_amanha(self):
        """'me liga amanhã' deve detectar continuidade."""
        has_signal, pattern = _has_continuity_signal("me liga amanhã")
        assert has_signal is True
        assert pattern is not None

    def test_mais_tarde(self):
        """'mais tarde' deve detectar continuidade."""
        has_signal, pattern = _has_continuity_signal("Vejo isso mais tarde")
        assert has_signal is True

    def test_agora_nao(self):
        """'agora não' deve detectar continuidade."""
        has_signal, pattern = _has_continuity_signal("Agora não posso")
        assert has_signal is True

    def test_estou_em_procedimento(self):
        """'estou em procedimento' deve detectar continuidade."""
        has_signal, pattern = _has_continuity_signal("Estou em procedimento agora")
        assert has_signal is True

    def test_to_no_cc(self):
        """'to no cc' (centro cirúrgico) deve detectar continuidade."""
        has_signal, pattern = _has_continuity_signal("To no CC, depois falo")
        assert has_signal is True

    def test_em_reuniao(self):
        """'em reunião' deve detectar continuidade."""
        has_signal, pattern = _has_continuity_signal("Estou em reunião")
        assert has_signal is True

    def test_ja_te_respondo(self):
        """'já te respondo' deve detectar continuidade."""
        has_signal, pattern = _has_continuity_signal("Já te respondo")
        assert has_signal is True

    def test_daqui_a_pouco(self):
        """'daqui a pouco' deve detectar continuidade."""
        has_signal, pattern = _has_continuity_signal("Daqui a pouco te falo")
        assert has_signal is True

    def test_mensagem_neutra(self):
        """Mensagem neutra não deve detectar continuidade."""
        has_signal, pattern = _has_continuity_signal("Pode me mandar os detalhes?")
        assert has_signal is False

    def test_ok_simples(self):
        """'ok' simples não deve detectar continuidade."""
        has_signal, pattern = _has_continuity_signal("Ok")
        assert has_signal is False

    def test_case_insensitive(self):
        """Detecção deve ser case insensitive."""
        has_signal, _ = _has_continuity_signal("MAIS TARDE")
        assert has_signal is True


class TestCheckAttributionLock:
    """Testes para _check_attribution_lock."""

    @pytest.mark.asyncio
    async def test_sem_doctor_state_retorna_no_lock(self):
        """Sem doctor_state, retorna lock desativado."""
        with patch("app.services.campaign_attribution.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data=None
            )

            result = await _check_attribution_lock("cliente-123")

            assert isinstance(result, LockInfo)
            assert result.is_locked is False
            assert result.lock_reason == "none"

    @pytest.mark.asyncio
    async def test_sem_last_inbound_retorna_no_lock(self):
        """Sem last_inbound_at, retorna lock desativado."""
        with patch("app.services.campaign_attribution.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"last_inbound_at": None}
            )

            result = await _check_attribution_lock("cliente-123")

            assert result.is_locked is False
            assert result.lock_reason == "none"

    @pytest.mark.asyncio
    async def test_inbound_antigo_nao_busca_texto(self):
        """Inbound >= 30 min não deve buscar texto (gate)."""
        # Inbound há 35 minutos
        inbound_at = (datetime.now(timezone.utc) - timedelta(minutes=35)).isoformat()

        with patch("app.services.campaign_attribution.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"last_inbound_at": inbound_at}
            )

            with patch("app.services.campaign_attribution._buscar_ultimo_inbound_texto") as mock_buscar:
                result = await _check_attribution_lock("cliente-123")

                # Não deve ter chamado busca de texto
                mock_buscar.assert_not_called()
                assert result.is_locked is False

    @pytest.mark.asyncio
    async def test_inbound_recente_sem_continuidade_lock_30(self):
        """Inbound < 30 min sem sinal de continuidade → lock 30 min."""
        # Inbound há 15 minutos
        inbound_at = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()

        with patch("app.services.campaign_attribution.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"last_inbound_at": inbound_at}
            )

            with patch("app.services.campaign_attribution._buscar_ultimo_inbound_texto") as mock_buscar:
                mock_buscar.return_value = "Pode me mandar os detalhes?"

                result = await _check_attribution_lock("cliente-123")

                assert result.is_locked is True
                assert result.lock_minutes == LOCK_DEFAULT_MINUTES
                assert result.lock_reason == "default"

    @pytest.mark.asyncio
    async def test_inbound_recente_com_continuidade_lock_60(self):
        """Inbound < 30 min com sinal de continuidade → lock 60 min."""
        # Inbound há 15 minutos
        inbound_at = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()

        with patch("app.services.campaign_attribution.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"last_inbound_at": inbound_at}
            )

            with patch("app.services.campaign_attribution._buscar_ultimo_inbound_texto") as mock_buscar:
                mock_buscar.return_value = "Me liga amanhã"

                result = await _check_attribution_lock("cliente-123")

                assert result.is_locked is True
                assert result.lock_minutes == LOCK_EXTENDED_MINUTES
                assert result.lock_reason == "continuity_signal"
                assert result.pattern_matched is not None

    @pytest.mark.asyncio
    async def test_inbound_45_min_com_continuidade_ainda_lockado(self):
        """Inbound há 45 min com continuidade ainda está no lock de 60 min."""
        # Inbound há 45 minutos (fora do default 30, dentro do extended 60)
        inbound_at = (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat()

        with patch("app.services.campaign_attribution.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"last_inbound_at": inbound_at}
            )

            # Importante: como delta >= 30, o gate não busca texto!
            # Então mesmo com continuidade no texto, vai retornar no_lock
            result = await _check_attribution_lock("cliente-123")

            # Gate: delta >= 30 min → não busca texto → sem lock
            assert result.is_locked is False

    @pytest.mark.asyncio
    async def test_erro_retorna_no_lock(self):
        """Em caso de erro, retorna lock desativado (fail-open)."""
        with patch("app.services.campaign_attribution.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception(
                "DB error"
            )

            result = await _check_attribution_lock("cliente-123")

            assert result.is_locked is False
            assert result.lock_reason == "none"


class TestRegistrarCampaignTouchWithLock:
    """Testes de integração para registrar_campaign_touch com lock."""

    @pytest.mark.asyncio
    async def test_sem_lock_atualiza_last_touch(self):
        """Sem lock, deve atualizar last_touch normalmente."""
        no_lock = LockInfo(is_locked=False, lock_minutes=0, lock_reason="none")

        with patch("app.services.campaign_attribution._check_attribution_lock") as mock_lock:
            mock_lock.return_value = no_lock

            with patch("app.services.campaign_attribution.supabase") as mock_supabase:
                mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                    data={"first_touch_campaign_id": 100}
                )
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

    @pytest.mark.asyncio
    async def test_com_lock_default_nao_atualiza_last_touch(self):
        """Com lock default (30 min), NÃO deve atualizar last_touch."""
        lock_info = LockInfo(
            is_locked=True,
            lock_minutes=30,
            lock_reason="default",
            delta_minutes=15,
        )

        with patch("app.services.campaign_attribution._check_attribution_lock") as mock_lock:
            mock_lock.return_value = lock_info

            with patch("app.services.campaign_attribution.supabase") as mock_supabase:
                mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                    data={"first_touch_campaign_id": 100}
                )

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
                    assert result.lock_info.lock_reason == "default"

    @pytest.mark.asyncio
    async def test_com_lock_continuity_inclui_pattern(self):
        """Com lock por continuidade, deve incluir pattern no resultado."""
        lock_info = LockInfo(
            is_locked=True,
            lock_minutes=60,
            lock_reason="continuity_signal",
            pattern_matched="\\bme\\s+liga",
            delta_minutes=10,
        )

        with patch("app.services.campaign_attribution._check_attribution_lock") as mock_lock:
            mock_lock.return_value = lock_info

            with patch("app.services.campaign_attribution.supabase") as mock_supabase:
                mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                    data={"first_touch_campaign_id": 100}
                )

                with patch("app.services.campaign_attribution.emit_event") as mock_emit:
                    result = await registrar_campaign_touch(
                        conversation_id="conv-123",
                        campaign_id=200,
                        touch_type="campaign",
                        cliente_id="cliente-123",
                    )

                    assert result.lock_info.lock_reason == "continuity_signal"
                    assert result.lock_info.pattern_matched is not None

                    # Verificar que evento inclui campos de observabilidade
                    call_args = mock_emit.call_args
                    event = call_args[0][0]
                    assert event.event_props["lock_reason"] == "continuity_signal"
                    assert "lock_pattern_matched" in event.event_props


class TestLockConfig:
    """Testes para configuração do lock."""

    def test_lock_default_30_minutos(self):
        """Lock default deve ser 30 minutos."""
        assert LOCK_DEFAULT_MINUTES == 30

    def test_lock_extended_60_minutos(self):
        """Lock extended deve ser 60 minutos."""
        assert LOCK_EXTENDED_MINUTES == 60
