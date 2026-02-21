"""
Testes para Template Variable Mapper.

Sprint 66 — Mapeamento de variáveis para formato Graph API.
"""

import pytest

from app.services.meta.template_mapper import TemplateMapper, template_mapper


@pytest.fixture
def mapper():
    return TemplateMapper()


@pytest.fixture
def destinatario_completo():
    return {
        "nome": "Carlos",
        "especialidade_nome": "Cardiologia",
        "hospital_nome": "São Luiz",
    }


@pytest.fixture
def campanha_completa():
    return {
        "escopo_vagas": {
            "data_plantao": "15/03",
            "valor": "2.500",
            "horario": "19h-7h",
            "periodo": "Noturno",
            "setor": "UTI",
        },
        "hospital_nome": "São Luiz",
    }


class TestMapeamentoBasico:
    """Testes para mapeamento básico de variáveis."""

    def test_mapeamento_nome_especialidade(self, mapper, destinatario_completo):
        template = {
            "variable_mapping": {"1": "nome", "2": "especialidade"},
        }
        result = mapper.mapear_variaveis(template, destinatario_completo)

        assert len(result) == 1
        assert result[0]["type"] == "body"
        params = result[0]["parameters"]
        assert len(params) == 2
        assert params[0] == {"type": "text", "text": "Carlos"}
        assert params[1] == {"type": "text", "text": "Cardiologia"}

    def test_mapeamento_completo_6_variaveis(
        self, mapper, destinatario_completo, campanha_completa
    ):
        template = {
            "variable_mapping": {
                "1": "nome",
                "2": "especialidade",
                "3": "hospital",
                "4": "data_plantao",
                "5": "horario",
                "6": "valor",
            },
        }
        result = mapper.mapear_variaveis(
            template, destinatario_completo, campanha_completa
        )

        params = result[0]["parameters"]
        assert len(params) == 6
        assert params[0]["text"] == "Carlos"
        assert params[1]["text"] == "Cardiologia"
        assert params[2]["text"] == "São Luiz"
        assert params[3]["text"] == "15/03"
        assert params[4]["text"] == "19h-7h"
        assert params[5]["text"] == "2.500"

    def test_variavel_ausente_retorna_string_vazia(self, mapper):
        template = {
            "variable_mapping": {"1": "nome", "2": "hospital"},
        }
        destinatario = {"nome": "Carlos"}
        result = mapper.mapear_variaveis(template, destinatario)

        params = result[0]["parameters"]
        assert params[0]["text"] == "Carlos"
        assert params[1]["text"] == ""

    def test_template_sem_variable_mapping_retorna_vazio(self, mapper):
        template = {}
        result = mapper.mapear_variaveis(template, {"nome": "Carlos"})
        assert result == []

    def test_template_com_mapping_vazio_retorna_vazio(self, mapper):
        template = {"variable_mapping": {}}
        result = mapper.mapear_variaveis(template, {"nome": "Carlos"})
        assert result == []


class TestResolucaoAliases:
    """Testes para resolução de aliases de campos."""

    def test_resolve_primeiro_nome(self, mapper):
        template = {"variable_mapping": {"1": "nome"}}
        result = mapper.mapear_variaveis(template, {"primeiro_nome": "Maria"})
        assert result[0]["parameters"][0]["text"] == "Maria"

    def test_resolve_especialidade_nome(self, mapper):
        template = {"variable_mapping": {"1": "especialidade"}}
        result = mapper.mapear_variaveis(
            template, {"especialidade_nome": "Ortopedia"}
        )
        assert result[0]["parameters"][0]["text"] == "Ortopedia"

    def test_prioridade_nome_sobre_primeiro_nome(self, mapper):
        template = {"variable_mapping": {"1": "nome"}}
        result = mapper.mapear_variaveis(
            template, {"nome": "Carlos", "primeiro_nome": "Maria"}
        )
        assert result[0]["parameters"][0]["text"] == "Carlos"


class TestFormatoSaida:
    """Testes para formato de saída compatível com Graph API."""

    def test_formato_graph_api_valido(self, mapper, destinatario_completo):
        template = {"variable_mapping": {"1": "nome"}}
        result = mapper.mapear_variaveis(template, destinatario_completo)

        # Deve ser lista de components
        assert isinstance(result, list)
        assert len(result) == 1

        component = result[0]
        assert component["type"] == "body"
        assert isinstance(component["parameters"], list)

        param = component["parameters"][0]
        assert param["type"] == "text"
        assert isinstance(param["text"], str)

    def test_ordenacao_por_indice(self, mapper):
        template = {"variable_mapping": {"3": "hospital", "1": "nome", "2": "especialidade"}}
        result = mapper.mapear_variaveis(
            template,
            {"nome": "A", "especialidade_nome": "B", "hospital_nome": "C"},
        )
        params = result[0]["parameters"]
        assert params[0]["text"] == "A"
        assert params[1]["text"] == "B"
        assert params[2]["text"] == "C"


class TestCampanhaMerge:
    """Testes para merge de dados campanha + destinatário."""

    def test_campanha_escopo_vagas_merge(self, mapper):
        template = {"variable_mapping": {"1": "nome", "2": "valor"}}
        dest = {"nome": "Carlos"}
        campanha = {"escopo_vagas": {"valor": "3.000"}}
        result = mapper.mapear_variaveis(template, dest, campanha)

        params = result[0]["parameters"]
        assert params[0]["text"] == "Carlos"
        assert params[1]["text"] == "3.000"

    def test_campanha_campo_direto_override(self, mapper):
        template = {"variable_mapping": {"1": "hospital"}}
        dest = {}
        campanha = {"hospital": "Albert Einstein"}
        result = mapper.mapear_variaveis(template, dest, campanha)
        assert result[0]["parameters"][0]["text"] == "Albert Einstein"


class TestSingleton:
    """Teste que singleton existe."""

    def test_singleton_exportado(self):
        assert template_mapper is not None
        assert isinstance(template_mapper, TemplateMapper)
