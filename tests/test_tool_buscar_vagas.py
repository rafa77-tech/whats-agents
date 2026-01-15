"""
Testes da tool buscar_vagas.
"""
import pytest
from app.tools.vagas import (
    TOOL_BUSCAR_VAGAS,
    _filtrar_por_periodo,
    _filtrar_por_dias_semana,
)


class TestToolSchema:
    """Testes do schema da tool."""

    def test_tool_name(self):
        """Tool tem nome correto."""
        assert TOOL_BUSCAR_VAGAS["name"] == "buscar_vagas"

    def test_tool_has_description(self):
        """Tool tem descricao."""
        assert "description" in TOOL_BUSCAR_VAGAS
        assert len(TOOL_BUSCAR_VAGAS["description"]) > 100

    def test_tool_has_input_schema(self):
        """Tool tem schema de input."""
        assert "input_schema" in TOOL_BUSCAR_VAGAS
        assert TOOL_BUSCAR_VAGAS["input_schema"]["type"] == "object"

    def test_tool_no_required_params(self):
        """Tool nao tem parametros obrigatorios."""
        schema = TOOL_BUSCAR_VAGAS["input_schema"]
        assert schema.get("required", []) == []

    def test_tool_has_expected_properties(self):
        """Tool tem propriedades esperadas."""
        props = TOOL_BUSCAR_VAGAS["input_schema"]["properties"]
        assert "regiao" in props
        assert "periodo" in props
        assert "valor_minimo" in props
        assert "dias_semana" in props
        assert "limite" in props

    def test_periodo_enum_values(self):
        """Periodo tem valores enum corretos."""
        props = TOOL_BUSCAR_VAGAS["input_schema"]["properties"]
        periodo_enum = props["periodo"]["enum"]
        assert "diurno" in periodo_enum
        assert "noturno" in periodo_enum
        assert "12h" in periodo_enum
        assert "24h" in periodo_enum
        assert "qualquer" in periodo_enum


class TestFiltrarPorPeriodo:
    """Testes do filtro de periodo."""

    def test_filtra_diurno(self):
        """Filtra vagas diurnas."""
        vagas = [
            {"id": "1", "periodos": {"nome": "Diurno"}},
            {"id": "2", "periodos": {"nome": "Noturno"}},
            {"id": "3", "periodos": {"nome": "Dia"}},
        ]
        resultado = _filtrar_por_periodo(vagas, "diurno")
        assert len(resultado) == 2
        ids = [v["id"] for v in resultado]
        assert "1" in ids
        assert "3" in ids

    def test_filtra_noturno(self):
        """Filtra vagas noturnas."""
        vagas = [
            {"id": "1", "periodos": {"nome": "Diurno"}},
            {"id": "2", "periodos": {"nome": "Noturno"}},
            {"id": "3", "periodos": {"nome": "Noite"}},
        ]
        resultado = _filtrar_por_periodo(vagas, "noturno")
        assert len(resultado) == 2
        ids = [v["id"] for v in resultado]
        assert "2" in ids
        assert "3" in ids

    def test_filtra_12h(self):
        """Filtra vagas de 12 horas."""
        vagas = [
            {"id": "1", "periodos": {"nome": "12h"}},
            {"id": "2", "periodos": {"nome": "24h"}},
            {"id": "3", "periodos": {"nome": "12 horas"}},
        ]
        resultado = _filtrar_por_periodo(vagas, "12h")
        assert len(resultado) == 2
        ids = [v["id"] for v in resultado]
        assert "1" in ids
        assert "3" in ids

    def test_sem_match_retorna_vazio(self):
        """Se nenhuma vaga match, retorna lista vazia."""
        vagas = [
            {"id": "1", "periodos": {"nome": "Especial"}},
            {"id": "2", "periodos": {"nome": "Plantao X"}},
        ]
        resultado = _filtrar_por_periodo(vagas, "diurno")
        assert len(resultado) == 0

    def test_periodo_none_nao_quebra(self):
        """Periodo None nao causa erro."""
        vagas = [
            {"id": "1", "periodos": {}},
            {"id": "2", "periodos": {"nome": "Diurno"}},
        ]
        resultado = _filtrar_por_periodo(vagas, "diurno")
        assert len(resultado) == 1


class TestFiltrarPorDiasSemana:
    """Testes do filtro de dias da semana."""

    def test_filtra_segunda(self):
        """Filtra vagas de segunda-feira."""
        vagas = [
            {"id": "1", "data": "2025-12-15"},  # Segunda
            {"id": "2", "data": "2025-12-16"},  # Terca
            {"id": "3", "data": "2025-12-22"},  # Segunda
        ]
        resultado = _filtrar_por_dias_semana(vagas, ["segunda"])
        assert len(resultado) == 2
        ids = [v["id"] for v in resultado]
        assert "1" in ids
        assert "3" in ids

    def test_filtra_multiplos_dias(self):
        """Filtra vagas de multiplos dias."""
        vagas = [
            {"id": "1", "data": "2025-12-15"},  # Segunda
            {"id": "2", "data": "2025-12-16"},  # Terca
            {"id": "3", "data": "2025-12-17"},  # Quarta
            {"id": "4", "data": "2025-12-18"},  # Quinta
        ]
        resultado = _filtrar_por_dias_semana(vagas, ["segunda", "quarta"])
        assert len(resultado) == 2
        ids = [v["id"] for v in resultado]
        assert "1" in ids
        assert "3" in ids

    def test_aceita_abreviacoes(self):
        """Aceita abreviacoes de dias."""
        vagas = [
            {"id": "1", "data": "2025-12-15"},  # Segunda
            {"id": "2", "data": "2025-12-16"},  # Terca
        ]
        resultado = _filtrar_por_dias_semana(vagas, ["seg", "ter"])
        assert len(resultado) == 2

    def test_filtra_fim_de_semana(self):
        """Filtra vagas de fim de semana."""
        vagas = [
            {"id": "1", "data": "2025-12-15"},  # Segunda
            {"id": "2", "data": "2025-12-13"},  # Sabado
            {"id": "3", "data": "2025-12-14"},  # Domingo
        ]
        resultado = _filtrar_por_dias_semana(vagas, ["sabado", "domingo"])
        assert len(resultado) == 2
        ids = [v["id"] for v in resultado]
        assert "2" in ids
        assert "3" in ids

    def test_sem_match_retorna_vazio(self):
        """Se nenhuma vaga match, retorna lista vazia."""
        vagas = [
            {"id": "1", "data": "2025-12-15"},  # Segunda
            {"id": "2", "data": "2025-12-16"},  # Terca
        ]
        resultado = _filtrar_por_dias_semana(vagas, ["sabado"])
        assert len(resultado) == 0

    def test_data_invalida_exclui_vaga(self):
        """Data invalida exclui a vaga do resultado."""
        vagas = [
            {"id": "1", "data": "invalid-date"},
            {"id": "2", "data": "2025-12-15"},  # Segunda
        ]
        resultado = _filtrar_por_dias_semana(vagas, ["segunda"])
        assert len(resultado) == 1
        assert resultado[0]["id"] == "2"

    def test_dias_vazios_retorna_todas(self):
        """Lista de dias vazia retorna todas as vagas."""
        vagas = [
            {"id": "1", "data": "2025-12-15"},
            {"id": "2", "data": "2025-12-16"},
        ]
        resultado = _filtrar_por_dias_semana(vagas, [])
        assert len(resultado) == 2
