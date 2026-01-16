"""
Testes para prompts específicos por tipo de campanha.

Sprint 32 E01 - Prompts por Tipo de Campanha.
"""
import pytest
from unittest.mock import MagicMock, patch

from app.prompts.loader import (
    buscar_prompt_por_tipo_campanha,
    TIPOS_CAMPANHA_VALIDOS,
)


class TestTiposCampanhaValidos:
    """Testes para constante TIPOS_CAMPANHA_VALIDOS."""

    def test_cinco_tipos_definidos(self):
        """Deve ter exatamente 5 tipos de campanha."""
        assert len(TIPOS_CAMPANHA_VALIDOS) == 5

    def test_tipos_esperados(self):
        """Deve conter os 5 tipos esperados."""
        tipos_esperados = {"discovery", "oferta", "followup", "feedback", "reativacao"}
        assert TIPOS_CAMPANHA_VALIDOS == tipos_esperados


class TestBuscarPromptPorTipoCampanha:
    """Testes para buscar_prompt_por_tipo_campanha."""

    @pytest.mark.asyncio
    async def test_tipo_invalido_raises_error(self):
        """Deve levantar erro para tipo inválido."""
        with pytest.raises(ValueError) as exc:
            await buscar_prompt_por_tipo_campanha("invalido")

        assert "Tipo de campanha inválido" in str(exc.value)
        assert "invalido" in str(exc.value)

    @pytest.mark.asyncio
    async def test_buscar_prompt_discovery(self):
        """Deve retornar prompt de discovery com regras corretas."""
        mock_conteudo = """Você é Júlia, escalista da Revoluna.
        OBJETIVO DESTA CONVERSA: Conhecer o médico.
        REGRAS ABSOLUTAS:
        1. NÃO mencione vagas, oportunidades ou plantões disponíveis
        2. NÃO fale de valores"""

        with patch("app.prompts.loader.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"conteudo": mock_conteudo}]
            )

            prompt = await buscar_prompt_por_tipo_campanha("discovery")

            assert prompt is not None
            assert "NÃO mencione vagas" in prompt
            assert "Conhecer o médico" in prompt

    @pytest.mark.asyncio
    async def test_buscar_prompt_oferta(self):
        """Deve retornar prompt de oferta com regras corretas."""
        mock_conteudo = """Você é Júlia, escalista da Revoluna.
        OBJETIVO: Apresentar vagas disponíveis.
        ESCOPO DA OFERTA: {escopo_vagas}
        REGRAS:
        1. ANTES de mencionar qualquer vaga, chame buscar_vagas()"""

        with patch("app.prompts.loader.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"conteudo": mock_conteudo}]
            )

            prompt = await buscar_prompt_por_tipo_campanha("oferta")

            assert prompt is not None
            assert "buscar_vagas()" in prompt
            assert "escopo" in prompt.lower()

    @pytest.mark.asyncio
    async def test_buscar_prompt_followup(self):
        """Deve retornar prompt de followup com regras corretas."""
        mock_conteudo = """Você é Júlia, escalista da Revoluna.
        OBJETIVO: Manter relacionamento ativo.
        REGRAS:
        1. NÃO oferte proativamente"""

        with patch("app.prompts.loader.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"conteudo": mock_conteudo}]
            )

            prompt = await buscar_prompt_por_tipo_campanha("followup")

            assert prompt is not None
            assert "relacionamento" in prompt.lower()
            assert "NÃO oferte proativamente" in prompt

    @pytest.mark.asyncio
    async def test_buscar_prompt_feedback(self):
        """Deve retornar prompt de feedback com regras corretas."""
        mock_conteudo = """Você é Júlia, escalista da Revoluna.
        OBJETIVO: Coletar feedback sobre plantão realizado.
        CONTEXTO: {plantao_realizado}"""

        with patch("app.prompts.loader.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"conteudo": mock_conteudo}]
            )

            prompt = await buscar_prompt_por_tipo_campanha("feedback")

            assert prompt is not None
            assert "feedback" in prompt.lower()
            assert "plantão" in prompt.lower()

    @pytest.mark.asyncio
    async def test_buscar_prompt_reativacao(self):
        """Deve retornar prompt de reativação com regras corretas."""
        mock_conteudo = """Você é Júlia, escalista da Revoluna.
        OBJETIVO: Retomar contato com médico inativo.
        REGRAS ABSOLUTAS:
        1. NÃO oferte de cara"""

        with patch("app.prompts.loader.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"conteudo": mock_conteudo}]
            )

            prompt = await buscar_prompt_por_tipo_campanha("reativacao")

            assert prompt is not None
            assert "inativo" in prompt.lower()
            assert "NÃO oferte de cara" in prompt

    @pytest.mark.asyncio
    async def test_prompt_nao_encontrado_retorna_none(self):
        """Deve retornar None se prompt não encontrado."""
        with patch("app.prompts.loader.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[]
            )

            prompt = await buscar_prompt_por_tipo_campanha("discovery")

            assert prompt is None

    @pytest.mark.asyncio
    async def test_erro_banco_retorna_none(self):
        """Deve retornar None e logar erro se banco falhar."""
        with patch("app.prompts.loader.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.side_effect = Exception(
                "Erro de conexão"
            )

            prompt = await buscar_prompt_por_tipo_campanha("discovery")

            assert prompt is None


class TestDiscoveryNaoMencionaVagas:
    """Testes específicos para garantir que discovery não menciona vagas."""

    @pytest.mark.asyncio
    async def test_discovery_nao_tem_palavras_de_oferta(self):
        """Discovery NÃO deve ter palavras que induzam oferta."""
        # Prompt real de discovery
        mock_conteudo = """Você é Júlia, escalista da Revoluna.
        OBJETIVO DESTA CONVERSA: Conhecer o médico.
        REGRAS ABSOLUTAS:
        1. NÃO mencione vagas, oportunidades ou plantões disponíveis
        2. NÃO fale de valores
        3. NÃO diga "tenho uma vaga" ou "surgiu uma oportunidade"
        4. Foque em PERGUNTAS sobre o médico"""

        with patch("app.prompts.loader.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"conteudo": mock_conteudo}]
            )

            prompt = await buscar_prompt_por_tipo_campanha("discovery")

            # Palavras que NÃO devem aparecer como instrução positiva
            # (podem aparecer em "NÃO FAZER" como exemplo negativo)
            assert prompt is not None

            # Verificar que as regras proíbem oferta
            assert "NÃO mencione vagas" in prompt
            assert "NÃO fale de valores" in prompt


class TestOfertaObrigaBuscarVagas:
    """Testes para garantir que oferta exige buscar_vagas()."""

    @pytest.mark.asyncio
    async def test_oferta_menciona_buscar_vagas(self):
        """Oferta DEVE mencionar a obrigatoriedade de chamar buscar_vagas()."""
        mock_conteudo = """Você é Júlia, escalista da Revoluna.
        OBJETIVO DESTA CONVERSA: Apresentar vagas disponíveis.
        REGRAS:
        1. ANTES de mencionar qualquer vaga, chame buscar_vagas() com o escopo definido
        2. Só apresente vagas que EXISTEM no resultado da busca
        O QUE NÃO FAZER:
        ❌ Dizer "tenho vaga" ANTES de chamar buscar_vagas()"""

        with patch("app.prompts.loader.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"conteudo": mock_conteudo}]
            )

            prompt = await buscar_prompt_por_tipo_campanha("oferta")

            assert prompt is not None
            assert "buscar_vagas()" in prompt
            assert "ANTES de mencionar" in prompt
