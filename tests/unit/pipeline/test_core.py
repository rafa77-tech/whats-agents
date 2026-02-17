"""
Testes unitários para o pipeline core (MessageProcessor).

Cobre:
- Processamento de mensagem simples com processadores mockados
- Execução na ordem correta de prioridade
- Interrupção do pipeline via should_continue=False
- Graceful handling de exceções em processadores
- Propagação de contexto entre processadores
- Pipeline sem processadores
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.pipeline.processor import MessageProcessor
from app.pipeline.base import (
    ProcessorContext,
    ProcessorResult,
    PreProcessor,
    PostProcessor,
)


# =============================================================================
# Helpers: Processadores de teste
# =============================================================================


class FakePreProcessor(PreProcessor):
    """Pre-processador fake para testes."""

    def __init__(self, name: str = "fake_pre", priority: int = 100, result: ProcessorResult | None = None):
        self.name = name
        self.priority = priority
        self._result = result or ProcessorResult(success=True)
        self.called = False
        self.received_context = None

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        self.called = True
        self.received_context = context
        return self._result


class FakePostProcessor(PostProcessor):
    """Pós-processador fake para testes."""

    def __init__(self, name: str = "fake_post", priority: int = 100, result: ProcessorResult | None = None):
        self.name = name
        self.priority = priority
        self._result = result or ProcessorResult(success=True, response=None)
        self.called = False
        self.received_response = None

    async def process(self, context: ProcessorContext, response: str) -> ProcessorResult:
        self.called = True
        self.received_response = response
        return self._result


class FakeCoreProcessor:
    """Core processor fake para testes."""

    name = "fake_core"

    def __init__(self, result: ProcessorResult | None = None):
        self._result = result or ProcessorResult(success=True, response="Resposta do LLM")
        self.called = False

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        self.called = True
        return self._result


class ErrorPreProcessor(PreProcessor):
    """Pre-processador que lança exceção."""

    name = "error_pre"
    priority = 50

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        raise RuntimeError("Erro inesperado no pre-processador")


class ContextModifyingPreProcessor(PreProcessor):
    """Pre-processador que modifica o contexto via metadata."""

    def __init__(self, name: str = "modifier", priority: int = 100, key: str = "flag", value: str = "set"):
        self.name = name
        self.priority = priority
        self._key = key
        self._value = value

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        context.metadata[self._key] = self._value
        return ProcessorResult(success=True)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def pipeline():
    """Pipeline limpo com core processor mockado."""
    p = MessageProcessor()
    p.set_core_processor(FakeCoreProcessor())
    return p


@pytest.fixture
def mensagem_raw():
    """Payload mínimo de mensagem."""
    return {"key": {"remoteJid": "5511999999999@s.whatsapp.net"}, "message": {"conversation": "Oi"}}


# =============================================================================
# Testes: Processamento básico
# =============================================================================


@pytest.mark.unit
class TestPipelineBasico:
    """Testes de fluxo básico do pipeline."""

    @pytest.mark.asyncio
    async def test_processa_mensagem_simples(self, pipeline, mensagem_raw):
        """Pipeline processa mensagem com processadores mockados e retorna resposta."""
        pre = FakePreProcessor(name="parse", priority=10)
        post = FakePostProcessor(name="send", priority=20)

        pipeline.add_pre_processor(pre)
        pipeline.add_post_processor(post)

        result = await pipeline.process(mensagem_raw)

        assert result.success is True
        assert result.response == "Resposta do LLM"
        assert pre.called is True
        assert post.called is True

    @pytest.mark.asyncio
    async def test_pipeline_sem_processadores(self, mensagem_raw):
        """Pipeline sem pre/pós-processadores executa apenas o core."""
        core = FakeCoreProcessor(result=ProcessorResult(success=True, response="Só core"))
        pipeline = MessageProcessor()
        pipeline.set_core_processor(core)

        result = await pipeline.process(mensagem_raw)

        assert result.success is True
        assert result.response == "Só core"
        assert core.called is True

    @pytest.mark.asyncio
    async def test_pipeline_sem_core_processor_falha(self, mensagem_raw):
        """Pipeline sem core processor retorna erro."""
        pipeline = MessageProcessor()

        result = await pipeline.process(mensagem_raw)

        assert result.success is False
        assert "Core processor" in result.error


# =============================================================================
# Testes: Ordenação por prioridade
# =============================================================================


@pytest.mark.unit
class TestOrdemPrioridade:
    """Testes de execução na ordem correta de prioridade."""

    @pytest.mark.asyncio
    async def test_pre_processadores_executam_em_ordem_de_prioridade(self, pipeline, mensagem_raw):
        """Pre-processadores com menor prioridade rodam primeiro."""
        execution_order = []

        class OrderTracker(PreProcessor):
            def __init__(self, name, priority):
                self.name = name
                self.priority = priority

            async def process(self, context):
                execution_order.append(self.name)
                return ProcessorResult(success=True)

        # Adicionar fora de ordem
        pipeline.add_pre_processor(OrderTracker("terceiro", 30))
        pipeline.add_pre_processor(OrderTracker("primeiro", 10))
        pipeline.add_pre_processor(OrderTracker("segundo", 20))

        await pipeline.process(mensagem_raw)

        assert execution_order == ["primeiro", "segundo", "terceiro"]

    @pytest.mark.asyncio
    async def test_post_processadores_executam_em_ordem_de_prioridade(self, pipeline, mensagem_raw):
        """Pós-processadores com menor prioridade rodam primeiro."""
        execution_order = []

        class OrderTracker(PostProcessor):
            def __init__(self, name, priority):
                self.name = name
                self.priority = priority

            async def process(self, context, response):
                execution_order.append(self.name)
                return ProcessorResult(success=True, response=response)

        pipeline.add_post_processor(OrderTracker("ultimo", 40))
        pipeline.add_post_processor(OrderTracker("primeiro", 5))
        pipeline.add_post_processor(OrderTracker("meio", 20))

        await pipeline.process(mensagem_raw)

        assert execution_order == ["primeiro", "meio", "ultimo"]


# =============================================================================
# Testes: Interrupção do pipeline
# =============================================================================


@pytest.mark.unit
class TestInterrupcaoPipeline:
    """Testes de interrupção do pipeline por processadores."""

    @pytest.mark.asyncio
    async def test_pre_processador_stop_interrompe_pipeline(self, pipeline, mensagem_raw):
        """Pre-processador retornando should_continue=False interrompe o pipeline."""
        stopper = FakePreProcessor(
            name="stopper",
            priority=10,
            result=ProcessorResult(success=True, should_continue=False),
        )
        never_reached = FakePreProcessor(name="never", priority=20)

        pipeline.add_pre_processor(stopper)
        pipeline.add_pre_processor(never_reached)

        result = await pipeline.process(mensagem_raw)

        assert stopper.called is True
        assert never_reached.called is False
        assert result.success is True
        assert result.should_continue is False

    @pytest.mark.asyncio
    async def test_pre_processador_stop_com_resposta_roda_post_processors(self, pipeline, mensagem_raw):
        """Pre-processador que para com resposta ainda roda pós-processadores de envio."""
        stopper = FakePreProcessor(
            name="opt_out",
            priority=10,
            result=ProcessorResult(success=True, should_continue=False, response="Entendi, não vou mais mandar msg"),
        )
        send_post = FakePostProcessor(name="send_message", priority=20)

        pipeline.add_pre_processor(stopper)
        pipeline.add_post_processor(send_post)

        result = await pipeline.process(mensagem_raw)

        assert stopper.called is True
        assert send_post.called is True
        assert result.success is True

    @pytest.mark.asyncio
    async def test_pre_processador_falha_retorna_resultado_imediato(self, pipeline, mensagem_raw):
        """Pre-processador com success=False retorna resultado imediatamente."""
        failing = FakePreProcessor(
            name="failing",
            priority=10,
            result=ProcessorResult(success=False, error="Falha crítica"),
        )

        pipeline.add_pre_processor(failing)

        result = await pipeline.process(mensagem_raw)

        assert result.success is False
        assert result.error == "Falha crítica"


# =============================================================================
# Testes: Graceful handling de exceções
# =============================================================================


@pytest.mark.unit
class TestExcecaoGraceful:
    """Testes de tratamento graceful de exceções."""

    @pytest.mark.asyncio
    async def test_excecao_no_pipeline_retorna_erro(self, mensagem_raw):
        """Exceção no pipeline é capturada e retorna ProcessorResult com erro."""
        core = FakeCoreProcessor()
        pipeline = MessageProcessor()
        pipeline.set_core_processor(core)

        # Pre-processor que lança exceção
        pipeline.add_pre_processor(ErrorPreProcessor())

        result = await pipeline.process(mensagem_raw)

        # A exceção no pre-processor propaga para o try/except geral
        assert result.success is False
        assert "Erro inesperado" in result.error

    @pytest.mark.asyncio
    async def test_post_processador_falha_nao_para_pipeline(self, pipeline, mensagem_raw):
        """Pós-processador falhando não impede outros pós-processadores."""
        failing_post = FakePostProcessor(
            name="failing",
            priority=10,
            result=ProcessorResult(success=False, error="Falha no pós"),
        )
        healthy_post = FakePostProcessor(
            name="healthy",
            priority=20,
            result=ProcessorResult(success=True, response="Resposta do LLM"),
        )

        pipeline.add_post_processor(failing_post)
        pipeline.add_post_processor(healthy_post)

        result = await pipeline.process(mensagem_raw)

        assert failing_post.called is True
        assert healthy_post.called is True
        assert result.success is True


# =============================================================================
# Testes: Propagação de contexto
# =============================================================================


@pytest.mark.unit
class TestPropagacaoContexto:
    """Testes de propagação de contexto entre processadores."""

    @pytest.mark.asyncio
    async def test_metadata_propagado_entre_pre_processadores(self, pipeline, mensagem_raw):
        """Metadata adicionado por um pre-processador é visível ao próximo."""
        setter = ContextModifyingPreProcessor(
            name="setter", priority=10, key="telefone_parsed", value="5511999"
        )
        reader = FakePreProcessor(name="reader", priority=20)

        pipeline.add_pre_processor(setter)
        pipeline.add_pre_processor(reader)

        await pipeline.process(mensagem_raw)

        assert reader.received_context is not None
        assert reader.received_context.metadata["telefone_parsed"] == "5511999"

    @pytest.mark.asyncio
    async def test_post_processador_recebe_resposta_do_core(self, pipeline, mensagem_raw):
        """Pós-processador recebe a resposta gerada pelo core processor."""
        post = FakePostProcessor(name="validator", priority=5)

        pipeline.add_post_processor(post)

        await pipeline.process(mensagem_raw)

        assert post.received_response == "Resposta do LLM"

    @pytest.mark.asyncio
    async def test_post_processador_modifica_resposta_para_proximo(self, pipeline, mensagem_raw):
        """Pós-processador que retorna resposta modificada atualiza para o próximo."""
        modifier = FakePostProcessor(
            name="modifier",
            priority=10,
            result=ProcessorResult(success=True, response="Resposta modificada"),
        )
        final = FakePostProcessor(name="final", priority=20)

        pipeline.add_post_processor(modifier)
        pipeline.add_post_processor(final)

        await pipeline.process(mensagem_raw)

        assert final.received_response == "Resposta modificada"

    @pytest.mark.asyncio
    async def test_core_result_vazio_propaga_string_vazia(self, mensagem_raw):
        """Core processor sem resposta propaga string vazia para pós-processadores."""
        core = FakeCoreProcessor(result=ProcessorResult(success=True, response=None))
        pipeline = MessageProcessor()
        pipeline.set_core_processor(core)

        post = FakePostProcessor(name="post", priority=10)
        pipeline.add_post_processor(post)

        await pipeline.process(mensagem_raw)

        assert post.received_response == ""
