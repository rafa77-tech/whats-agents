"""
Testes unitários para o HumanControlProcessor.

Cobre:
- Conversa sob controle humano: bloqueia Julia
- Conversa sob controle da Julia: permite processamento
- Transição de controle humano para Julia
- Sincronização com Chatwoot quando sob controle humano
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.pipeline.base import ProcessorContext, ProcessorResult
from app.pipeline.processors.human_control import HumanControlProcessor


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def processor():
    """Instância do HumanControlProcessor."""
    return HumanControlProcessor()


@pytest.fixture
def context_ai():
    """Contexto com conversa controlada pela Julia (AI)."""
    return ProcessorContext(
        mensagem_raw={"key": {"remoteJid": "5511999999999@s.whatsapp.net"}},
        mensagem_texto="Oi, tudo bem?",
        telefone="5511999999999",
        conversa={
            "id": "conv-123",
            "controlled_by": "ai",
            "chatwoot_conversation_id": None,
        },
        medico={"id": "medico-abc"},
    )


@pytest.fixture
def context_human():
    """Contexto com conversa controlada por humano."""
    return ProcessorContext(
        mensagem_raw={"key": {"remoteJid": "5511999999999@s.whatsapp.net"}},
        mensagem_texto="Preciso falar sobre pagamento",
        telefone="5511999999999",
        conversa={
            "id": "conv-456",
            "controlled_by": "human",
            "chatwoot_conversation_id": 789,
        },
        medico={"id": "medico-xyz"},
    )


@pytest.fixture
def context_human_sem_chatwoot():
    """Contexto com conversa controlada por humano sem Chatwoot."""
    return ProcessorContext(
        mensagem_raw={"key": {"remoteJid": "5511999999999@s.whatsapp.net"}},
        mensagem_texto="Oi",
        telefone="5511999999999",
        conversa={
            "id": "conv-789",
            "controlled_by": "human",
            "chatwoot_conversation_id": None,
        },
        medico={"id": "medico-xyz"},
    )


# =============================================================================
# Testes: Controle humano bloqueia Julia
# =============================================================================


@pytest.mark.unit
class TestControleHumanoBloqueia:
    """Testes para quando conversa está sob controle humano."""

    @pytest.mark.asyncio
    async def test_conversa_humana_interrompe_pipeline(self, processor, context_human):
        """Conversa controlada por humano deve interromper o pipeline."""
        with patch(
            "app.services.chatwoot.chatwoot_service"
        ) as mock_chatwoot:
            mock_chatwoot.configurado = True
            mock_chatwoot.enviar_mensagem = AsyncMock()

            result = await processor.process(context_human)

        assert result.success is True
        assert result.should_continue is False
        assert result.metadata.get("human_control") is True

    @pytest.mark.asyncio
    async def test_conversa_humana_sem_resposta(self, processor, context_human):
        """Conversa sob controle humano não gera resposta da Julia."""
        with patch(
            "app.services.chatwoot.chatwoot_service"
        ) as mock_chatwoot:
            mock_chatwoot.configurado = True
            mock_chatwoot.enviar_mensagem = AsyncMock()

            result = await processor.process(context_human)

        assert result.response is None

    @pytest.mark.asyncio
    async def test_sincroniza_com_chatwoot_quando_humano(self, processor, context_human):
        """Mensagem do médico é sincronizada com Chatwoot para o gestor ver."""
        with patch(
            "app.services.chatwoot.chatwoot_service"
        ) as mock_chatwoot:
            mock_chatwoot.configurado = True
            mock_chatwoot.enviar_mensagem = AsyncMock()

            await processor.process(context_human)

        mock_chatwoot.enviar_mensagem.assert_called_once_with(
            conversation_id=789,
            content="Preciso falar sobre pagamento",
            message_type="incoming",
        )

    @pytest.mark.asyncio
    async def test_sem_chatwoot_nao_sincroniza(self, processor, context_human_sem_chatwoot):
        """Sem Chatwoot configurado, não tenta sincronizar."""
        with patch(
            "app.services.chatwoot.chatwoot_service"
        ) as mock_chatwoot:
            mock_chatwoot.configurado = True
            mock_chatwoot.enviar_mensagem = AsyncMock()

            result = await processor.process(context_human_sem_chatwoot)

        # Não deve chamar enviar_mensagem pois chatwoot_conversation_id é None
        mock_chatwoot.enviar_mensagem.assert_not_called()
        assert result.should_continue is False

    @pytest.mark.asyncio
    async def test_erro_chatwoot_nao_para_processador(self, processor, context_human):
        """Erro ao sincronizar com Chatwoot não impede o resultado."""
        with patch(
            "app.services.chatwoot.chatwoot_service"
        ) as mock_chatwoot:
            mock_chatwoot.configurado = True
            mock_chatwoot.enviar_mensagem = AsyncMock(side_effect=Exception("Chatwoot down"))

            result = await processor.process(context_human)

        # Pipeline para mas não falha
        assert result.success is True
        assert result.should_continue is False


# =============================================================================
# Testes: Controle da Julia permite processamento
# =============================================================================


@pytest.mark.unit
class TestControleJuliaPermite:
    """Testes para quando conversa está sob controle da Julia."""

    @pytest.mark.asyncio
    async def test_conversa_ai_permite_continuar(self, processor, context_ai):
        """Conversa controlada pela Julia permite pipeline continuar."""
        result = await processor.process(context_ai)

        assert result.success is True
        assert result.should_continue is True

    @pytest.mark.asyncio
    async def test_conversa_ai_nao_gera_resposta(self, processor, context_ai):
        """Quando permite continuar, não gera resposta própria."""
        result = await processor.process(context_ai)

        assert result.response is None


# =============================================================================
# Testes: Transição de controle
# =============================================================================


@pytest.mark.unit
class TestTransicaoControle:
    """Testes para transição de controle humano -> Julia."""

    @pytest.mark.asyncio
    async def test_transicao_humano_para_julia(self, processor):
        """Após controlled_by voltar para 'ai', Julia processa normalmente."""
        # Primeiro: humano controla
        context_human = ProcessorContext(
            mensagem_raw={},
            mensagem_texto="Msg durante controle humano",
            conversa={"id": "conv-1", "controlled_by": "human"},
        )

        with patch(
            "app.services.chatwoot.chatwoot_service"
        ) as mock_chatwoot:
            mock_chatwoot.configurado = False
            result_human = await processor.process(context_human)

        assert result_human.should_continue is False

        # Depois: Julia retoma controle
        context_ai = ProcessorContext(
            mensagem_raw={},
            mensagem_texto="Msg após Julia retomar",
            conversa={"id": "conv-1", "controlled_by": "ai"},
        )

        result_ai = await processor.process(context_ai)

        assert result_ai.should_continue is True

    @pytest.mark.asyncio
    async def test_controlled_by_none_bloqueia(self, processor):
        """Conversa sem controlled_by definido (None) bloqueia Julia por segurança."""
        context = ProcessorContext(
            mensagem_raw={},
            mensagem_texto="Msg",
            conversa={"id": "conv-1", "controlled_by": None},
        )

        with patch(
            "app.services.chatwoot.chatwoot_service"
        ) as mock_chatwoot:
            mock_chatwoot.configurado = False
            result = await processor.process(context)

        # controlled_by != "ai", então bloqueia
        assert result.should_continue is False


# =============================================================================
# Testes: Propriedades do processador
# =============================================================================


@pytest.mark.unit
class TestPropriedadesProcessador:
    """Testes para propriedades do HumanControlProcessor."""

    def test_nome_processador(self, processor):
        """Nome do processador deve ser 'human_control'."""
        assert processor.name == "human_control"

    def test_prioridade_processador(self, processor):
        """Prioridade deve ser 60 (último pre-processador)."""
        assert processor.priority == 60
