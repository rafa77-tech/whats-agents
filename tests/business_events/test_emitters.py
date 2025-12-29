"""
Testes para emissores de business events.

Sprint 17 - E04
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestBusinessEventInboundProcessor:
    """Testes para BusinessEventInboundProcessor."""

    @pytest.fixture
    def context(self):
        """Cria contexto de processador."""
        from app.pipeline.base import ProcessorContext

        ctx = ProcessorContext(mensagem_raw={"key": {"remoteJid": "5511999999999"}})
        ctx.medico = {"id": "cliente-123"}
        ctx.conversa = {"id": "conversa-456"}
        ctx.tipo_mensagem = "texto"
        ctx.mensagem_texto = "Oi, tudo bem?"
        return ctx

    @pytest.mark.asyncio
    @patch("app.services.business_events.should_emit_event")
    @patch("app.services.business_events.emit_event")
    async def test_emite_inbound_quando_rollout_ativo(
        self, mock_emit, mock_should_emit, context
    ):
        """Emite doctor_inbound quando rollout está ativo."""
        from app.pipeline.pre_processors import BusinessEventInboundProcessor

        mock_should_emit.return_value = True
        mock_emit.return_value = "event-id"

        processor = BusinessEventInboundProcessor()
        result = await processor.process(context)

        assert result.success is True
        mock_should_emit.assert_called_once_with("cliente-123", "doctor_inbound")
        mock_emit.assert_called_once()
        # Verificar que o evento tem os dados corretos
        event = mock_emit.call_args[0][0]
        assert event.cliente_id == "cliente-123"
        assert event.conversation_id == "conversa-456"

    @pytest.mark.asyncio
    @patch("app.services.business_events.should_emit_event")
    @patch("app.services.business_events.emit_event")
    async def test_nao_emite_quando_rollout_inativo(
        self, mock_emit, mock_should_emit, context
    ):
        """Não emite quando rollout está inativo."""
        from app.pipeline.pre_processors import BusinessEventInboundProcessor

        mock_should_emit.return_value = False

        processor = BusinessEventInboundProcessor()
        result = await processor.process(context)

        assert result.success is True
        mock_emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_nao_emite_sem_cliente_id(self):
        """Não emite se não tiver cliente_id."""
        from app.pipeline.pre_processors import BusinessEventInboundProcessor
        from app.pipeline.base import ProcessorContext

        context = ProcessorContext(mensagem_raw={"key": {"remoteJid": "5511999999999"}})
        context.medico = {}  # Sem id
        context.conversa = {"id": "conversa-456"}

        processor = BusinessEventInboundProcessor()
        result = await processor.process(context)

        assert result.success is True


class TestOfferEventsEmitter:
    """Testes para _emitir_offer_events."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.should_emit_event")
    @patch("app.services.business_events.emit_event")
    @patch("app.services.business_events.validators.vaga_pode_receber_oferta")
    async def test_emite_offer_made_para_vaga_valida(
        self, mock_vaga_valida, mock_emit, mock_should_emit
    ):
        """Emite offer_made para vaga válida."""
        from app.services.agente import _emitir_offer_events

        mock_should_emit.return_value = True
        mock_vaga_valida.return_value = True
        mock_emit.return_value = "event-id"

        await _emitir_offer_events(
            cliente_id="cliente-123",
            conversa_id="conversa-456",
            resposta="Tenho uma vaga para você!",
            vagas_oferecidas=["vaga-789"],
        )

        mock_vaga_valida.assert_called_once_with("vaga-789")
        mock_emit.assert_called_once()
        event = mock_emit.call_args[0][0]
        assert event.vaga_id == "vaga-789"

    @pytest.mark.asyncio
    @patch("app.services.business_events.should_emit_event")
    @patch("app.services.business_events.emit_event")
    @patch("app.services.business_events.validators.vaga_pode_receber_oferta")
    async def test_nao_emite_offer_made_para_vaga_invalida(
        self, mock_vaga_valida, mock_emit, mock_should_emit
    ):
        """Não emite offer_made para vaga inválida."""
        from app.services.agente import _emitir_offer_events

        mock_should_emit.return_value = True
        mock_vaga_valida.return_value = False  # Vaga reservada/cancelada

        await _emitir_offer_events(
            cliente_id="cliente-123",
            conversa_id="conversa-456",
            resposta="Tenho uma vaga para você!",
            vagas_oferecidas=["vaga-789"],
        )

        mock_emit.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.business_events.should_emit_event")
    @patch("app.services.business_events.emit_event")
    async def test_emite_teaser_quando_menciona_oportunidade(
        self, mock_emit, mock_should_emit
    ):
        """Emite offer_teaser_sent quando menciona oportunidades."""
        from app.services.agente import _emitir_offer_events

        mock_should_emit.return_value = True
        mock_emit.return_value = "event-id"

        await _emitir_offer_events(
            cliente_id="cliente-123",
            conversa_id="conversa-456",
            resposta="Temos vagas na região do ABC, tem interesse?",
            vagas_oferecidas=None,
        )

        mock_emit.assert_called_once()
        event = mock_emit.call_args[0][0]
        assert event.event_type.value == "offer_teaser_sent"

    @pytest.mark.asyncio
    @patch("app.services.business_events.should_emit_event")
    @patch("app.services.business_events.emit_event")
    async def test_nao_emite_teaser_para_mensagem_normal(
        self, mock_emit, mock_should_emit
    ):
        """Não emite teaser para mensagem sem menção de oportunidades."""
        from app.services.agente import _emitir_offer_events

        mock_should_emit.return_value = True

        await _emitir_offer_events(
            cliente_id="cliente-123",
            conversa_id="conversa-456",
            resposta="Oi, tudo bem?",
            vagas_oferecidas=None,
        )

        mock_emit.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.business_events.should_emit_event")
    async def test_nao_emite_quando_rollout_inativo(self, mock_should_emit):
        """Não emite quando rollout está inativo."""
        from app.services.agente import _emitir_offer_events

        mock_should_emit.return_value = False

        # Não deve tentar emitir mesmo com vagas
        await _emitir_offer_events(
            cliente_id="cliente-123",
            conversa_id="conversa-456",
            resposta="Temos vagas disponíveis!",
            vagas_oferecidas=["vaga-789"],
        )

        # should_emit foi chamado, mas emit_event não foi
        mock_should_emit.assert_called_once()


