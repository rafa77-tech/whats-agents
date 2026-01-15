"""
Testes do módulo de filtros de vagas.

Sprint 31 - S31.E5.5
"""
import pytest
from datetime import datetime

from app.services.vagas.filtros import (
    filtrar_por_periodo,
    filtrar_por_dias_semana,
    aplicar_filtros,
    MAPEAMENTO_PERIODOS,
    DIAS_SEMANA_MAP,
)


class TestFiltrarPorPeriodo:
    """Testes da função filtrar_por_periodo."""

    def test_filtrar_diurno(self):
        """Deve filtrar vagas diurnas."""
        vagas = [
            {"id": "1", "periodos": {"nome": "Diurno"}},
            {"id": "2", "periodos": {"nome": "Noturno"}},
            {"id": "3", "periodos": {"nome": "Dia"}},  # "dia" está no mapeamento
        ]

        resultado, total_antes = filtrar_por_periodo(vagas, "diurno")

        assert total_antes == 3
        assert len(resultado) == 2
        assert resultado[0]["id"] == "1"
        assert resultado[1]["id"] == "3"

    def test_filtrar_noturno(self):
        """Deve filtrar vagas noturnas."""
        vagas = [
            {"id": "1", "periodos": {"nome": "Diurno"}},
            {"id": "2", "periodos": {"nome": "Noturno"}},
            {"id": "3", "periodos": {"nome": "Cinderela"}},
        ]

        resultado, total_antes = filtrar_por_periodo(vagas, "noturno")

        assert total_antes == 3
        assert len(resultado) == 2
        assert resultado[0]["id"] == "2"
        assert resultado[1]["id"] == "3"

    def test_filtrar_12h(self):
        """Deve filtrar vagas de 12 horas."""
        vagas = [
            {"id": "1", "periodos": {"nome": "12h"}},
            {"id": "2", "periodos": {"nome": "12 horas"}},
            {"id": "3", "periodos": {"nome": "24h"}},
        ]

        resultado, total_antes = filtrar_por_periodo(vagas, "12h")

        assert len(resultado) == 2
        assert resultado[0]["id"] == "1"
        assert resultado[1]["id"] == "2"

    def test_filtrar_24h(self):
        """Deve filtrar vagas de 24 horas."""
        vagas = [
            {"id": "1", "periodos": {"nome": "24h"}},
            {"id": "2", "periodos": {"nome": "24 horas"}},
            {"id": "3", "periodos": {"nome": "12h"}},
        ]

        resultado, total_antes = filtrar_por_periodo(vagas, "24h")

        assert len(resultado) == 2

    def test_vagas_vazia(self):
        """Deve retornar lista vazia se não há vagas."""
        resultado, total_antes = filtrar_por_periodo([], "diurno")

        assert total_antes == 0
        assert resultado == []

    def test_periodo_none(self):
        """Deve lidar com período None em vagas."""
        vagas = [
            {"id": "1", "periodos": None},
            {"id": "2", "periodos": {"nome": "Diurno"}},
        ]

        resultado, total_antes = filtrar_por_periodo(vagas, "diurno")

        assert len(resultado) == 1
        assert resultado[0]["id"] == "2"

    def test_case_insensitive(self):
        """Deve ignorar case no filtro."""
        vagas = [
            {"id": "1", "periodos": {"nome": "DIURNO"}},
            {"id": "2", "periodos": {"nome": "diurno"}},
        ]

        resultado, total_antes = filtrar_por_periodo(vagas, "DIURNO")

        assert len(resultado) == 2


