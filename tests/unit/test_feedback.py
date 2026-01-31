"""
Testes para o serviço de feedback - Sprint 42

Testa a função atualizar_prompt_com_feedback que extrai exemplos
de conversas boas/ruins e salva no banco de dados.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime


class TestAtualizarPromptComFeedback:
    """Testes para atualizar_prompt_com_feedback."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do cliente Supabase."""
        with patch("app.services.feedback.supabase") as mock:
            yield mock

    @pytest.fixture
    def mock_gerar_exemplos(self):
        """Mock da função gerar_exemplos_prompt."""
        with patch("app.services.feedback.gerar_exemplos_prompt") as mock:
            mock.return_value = "## Exemplos de Conversas\n\nExemplo teste"
            yield mock

    @pytest.fixture
    def mock_extrair_exemplos(self):
        """Mock da função extrair_exemplos_treinamento."""
        with patch("app.services.feedback.extrair_exemplos_treinamento") as mock:
            mock.return_value = {
                "bons": [
                    {"conversa_id": "123", "score": 9, "interacoes": []},
                    {"conversa_id": "456", "score": 8, "interacoes": []},
                ],
                "ruins": [
                    {"conversa_id": "789", "score": 2, "interacoes": []},
                ],
            }
            yield mock

    @pytest.mark.asyncio
    async def test_cria_novo_registro_quando_nao_existe(
        self, mock_supabase, mock_gerar_exemplos, mock_extrair_exemplos
    ):
        """Deve criar novo registro quando não existe exemplos_feedback."""
        from app.services.feedback import atualizar_prompt_com_feedback

        # Mock: não existe registro
        mock_select = MagicMock()
        mock_select.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value = mock_select

        # Mock: insert
        mock_insert = MagicMock()
        mock_insert.execute.return_value = MagicMock(data=[{"id": "new-id"}])
        mock_supabase.table.return_value.insert.return_value = mock_insert

        # Mock: update sugestoes
        mock_update = MagicMock()
        mock_update.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.update.return_value = mock_update

        resultado = await atualizar_prompt_com_feedback()

        assert resultado["status"] == "ok"
        assert resultado["exemplos_bons"] == 2
        assert resultado["exemplos_ruins"] == 1

        # Verifica que insert foi chamado
        mock_supabase.table.return_value.insert.assert_called_once()
        call_args = mock_supabase.table.return_value.insert.call_args[0][0]
        assert call_args["nome"] == "exemplos_conversas"
        assert call_args["tipo"] == "exemplos_feedback"
        assert call_args["ativo"] is True

    @pytest.mark.asyncio
    async def test_atualiza_registro_quando_existe(
        self, mock_supabase, mock_gerar_exemplos, mock_extrair_exemplos
    ):
        """Deve atualizar registro existente quando já existe exemplos_feedback."""
        from app.services.feedback import atualizar_prompt_com_feedback

        # Mock: existe registro
        mock_select = MagicMock()
        mock_select.execute.return_value = MagicMock(data=[{"id": "existing-id"}])
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value = mock_select

        # Mock: update prompts
        mock_update_prompts = MagicMock()
        mock_update_prompts.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.update.return_value = mock_update_prompts

        resultado = await atualizar_prompt_com_feedback()

        assert resultado["status"] == "ok"
        assert resultado["exemplos_bons"] == 2
        assert resultado["exemplos_ruins"] == 1

        # Verifica que update foi chamado (não insert)
        mock_supabase.table.return_value.update.assert_called()

    @pytest.mark.asyncio
    async def test_marca_sugestoes_como_aplicadas(
        self, mock_supabase, mock_gerar_exemplos, mock_extrair_exemplos
    ):
        """Deve marcar sugestões pendentes como aplicadas."""
        from app.services.feedback import atualizar_prompt_com_feedback

        # Mock: não existe registro
        mock_select = MagicMock()
        mock_select.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value = mock_select

        # Mock: insert
        mock_insert = MagicMock()
        mock_insert.execute.return_value = MagicMock(data=[{"id": "new-id"}])
        mock_supabase.table.return_value.insert.return_value = mock_insert

        # Mock: update sugestoes
        mock_update = MagicMock()
        mock_update.eq.return_value.execute.return_value = MagicMock(data=[])
        mock_supabase.table.return_value.update.return_value = mock_update

        await atualizar_prompt_com_feedback()

        # Verifica que sugestoes_prompt foi atualizado
        calls = mock_supabase.table.call_args_list
        sugestoes_calls = [c for c in calls if "sugestoes_prompt" in str(c)]
        assert len(sugestoes_calls) > 0

    @pytest.mark.asyncio
    async def test_propaga_erro_quando_falha(self, mock_supabase):
        """Deve propagar erro quando ocorre exceção."""
        from app.services.feedback import atualizar_prompt_com_feedback

        mock_supabase.table.side_effect = Exception("Erro de conexão")

        with pytest.raises(Exception) as exc_info:
            await atualizar_prompt_com_feedback()

        assert "Erro de conexão" in str(exc_info.value)


