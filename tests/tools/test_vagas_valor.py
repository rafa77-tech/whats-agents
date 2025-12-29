"""
Testes para formatacao de valor nas tools de vagas.

Sprint 19 - Valor Flexivel em Vagas - E04
"""

import pytest
from app.tools.vagas import (
    _formatar_valor_display,
    _construir_instrucao_confirmacao,
)


class TestFormatarValorDisplay:
    """Testes para formatacao de valor em resposta de tools."""

    def test_valor_fixo(self):
        """Valor fixo deve formatar como R$ X.XXX."""
        vaga = {"valor": 1800, "valor_tipo": "fixo"}
        assert _formatar_valor_display(vaga) == "R$ 1.800"

    def test_valor_faixa_completa(self):
        """Faixa com min e max deve mostrar intervalo."""
        vaga = {"valor_minimo": 1500, "valor_maximo": 2000, "valor_tipo": "faixa"}
        assert _formatar_valor_display(vaga) == "R$ 1.500 a R$ 2.000"

    def test_valor_faixa_so_minimo(self):
        """Faixa so com minimo deve mostrar 'a partir de'."""
        vaga = {"valor_minimo": 1500, "valor_tipo": "faixa"}
        assert _formatar_valor_display(vaga) == "a partir de R$ 1.500"

    def test_valor_faixa_so_maximo(self):
        """Faixa so com maximo deve mostrar 'ate'."""
        vaga = {"valor_maximo": 2000, "valor_tipo": "faixa"}
        assert _formatar_valor_display(vaga) == "ate R$ 2.000"

    def test_valor_a_combinar(self):
        """A combinar deve mostrar texto."""
        vaga = {"valor_tipo": "a_combinar"}
        assert _formatar_valor_display(vaga) == "a combinar"

    def test_valor_sem_tipo_com_valor(self):
        """Fallback: valor sem tipo deve formatar normalmente."""
        vaga = {"valor": 1500}
        assert _formatar_valor_display(vaga) == "R$ 1.500"

    def test_valor_sem_nada(self):
        """Sem valor deve retornar 'nao informado'."""
        vaga = {}
        assert _formatar_valor_display(vaga) == "nao informado"


class TestConstruirInstrucaoConfirmacao:
    """Testes para construcao de instrucao de confirmacao."""

    def test_valor_fixo(self):
        """Valor fixo deve mencionar o valor."""
        vaga = {"valor": 1800, "valor_tipo": "fixo"}
        hospital = {"endereco_formatado": "Rua X, 123"}

        instrucao = _construir_instrucao_confirmacao(vaga, hospital)

        assert "R$ 1800" in instrucao
        assert "Rua X, 123" in instrucao

    def test_valor_a_combinar(self):
        """Valor a combinar deve pedir expectativa."""
        vaga = {"valor_tipo": "a_combinar"}
        hospital = {"endereco_formatado": "Rua Y, 456"}

        instrucao = _construir_instrucao_confirmacao(vaga, hospital)

        assert "combinar" in instrucao.lower() or "combinado" in instrucao.lower()
        assert "expectativa" in instrucao.lower()

    def test_valor_faixa(self):
        """Valor em faixa deve mencionar faixa acordada."""
        vaga = {"valor_tipo": "faixa", "valor_minimo": 1500, "valor_maximo": 2000}
        hospital = {"endereco_formatado": "Rua Z, 789"}

        instrucao = _construir_instrucao_confirmacao(vaga, hospital)

        assert "faixa" in instrucao.lower()

    def test_sem_endereco(self):
        """Sem endereco deve usar fallback."""
        vaga = {"valor": 1500, "valor_tipo": "fixo"}
        hospital = {}

        instrucao = _construir_instrucao_confirmacao(vaga, hospital)

        assert "endereco nao disponivel" in instrucao
