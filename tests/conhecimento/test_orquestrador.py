"""Testes de integração para o OrquestradorConhecimento."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.conhecimento import (
    OrquestradorConhecimento,
    ContextoSituacao,
    TipoObjecao,
    PerfilMedico,
    ObjetivoConversa,
)


class TestOrquestradorConhecimento:
    """Testes do orquestrador."""

    @pytest.fixture
    def orquestrador(self):
        return OrquestradorConhecimento()

    @pytest.mark.asyncio
    async def test_analisar_situacao_detecta_objecao(self, orquestrador):
        """Deve detectar objeção e buscar conhecimento relevante."""
        with patch.object(
            orquestrador.buscador, "buscar_para_objecao", new_callable=AsyncMock
        ) as mock_buscar:
            mock_buscar.return_value = []

            resultado = await orquestrador.analisar_situacao(
                mensagem="O valor está muito baixo pra mim",
                historico=[],
                dados_cliente=None,
                stage="em_conversacao",
            )

            assert isinstance(resultado, ContextoSituacao)
            assert resultado.objecao.tem_objecao is True
            assert resultado.objecao.tipo == TipoObjecao.PRECO
            mock_buscar.assert_called_once()

    @pytest.mark.asyncio
    async def test_analisar_situacao_detecta_perfil(self, orquestrador):
        """Deve detectar perfil baseado nos dados do cliente."""
        with patch.object(
            orquestrador.buscador, "buscar_para_perfil", new_callable=AsyncMock
        ) as mock_buscar:
            mock_buscar.return_value = []

            resultado = await orquestrador.analisar_situacao(
                mensagem="Olá",
                historico=[],
                dados_cliente={"anos_experiencia": 20, "titulo": "Professor"},
                stage="novo",
            )

            assert resultado.perfil.perfil == PerfilMedico.SENIOR

    @pytest.mark.asyncio
    async def test_analisar_situacao_detecta_objetivo(self, orquestrador):
        """Deve detectar objetivo baseado no stage."""
        with patch.object(
            orquestrador.buscador, "buscar", new_callable=AsyncMock
        ) as mock_buscar:
            mock_buscar.return_value = []

            resultado = await orquestrador.analisar_situacao(
                mensagem="Quero essa vaga",
                historico=[],
                dados_cliente=None,
                stage="qualificado",
            )

            # Mensagem indica fechamento
            assert resultado.objetivo.objetivo in [
                ObjetivoConversa.FECHAR,
                ObjetivoConversa.OFERTAR,
            ]

    @pytest.mark.asyncio
    async def test_analisar_situacao_gera_resumo(self, orquestrador):
        """Deve gerar resumo formatado para injeção."""
        with patch.object(
            orquestrador.buscador, "buscar_para_objecao", new_callable=AsyncMock
        ) as mock_buscar:
            mock_buscar.return_value = []

            resultado = await orquestrador.analisar_situacao(
                mensagem="Paga pouco demais",
                historico=[],
                dados_cliente=None,
                stage="em_conversacao",
            )

            assert "## SITUAÇÃO DETECTADA" in resultado.resumo
            assert "Objeção" in resultado.resumo
            assert "preco" in resultado.resumo.lower()

    @pytest.mark.asyncio
    async def test_analisar_rapido_sem_rag(self, orquestrador):
        """Deve fazer análise rápida sem busca de conhecimento."""
        resultado = await orquestrador.analisar_rapido(
            "Não tenho tempo agora"
        )

        assert isinstance(resultado, dict)
        assert resultado["tem_objecao"] is True
        assert resultado["tipo_objecao"] == "tempo"
        assert "confianca_media" in resultado


class TestOrquestradorCenariosReais:
    """Testes com cenários reais de conversa."""

    @pytest.fixture
    def orquestrador(self):
        return OrquestradorConhecimento()

    @pytest.mark.asyncio
    async def test_cenario_medico_senior_com_objecao_preco(self, orquestrador):
        """Cenário: médico sênior reclama do valor."""
        with patch.object(
            orquestrador.buscador, "buscar_para_objecao", new_callable=AsyncMock
        ) as mock_objecao, patch.object(
            orquestrador.buscador, "buscar_para_perfil", new_callable=AsyncMock
        ) as mock_perfil:
            mock_objecao.return_value = []
            mock_perfil.return_value = []

            resultado = await orquestrador.analisar_situacao(
                mensagem="Paga muito pouco para o que fazemos",
                historico=["Trabalho há 25 anos nessa área"],
                dados_cliente={"anos_experiencia": 25, "titulo": "Doutor"},
                stage="em_conversacao",
            )

            # Deve detectar objeção de preço
            assert resultado.objecao.tem_objecao is True
            assert resultado.objecao.tipo == TipoObjecao.PRECO

            # Deve detectar perfil sênior
            assert resultado.perfil.perfil == PerfilMedico.SENIOR
            assert "NUNCA pressione" in resultado.perfil.recomendacao_abordagem

            # Deve recomendar negociação
            assert resultado.objetivo.objetivo == ObjetivoConversa.NEGOCIAR

    @pytest.mark.asyncio
    async def test_cenario_recem_formado_interessado(self, orquestrador):
        """Cenário: recém-formado mostrando interesse."""
        with patch.object(
            orquestrador.buscador, "buscar", new_callable=AsyncMock
        ) as mock_buscar:
            mock_buscar.return_value = []

            resultado = await orquestrador.analisar_situacao(
                mensagem="Acabei a residência, quais vagas tem?",
                historico=[],
                dados_cliente={"anos_experiencia": 1},
                stage="respondeu",
            )

            # Não deve ter objeção
            assert resultado.objecao.tem_objecao is False

            # Deve detectar recém-formado
            assert resultado.perfil.perfil == PerfilMedico.RECEM_FORMADO

            # Deve recomendar qualificação
            assert resultado.objetivo.objetivo == ObjetivoConversa.QUALIFICAR

    @pytest.mark.asyncio
    async def test_cenario_medico_inativo_reativacao(self, orquestrador):
        """Cenário: médico inativo há mais de 7 dias."""
        with patch.object(
            orquestrador.buscador, "buscar", new_callable=AsyncMock
        ) as mock_buscar:
            mock_buscar.return_value = []

            resultado = await orquestrador.analisar_situacao(
                mensagem="Oi, lembrei de vocês",
                historico=[],
                dados_cliente=None,
                stage="inativo",
                dias_inativo=15,
            )

            # Deve recomendar reativação
            assert resultado.objetivo.objetivo == ObjetivoConversa.REATIVAR


class TestOrquestradorLatencia:
    """Testes de latência do orquestrador."""

    @pytest.fixture
    def orquestrador(self):
        return OrquestradorConhecimento()

    @pytest.mark.asyncio
    async def test_analise_rapida_latencia(self, orquestrador):
        """Análise rápida deve ser < 50ms."""
        import time

        inicio = time.time()
        await orquestrador.analisar_rapido("Não tenho interesse")
        duracao_ms = (time.time() - inicio) * 1000

        assert duracao_ms < 50, f"Análise rápida demorou {duracao_ms:.2f}ms (limite: 50ms)"

    @pytest.mark.asyncio
    async def test_detectores_sem_llm_latencia(self, orquestrador):
        """Detectores sem LLM devem ser < 10ms."""
        import time

        inicio = time.time()
        orquestrador.detector_objecao.detectar("O valor está baixo")
        orquestrador.detector_perfil.detectar_por_dados(anos_experiencia=10)
        orquestrador.detector_objetivo.detectar_por_stage("em_conversacao")
        duracao_ms = (time.time() - inicio) * 1000

        assert duracao_ms < 10, f"Detectores demoraram {duracao_ms:.2f}ms (limite: 10ms)"
