"""Testes para extrator de valores."""
import pytest

from app.services.grupos.extrator_v2.extrator_valores import (
    extrair_valores,
    obter_valor_para_dia,
    _normalizar_valor,
    _extrair_valores_linha,
    _detectar_grupo_dia,
    _parsear_linha_valor,
)
from app.services.grupos.extrator_v2.types import (
    GrupoDia, Periodo, DiaSemana, RegraValor, ValoresExtraidos
)


class TestNormalizarValor:
    """Testes para normalização de valor."""

    def test_valor_simples(self):
        assert _normalizar_valor("1800") == 1800

    def test_valor_com_ponto(self):
        assert _normalizar_valor("1.800") == 1800

    def test_valor_com_virgula(self):
        assert _normalizar_valor("1,800") == 1800

    def test_valor_com_centavos(self):
        assert _normalizar_valor("1.800,00") == 1800

    def test_valor_prefixo_rs(self):
        assert _normalizar_valor("R$ 1.800") == 1800

    def test_valor_fora_range_baixo(self):
        assert _normalizar_valor("50") is None

    def test_valor_fora_range_alto(self):
        assert _normalizar_valor("100000") is None


class TestExtrairValoresLinha:
    """Testes para extração de valores de linha."""

    def test_um_valor(self):
        valores = _extrair_valores_linha("R$ 1.800")
        assert valores == [1800]

    def test_multiplos_valores(self):
        valores = _extrair_valores_linha("Entre R$ 1.500 e R$ 2.000")
        assert 1500 in valores
        assert 2000 in valores

    def test_sem_valor(self):
        valores = _extrair_valores_linha("Bom dia")
        assert valores == []


class TestDetectarGrupoDia:
    """Testes para detecção de grupo de dias."""

    def test_seg_sex(self):
        assert _detectar_grupo_dia("Segunda a Sexta") == GrupoDia.SEG_SEX
        assert _detectar_grupo_dia("seg-sex") == GrupoDia.SEG_SEX
        assert _detectar_grupo_dia("Seg/Sex") == GrupoDia.SEG_SEX

    def test_sab_dom(self):
        assert _detectar_grupo_dia("Sábado e Domingo") == GrupoDia.SAB_DOM
        assert _detectar_grupo_dia("sab-dom") == GrupoDia.SAB_DOM
        assert _detectar_grupo_dia("fim de semana") == GrupoDia.SAB_DOM

    def test_sabado(self):
        assert _detectar_grupo_dia("Sábado") == GrupoDia.SAB

    def test_domingo(self):
        assert _detectar_grupo_dia("Domingo") == GrupoDia.DOM

    def test_feriado(self):
        assert _detectar_grupo_dia("Feriado") == GrupoDia.FERIADO

    def test_sem_grupo(self):
        assert _detectar_grupo_dia("Valor") is None


class TestParsearLinhaValor:
    """Testes para parsing de linha de valor."""

    def test_valor_com_grupo(self):
        regras = _parsear_linha_valor("Segunda a Sexta: R$ 1.700")

        assert len(regras) == 1
        assert regras[0].grupo_dia == GrupoDia.SEG_SEX
        assert regras[0].valor == 1700

    def test_valor_simples(self):
        regras = _parsear_linha_valor("R$ 1.800 PJ")

        assert len(regras) == 1
        assert regras[0].grupo_dia == GrupoDia.TODOS
        assert regras[0].valor == 1800

    def test_valor_com_periodo(self):
        regras = _parsear_linha_valor("Noturno: R$ 2.000")

        assert len(regras) == 1
        assert regras[0].periodo == Periodo.NOTURNO
        assert regras[0].valor == 2000


class TestExtrairValores:
    """Testes para extração completa de valores."""

    def test_valor_unico(self):
        linhas = ["💰 R$ 1.800"]
        valores = extrair_valores(linhas)

        assert valores.valor_unico == 1800

    def test_multiplas_regras(self):
        linhas = [
            "Segunda a Sexta: R$ 1.700",
            "Sábado e Domingo: R$ 1.800"
        ]
        valores = extrair_valores(linhas)

        assert valores.valor_unico is None
        assert len(valores.regras) == 2

    def test_lista_vazia(self):
        valores = extrair_valores([])
        assert valores.valor_unico is None
        assert valores.regras == []


