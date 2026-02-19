"""
Testes do extrator LLM unificado.

Sprint 63 - Fix cache key que ignorava data_referencia.
"""

import pytest
from datetime import date
from unittest.mock import patch, AsyncMock

from app.services.grupos.extrator_v2.extrator_llm import (
    _hash_texto,
    _chave_cache,
    buscar_extracao_cache,
    salvar_extracao_cache,
    ResultadoExtracaoLLM,
    CACHE_PREFIX,
)


class TestHashTexto:
    """Testes do hash de texto."""

    def test_hash_normaliza_lowercase(self):
        """Deve normalizar para lowercase antes de gerar hash."""
        assert _hash_texto("HOSPITAL ABC") == _hash_texto("hospital abc")

    def test_hash_normaliza_espacos(self):
        """Deve normalizar espaços antes de gerar hash."""
        assert _hash_texto("hospital  abc") == _hash_texto("hospital abc")

    def test_hash_textos_diferentes(self):
        """Textos diferentes devem gerar hashes diferentes."""
        assert _hash_texto("hospital abc") != _hash_texto("hospital xyz")


class TestChaveCache:
    """Testes da geração de chave de cache."""

    def test_chave_com_data(self):
        """Deve incluir data na chave."""
        data = date(2026, 2, 19)
        chave = _chave_cache("texto", data)
        assert "2026-02-19" in chave
        assert chave.startswith(CACHE_PREFIX)

    def test_chave_sem_data(self):
        """Deve usar 'sem_data' quando não tem data."""
        chave = _chave_cache("texto", None)
        assert "sem_data" in chave

    def test_chaves_diferentes_para_datas_diferentes(self):
        """Mesma mensagem em datas diferentes deve gerar chaves diferentes."""
        chave_dia1 = _chave_cache("plantao amanha", date(2026, 2, 19))
        chave_dia2 = _chave_cache("plantao amanha", date(2026, 2, 20))
        assert chave_dia1 != chave_dia2

    def test_chaves_iguais_para_mesma_data(self):
        """Mesma mensagem na mesma data deve gerar mesma chave."""
        chave1 = _chave_cache("plantao amanha", date(2026, 2, 19))
        chave2 = _chave_cache("plantao amanha", date(2026, 2, 19))
        assert chave1 == chave2

    def test_chaves_diferentes_para_textos_diferentes(self):
        """Textos diferentes na mesma data devem gerar chaves diferentes."""
        data = date(2026, 2, 19)
        chave1 = _chave_cache("plantao cm", data)
        chave2 = _chave_cache("plantao go", data)
        assert chave1 != chave2


class TestBuscarExtracaoCache:
    """Testes da busca no cache com data_referencia."""

    @pytest.mark.asyncio
    async def test_cache_hit_com_data(self):
        """Deve retornar cache quando existe para data específica."""
        import json

        dados_cache = json.dumps(
            {
                "eh_vaga": True,
                "confianca": 0.9,
                "motivo_descarte": None,
                "vagas": [{"hospital": "H. ABC", "data": "2026-02-20"}],
            }
        )

        with patch(
            "app.services.grupos.extrator_v2.extrator_llm.cache_get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = dados_cache

            resultado = await buscar_extracao_cache("plantao amanha", date(2026, 2, 19))

            assert resultado is not None
            assert resultado.eh_vaga is True
            assert resultado.do_cache is True
            # Verifica que usou chave com data
            chave_esperada = _chave_cache("plantao amanha", date(2026, 2, 19))
            mock_get.assert_called_once_with(chave_esperada)

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Deve retornar None quando cache não existe."""
        with patch(
            "app.services.grupos.extrator_v2.extrator_llm.cache_get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            resultado = await buscar_extracao_cache("texto", date(2026, 2, 19))

            assert resultado is None

    @pytest.mark.asyncio
    async def test_cache_data_diferente_nao_retorna(self):
        """Deve não encontrar cache se data é diferente."""
        import json

        dados_cache = json.dumps(
            {
                "eh_vaga": True,
                "confianca": 0.9,
                "motivo_descarte": None,
                "vagas": [],
            }
        )

        call_count = 0

        async def mock_cache_get(chave):
            nonlocal call_count
            call_count += 1
            # Só retorna dados se a chave contém dia 19
            if "2026-02-19" in chave:
                return dados_cache
            return None

        with patch(
            "app.services.grupos.extrator_v2.extrator_llm.cache_get", side_effect=mock_cache_get
        ):
            # Dia 19: hit
            r1 = await buscar_extracao_cache("plantao amanha", date(2026, 2, 19))
            assert r1 is not None

            # Dia 20: miss (chave diferente)
            r2 = await buscar_extracao_cache("plantao amanha", date(2026, 2, 20))
            assert r2 is None


class TestSalvarExtracaoCache:
    """Testes de salvar no cache com data_referencia."""

    @pytest.mark.asyncio
    async def test_salva_com_data_na_chave(self):
        """Deve salvar usando chave com data."""
        resultado = ResultadoExtracaoLLM(
            eh_vaga=True,
            confianca=0.9,
            vagas=[{"hospital": "ABC"}],
        )

        with patch(
            "app.services.grupos.extrator_v2.extrator_llm.cache_set", new_callable=AsyncMock
        ) as mock_set:
            await salvar_extracao_cache("texto", resultado, date(2026, 2, 19))

            chave_esperada = _chave_cache("texto", date(2026, 2, 19))
            mock_set.assert_called_once()
            assert mock_set.call_args[0][0] == chave_esperada
