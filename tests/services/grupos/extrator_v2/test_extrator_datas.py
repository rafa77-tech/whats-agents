"""Testes para extrator de datas e períodos."""
import pytest
from datetime import date, time

from app.services.grupos.extrator_v2.extrator_datas import (
    extrair_datas_periodos,
    extrair_data_periodo,
    _parsear_data_barra,
    _parsear_horario,
    _extrair_periodo,
    _calcular_dia_semana,
)
from app.services.grupos.extrator_v2.types import DiaSemana, Periodo


# Data de referência para testes
HOJE = date(2026, 1, 25)  # Sábado


class TestParsearDataBarra:
    """Testes para parsing de data com barra."""

    def test_data_dia_mes(self):
        """Data dd/mm."""
        data = _parsear_data_barra("26/01", HOJE)
        assert data == date(2026, 1, 26)

    def test_data_dia_mes_ano_curto(self):
        """Data dd/mm/yy."""
        data = _parsear_data_barra("26/01/26", HOJE)
        assert data == date(2026, 1, 26)

    def test_data_dia_mes_ano_longo(self):
        """Data dd/mm/yyyy."""
        data = _parsear_data_barra("26/01/2026", HOJE)
        assert data == date(2026, 1, 26)

    def test_data_com_ponto(self):
        """Data com ponto como separador."""
        data = _parsear_data_barra("26.01.2026", HOJE)
        assert data == date(2026, 1, 26)

    def test_data_com_hifen(self):
        """Data com hífen como separador."""
        data = _parsear_data_barra("26-01-2026", HOJE)
        assert data == date(2026, 1, 26)

    def test_data_passada_vai_proximo_ano(self):
        """Data que já passou este ano vai para próximo."""
        # Estamos em 25/01/2026, então 24/01 seria 2027
        data = _parsear_data_barra("24/01", HOJE)
        assert data == date(2027, 1, 24)

    def test_data_invalida(self):
        """Data inválida retorna None."""
        data = _parsear_data_barra("32/01/2026", HOJE)
        assert data is None


class TestParsearHorario:
    """Testes para parsing de horário."""

    def test_horario_h(self):
        """Formato 7h-13h."""
        ini, fim = _parsear_horario("7h-13h")
        assert ini == time(7, 0)
        assert fim == time(13, 0)

    def test_horario_dois_pontos(self):
        """Formato 07:00-13:00."""
        ini, fim = _parsear_horario("07:00-13:00")
        assert ini == time(7, 0)
        assert fim == time(13, 0)

    def test_horario_com_as(self):
        """Formato 7 às 13."""
        ini, fim = _parsear_horario("7 às 13")
        assert ini == time(7, 0)
        assert fim == time(13, 0)

    def test_horario_noturno(self):
        """Horário noturno 19-7."""
        ini, fim = _parsear_horario("19h-7h")
        assert ini == time(19, 0)
        assert fim == time(7, 0)

    def test_sem_horario(self):
        """Texto sem horário."""
        ini, fim = _parsear_horario("Segunda manhã")
        assert ini is None
        assert fim is None


class TestExtrairPeriodo:
    """Testes para extração de período por keyword."""

    def test_periodo_manha(self):
        assert _extrair_periodo("manhã") == Periodo.MANHA
        assert _extrair_periodo("Manhã 7-13h") == Periodo.MANHA

    def test_periodo_tarde(self):
        assert _extrair_periodo("tarde") == Periodo.TARDE
        assert _extrair_periodo("Tarde 13-19h") == Periodo.TARDE

    def test_periodo_noite(self):
        assert _extrair_periodo("noite") == Periodo.NOITE
        assert _extrair_periodo("noturno") == Periodo.NOTURNO

    def test_periodo_diurno(self):
        assert _extrair_periodo("SD") == Periodo.DIURNO
        assert _extrair_periodo("diurno") == Periodo.DIURNO

    def test_periodo_noturno_sn(self):
        assert _extrair_periodo("SN") == Periodo.NOTURNO

    def test_periodo_cinderela(self):
        assert _extrair_periodo("cinderela") == Periodo.CINDERELA


