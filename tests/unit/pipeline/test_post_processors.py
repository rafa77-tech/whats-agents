"""
Testes unitários para pós-processadores do pipeline.

Cobre os caminhos-chave:
- ValidateOutputProcessor: validação e bloqueio de respostas
- TimingProcessor: delay humanizado
- SendMessageProcessor: envio via Evolution API e tratamento de falhas
- MetricsProcessor: registro de métricas
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from typing import Optional

from app.pipeline.base import ProcessorContext, ProcessorResult
from app.pipeline.post_processors import (
    ValidateOutputProcessor,
    TimingProcessor,
    SendMessageProcessor,
    SaveInteractionProcessor,
    MetricsProcessor,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def context():
    """Contexto básico para testes de pós-processadores."""
    ctx = ProcessorContext(
        mensagem_raw={"key": {"remoteJid": "5511999999999@s.whatsapp.net"}},
        mensagem_texto="Oi, tudo bem?",
        telefone="5511999999999",
        message_id="msg-123",
        medico={"id": "medico-abc", "primeiro_nome": "Carlos"},
        conversa={"id": "conv-xyz", "controlled_by": "ai"},
    )
    ctx.metadata["tempo_inicio"] = time.time()
    return ctx


# =============================================================================
# Testes: ValidateOutputProcessor
# =============================================================================


@pytest.mark.unit
class TestValidateOutputProcessor:
    """Testes para validação de output da Julia."""

    @pytest.fixture
    def processor(self):
        return ValidateOutputProcessor()

    @pytest.mark.asyncio
    async def test_resposta_valida_passa_sem_alteracao(self, processor, context):
        """Resposta válida passa pelo validador sem modificação."""
        with patch(
            "app.pipeline.post_processors.validar_e_corrigir",
            new_callable=AsyncMock,
            return_value=("Oi Dr Carlos! Tudo certo?", False),
        ):
            result = await processor.process(context, "Oi Dr Carlos! Tudo certo?")

        assert result.success is True
        assert result.response == "Oi Dr Carlos! Tudo certo?"

    @pytest.mark.asyncio
    async def test_resposta_corrigida_retorna_versao_corrigida(self, processor, context):
        """Resposta com problemas menores é corrigida e retornada."""
        with patch(
            "app.pipeline.post_processors.validar_e_corrigir",
            new_callable=AsyncMock,
            return_value=("Oi Dr Carlos, tudo bem?", True),
        ):
            result = await processor.process(context, "Resposta original com bullet points")

        assert result.success is True
        assert result.response == "Oi Dr Carlos, tudo bem?"
        assert context.metadata.get("resposta_corrigida") is True

    @pytest.mark.asyncio
    async def test_resposta_bloqueada_retorna_vazio(self, processor, context):
        """Resposta que revelaria IA é bloqueada (retorna string vazia)."""
        with patch(
            "app.pipeline.post_processors.validar_e_corrigir",
            new_callable=AsyncMock,
            return_value=(None, True),  # None = bloqueada
        ):
            result = await processor.process(context, "Sou uma IA assistente virtual")

        assert result.success is True
        assert result.response == ""
        assert result.metadata.get("blocked") is True
        assert context.metadata.get("resposta_bloqueada") is True

    @pytest.mark.asyncio
    async def test_resposta_vazia_passa_direto(self, processor, context):
        """Resposta vazia não é processada pelo validador."""
        result = await processor.process(context, "")

        assert result.success is True
        assert result.response == ""


# =============================================================================
# Testes: TimingProcessor (delay humanizado)
# =============================================================================


@pytest.mark.unit
class TestTimingProcessor:
    """Testes para delay humanizado antes de enviar."""

    @pytest.fixture
    def processor(self):
        return TimingProcessor()

    @pytest.mark.asyncio
    async def test_resposta_vazia_nao_aplica_delay(self, processor, context):
        """Resposta vazia não aplica delay (não vai enviar nada)."""
        result = await processor.process(context, "")

        assert result.success is True
        assert result.response == ""

    @pytest.mark.asyncio
    async def test_delay_calculado_via_delay_engine(self, processor, context):
        """Delay é calculado via delay_engine e aguardado."""
        with patch(
            "app.pipeline.post_processors.get_delay_seconds",
            new_callable=AsyncMock,
            return_value=0.0,  # Sem delay para teste rápido
        ) as mock_delay:
            with patch(
                "app.pipeline.post_processors.mostrar_digitando",
                new_callable=AsyncMock,
            ):
                result = await processor.process(context, "Oi!")

        assert result.success is True
        assert result.response == "Oi!"
        mock_delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_erro_mostrar_digitando_nao_para_pipeline(self, processor, context):
        """Erro ao mostrar 'digitando' não interrompe o pipeline."""
        with patch(
            "app.pipeline.post_processors.get_delay_seconds",
            new_callable=AsyncMock,
            return_value=0.1,  # Delay mínimo para entrar no elif
        ):
            with patch(
                "app.pipeline.post_processors.mostrar_digitando",
                new_callable=AsyncMock,
                side_effect=Exception("Erro Evolution API"),
            ):
                result = await processor.process(context, "Oi!")

        assert result.success is True
        assert result.response == "Oi!"


# =============================================================================
# Testes: SendMessageProcessor
# =============================================================================


@pytest.mark.unit
class TestSendMessageProcessor:
    """Testes para envio de mensagem via WhatsApp."""

    @pytest.fixture
    def processor(self):
        return SendMessageProcessor()

    @pytest.mark.asyncio
    async def test_envia_resposta_via_evolution_api(self, processor, context):
        """Mensagem é enviada com sucesso via enviar_resposta."""
        mock_resultado = MagicMock(
            blocked=False,
            success=True,
            evolution_response={"key": {"id": "sent-msg-456"}},
            chip_id="chip-1",
        )

        with (
            patch(
                "app.pipeline.post_processors.salvar_interacao",
                new_callable=AsyncMock,
                return_value={"id": 100},
            ),
            patch(
                "app.pipeline.post_processors.criar_contexto_reply",
                return_value=MagicMock(),
            ),
            patch(
                "app.pipeline.post_processors.enviar_resposta",
                new_callable=AsyncMock,
                return_value=mock_resultado,
            ) as mock_enviar,
        ):
            result = await processor.process(context, "Oi Dr Carlos!")

        assert result.success is True
        mock_enviar.assert_called_once()
        assert context.metadata.get("message_sent") is True
        assert context.metadata.get("sent_message_id") == "sent-msg-456"

    @pytest.mark.asyncio
    async def test_mensagem_bloqueada_por_guardrail(self, processor, context):
        """Mensagem bloqueada por guardrail retorna erro."""
        mock_resultado = MagicMock(
            blocked=True,
            block_reason="rate_limit_exceeded",
            success=False,
        )

        with (
            patch(
                "app.pipeline.post_processors.salvar_interacao",
                new_callable=AsyncMock,
                return_value={"id": 100},
            ),
            patch(
                "app.pipeline.post_processors.criar_contexto_reply",
                return_value=MagicMock(),
            ),
            patch(
                "app.pipeline.post_processors.enviar_resposta",
                new_callable=AsyncMock,
                return_value=mock_resultado,
            ),
        ):
            result = await processor.process(context, "Oi!")

        assert result.success is False
        assert "Guardrail" in result.error
        assert context.metadata.get("message_sent") is None

    @pytest.mark.asyncio
    async def test_falha_envio_retorna_erro(self, processor, context):
        """Falha no envio retorna ProcessorResult com success=False."""
        mock_resultado = MagicMock(
            blocked=False,
            success=False,
            error="Connection timeout",
        )

        with (
            patch(
                "app.pipeline.post_processors.salvar_interacao",
                new_callable=AsyncMock,
                return_value={"id": 100},
            ),
            patch(
                "app.pipeline.post_processors.criar_contexto_reply",
                return_value=MagicMock(),
            ),
            patch(
                "app.pipeline.post_processors.enviar_resposta",
                new_callable=AsyncMock,
                return_value=mock_resultado,
            ),
        ):
            result = await processor.process(context, "Oi!")

        assert result.success is False
        assert "Connection timeout" in result.error

    @pytest.mark.asyncio
    async def test_resposta_vazia_nao_envia(self, processor, context):
        """Resposta vazia não tenta enviar mensagem."""
        result = await processor.process(context, "")

        assert result.success is True
        assert context.metadata.get("message_sent") is None

    @pytest.mark.asyncio
    async def test_emite_evento_doctor_outbound(self, processor, context):
        """Após envio, emite evento doctor_outbound se no rollout."""
        mock_resultado = MagicMock(
            blocked=False,
            success=True,
            evolution_response={"key": {"id": "msg-1"}},
            chip_id=None,
        )

        with (
            patch(
                "app.pipeline.post_processors.salvar_interacao",
                new_callable=AsyncMock,
                return_value={"id": 100},
            ),
            patch(
                "app.pipeline.post_processors.criar_contexto_reply",
                return_value=MagicMock(),
            ),
            patch(
                "app.pipeline.post_processors.enviar_resposta",
                new_callable=AsyncMock,
                return_value=mock_resultado,
            ),
            patch(
                "app.services.business_events.should_emit_event",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "app.services.business_events.emit_event",
                new_callable=AsyncMock,
            ),
            patch(
                "app.pipeline.post_processors.safe_create_task",
            ) as mock_task,
        ):
            await processor.process(context, "Oi Dr Carlos!")

        mock_task.assert_called_once()


# =============================================================================
# Testes: MetricsProcessor
# =============================================================================


@pytest.mark.unit
class TestMetricsProcessor:
    """Testes para registro de métricas."""

    @pytest.fixture
    def processor(self):
        return MetricsProcessor()

    @pytest.mark.asyncio
    async def test_registra_metricas_com_resposta(self, processor, context):
        """Registra métricas do médico e da Julia quando há resposta."""
        with patch(
            "app.pipeline.post_processors.metricas_service"
        ) as mock_metricas:
            mock_metricas.registrar_mensagem = AsyncMock()

            result = await processor.process(context, "Oi Dr Carlos!")

        assert result.success is True
        assert mock_metricas.registrar_mensagem.call_count == 2  # medico + julia

    @pytest.mark.asyncio
    async def test_registra_apenas_medico_sem_resposta(self, processor, context):
        """Sem resposta, registra apenas mensagem do médico."""
        with patch(
            "app.pipeline.post_processors.metricas_service"
        ) as mock_metricas:
            mock_metricas.registrar_mensagem = AsyncMock()

            result = await processor.process(context, "")

        assert result.success is True
        assert mock_metricas.registrar_mensagem.call_count == 1

    @pytest.mark.asyncio
    async def test_erro_metricas_nao_para_pipeline(self, processor, context):
        """Erro ao registrar métricas não interrompe o pipeline."""
        with patch(
            "app.pipeline.post_processors.metricas_service"
        ) as mock_metricas:
            mock_metricas.registrar_mensagem = AsyncMock(side_effect=Exception("DB error"))

            result = await processor.process(context, "Oi!")

        assert result.success is True