class TestObterValorParaDia:
    """Testes para obtenção de valor por dia."""

    def test_valor_unico(self):
        valores = ValoresExtraidos(valor_unico=1800)

        assert obter_valor_para_dia(valores, DiaSemana.SEGUNDA) == 1800
        assert obter_valor_para_dia(valores, DiaSemana.SABADO) == 1800

    def test_seg_sex_vs_sab_dom(self):
        valores = ValoresExtraidos(regras=[
            RegraValor(grupo_dia=GrupoDia.SEG_SEX, valor=1700),
            RegraValor(grupo_dia=GrupoDia.SAB_DOM, valor=1800),
        ])

        assert obter_valor_para_dia(valores, DiaSemana.SEGUNDA) == 1700
        assert obter_valor_para_dia(valores, DiaSemana.TERCA) == 1700
        assert obter_valor_para_dia(valores, DiaSemana.QUARTA) == 1700
        assert obter_valor_para_dia(valores, DiaSemana.QUINTA) == 1700
        assert obter_valor_para_dia(valores, DiaSemana.SEXTA) == 1700
        assert obter_valor_para_dia(valores, DiaSemana.SABADO) == 1800
        assert obter_valor_para_dia(valores, DiaSemana.DOMINGO) == 1800

    def test_sabado_especifico(self):
        valores = ValoresExtraidos(regras=[
            RegraValor(grupo_dia=GrupoDia.SEG_SEX, valor=1700),
            RegraValor(grupo_dia=GrupoDia.SAB, valor=1800),
            RegraValor(grupo_dia=GrupoDia.DOM, valor=2000),
        ])

        assert obter_valor_para_dia(valores, DiaSemana.SEXTA) == 1700
        assert obter_valor_para_dia(valores, DiaSemana.SABADO) == 1800
        assert obter_valor_para_dia(valores, DiaSemana.DOMINGO) == 2000

    def test_com_periodo(self):
        valores = ValoresExtraidos(regras=[
            RegraValor(grupo_dia=GrupoDia.TODOS, periodo=Periodo.DIURNO, valor=1500),
            RegraValor(grupo_dia=GrupoDia.TODOS, periodo=Periodo.NOTURNO, valor=1800),
        ])

        assert obter_valor_para_dia(valores, DiaSemana.SEGUNDA, Periodo.DIURNO) == 1500
        assert obter_valor_para_dia(valores, DiaSemana.SEGUNDA, Periodo.NOTURNO) == 1800

    def test_fallback_todos(self):
        valores = ValoresExtraidos(regras=[
            RegraValor(grupo_dia=GrupoDia.TODOS, valor=1700),
        ])

        assert obter_valor_para_dia(valores, DiaSemana.SEGUNDA) == 1700
        assert obter_valor_para_dia(valores, DiaSemana.DOMINGO) == 1700


class TestCasosReais:
    """Testes com formatos reais."""

    def test_formato_emoji(self):
        linhas = [
            "💰 Valores:",
            "Segunda a Sexta: R$ 1.700",
            "Sábado e Domingo: R$ 1.800"
        ]
        valores = extrair_valores(linhas)

        assert len(valores.regras) == 2

        # Verificar associação
        assert obter_valor_para_dia(valores, DiaSemana.QUARTA) == 1700
        assert obter_valor_para_dia(valores, DiaSemana.DOMINGO) == 1800

    def test_formato_pipe(self):
        linhas = ["Seg-Sex: R$ 1.700 | Sab-Dom: R$ 1.800"]
        valores = extrair_valores(linhas)

        # Pode extrair apenas o primeiro ou ambos dependendo da implementação
        assert len(valores.regras) >= 1

    def test_formato_compacto(self):
        linhas = ["💰1.600"]
        valores = extrair_valores(linhas)

        assert valores.valor_unico == 1600 or valores.regras[0].valor == 1600