class TestCalcularDiaSemana:
    """Testes para cálculo de dia da semana."""

    def test_segunda(self):
        assert _calcular_dia_semana(date(2026, 1, 26)) == DiaSemana.SEGUNDA

    def test_terca(self):
        assert _calcular_dia_semana(date(2026, 1, 27)) == DiaSemana.TERCA

    def test_sabado(self):
        assert _calcular_dia_semana(date(2026, 1, 31)) == DiaSemana.SABADO

    def test_domingo(self):
        assert _calcular_dia_semana(date(2026, 2, 1)) == DiaSemana.DOMINGO


class TestExtrairDataPeriodo:
    """Testes para extração completa."""

    def test_linha_completa(self):
        """Linha com todos os dados."""
        resultado = extrair_data_periodo(
            "🗓 26/01 - Segunda - Manhã 7-13h",
            data_referencia=HOJE
        )

        assert resultado is not None
        assert resultado.data == date(2026, 1, 26)
        assert resultado.dia_semana == DiaSemana.SEGUNDA
        assert resultado.periodo == Periodo.MANHA
        assert resultado.hora_inicio == time(7, 0)
        assert resultado.hora_fim == time(13, 0)

    def test_linha_sem_horario(self):
        """Linha sem horário explícito."""
        resultado = extrair_data_periodo(
            "26/01 Segunda Manhã",
            data_referencia=HOJE
        )

        assert resultado is not None
        assert resultado.data == date(2026, 1, 26)
        assert resultado.periodo == Periodo.MANHA
        assert resultado.hora_inicio is None

    def test_linha_so_data(self):
        """Linha só com data."""
        resultado = extrair_data_periodo(
            "26/01",
            data_referencia=HOJE
        )

        assert resultado is not None
        assert resultado.data == date(2026, 1, 26)
        # Período default

    def test_linha_vazia(self):
        """Linha vazia retorna None."""
        resultado = extrair_data_periodo("", data_referencia=HOJE)
        assert resultado is None


class TestExtrairDatasPeriodos:
    """Testes para extração de múltiplas datas."""

    def test_multiplas_datas(self):
        """Extrai múltiplas datas."""
        linhas = [
            "🗓 26/01 - Segunda - Manhã 7-13h",
            "🗓 27/01 - Terça - Tarde 13-19h",
            "🗓 28/01 - Quarta - Noite 19-7h",
        ]

        resultados = extrair_datas_periodos(linhas, data_referencia=HOJE)

        assert len(resultados) == 3
        assert resultados[0].periodo == Periodo.MANHA
        assert resultados[1].periodo == Periodo.TARDE
        assert resultados[2].periodo == Periodo.NOITE

    def test_lista_vazia(self):
        """Lista vazia retorna lista vazia."""
        resultados = extrair_datas_periodos([], data_referencia=HOJE)
        assert resultados == []

    def test_linhas_invalidas_ignoradas(self):
        """Linhas sem data são ignoradas."""
        linhas = [
            "Bom dia",
            "🗓 26/01 - Segunda",
            "Interessados falar comigo",
        ]

        resultados = extrair_datas_periodos(linhas, data_referencia=HOJE)
        assert len(resultados) == 1


class TestCasosReais:
    """Testes com formatos reais."""

    def test_formato_completo(self):
        """Formato mais comum em grupos."""
        linhas = [
            "📅 27/01 SEGUNDA",
            "⏰ 19 as 07",
        ]

        # Só a primeira linha tem data
        resultados = extrair_datas_periodos(linhas, data_referencia=HOJE)
        assert len(resultados) >= 1

    def test_formato_compacto(self):
        """Formato compacto."""
        linha = "26/01 dom diurno 7-19h"
        resultado = extrair_data_periodo(linha, data_referencia=HOJE)

        assert resultado is not None
        assert resultado.periodo == Periodo.DIURNO

    def test_formato_sd_sn(self):
        """Formato SD/SN."""
        linha1 = "26/01 - SD"
        linha2 = "27/01 - SN"

        r1 = extrair_data_periodo(linha1, data_referencia=HOJE)
        r2 = extrair_data_periodo(linha2, data_referencia=HOJE)

        assert r1.periodo == Periodo.DIURNO
        assert r2.periodo == Periodo.NOTURNO