class TestExtrairExemplosTreinamento:
    """Testes para extrair_exemplos_treinamento."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do cliente Supabase."""
        with patch("app.services.feedback.supabase") as mock:
            yield mock

    @pytest.fixture
    def mock_obter_interacoes(self):
        """Mock da função obter_interacoes."""
        with patch("app.services.feedback.obter_interacoes") as mock:
            mock.return_value = [
                {"conteudo": "Oi", "direcao": "entrada"},
                {"conteudo": "Olá!", "direcao": "saida"},
            ]
            yield mock

    @pytest.mark.asyncio
    async def test_separa_exemplos_bons_e_ruins(
        self, mock_supabase, mock_obter_interacoes
    ):
        """Deve separar exemplos com score >= 8 como bons e <= 4 como ruins."""
        from app.services.feedback import extrair_exemplos_treinamento

        mock_response = MagicMock()
        mock_response.data = [
            {"score_geral": 9, "conversa_id": "conv1", "notas": "Excelente"},
            {"score_geral": 8, "conversa_id": "conv2", "notas": "Bom"},
            {"score_geral": 5, "conversa_id": "conv3", "notas": "Mediano"},  # Ignorado
            {"score_geral": 3, "conversa_id": "conv4", "notas": "Ruim"},
            {"score_geral": 2, "conversa_id": "conv5", "notas": "Péssimo"},
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        resultado = await extrair_exemplos_treinamento()

        assert len(resultado["bons"]) == 2
        assert len(resultado["ruins"]) == 2
        # Verifica ordenação (melhores primeiro para bons)
        assert resultado["bons"][0]["score"] == 9
        # Verifica ordenação (piores primeiro para ruins)
        assert resultado["ruins"][0]["score"] == 2

    @pytest.mark.asyncio
    async def test_retorna_vazio_quando_sem_avaliacoes(self, mock_supabase):
        """Deve retornar listas vazias quando não há avaliações."""
        from app.services.feedback import extrair_exemplos_treinamento

        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        resultado = await extrair_exemplos_treinamento()

        assert resultado["bons"] == []
        assert resultado["ruins"] == []

    @pytest.mark.asyncio
    async def test_limita_top_10_exemplos(
        self, mock_supabase, mock_obter_interacoes
    ):
        """Deve limitar a 10 exemplos de cada tipo."""
        from app.services.feedback import extrair_exemplos_treinamento

        # Criar 15 avaliações boas
        avaliacoes = [
            {"score_geral": 10, "conversa_id": f"conv{i}", "notas": "Bom"}
            for i in range(15)
        ]
        mock_response = MagicMock()
        mock_response.data = avaliacoes
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        resultado = await extrair_exemplos_treinamento()

        assert len(resultado["bons"]) <= 10


class TestGerarExemplosPrompt:
    """Testes para gerar_exemplos_prompt."""

    @pytest.fixture
    def mock_extrair_exemplos(self):
        """Mock da função extrair_exemplos_treinamento."""
        with patch("app.services.feedback.extrair_exemplos_treinamento") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_gera_texto_formatado(self, mock_extrair_exemplos):
        """Deve gerar texto formatado com exemplos."""
        from app.services.feedback import gerar_exemplos_prompt

        mock_extrair_exemplos.return_value = {
            "bons": [
                {
                    "conversa_id": "123",
                    "score": 9,
                    "interacoes": [
                        {"conteudo": "Oi doutor", "direcao": "saida"},
                        {"conteudo": "Olá", "direcao": "entrada"},
                    ],
                    "porque_bom": "Abordagem natural",
                }
            ],
            "ruins": [
                {
                    "conversa_id": "456",
                    "score": 2,
                    "interacoes": [
                        {"conteudo": "PLANTÃO DISPONÍVEL", "direcao": "saida"},
                    ],
                    "porque_ruim": "Muito formal",
                }
            ],
        }

        resultado = await gerar_exemplos_prompt()

        assert "## Exemplos de Conversas" in resultado
        assert "✅ Respostas que funcionaram bem" in resultado
        assert "❌ Evitar respostas assim" in resultado
        assert "Abordagem natural" in resultado
        assert "Muito formal" in resultado

    @pytest.mark.asyncio
    async def test_retorna_mensagem_padrao_sem_exemplos(self, mock_extrair_exemplos):
        """Deve retornar mensagem padrão quando não há exemplos."""
        from app.services.feedback import gerar_exemplos_prompt

        mock_extrair_exemplos.return_value = {"bons": [], "ruins": []}

        resultado = await gerar_exemplos_prompt()

        assert "## Exemplos de Conversas" in resultado


class TestObterInteracoes:
    """Testes para obter_interacoes."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock do cliente Supabase."""
        with patch("app.services.feedback.supabase") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_busca_interacoes_ordenadas(self, mock_supabase):
        """Deve buscar interações ordenadas por created_at."""
        from app.services.feedback import obter_interacoes

        mock_response = MagicMock()
        mock_response.data = [
            {"id": 1, "conteudo": "Msg 1"},
            {"id": 2, "conteudo": "Msg 2"},
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        resultado = await obter_interacoes("conv-123")

        assert len(resultado) == 2
        mock_supabase.table.return_value.select.return_value.eq.assert_called_with(
            "conversation_id", "conv-123"
        )

    @pytest.mark.asyncio
    async def test_retorna_vazio_em_erro(self, mock_supabase):
        """Deve retornar lista vazia em caso de erro."""
        from app.services.feedback import obter_interacoes

        mock_supabase.table.side_effect = Exception("Erro")

        resultado = await obter_interacoes("conv-123")

        assert resultado == []
