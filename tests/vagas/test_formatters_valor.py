"""
Testes para formatacao de valor em vagas.

Sprint 19 - Valor Flexivel em Vagas - E04
"""

import pytest
from app.services.vagas.formatters import (
    formatar_para_mensagem,
    formatar_valor_para_mensagem,
    formatar_para_contexto,
    _formatar_valor_contexto,
)


class TestFormatarValorParaMensagem:
    """Testes para formatacao de valor em mensagens."""

    def test_valor_fixo(self):
        """Valor fixo deve formatar como R$ X.XXX."""
        vaga = {"valor": 1800, "valor_tipo": "fixo"}
        assert formatar_valor_para_mensagem(vaga) == "R$ 1.800"

    def test_valor_faixa_completa(self):
        """Faixa com min e max deve mostrar intervalo."""
        vaga = {"valor_minimo": 1500, "valor_maximo": 2000, "valor_tipo": "faixa"}
        assert formatar_valor_para_mensagem(vaga) == "R$ 1.500 a 2.000"

    def test_valor_faixa_so_minimo(self):
        """Faixa so com minimo deve mostrar 'a partir de'."""
        vaga = {"valor_minimo": 1500, "valor_tipo": "faixa"}
        assert formatar_valor_para_mensagem(vaga) == "a partir de R$ 1.500"

    def test_valor_faixa_so_maximo(self):
        """Faixa so com maximo deve mostrar 'ate'."""
        vaga = {"valor_maximo": 2000, "valor_tipo": "faixa"}
        assert formatar_valor_para_mensagem(vaga) == "ate R$ 2.000"

    def test_valor_a_combinar(self):
        """A combinar deve mostrar texto."""
        vaga = {"valor_tipo": "a_combinar"}
        assert formatar_valor_para_mensagem(vaga) == "valor a combinar"

    def test_valor_sem_tipo_com_valor(self):
        """Fallback: valor sem tipo deve formatar normalmente."""
        vaga = {"valor": 1500}
        assert formatar_valor_para_mensagem(vaga) == "R$ 1.500"

    def test_valor_sem_tipo_sem_valor(self):
        """Sem valor e sem tipo deve retornar vazio."""
        vaga = {}
        assert formatar_valor_para_mensagem(vaga) == ""


class TestFormatarParaMensagem:
    """Testes para formatacao completa de vaga."""

    def test_vaga_completa_valor_fixo(self):
        """Vaga com valor fixo deve mostrar R$."""
        vaga = {
            "hospitais": {"nome": "Hospital ABC"},
            "data": "2025-01-15",
            "periodos": {"nome": "Noturno"},
            "setores": {"nome": "UTI"},
            "valor": 2000,
            "valor_tipo": "fixo",
        }
        resultado = formatar_para_mensagem(vaga)
        assert "Hospital ABC" in resultado
        assert "15/01" in resultado
        assert "R$ 2.000" in resultado

    def test_vaga_completa_valor_a_combinar(self):
        """Vaga a combinar deve mostrar texto."""
        vaga = {
            "hospitais": {"nome": "Hospital ABC"},
            "data": "2025-01-15",
            "periodos": {"nome": "Noturno"},
            "valor_tipo": "a_combinar",
        }
        resultado = formatar_para_mensagem(vaga)
        assert "Hospital ABC" in resultado
        assert "valor a combinar" in resultado

    def test_vaga_com_faixa(self):
        """Vaga com faixa deve mostrar intervalo."""
        vaga = {
            "hospitais": {"nome": "Hospital XYZ"},
            "data": "2025-01-20",
            "periodos": {"nome": "Diurno"},
            "valor_tipo": "faixa",
            "valor_minimo": 1500,
            "valor_maximo": 2000,
        }
        resultado = formatar_para_mensagem(vaga)
        assert "Hospital XYZ" in resultado
        assert "R$ 1.500 a 2.000" in resultado


class TestFormatarValorContexto:
    """Testes para formatacao de valor em contexto LLM."""

    def test_valor_fixo_contexto(self):
        """Valor fixo deve indicar (fixo)."""
        vaga = {"valor": 1800, "valor_tipo": "fixo"}
        resultado = _formatar_valor_contexto(vaga)
        assert "R$ 1800" in resultado
        assert "(fixo)" in resultado

    def test_valor_faixa_contexto(self):
        """Faixa deve indicar (faixa)."""
        vaga = {"valor_minimo": 1500, "valor_maximo": 2000, "valor_tipo": "faixa"}
        resultado = _formatar_valor_contexto(vaga)
        assert "(faixa)" in resultado

    def test_valor_a_combinar_contexto(self):
        """A combinar deve ter instrucao para LLM."""
        vaga = {"valor_tipo": "a_combinar"}
        resultado = _formatar_valor_contexto(vaga)
        assert "A COMBINAR" in resultado
        assert "informar medico" in resultado


class TestFormatarParaContexto:
    """Testes para formatacao de contexto completo."""

    def test_contexto_valor_a_combinar(self):
        """Contexto com vaga a combinar deve ter instrucao."""
        vagas = [{
            "hospitais": {"nome": "Hospital ABC", "cidade": "SP"},
            "periodos": {"nome": "Noturno", "hora_inicio": "19:00", "hora_fim": "07:00"},
            "setores": {"nome": "UTI"},
            "data": "2025-01-15",
            "valor_tipo": "a_combinar",
            "id": "123",
        }]
        resultado = formatar_para_contexto(vagas)
        assert "A COMBINAR" in resultado
        assert "informar medico" in resultado

    def test_contexto_sem_vagas(self):
        """Sem vagas deve retornar mensagem padrao."""
        resultado = formatar_para_contexto([])
        assert "Não há vagas disponíveis" in resultado
