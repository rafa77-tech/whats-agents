"""
Testes para os processadores de handoff no pipeline.

Cobre:
- HandoffTriggerProcessor: deteccao de triggers de handoff
- HandoffTriggerProcessor: mensagem sem trigger passa normalmente
- HandoffTriggerProcessor: mensagem vazia passa normalmente
- HandoffKeywordProcessor: deteccao de keywords de confirmacao
- HandoffKeywordProcessor: negacao detectada corretamente
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.pipeline.base import ProcessorContext, ProcessorResult


# ---- Fixtures ----


@pytest.fixture
def make_context():
    """Factory de ProcessorContext para testes."""

    def _make(
        mensagem_texto="",
        telefone="5511999990000",
        conversa_id="conv-123",
        medico_id="med-456",
    ):
        return ProcessorContext(
            mensagem_raw={"key": "test"},
            mensagem_texto=mensagem_texto,
            telefone=telefone,
            message_id="msg-001",
            tipo_mensagem="texto",
            medico={"id": medico_id, "primeiro_nome": "Carlos"},
            conversa={"id": conversa_id, "controlled_by": "ai"},
            metadata={},
        )

    return _make


# ---- Testes de HandoffTriggerProcessor ----


@pytest.mark.unit
@pytest.mark.asyncio
async def test_trigger_pedido_humano(make_context):
    """Detecta pedido explicito de falar com humano e inicia handoff."""
    from app.pipeline.processors.handoff import HandoffTriggerProcessor

    processor = HandoffTriggerProcessor()
    context = make_context(mensagem_texto="Quero falar com uma pessoa de verdade")

    with patch(
        "app.pipeline.processors.handoff.detectar_trigger_handoff"
    ) as mock_detect, patch(
        "app.services.handoff.iniciar_handoff", new_callable=AsyncMock
    ) as mock_handoff:
        mock_detect.return_value = {
            "trigger": True,
            "motivo": "Medico pediu para falar com humano",
            "tipo": "pedido_humano",
        }
        mock_handoff.return_value = {"id": "hoff-123"}

        result = await processor.process(context)

    assert result.success is True
    assert result.should_continue is False
    assert result.metadata["handoff_trigger"] == "pedido_humano"
    mock_handoff.assert_called_once_with(
        conversa_id="conv-123",
        cliente_id="med-456",
        motivo="Medico pediu para falar com humano",
        trigger_type="pedido_humano",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_trigger_sentimento_negativo(make_context):
    """Detecta sentimento negativo forte e inicia handoff."""
    from app.pipeline.processors.handoff import HandoffTriggerProcessor

    processor = HandoffTriggerProcessor()
    context = make_context(mensagem_texto="Isso eh um absurdo! Ridiculo!")

    with patch(
        "app.pipeline.processors.handoff.detectar_trigger_handoff"
    ) as mock_detect, patch(
        "app.services.handoff.iniciar_handoff", new_callable=AsyncMock
    ) as mock_handoff:
        mock_detect.return_value = {
            "trigger": True,
            "motivo": "Sentimento muito negativo detectado",
            "tipo": "sentimento_negativo",
        }
        mock_handoff.return_value = {"id": "hoff-456"}

        result = await processor.process(context)

    assert result.success is True
    assert result.should_continue is False
    assert result.metadata["handoff_trigger"] == "sentimento_negativo"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_trigger_juridico(make_context):
    """Detecta situacao juridica e inicia handoff."""
    from app.pipeline.processors.handoff import HandoffTriggerProcessor

    processor = HandoffTriggerProcessor()
    context = make_context(mensagem_texto="Meu advogado vai entrar com processo")

    with patch(
        "app.pipeline.processors.handoff.detectar_trigger_handoff"
    ) as mock_detect, patch(
        "app.services.handoff.iniciar_handoff", new_callable=AsyncMock
    ) as mock_handoff:
        mock_detect.return_value = {
            "trigger": True,
            "motivo": "Situacao juridica/formal detectada",
            "tipo": "juridico",
        }
        mock_handoff.return_value = {"id": "hoff-789"}

        result = await processor.process(context)

    assert result.success is True
    assert result.should_continue is False
    assert result.metadata["handoff_trigger"] == "juridico"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sem_trigger_permite_continuacao(make_context):
    """Mensagem normal sem trigger permite pipeline continuar."""
    from app.pipeline.processors.handoff import HandoffTriggerProcessor

    processor = HandoffTriggerProcessor()
    context = make_context(mensagem_texto="Oi, tudo bem? Tem vagas?")

    with patch(
        "app.pipeline.processors.handoff.detectar_trigger_handoff"
    ) as mock_detect:
        mock_detect.return_value = None

        result = await processor.process(context)

    assert result.success is True
    assert result.should_continue is True
    assert "handoff_trigger" not in result.metadata


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mensagem_vazia_permite_continuacao(make_context):
    """Mensagem vazia passa sem acionar deteccao."""
    from app.pipeline.processors.handoff import HandoffTriggerProcessor

    processor = HandoffTriggerProcessor()
    context = make_context(mensagem_texto="")

    with patch(
        "app.pipeline.processors.handoff.detectar_trigger_handoff"
    ) as mock_detect:
        result = await processor.process(context)

    assert result.success is True
    assert result.should_continue is True
    # Detector nem deve ser chamado para mensagem vazia
    mock_detect.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mensagem_none_permite_continuacao():
    """Mensagem None passa sem acionar deteccao."""
    from app.pipeline.processors.handoff import HandoffTriggerProcessor

    processor = HandoffTriggerProcessor()
    context = ProcessorContext(
        mensagem_raw={"key": "test"},
        mensagem_texto=None,
        telefone="5511999990000",
        message_id="msg-001",
        medico={"id": "med-456"},
        conversa={"id": "conv-123"},
    )

    with patch(
        "app.pipeline.processors.handoff.detectar_trigger_handoff"
    ) as mock_detect:
        result = await processor.process(context)

    assert result.success is True
    assert result.should_continue is True
    mock_detect.assert_not_called()


# ---- Testes de HandoffKeywordProcessor ----


@pytest.mark.unit
@pytest.mark.asyncio
async def test_keyword_confirmado_com_handoff_pendente(make_context):
    """Keyword 'confirmado' processa handoff e para pipeline."""
    from app.pipeline.processors.handoff import HandoffKeywordProcessor

    processor = HandoffKeywordProcessor()
    context = make_context(mensagem_texto="Confirmado!")

    handoff_pendente = {"id": "hoff-ext-1", "status": "pending"}

    with (
        patch(
            "app.services.external_handoff.repository.buscar_handoff_pendente_por_telefone",
            new_callable=AsyncMock,
        ) as mock_buscar,
        patch(
            "app.services.external_handoff.confirmacao.processar_confirmacao",
            new_callable=AsyncMock,
        ) as mock_confirmar,
        patch(
            "app.services.business_events.emit_event",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.templates.get_template",
            new_callable=AsyncMock,
        ) as mock_template,
    ):
        mock_buscar.return_value = handoff_pendente
        mock_template.return_value = None  # Usa fallback

        result = await processor.process(context)

    assert result.success is True
    assert result.should_continue is False
    assert result.metadata["handoff_keyword"] is True
    assert result.metadata["action"] == "confirmed"
    mock_confirmar.assert_called_once_with(
        handoff=handoff_pendente,
        action="confirmed",
        confirmed_by="keyword",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_keyword_nao_fechou_com_handoff_pendente(make_context):
    """Keyword 'nao fechou' detecta negacao corretamente."""
    from app.pipeline.processors.handoff import HandoffKeywordProcessor

    processor = HandoffKeywordProcessor()
    context = make_context(mensagem_texto="nao fechou")

    handoff_pendente = {"id": "hoff-ext-2", "status": "pending"}

    with (
        patch(
            "app.services.external_handoff.repository.buscar_handoff_pendente_por_telefone",
            new_callable=AsyncMock,
        ) as mock_buscar,
        patch(
            "app.services.external_handoff.confirmacao.processar_confirmacao",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.business_events.emit_event",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.templates.get_template",
            new_callable=AsyncMock,
        ) as mock_template,
    ):
        mock_buscar.return_value = handoff_pendente
        mock_template.return_value = None

        result = await processor.process(context)

    assert result.success is True
    assert result.should_continue is False
    assert result.metadata["action"] == "not_confirmed"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_keyword_sem_handoff_pendente_permite_continuacao(make_context):
    """Sem handoff pendente, mensagem passa normalmente."""
    from app.pipeline.processors.handoff import HandoffKeywordProcessor

    processor = HandoffKeywordProcessor()
    context = make_context(mensagem_texto="Confirmado!")

    with patch(
        "app.services.external_handoff.repository.buscar_handoff_pendente_por_telefone",
        new_callable=AsyncMock,
    ) as mock_buscar:
        mock_buscar.return_value = None

        result = await processor.process(context)

    assert result.success is True
    assert result.should_continue is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_keyword_mensagem_sem_keyword_permite_continuacao(make_context):
    """Mensagem sem keyword reconhecida permite pipeline continuar."""
    from app.pipeline.processors.handoff import HandoffKeywordProcessor

    processor = HandoffKeywordProcessor()
    context = make_context(mensagem_texto="Oi, tudo bem?")

    handoff_pendente = {"id": "hoff-ext-3", "status": "pending"}

    with patch(
        "app.services.external_handoff.repository.buscar_handoff_pendente_por_telefone",
        new_callable=AsyncMock,
    ) as mock_buscar:
        mock_buscar.return_value = handoff_pendente

        result = await processor.process(context)

    assert result.success is True
    assert result.should_continue is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_keyword_mensagem_vazia_permite_continuacao(make_context):
    """Mensagem vazia passa sem processar keywords."""
    from app.pipeline.processors.handoff import HandoffKeywordProcessor

    processor = HandoffKeywordProcessor()
    context = make_context(mensagem_texto="")

    result = await processor.process(context)

    assert result.success is True
    assert result.should_continue is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_keyword_erro_processamento_permite_continuacao(make_context):
    """Erro ao processar keyword permite Julia responder normalmente."""
    from app.pipeline.processors.handoff import HandoffKeywordProcessor

    processor = HandoffKeywordProcessor()
    context = make_context(mensagem_texto="Confirmado!")

    handoff_pendente = {"id": "hoff-ext-4", "status": "pending"}

    with (
        patch(
            "app.services.external_handoff.repository.buscar_handoff_pendente_por_telefone",
            new_callable=AsyncMock,
        ) as mock_buscar,
        patch(
            "app.services.external_handoff.confirmacao.processar_confirmacao",
            new_callable=AsyncMock,
        ) as mock_confirmar,
    ):
        mock_buscar.return_value = handoff_pendente
        mock_confirmar.side_effect = Exception("Erro inesperado")

        result = await processor.process(context)

    assert result.success is True
    assert result.should_continue is True  # Degrada graciosamente


# ---- Testes de _detectar_keyword ----


@pytest.mark.unit
def test_detectar_keyword_confirmado():
    """Detecta variantes de confirmacao."""
    from app.pipeline.processors.handoff import HandoffKeywordProcessor

    processor = HandoffKeywordProcessor()

    assert processor._detectar_keyword("confirmado") == "confirmed"
    assert processor._detectar_keyword("fechou") == "confirmed"
    assert processor._detectar_keyword("ok, fechou") == "confirmed"
    assert processor._detectar_keyword("tudo certo") == "confirmed"
    assert processor._detectar_keyword("pode confirmar") == "confirmed"
    assert processor._detectar_keyword("fechamos") == "confirmed"


@pytest.mark.unit
def test_detectar_keyword_nao_confirmado():
    """Detecta variantes de negacao (prioridade sobre confirmacao)."""
    from app.pipeline.processors.handoff import HandoffKeywordProcessor

    processor = HandoffKeywordProcessor()

    assert processor._detectar_keyword("nao fechou") == "not_confirmed"
    assert processor._detectar_keyword("desistiu") == "not_confirmed"
    assert processor._detectar_keyword("cancelou") == "not_confirmed"
    assert processor._detectar_keyword("nao vai dar") == "not_confirmed"
    assert processor._detectar_keyword("perdeu") == "not_confirmed"
    assert processor._detectar_keyword("nao confirmou") == "not_confirmed"
    assert processor._detectar_keyword("nao rolou") == "not_confirmed"


@pytest.mark.unit
def test_detectar_keyword_nenhuma():
    """Retorna None para mensagens sem keyword."""
    from app.pipeline.processors.handoff import HandoffKeywordProcessor

    processor = HandoffKeywordProcessor()

    assert processor._detectar_keyword("oi tudo bem") is None
    assert processor._detectar_keyword("tenho interesse na vaga") is None
    assert processor._detectar_keyword("qual o valor?") is None


# ---- Testes de propriedades do processador ----


@pytest.mark.unit
def test_handoff_trigger_processor_propriedades():
    """Verifica nome e prioridade do processador."""
    from app.pipeline.processors.handoff import HandoffTriggerProcessor

    processor = HandoffTriggerProcessor()
    assert processor.name == "handoff_trigger"
    assert processor.priority == 50


@pytest.mark.unit
def test_handoff_keyword_processor_propriedades():
    """Verifica nome e prioridade do processador."""
    from app.pipeline.processors.handoff import HandoffKeywordProcessor

    processor = HandoffKeywordProcessor()
    assert processor.name == "handoff_keyword"
    assert processor.priority == 55