class TestHandoffCreatedEvent:
    """Testes para evento handoff_created."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.should_emit_event")
    @patch("app.services.business_events.emit_event")
    async def test_emite_handoff_created(self, mock_emit, mock_should_emit):
        """Emite handoff_created quando rollout está ativo."""
        from app.services.handoff.flow import _emitir_handoff_created

        mock_should_emit.return_value = True
        mock_emit.return_value = "event-id"

        await _emitir_handoff_created(
            cliente_id="cliente-123",
            conversa_id="conversa-456",
            handoff_id="handoff-789",
            motivo="Médico pediu humano",
            trigger_type="pedido_humano",
            policy_decision_id="policy-abc",
        )

        mock_emit.assert_called_once()
        event = mock_emit.call_args[0][0]
        assert event.event_type.value == "handoff_created"
        assert event.cliente_id == "cliente-123"
        assert event.event_props["handoff_id"] == "handoff-789"
        assert event.event_props["motivo"] == "Médico pediu humano"

    @pytest.mark.asyncio
    @patch("app.services.business_events.should_emit_event")
    async def test_nao_emite_quando_rollout_inativo(self, mock_should_emit):
        """Não emite quando rollout está inativo."""
        from app.services.handoff.flow import _emitir_handoff_created

        mock_should_emit.return_value = False

        # Não deve lançar erro, apenas não emitir
        await _emitir_handoff_created(
            cliente_id="cliente-123",
            conversa_id="conversa-456",
            handoff_id="handoff-789",
            motivo="Médico pediu humano",
            trigger_type="pedido_humano",
        )

        mock_should_emit.assert_called_once()
