"""
Testes para o sistema de variacoes de abertura.

Garante que Julia nao pareca robotica por repetir sempre a mesma abertura.
"""
import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock

from app.templates.aberturas import (
    SAUDACOES,
    APRESENTACOES,
    CONTEXTOS,
    GANCHOS,
    montar_abertura_completa,
    gerar_abertura_texto_unico,
    obter_saudacao_por_periodo,
    contar_variacoes,
)


class TestTemplatesAberturas:
    """Testes para os templates de abertura."""

    def test_tem_saudacoes_suficientes(self):
        """Deve ter pelo menos 15 saudacoes."""
        assert len(SAUDACOES) >= 15

    def test_tem_apresentacoes_suficientes(self):
        """Deve ter pelo menos 8 apresentacoes."""
        assert len(APRESENTACOES) >= 8

    def test_tem_contextos_suficientes(self):
        """Deve ter pelo menos 7 contextos."""
        assert len(CONTEXTOS) >= 7

    def test_tem_ganchos_suficientes(self):
        """Deve ter pelo menos 7 ganchos."""
        assert len(GANCHOS) >= 7

    def test_saudacoes_tem_formato_correto(self):
        """Saudacoes devem ter formato (id, texto, periodo)."""
        for saudacao in SAUDACOES:
            assert len(saudacao) == 3
            assert saudacao[0].startswith("s")  # ID comeca com 's'
            assert "{nome}" in saudacao[1]  # Tem placeholder de nome
            assert saudacao[2] in [None, "manha", "tarde", "noite"]

    def test_apresentacoes_tem_formato_correto(self):
        """Apresentacoes devem ter formato (id, texto)."""
        for apresentacao in APRESENTACOES:
            assert len(apresentacao) == 2
            assert apresentacao[0].startswith("a")  # ID comeca com 'a'
            assert "julia" in apresentacao[1].lower() or "revoluna" in apresentacao[1].lower()

    def test_contextos_tem_formato_correto(self):
        """Contextos devem ter formato (id, texto)."""
        for contexto in CONTEXTOS:
            assert len(contexto) == 2
            assert contexto[0].startswith("c")  # ID comeca com 'c'

    def test_ganchos_tem_formato_correto(self):
        """Ganchos devem ter formato (id, texto)."""
        for gancho in GANCHOS:
            assert len(gancho) == 2
            assert gancho[0].startswith("g")  # ID comeca com 'g'


class TestMontarAberturaCompleta:
    """Testes para montagem de abertura."""

    def test_monta_abertura_com_nome(self):
        """Deve montar abertura substituindo nome."""
        mensagens = montar_abertura_completa(
            nome="Carlos",
            saudacao_id="s1",
            apresentacao_id="a1",
            gancho_id="g1",
            incluir_contexto=False
        )

        assert len(mensagens) >= 3
        assert "Carlos" in mensagens[0]

    def test_monta_abertura_com_contexto(self):
        """Deve incluir contexto quando solicitado."""
        mensagens = montar_abertura_completa(
            nome="Ana",
            saudacao_id="s1",
            apresentacao_id="a1",
            contexto_id="c1",
            gancho_id="g1",
            incluir_contexto=True
        )

        assert len(mensagens) == 4

    def test_monta_abertura_sem_contexto(self):
        """Deve omitir contexto quando solicitado."""
        mensagens = montar_abertura_completa(
            nome="Pedro",
            saudacao_id="s1",
            apresentacao_id="a1",
            gancho_id="g1",
            incluir_contexto=False
        )

        assert len(mensagens) == 3

    def test_monta_abertura_aleatorio(self):
        """Deve montar abertura com selecao aleatoria."""
        mensagens = montar_abertura_completa(nome="Maria")

        assert len(mensagens) >= 3
        assert "Maria" in mensagens[0]

    def test_nao_tem_lista_ou_bullets(self):
        """Abertura nao deve ter formatacao proibida."""
        for _ in range(20):  # Testar varias vezes por ser aleatorio
            mensagens = montar_abertura_completa(nome="Lucas")
            texto = " ".join(mensagens)

            assert "-" not in texto or texto.count("-") == 0
            assert "*" not in texto
            assert "1." not in texto
            assert "2." not in texto


class TestGerarAberturaTextoUnico:
    """Testes para geracao de texto unico."""

    def test_gera_texto_com_quebras(self):
        """Deve gerar texto com quebras de linha."""
        texto = gerar_abertura_texto_unico(
            nome="Carlos",
            saudacao_id="s1",
            apresentacao_id="a1",
            gancho_id="g1"
        )

        assert "\n\n" in texto
        assert "Carlos" in texto


