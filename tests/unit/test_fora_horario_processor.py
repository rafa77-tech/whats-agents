"""
Testes do ForaHorarioProcessor.

Sprint 22 - Responsividade Inteligente
"""
import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock

from app.pipeline.pre_processors import ForaHorarioProcessor
from app.pipeline.base import ProcessorContext
from app.services.fora_horario import TZ_BRASIL
from app.services.message_context_classifier import ContextType, ContextClassification


@pytest.fixture
def processor():
    return ForaHorarioProcessor()


@pytest.fixture
def context_base():
    """Contexto basico para testes."""
    return ProcessorContext(
        mensagem_raw={},
        mensagem_texto="Oi, tudo bem?",
        telefone="5511999998888",
        message_id="msg-123",
        medico={"id": "medico-123", "nome": "Dr Carlos Silva"},
        conversa={"id": "conv-123"},
        metadata={}
    )


class TestForaHorarioProcessorHorarioComercial:
    """Testes quando esta dentro do horario comercial."""

    @pytest.mark.asyncio
    @patch("app.services.fora_horario.eh_horario_comercial")
    async def test_dentro_horario_continua_pipeline(
        self, mock_eh_horario, processor, context_base
    ):
        """Dentro do horario comercial, deve continuar pipeline."""
        mock_eh_horario.return_value = True

        result = await processor.process(context_base)

        assert result.success is True
        assert result.should_continue is True
        assert result.response is None


class TestForaHorarioProcessorForaHorario:
    """Testes quando esta fora do horario comercial."""

    @pytest.mark.asyncio
    @patch("app.services.fora_horario.processar_mensagem_fora_horario")
    @patch("app.services.fora_horario.pode_responder_fora_horario")
    @patch("app.services.message_context_classifier.classificar_contexto")
    @patch("app.services.fora_horario.eh_horario_comercial")
    async def test_fora_horario_envia_ack(
        self,
        mock_eh_horario,
        mock_classificar,
        mock_pode_responder,
        mock_processar,
        processor,
        context_base
    ):
        """Fora do horario, deve enviar ACK e parar pipeline."""
        mock_eh_horario.return_value = False
        mock_classificar.return_value = ContextClassification(
            tipo=ContextType.REPLY_DIRETA,
            prioridade=1,
            confianca=0.9,
            razao="teste"
        )
        mock_pode_responder.return_value = True
        mock_processar.return_value = {
            "ack_mensagem": "Oi Dr Carlos! Recebi sua mensagem...",
            "registro_id": "reg-123",
            "template_tipo": "generico"
        }

        result = await processor.process(context_base)

        assert result.success is True
        assert result.should_continue is False
        assert result.response == "Oi Dr Carlos! Recebi sua mensagem..."
        assert result.metadata.get("fora_horario") is True
        assert result.metadata.get("ack_template") == "generico"
        assert result.metadata.get("registro_id") == "reg-123"

    @pytest.mark.asyncio
    @patch("app.services.fora_horario.processar_mensagem_fora_horario")
    @patch("app.services.fora_horario.pode_responder_fora_horario")
    @patch("app.services.message_context_classifier.classificar_contexto")
    @patch("app.services.fora_horario.eh_horario_comercial")
    async def test_ack_ceiling_atingido(
        self,
        mock_eh_horario,
        mock_classificar,
        mock_pode_responder,
        mock_processar,
        processor,
        context_base
    ):
        """Se ACK ceiling atingido, para pipeline sem enviar novo ACK."""
        mock_eh_horario.return_value = False
        mock_classificar.return_value = ContextClassification(
            tipo=ContextType.REPLY_DIRETA,
            prioridade=1,
            confianca=0.9,
            razao="teste"
        )
        mock_pode_responder.return_value = True
        mock_processar.return_value = {
            "ack_mensagem": None,  # Ceiling atingido
            "registro_id": "reg-123",
            "template_tipo": None,
            "motivo_sem_ack": "ceiling_6h"
        }

        result = await processor.process(context_base)

        assert result.success is True
        assert result.should_continue is False
        assert result.response is None  # Sem ACK
        assert result.metadata.get("fora_horario") is True
        assert result.metadata.get("ack_ceiling") is True

    @pytest.mark.asyncio
    @patch("app.services.fora_horario.pode_responder_fora_horario")
    @patch("app.services.message_context_classifier.classificar_contexto")
    @patch("app.services.fora_horario.eh_horario_comercial")
    async def test_tipo_nao_elegivel_para_ack(
        self,
        mock_eh_horario,
        mock_classificar,
        mock_pode_responder,
        processor,
        context_base
    ):
        """Tipo de contexto nao elegivel para ACK para pipeline sem resposta."""
        mock_eh_horario.return_value = False
        mock_classificar.return_value = ContextClassification(
            tipo=ContextType.CAMPANHA_FRIA,
            prioridade=5,
            confianca=0.9,
            razao="teste"
        )
        mock_pode_responder.return_value = False

        result = await processor.process(context_base)

        assert result.success is True
        assert result.should_continue is False
        assert result.response is None
        assert result.metadata.get("fora_horario") is True
        assert result.metadata.get("sem_ack") is True


class TestForaHorarioProcessorIntegracao:
    """Testes de integracao com servicos reais mockados."""

    @pytest.mark.asyncio
    @patch("app.services.fora_horario.salvar_mensagem_fora_horario")
    @patch("app.services.fora_horario.verificar_ack_recente")
    @patch("app.services.fora_horario.eh_horario_comercial")
    async def test_fluxo_completo_fora_horario(
        self,
        mock_eh_horario,
        mock_verificar_ack,
        mock_salvar,
        processor,
        context_base
    ):
        """Testa fluxo completo de mensagem fora do horario."""
        mock_eh_horario.return_value = False
        mock_verificar_ack.return_value = False  # Sem ACK recente
        mock_salvar.return_value = "reg-novo-123"

        result = await processor.process(context_base)

        assert result.success is True
        assert result.should_continue is False
        assert result.response is not None
        assert "Dr(a)" in result.response  # Nome usado no template
        assert result.metadata.get("fora_horario") is True
        assert result.metadata.get("ack_template") == "generico"

    @pytest.mark.asyncio
    @patch("app.services.fora_horario.salvar_mensagem_fora_horario")
    @patch("app.services.fora_horario.verificar_ack_recente")
    @patch("app.services.fora_horario.eh_horario_comercial")
    async def test_fluxo_com_ack_recente(
        self,
        mock_eh_horario,
        mock_verificar_ack,
        mock_salvar,
        processor,
        context_base
    ):
        """Testa fluxo quando ja tem ACK recente (ceiling)."""
        mock_eh_horario.return_value = False
        mock_verificar_ack.return_value = True  # ACK recente existe
        mock_salvar.return_value = "reg-novo-123"

        result = await processor.process(context_base)

        assert result.success is True
        assert result.should_continue is False
        assert result.response is None  # Sem ACK por causa do ceiling
        assert result.metadata.get("fora_horario") is True
        assert result.metadata.get("ack_ceiling") is True


class TestForaHorarioProcessorPrioridade:
    """Testes de prioridade do processor."""

    def test_prioridade_entre_optout_e_bot_detection(self, processor):
        """Prioridade deve estar entre OptOut (30) e BotDetection (35)."""
        assert processor.priority == 32

    def test_nome_do_processor(self, processor):
        """Nome deve ser 'fora_horario'."""
        assert processor.name == "fora_horario"
