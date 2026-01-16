"""
Testes para servico de atribuicao de campanhas.

Sprint 23 E02 - First/Last Touch Attribution.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.campaign_attribution import (
    registrar_campaign_touch,
    atribuir_reply_a_campanha,
    buscar_atribuicao_conversa,
    contar_replies_por_campanha,
    AttributionResult,
    ATTRIBUTION_WINDOW_DAYS,
)


class TestRegistrarCampaignTouch:
    """Testes para registrar_campaign_touch."""

    @pytest.mark.asyncio
    async def test_primeiro_touch_seta_first_e_last(self):
        """Primeiro touch deve setar first_touch e last_touch."""
        with patch("app.services.campaign_attribution.supabase") as mock_supabase, \
             patch("app.services.campaign_attribution.emit_event") as mock_emit:

            # Simular conversa sem first_touch
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"first_touch_campaign_id": None, "first_touch_at": None}
            )
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            result = await registrar_campaign_touch(
                conversation_id="conv-123",
                campaign_id=1,
                touch_type="campaign",
                cliente_id="cliente-456",
            )

            assert result.success is True
            assert result.first_touch_set is True
            assert result.last_touch_updated is True

            # Verificar que update foi chamado com first_touch
            update_call = mock_supabase.table.return_value.update.call_args
            update_data = update_call[0][0]
            assert "first_touch_campaign_id" in update_data
            assert "last_touch_campaign_id" in update_data

    @pytest.mark.asyncio
    async def test_segundo_touch_atualiza_apenas_last(self):
        """Touch subsequente deve atualizar apenas last_touch."""
        with patch("app.services.campaign_attribution.supabase") as mock_supabase, \
             patch("app.services.campaign_attribution.emit_event") as mock_emit:

            # Simular conversa com first_touch existente
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={
                    "first_touch_campaign_id": 1,
                    "first_touch_at": "2024-01-01T00:00:00+00:00"
                }
            )
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            result = await registrar_campaign_touch(
                conversation_id="conv-123",
                campaign_id=2,  # Campanha diferente
                touch_type="reactivation",
                cliente_id="cliente-456",
            )

            assert result.success is True
            assert result.first_touch_set is False  # Nao seta first
            assert result.last_touch_updated is True

            # Verificar que update NAO inclui first_touch
            update_call = mock_supabase.table.return_value.update.call_args
            update_data = update_call[0][0]
            assert "first_touch_campaign_id" not in update_data
            assert "last_touch_campaign_id" in update_data

    @pytest.mark.asyncio
    async def test_touch_emite_evento(self):
        """Touch deve emitir evento CAMPAIGN_TOUCH_LINKED."""
        with patch("app.services.campaign_attribution.supabase") as mock_supabase, \
             patch("app.services.campaign_attribution.emit_event") as mock_emit:

            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"first_touch_campaign_id": None, "first_touch_at": None}
            )
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            await registrar_campaign_touch(
                conversation_id="conv-123",
                campaign_id=1,
                touch_type="campaign",
                cliente_id="cliente-456",
            )

            # Verificar emissao de evento
            mock_emit.assert_called_once()
            event = mock_emit.call_args[0][0]
            assert event.event_type.value == "campaign_touch_linked"
            assert event.event_props["campaign_id"] == 1

    @pytest.mark.asyncio
    async def test_conversa_nao_encontrada(self):
        """Conversa nao encontrada deve retornar erro."""
        with patch("app.services.campaign_attribution.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data=None
            )

            result = await registrar_campaign_touch(
                conversation_id="conv-inexistente",
                campaign_id=1,
                touch_type="campaign",
                cliente_id="cliente-456",
            )

            assert result.success is False
            assert "nao encontrada" in result.error


class TestAtribuirReplyACampanha:
    """Testes para atribuir_reply_a_campanha."""

    @pytest.mark.asyncio
    async def test_reply_dentro_janela_atribui(self):
        """Reply dentro da janela de 7 dias deve atribuir."""
        with patch("app.services.campaign_attribution.supabase") as mock_supabase, \
             patch("app.services.campaign_attribution.emit_event") as mock_emit:

            # Last touch ha 2 dias
            last_touch_at = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={
                    "last_touch_campaign_id": 42,
                    "last_touch_at": last_touch_at
                }
            )
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            result = await atribuir_reply_a_campanha(
                interaction_id=100,
                conversation_id="conv-123",
                cliente_id="cliente-456",
            )

            assert result.success is True
            assert result.attributed_campaign_id == 42

    @pytest.mark.asyncio
    async def test_reply_fora_janela_nao_atribui(self):
        """Reply fora da janela (>7 dias) nao deve atribuir."""
        with patch("app.services.campaign_attribution.supabase") as mock_supabase:
            # Last touch ha 10 dias (fora da janela)
            last_touch_at = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()

            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={
                    "last_touch_campaign_id": 42,
                    "last_touch_at": last_touch_at
                }
            )

            result = await atribuir_reply_a_campanha(
                interaction_id=100,
                conversation_id="conv-123",
                cliente_id="cliente-456",
            )

            assert result.success is True
            assert result.attributed_campaign_id is None  # Nao atribuido

    @pytest.mark.asyncio
    async def test_reply_sem_touch_anterior_organica(self):
        """Reply sem touch anterior e organica (nao atribuida)."""
        with patch("app.services.campaign_attribution.supabase") as mock_supabase:
            # Conversa sem last_touch
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={
                    "last_touch_campaign_id": None,
                    "last_touch_at": None
                }
            )

            result = await atribuir_reply_a_campanha(
                interaction_id=100,
                conversation_id="conv-123",
                cliente_id="cliente-456",
            )

            assert result.success is True
            assert result.attributed_campaign_id is None

    @pytest.mark.asyncio
    async def test_reply_atribuida_emite_evento(self):
        """Reply atribuida deve emitir evento CAMPAIGN_REPLY_ATTRIBUTED."""
        with patch("app.services.campaign_attribution.supabase") as mock_supabase, \
             patch("app.services.campaign_attribution.emit_event") as mock_emit:

            last_touch_at = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={
                    "last_touch_campaign_id": 42,
                    "last_touch_at": last_touch_at
                }
            )
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            await atribuir_reply_a_campanha(
                interaction_id=100,
                conversation_id="conv-123",
                cliente_id="cliente-456",
            )

            # Verificar emissao de evento
            mock_emit.assert_called_once()
            event = mock_emit.call_args[0][0]
            assert event.event_type.value == "campaign_reply_attributed"
            assert event.event_props["campaign_id"] == 42
            assert event.event_props["interaction_id"] == 100

    @pytest.mark.asyncio
    async def test_janela_atribuicao_configuravel(self):
        """Janela de atribuicao deve ser configuravel (default 7 dias)."""
        assert ATTRIBUTION_WINDOW_DAYS == 7


class TestInvarianteC2:
    """Testes para invariante C2: SENT com campaign_id atualiza last_touch."""

    @pytest.mark.asyncio
    async def test_outbound_sent_com_campaign_registra_touch(self):
        """Outbound SENT com campaign_id deve registrar touch."""
        # Este teste valida a integracao em outbound.py
        # O mock verifica que registrar_campaign_touch e chamado

        with patch("app.services.outbound.evolution") as mock_evolution, \
             patch("app.services.outbound.verificar_e_reservar", new_callable=AsyncMock) as mock_dedupe, \
             patch("app.services.outbound.check_outbound_guardrails", new_callable=AsyncMock) as mock_guardrails, \
             patch("app.services.outbound.marcar_enviado", new_callable=AsyncMock) as mock_marcar, \
             patch("app.services.outbound._verificar_dev_allowlist", return_value=(True, None)) as mock_dev, \
             patch("app.services.campaign_attribution.supabase") as mock_supabase, \
             patch("app.services.campaign_attribution.emit_event", new_callable=AsyncMock) as mock_emit:

            # Setup mocks
            mock_dedupe.return_value = (True, "dedupe-key", None)
            mock_guardrails.return_value = MagicMock(
                is_blocked=False,
                human_bypass=False,
                reason_code=None
            )
            mock_evolution.enviar_mensagem = AsyncMock(return_value={"key": {"id": "msg-123"}})
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"first_touch_campaign_id": None}
            )
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            from app.services.outbound import send_outbound_message
            from app.services.guardrails import OutboundContext, OutboundMethod, OutboundChannel, ActorType

            ctx = OutboundContext(
                cliente_id="cliente-123",
                campaign_id="42",  # Campaign ID presente
                conversation_id="conv-456",
                actor_type=ActorType.SYSTEM,
                channel=OutboundChannel.JOB,
                method=OutboundMethod.CAMPAIGN,
                is_proactive=True,
            )

            result = await send_outbound_message(
                telefone="5511999999999",
                texto="Teste",
                ctx=ctx,
            )

            # Verificar que touch foi registrado
            assert result.success is True
            mock_emit.assert_called()  # Evento de touch emitido


class TestInvarianteC3:
    """Testes para invariante C3: Inbound dentro da janela herda campaign_id."""

    @pytest.mark.asyncio
    async def test_inbound_herda_campaign_id_da_conversa(self):
        """Inbound reply herda attributed_campaign_id do last_touch."""
        with patch("app.services.campaign_attribution.supabase") as mock_supabase, \
             patch("app.services.campaign_attribution.emit_event") as mock_emit:

            last_touch_at = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()

            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={
                    "last_touch_campaign_id": 99,
                    "last_touch_at": last_touch_at
                }
            )
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            result = await atribuir_reply_a_campanha(
                interaction_id=200,
                conversation_id="conv-abc",
                cliente_id="cliente-xyz",
            )

            # Verificar que update foi chamado na interacao
            update_call = mock_supabase.table.return_value.update.call_args
            assert update_call is not None

            # Verificar resultado
            assert result.attributed_campaign_id == 99


class TestBuscarAtribuicaoConversa:
    """Testes para buscar_atribuicao_conversa."""

    @pytest.mark.asyncio
    async def test_retorna_info_completa(self):
        """Deve retornar informacoes de first e last touch."""
        with patch("app.services.campaign_attribution.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={
                    "first_touch_campaign_id": 1,
                    "first_touch_type": "campaign",
                    "first_touch_at": "2024-01-01T00:00:00+00:00",
                    "last_touch_campaign_id": 2,
                    "last_touch_type": "reactivation",
                    "last_touch_at": "2024-01-15T00:00:00+00:00",
                }
            )

            result = await buscar_atribuicao_conversa("conv-123")

            assert result["first_touch_campaign_id"] == 1
            assert result["last_touch_campaign_id"] == 2
            assert result["first_touch_type"] == "campaign"
            assert result["last_touch_type"] == "reactivation"

    @pytest.mark.asyncio
    async def test_conversa_sem_touch_retorna_vazio(self):
        """Conversa sem touch retorna dict vazio ou com nulls."""
        with patch("app.services.campaign_attribution.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data=None
            )

            result = await buscar_atribuicao_conversa("conv-inexistente")

            assert result == {}