class TestObterSaudacaoPorPeriodo:
    """Testes para selecao de saudacao por periodo."""

    def test_filtra_por_manha(self):
        """Deve filtrar saudacoes de manha."""
        saudacoes = obter_saudacao_por_periodo("manha")

        # Deve incluir saudacoes de manha e genericas
        for s in saudacoes:
            assert s[2] in [None, "manha"]

    def test_filtra_por_tarde(self):
        """Deve filtrar saudacoes de tarde."""
        saudacoes = obter_saudacao_por_periodo("tarde")

        for s in saudacoes:
            assert s[2] in [None, "tarde"]

    def test_filtra_por_noite(self):
        """Deve filtrar saudacoes de noite."""
        saudacoes = obter_saudacao_por_periodo("noite")

        for s in saudacoes:
            assert s[2] in [None, "noite"]

    def test_retorna_todas_sem_filtro(self):
        """Deve retornar todas se periodo None."""
        saudacoes = obter_saudacao_por_periodo(None)
        assert saudacoes == SAUDACOES


class TestContarVariacoes:
    """Testes para contagem de variacoes."""

    def test_conta_todas_variacoes(self):
        """Deve contar variacoes corretamente."""
        stats = contar_variacoes()

        assert stats["saudacoes"] >= 15
        assert stats["apresentacoes"] >= 8
        assert stats["contextos"] >= 7
        assert stats["ganchos"] >= 7
        assert stats["combinacoes_possiveis"] > 10000  # Muitas combinacoes


class TestServicoAbertura:
    """Testes para o servico de abertura."""

    @pytest.mark.asyncio
    async def test_obter_abertura_retorna_lista(self):
        """Deve retornar lista de mensagens."""
        from app.services.abertura import obter_abertura

        with patch('app.services.abertura._get_ultima_abertura', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            with patch('app.services.abertura._salvar_abertura_usada', new_callable=AsyncMock):
                mensagens = await obter_abertura(
                    cliente_id="test-123",
                    nome="Carlos"
                )

                assert isinstance(mensagens, list)
                assert len(mensagens) >= 3
                assert "Carlos" in mensagens[0]

    @pytest.mark.asyncio
    async def test_evita_repeticao(self):
        """Deve evitar repetir mesma abertura."""
        from app.services.abertura import _selecionar_sem_repetir

        # Simular ultima abertura usada
        opcoes = [("o1", "Opcao 1"), ("o2", "Opcao 2"), ("o3", "Opcao 3")]

        # Com repeticao a evitar
        resultado = _selecionar_sem_repetir(opcoes, "o1")
        assert resultado[0] != "o1"

        # Sem repeticao
        resultado = _selecionar_sem_repetir(opcoes, None)
        assert resultado in opcoes

    @pytest.mark.asyncio
    async def test_seleciona_saudacao_por_horario(self):
        """Deve selecionar saudacao apropriada ao horario."""
        from app.services.abertura import _selecionar_saudacao

        # Manha (8h)
        hora_manha = datetime(2025, 12, 10, 8, 0)
        saudacao = _selecionar_saudacao(hora_manha)
        assert saudacao[2] in [None, "manha"]

        # Tarde (14h)
        hora_tarde = datetime(2025, 12, 10, 14, 0)
        saudacao = _selecionar_saudacao(hora_tarde)
        assert saudacao[2] in [None, "tarde"]

        # Noite (20h)
        hora_noite = datetime(2025, 12, 10, 20, 0)
        saudacao = _selecionar_saudacao(hora_noite)
        assert saudacao[2] in [None, "noite"]


class TestVariacaoReal:
    """Testes de variacao com cenarios reais."""

    def test_cinco_medicos_diferentes(self):
        """Deve gerar aberturas diferentes para varios medicos."""
        nomes = ["Carlos", "Ana", "Pedro", "Maria", "Lucas"]
        aberturas = []

        for nome in nomes:
            abertura = gerar_abertura_texto_unico(nome)
            aberturas.append(abertura)

        # Pelo menos algumas devem ser diferentes
        # (e muito improvavel que todas sejam iguais)
        aberturas_unicas = set(aberturas)
        assert len(aberturas_unicas) >= 3  # Pelo menos 3 diferentes de 5

    def test_nao_parece_robotico(self):
        """Aberturas nao devem parecer roboticas."""
        for _ in range(10):
            mensagens = montar_abertura_completa(nome="Dr Carlos")
            texto = " ".join(mensagens)

            # Nao deve ter marcadores de lista
            assert not texto.startswith("-")
            assert "•" not in texto

            # Nao deve ser muito formal
            assert "Prezado" not in texto
            assert "Senhor" not in texto
            assert "Atenciosamente" not in texto

            # Deve mencionar Julia ou Revoluna
            assert "julia" in texto.lower() or "revoluna" in texto.lower()
