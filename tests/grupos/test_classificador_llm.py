"""
Testes para o classificador LLM.

Sprint 14 - E04 - S04.4
"""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4

from app.services.grupos.classificador_llm import (
    classificar_com_llm,
    _parsear_resposta_llm,
    ResultadoClassificacaoLLM,
    _hash_texto,
)


class TestParsearRespostaLLM:
    """Testes do parser de resposta."""

    def test_json_simples(self):
        """Deve parsear JSON simples."""
        texto = '{"eh_oferta": true, "confianca": 0.95, "motivo": "Oferta clara"}'
        resultado = _parsear_resposta_llm(texto)

        assert resultado.eh_oferta is True
        assert resultado.confianca == 0.95
        assert resultado.motivo == "Oferta clara"

    def test_json_com_texto_antes(self):
        """Deve extrair JSON do meio do texto."""
        texto = 'Analisando a mensagem:\n{"eh_oferta": false, "confianca": 0.8, "motivo": "Pergunta"}'
        resultado = _parsear_resposta_llm(texto)

        assert resultado.eh_oferta is False

    def test_json_com_espacos(self):
        """Deve parsear JSON com espaços/newlines."""
        texto = '''
        {
            "eh_oferta": true,
            "confianca": 0.9,
            "motivo": "teste"
        }
        '''
        resultado = _parsear_resposta_llm(texto)

        assert resultado.eh_oferta is True
        assert resultado.confianca == 0.9

    def test_json_invalido(self):
        """Deve levantar erro para JSON inválido."""
        with pytest.raises(json.JSONDecodeError):
            _parsear_resposta_llm("isso não é json")

    def test_json_sem_campos(self):
        """Deve usar defaults para campos ausentes."""
        texto = '{"eh_oferta": true}'
        resultado = _parsear_resposta_llm(texto)

        assert resultado.eh_oferta is True
        assert resultado.confianca == 0.0
        assert resultado.motivo == ""


class TestHashTexto:
    """Testes do hash de texto para cache."""

    def test_hash_consistente(self):
        """Hash deve ser consistente para mesmo texto."""
        texto = "Plantão disponível"
        hash1 = _hash_texto(texto)
        hash2 = _hash_texto(texto)

        assert hash1 == hash2

    def test_hash_diferente(self):
        """Hash deve ser diferente para textos diferentes."""
        hash1 = _hash_texto("Texto 1")
        hash2 = _hash_texto("Texto 2")

        assert hash1 != hash2


class TestClassificarComLLM:
    """Testes da função de classificação."""

    @pytest.fixture
    def mock_anthropic(self):
        """Mock do cliente AsyncAnthropic."""
        with patch("app.services.grupos.classificador_llm.anthropic.AsyncAnthropic") as mock:
            yield mock.return_value

    @pytest.fixture
    def mock_redis(self):
        """Mock do Redis para cache."""
        with patch("app.services.grupos.classificador_llm.cache_get", new_callable=AsyncMock) as mock_get, \
             patch("app.services.grupos.classificador_llm.cache_set", new_callable=AsyncMock) as mock_set:
            mock_get.return_value = None
            mock_set.return_value = True
            yield {"get": mock_get, "set": mock_set}

    @pytest.mark.asyncio
    async def test_classificacao_oferta(self, mock_anthropic, mock_redis):
        """Deve classificar oferta corretamente."""
        mock_anthropic.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"eh_oferta": true, "confianca": 0.95, "motivo": "Oferta completa"}')],
            usage=MagicMock(input_tokens=100, output_tokens=50)
        ))

        resultado = await classificar_com_llm(
            texto="Plantão disponível Hospital X R$ 1500",
            nome_grupo="Vagas ABC"
        )

        assert resultado.eh_oferta is True
        assert resultado.confianca == 0.95
        assert resultado.tokens_usados == 150
        assert resultado.erro is None

    @pytest.mark.asyncio
    async def test_classificacao_nao_oferta(self, mock_anthropic, mock_redis):
        """Deve identificar não-ofertas."""
        mock_anthropic.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"eh_oferta": false, "confianca": 0.9, "motivo": "Cumprimento"}')],
            usage=MagicMock(input_tokens=50, output_tokens=30)
        ))

        resultado = await classificar_com_llm("Bom dia pessoal!")

        assert resultado.eh_oferta is False
        assert resultado.confianca == 0.9

    @pytest.mark.asyncio
    async def test_erro_parse_json(self, mock_anthropic, mock_redis):
        """Deve tratar erro de parse JSON."""
        mock_anthropic.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='Resposta sem JSON')],
            usage=MagicMock(input_tokens=50, output_tokens=30)
        ))

        resultado = await classificar_com_llm("Teste")

        assert resultado.eh_oferta is False
        assert resultado.erro is not None
        assert "erro_parse" in resultado.motivo

    @pytest.mark.asyncio
    async def test_usa_cache(self, mock_anthropic, mock_redis):
        """Deve usar resultado do cache."""
        # Configurar cache com resultado
        mock_redis["get"].return_value = json.dumps({
            "eh_oferta": True,
            "confianca": 0.85,
            "motivo": "Do cache"
        })

        resultado = await classificar_com_llm("Texto cacheado")

        assert resultado.eh_oferta is True
        assert resultado.do_cache is True
        assert resultado.tokens_usados == 0
        # LLM não deve ser chamado
        mock_anthropic.messages.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_salva_no_cache(self, mock_anthropic, mock_redis):
        """Deve salvar resultado no cache."""
        mock_anthropic.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"eh_oferta": true, "confianca": 0.9, "motivo": "ok"}')],
            usage=MagicMock(input_tokens=50, output_tokens=30)
        ))

        await classificar_com_llm("Plantão Hospital ABC")

        # Verificar que cache_set foi chamado
        mock_redis["set"].assert_called_once()

    @pytest.mark.asyncio
    async def test_bypass_cache(self, mock_anthropic, mock_redis):
        """Deve ignorar cache quando solicitado."""
        mock_redis["get"].return_value = json.dumps({
            "eh_oferta": True,
            "confianca": 0.85,
            "motivo": "Do cache"
        })
        mock_anthropic.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"eh_oferta": false, "confianca": 0.9, "motivo": "fresh"}')],
            usage=MagicMock(input_tokens=50, output_tokens=30)
        ))

        resultado = await classificar_com_llm("Texto", usar_cache=False)

        assert resultado.eh_oferta is False
        assert resultado.do_cache is False
        mock_anthropic.messages.create.assert_called_once()


class TestResultadoClassificacaoLLM:
    """Testes da dataclass de resultado."""

    def test_criacao_basica(self):
        """Deve criar resultado com valores básicos."""
        resultado = ResultadoClassificacaoLLM(
            eh_oferta=True,
            confianca=0.9,
            motivo="Teste"
        )

        assert resultado.eh_oferta is True
        assert resultado.confianca == 0.9
        assert resultado.motivo == "Teste"
        assert resultado.tokens_usados == 0
        assert resultado.erro is None
        assert resultado.do_cache is False

    def test_criacao_com_erro(self):
        """Deve criar resultado com erro."""
        resultado = ResultadoClassificacaoLLM(
            eh_oferta=False,
            confianca=0.0,
            motivo="erro",
            erro="API Error"
        )

        assert resultado.erro == "API Error"
