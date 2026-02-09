"""
Testes para o extrator de dados.

Sprint 53: Discovery Intelligence Pipeline.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import json

from app.services.extraction.extractor import (
    extrair_dados_conversa,
    _gerar_cache_key,
    _parsear_resposta,
    _parsear_objecao,
    _resultado_padrao,
)
from app.services.extraction.schemas import (
    ExtractionContext,
    ExtractionResult,
    Interesse,
    ProximoPasso,
    TipoObjecao,
)


class TestCacheKey:
    """Testes para geracao de chave de cache."""

    def test_gerar_cache_key(self):
        """Gera chave de cache baseada no conteudo."""
        ctx = ExtractionContext(
            mensagem_medico="Oi",
            resposta_julia="Ola",
            nome_medico="Dr. Teste",
        )
        key = _gerar_cache_key(ctx)
        assert key.startswith("extraction:")
        assert len(key) > 20  # hash MD5 tem 32 chars

    def test_mesma_mensagem_mesma_chave(self):
        """Mesma mensagem gera mesma chave."""
        ctx1 = ExtractionContext(
            mensagem_medico="Oi, tenho interesse",
            resposta_julia="Otimo!",
            nome_medico="Dr. A",
        )
        ctx2 = ExtractionContext(
            mensagem_medico="Oi, tenho interesse",
            resposta_julia="Otimo!",
            nome_medico="Dr. B",  # nome diferente, mas nao afeta cache
        )
        assert _gerar_cache_key(ctx1) == _gerar_cache_key(ctx2)

    def test_mensagens_diferentes_chaves_diferentes(self):
        """Mensagens diferentes geram chaves diferentes."""
        ctx1 = ExtractionContext(
            mensagem_medico="Oi",
            resposta_julia="Ola",
            nome_medico="Dr. Teste",
        )
        ctx2 = ExtractionContext(
            mensagem_medico="Oi, tenho interesse",
            resposta_julia="Ola",
            nome_medico="Dr. Teste",
        )
        assert _gerar_cache_key(ctx1) != _gerar_cache_key(ctx2)


class TestParsearResposta:
    """Testes para parsing de resposta do LLM."""

    def test_parse_json_valido(self):
        """Parseia JSON valido."""
        resposta = json.dumps({
            "interesse": "positivo",
            "interesse_score": 0.8,
            "especialidade_mencionada": "Cardiologia",
            "proximo_passo": "enviar_vagas",
            "confianca": 0.9,
        })
        ctx = ExtractionContext(
            mensagem_medico="Test",
            resposta_julia="Test",
            nome_medico="Dr.",
        )
        result = _parsear_resposta(resposta, ctx)

        assert result.interesse == Interesse.POSITIVO
        assert result.interesse_score == 0.8
        assert result.especialidade_mencionada == "Cardiologia"
        assert result.proximo_passo == ProximoPasso.ENVIAR_VAGAS

    def test_parse_json_com_markdown(self):
        """Parseia JSON dentro de bloco markdown."""
        resposta = '''```json
{
    "interesse": "negativo",
    "interesse_score": 0.2,
    "proximo_passo": "marcar_inativo",
    "confianca": 0.7
}
```'''
        ctx = ExtractionContext(
            mensagem_medico="Test",
            resposta_julia="Test",
            nome_medico="Dr.",
        )
        result = _parsear_resposta(resposta, ctx)

        assert result.interesse == Interesse.NEGATIVO
        assert result.interesse_score == 0.2

    def test_parse_json_invalido_fallback(self):
        """Fallback para JSON invalido."""
        resposta = "Isso nao e JSON"
        ctx = ExtractionContext(
            mensagem_medico="Test",
            resposta_julia="Test",
            nome_medico="Dr.",
        )
        result = _parsear_resposta(resposta, ctx)

        # Deve retornar resultado padrao
        assert result.interesse == Interesse.INCERTO
        assert result.confianca == 0.0
        assert result.raw_json.get("_fallback") is True

    def test_parse_com_objecao(self):
        """Parseia JSON com objecao."""
        resposta = json.dumps({
            "interesse": "negativo",
            "interesse_score": 0.1,
            "objecao": {
                "tipo": "preco",
                "descricao": "Valor muito baixo",
                "severidade": "alta",
            },
            "proximo_passo": "agendar_followup",
            "confianca": 0.8,
        })
        ctx = ExtractionContext(
            mensagem_medico="Test",
            resposta_julia="Test",
            nome_medico="Dr.",
        )
        result = _parsear_resposta(resposta, ctx)

        assert result.objecao is not None
        assert result.objecao.tipo == TipoObjecao.PRECO
        assert result.objecao.descricao == "Valor muito baixo"

    def test_parse_com_preferencias_e_restricoes(self):
        """Parseia JSON com preferencias e restricoes."""
        resposta = json.dumps({
            "interesse": "positivo",
            "interesse_score": 0.7,
            "preferencias": ["plantoes noturnos", "UTI"],
            "restricoes": ["nao trabalho fins de semana"],
            "proximo_passo": "enviar_vagas",
            "confianca": 0.8,
        })
        ctx = ExtractionContext(
            mensagem_medico="Test",
            resposta_julia="Test",
            nome_medico="Dr.",
        )
        result = _parsear_resposta(resposta, ctx)

        assert len(result.preferencias) == 2
        assert "plantoes noturnos" in result.preferencias
        assert len(result.restricoes) == 1


class TestParsearObjecao:
    """Testes para parsing de objecao."""

    def test_parse_objecao_valida(self):
        """Parseia objecao valida."""
        data = {
            "tipo": "tempo",
            "descricao": "Muito ocupado agora",
            "severidade": "media",
        }
        objecao = _parsear_objecao(data)

        assert objecao is not None
        assert objecao.tipo == TipoObjecao.TEMPO
        assert objecao.descricao == "Muito ocupado agora"

    def test_parse_objecao_none(self):
        """Retorna None para dados nulos."""
        assert _parsear_objecao(None) is None
        assert _parsear_objecao({}) is None
        assert _parsear_objecao({"tipo": None}) is None

    def test_parse_objecao_tipo_invalido(self):
        """Retorna None para tipo invalido."""
        data = {
            "tipo": "tipo_inexistente",
            "descricao": "Teste",
            "severidade": "media",
        }
        objecao = _parsear_objecao(data)
        assert objecao is None


class TestResultadoPadrao:
    """Testes para resultado padrao."""

    def test_resultado_padrao_basico(self):
        """Resultado padrao tem valores corretos."""
        ctx = ExtractionContext(
            mensagem_medico="Test",
            resposta_julia="Test",
            nome_medico="Dr.",
        )
        result = _resultado_padrao(ctx, "teste_motivo")

        assert result.interesse == Interesse.INCERTO
        assert result.interesse_score == 0.5
        assert result.proximo_passo == ProximoPasso.SEM_ACAO
        assert result.confianca == 0.0
        assert result.raw_json.get("_fallback") is True
        assert result.raw_json.get("_motivo") == "teste_motivo"


class TestExtrairDadosConversa:
    """Testes de integracao para extrair_dados_conversa."""

    @pytest.mark.asyncio
    async def test_mensagem_muito_curta(self):
        """Retorna resultado padrao para mensagem muito curta."""
        ctx = ExtractionContext(
            mensagem_medico="",
            resposta_julia="Ola!",
            nome_medico="Dr.",
        )
        result = await extrair_dados_conversa(ctx)

        assert result.interesse == Interesse.INCERTO
        assert result.confianca == 0.0
        assert "mensagem_muito_curta" in str(result.raw_json)

    @pytest.mark.asyncio
    async def test_mensagem_curta_demais(self):
        """Retorna resultado padrao para mensagem com 1 char."""
        ctx = ExtractionContext(
            mensagem_medico="a",
            resposta_julia="Ola!",
            nome_medico="Dr.",
        )
        result = await extrair_dados_conversa(ctx)

        assert result.interesse == Interesse.INCERTO

    @pytest.mark.asyncio
    @patch("app.services.extraction.extractor.cache_get")
    async def test_cache_hit(self, mock_cache_get):
        """Retorna resultado do cache se existir."""
        cached_data = json.dumps({
            "interesse": "positivo",
            "interesse_score": 0.9,
            "proximo_passo": "enviar_vagas",
            "confianca": 0.95,
        })
        mock_cache_get.return_value = cached_data

        ctx = ExtractionContext(
            mensagem_medico="Tenho interesse em vagas",
            resposta_julia="Otimo!",
            nome_medico="Dr. Teste",
        )
        result = await extrair_dados_conversa(ctx)

        assert result.interesse == Interesse.POSITIVO
        assert result.interesse_score == 0.9
        mock_cache_get.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.extraction.extractor.cache_get")
    @patch("app.services.extraction.extractor.cache_set")
    @patch("app.services.extraction.extractor._chamar_llm")
    async def test_llm_chamado_quando_sem_cache(
        self,
        mock_llm,
        mock_cache_set,
        mock_cache_get,
    ):
        """Chama LLM quando nao ha cache."""
        mock_cache_get.return_value = None
        mock_llm.return_value = (
            json.dumps({
                "interesse": "positivo",
                "interesse_score": 0.8,
                "proximo_passo": "enviar_vagas",
                "confianca": 0.9,
            }),
            100,  # tokens_input
            50,   # tokens_output
        )

        ctx = ExtractionContext(
            mensagem_medico="Tenho muito interesse em vagas",
            resposta_julia="Otimo! Temos varias opcoes",
            nome_medico="Dr. Teste",
        )
        result = await extrair_dados_conversa(ctx)

        assert result.interesse == Interesse.POSITIVO
        assert result.tokens_input == 100
        assert result.tokens_output == 50
        mock_llm.assert_called_once()
        mock_cache_set.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.extraction.extractor.cache_get")
    @patch("app.services.extraction.extractor._chamar_llm")
    async def test_erro_llm_retorna_fallback(
        self,
        mock_llm,
        mock_cache_get,
    ):
        """Retorna fallback quando LLM falha."""
        mock_cache_get.return_value = None
        mock_llm.side_effect = Exception("API Error")

        ctx = ExtractionContext(
            mensagem_medico="Tenho interesse",
            resposta_julia="Otimo!",
            nome_medico="Dr. Teste",
        )
        result = await extrair_dados_conversa(ctx)

        assert result.interesse == Interesse.INCERTO
        assert result.confianca == 0.0
        assert "erro_llm" in str(result.raw_json)