class TestFiltrarPorDiasSemana:
    """Testes da função filtrar_por_dias_semana."""

    def test_filtrar_segunda(self):
        """Deve filtrar vagas de segunda-feira."""
        # 2025-01-06 é segunda-feira
        vagas = [
            {"id": "1", "data": "2025-01-06"},  # Segunda
            {"id": "2", "data": "2025-01-07"},  # Terça
            {"id": "3", "data": "2025-01-13"},  # Segunda
        ]

        resultado, total_antes = filtrar_por_dias_semana(vagas, ["segunda"])

        assert total_antes == 3
        assert len(resultado) == 2
        assert resultado[0]["id"] == "1"
        assert resultado[1]["id"] == "3"

    def test_filtrar_multiplos_dias(self):
        """Deve filtrar múltiplos dias."""
        vagas = [
            {"id": "1", "data": "2025-01-06"},  # Segunda
            {"id": "2", "data": "2025-01-07"},  # Terça
            {"id": "3", "data": "2025-01-08"},  # Quarta
        ]

        resultado, total_antes = filtrar_por_dias_semana(vagas, ["segunda", "quarta"])

        assert len(resultado) == 2
        assert resultado[0]["id"] == "1"
        assert resultado[1]["id"] == "3"

    def test_abreviacoes(self):
        """Deve aceitar abreviações de dias."""
        vagas = [
            {"id": "1", "data": "2025-01-06"},  # Segunda
            {"id": "2", "data": "2025-01-07"},  # Terça
        ]

        resultado, total_antes = filtrar_por_dias_semana(vagas, ["seg"])

        assert len(resultado) == 1
        assert resultado[0]["id"] == "1"

    def test_sabado_domingo(self):
        """Deve filtrar fins de semana."""
        vagas = [
            {"id": "1", "data": "2025-01-11"},  # Sábado
            {"id": "2", "data": "2025-01-12"},  # Domingo
            {"id": "3", "data": "2025-01-13"},  # Segunda
        ]

        resultado, total_antes = filtrar_por_dias_semana(vagas, ["sabado", "domingo"])

        assert len(resultado) == 2

    def test_vaga_sem_data(self):
        """Deve ignorar vagas sem data."""
        vagas = [
            {"id": "1", "data": "2025-01-06"},
            {"id": "2", "data": None},
            {"id": "3"},  # Sem campo data
        ]

        resultado, total_antes = filtrar_por_dias_semana(vagas, ["segunda"])

        assert total_antes == 3
        assert len(resultado) == 1

    def test_data_invalida(self):
        """Deve ignorar datas inválidas."""
        vagas = [
            {"id": "1", "data": "2025-01-06"},
            {"id": "2", "data": "invalid-date"},
        ]

        resultado, total_antes = filtrar_por_dias_semana(vagas, ["segunda"])

        assert len(resultado) == 1

    def test_dias_vazios(self):
        """Deve retornar todas as vagas se dias vazios."""
        vagas = [
            {"id": "1", "data": "2025-01-06"},
            {"id": "2", "data": "2025-01-07"},
        ]

        resultado, total_antes = filtrar_por_dias_semana(vagas, [])

        assert len(resultado) == 2

    def test_remove_feira_suffix(self):
        """Deve remover sufixo -feira."""
        vagas = [
            {"id": "1", "data": "2025-01-06"},  # Segunda
        ]

        resultado, total_antes = filtrar_por_dias_semana(vagas, ["segunda-feira"])

        assert len(resultado) == 1


class TestAplicarFiltros:
    """Testes da função aplicar_filtros."""

    def test_sem_filtros(self):
        """Deve retornar todas as vagas sem filtros."""
        vagas = [
            {"id": "1", "periodos": {"nome": "Diurno"}, "data": "2025-01-06"},
            {"id": "2", "periodos": {"nome": "Noturno"}, "data": "2025-01-07"},
        ]

        resultado, filtros = aplicar_filtros(vagas)

        assert len(resultado) == 2
        assert filtros == []

    def test_apenas_periodo(self):
        """Deve aplicar apenas filtro de período."""
        vagas = [
            {"id": "1", "periodos": {"nome": "Diurno"}, "data": "2025-01-06"},
            {"id": "2", "periodos": {"nome": "Noturno"}, "data": "2025-01-07"},
        ]

        resultado, filtros = aplicar_filtros(vagas, periodo="diurno")

        assert len(resultado) == 1
        assert "período diurno" in filtros

    def test_apenas_dias(self):
        """Deve aplicar apenas filtro de dias."""
        vagas = [
            {"id": "1", "periodos": {"nome": "Diurno"}, "data": "2025-01-06"},  # Seg
            {"id": "2", "periodos": {"nome": "Noturno"}, "data": "2025-01-07"},  # Ter
        ]

        resultado, filtros = aplicar_filtros(vagas, dias_semana=["segunda"])

        assert len(resultado) == 1
        assert "dias segunda" in filtros

    def test_periodo_e_dias(self):
        """Deve aplicar ambos os filtros."""
        vagas = [
            {"id": "1", "periodos": {"nome": "Diurno"}, "data": "2025-01-06"},
            {"id": "2", "periodos": {"nome": "Diurno"}, "data": "2025-01-07"},
            {"id": "3", "periodos": {"nome": "Noturno"}, "data": "2025-01-06"},
        ]

        resultado, filtros = aplicar_filtros(
            vagas, periodo="diurno", dias_semana=["segunda"]
        )

        assert len(resultado) == 1
        assert resultado[0]["id"] == "1"
        assert len(filtros) == 2

    def test_periodo_qualquer(self):
        """Deve ignorar período 'qualquer'."""
        vagas = [
            {"id": "1", "periodos": {"nome": "Diurno"}},
            {"id": "2", "periodos": {"nome": "Noturno"}},
        ]

        resultado, filtros = aplicar_filtros(vagas, periodo="qualquer")

        assert len(resultado) == 2
        assert filtros == []


class TestMapeamentos:
    """Testes dos mapeamentos de constantes."""

    def test_mapeamento_periodos(self):
        """Deve ter os períodos esperados."""
        assert "diurno" in MAPEAMENTO_PERIODOS
        assert "noturno" in MAPEAMENTO_PERIODOS
        assert "12h" in MAPEAMENTO_PERIODOS
        assert "24h" in MAPEAMENTO_PERIODOS

    def test_mapeamento_dias(self):
        """Deve ter todos os dias da semana."""
        assert DIAS_SEMANA_MAP["segunda"] == 0
        assert DIAS_SEMANA_MAP["domingo"] == 6
        assert DIAS_SEMANA_MAP["seg"] == 0
        assert DIAS_SEMANA_MAP["dom"] == 6
