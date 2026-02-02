"""Testes para AgenteHelena."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.helena.agent import AgenteHelena, PADROES_INCOMPLETOS


class TestAgenteHelena:
    """Testes para o agente Helena."""

    @pytest.fixture
    def agente(self):
        """Fixture do agente."""
        return AgenteHelena(user_id="U123", channel_id="C456")

    def test_init(self, agente):
        """Verifica inicialização."""
        assert agente.user_id == "U123"
        assert agente.channel_id == "C456"
        assert agente.session is not None

    def test_resposta_incompleta_detecta_dois_pontos(self, agente):
        """Detecta resposta terminando em ':'."""
        assert agente._resposta_incompleta("Vou verificar:", "end_turn") is True

    def test_resposta_incompleta_detecta_reticencias(self, agente):
        """Detecta resposta terminando em '...'."""
        assert agente._resposta_incompleta("Deixa eu ver...", "end_turn") is True

    def test_resposta_completa(self, agente):
        """Resposta completa não é marcada como incompleta."""
        assert agente._resposta_incompleta("Tivemos 50 conversas hoje.", "end_turn") is False

    def test_resposta_com_tool_use_nao_incompleta(self, agente):
        """Resposta com tool_use não é incompleta."""
        assert agente._resposta_incompleta("", "tool_use") is False

    def test_resposta_incompleta_vou_verificar(self, agente):
        """Detecta 'vou verificar' como incompleto."""
        assert agente._resposta_incompleta("Deixa eu olhar, vou verificar", "end_turn") is True

    def test_resposta_incompleta_consultando(self, agente):
        """Detecta 'consultando' como incompleto."""
        assert agente._resposta_incompleta("consultando", "end_turn") is True

    @pytest.mark.asyncio
    async def test_processar_mensagem_simples(self, agente):
        """Testa processamento de mensagem simples."""
        with patch.object(agente, '_chamar_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "Tivemos 50 conversas hoje."

            with patch.object(agente.session, 'carregar', new_callable=AsyncMock):
                with patch.object(agente.session, 'salvar', new_callable=AsyncMock):
                    resposta = await agente.processar_mensagem("Como foi hoje?")

        assert resposta == "Tivemos 50 conversas hoje."
        mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_processar_mensagem_erro_api(self, agente):
        """Testa tratamento de erro da API."""
        import anthropic

        with patch.object(agente, '_chamar_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = anthropic.APIError(
                message="Rate limit",
                request=MagicMock(),
                body=None
            )

            with patch.object(agente.session, 'carregar', new_callable=AsyncMock):
                resposta = await agente.processar_mensagem("teste")

        assert "problema técnico" in resposta.lower()

    @pytest.mark.asyncio
    async def test_processar_mensagem_erro_generico(self, agente):
        """Testa tratamento de erro genérico."""
        with patch.object(agente, '_chamar_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("Erro inesperado")

            with patch.object(agente.session, 'carregar', new_callable=AsyncMock):
                resposta = await agente.processar_mensagem("teste")

        assert "deu errado" in resposta.lower()


class TestSessionManager:
    """Testes para SessionManager."""

    @pytest.mark.asyncio
    async def test_carregar_sessao_nova(self):
        """Carrega sessão nova quando não existe."""
        from app.services.helena.session import SessionManager

        with patch('app.services.helena.session.supabase') as mock_db:
            mock_result = MagicMock()
            mock_result.data = None
            mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value = mock_result

            manager = SessionManager("U123", "C456")
            session = await manager.carregar()

        assert session.user_id == "U123"
        assert session.mensagens == []

    @pytest.mark.asyncio
    async def test_adicionar_mensagem_limita_historico(self):
        """Histórico é limitado a MAX_MESSAGES."""
        from app.services.helena.session import SessionManager, MAX_MESSAGES

        with patch('app.services.helena.session.supabase') as mock_db:
            mock_result = MagicMock()
            mock_result.data = None
            mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value = mock_result

            manager = SessionManager("U123", "C456")
            await manager.carregar()

            # Adicionar mais que o limite
            for i in range(MAX_MESSAGES + 5):
                manager.adicionar_mensagem("user", f"msg {i}")

            assert len(manager.mensagens) == MAX_MESSAGES

    @pytest.mark.asyncio
    async def test_atualizar_contexto(self):
        """Atualiza contexto da sessão."""
        from app.services.helena.session import SessionManager

        with patch('app.services.helena.session.supabase') as mock_db:
            mock_result = MagicMock()
            mock_result.data = None
            mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value = mock_result

            manager = SessionManager("U123", "C456")
            await manager.carregar()

            manager.atualizar_contexto("ultima_query", {"data": "teste"})

            assert manager.session.contexto["ultima_query"] == {"data": "teste"}
