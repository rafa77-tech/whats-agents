"""
Testes do módulo de formatação de respostas de tools.

Sprint 31 - S31.E5.5
"""
import pytest

from app.tools.response_formatter import (
    ToolResponse,
    VagasResponseFormatter,
    ReservaResponseFormatter,
    get_vagas_formatter,
    get_reserva_formatter,
)


class TestToolResponse:
    """Testes da dataclass ToolResponse."""

    def test_default_success(self):
        """Deve ter success=True por padrão."""
        response = ToolResponse()

        assert response.success is True
        assert response.error is None
        assert response.data == {}

    def test_to_dict_success(self):
        """Deve converter para dict corretamente."""
        response = ToolResponse(
            success=True,
            data={"vagas": [{"id": "1"}]},
            instrucao="Apresente as vagas"
        )

        result = response.to_dict()

        assert result["success"] is True
        assert result["vagas"] == [{"id": "1"}]
        assert result["instrucao"] == "Apresente as vagas"
        assert "error" not in result

    def test_to_dict_error(self):
        """Deve incluir error quando presente."""
        response = ToolResponse(
            success=False,
            error="Especialidade não encontrada",
            mensagem_sugerida="Pode confirmar o nome?"
        )

        result = response.to_dict()

        assert result["success"] is False
        assert result["error"] == "Especialidade não encontrada"
        assert result["mensagem_sugerida"] == "Pode confirmar o nome?"


class TestVagasResponseFormatter:
    """Testes do formatador de respostas de vagas."""

    @pytest.fixture
    def formatter(self):
        """Fixture para o formatter."""
        return VagasResponseFormatter()

    def test_formatar_valor_display_fixo(self, formatter):
        """Deve formatar valor fixo."""
        vaga = {"valor": 2500, "valor_tipo": "fixo"}

        result = formatter.formatar_valor_display(vaga)

        assert result == "R$ 2.500"

    def test_formatar_valor_display_faixa(self, formatter):
        """Deve formatar faixa de valores."""
        vaga = {
            "valor_tipo": "faixa",
            "valor_minimo": 2000,
            "valor_maximo": 3000
        }

        result = formatter.formatar_valor_display(vaga)

        assert result == "R$ 2.000 a R$ 3.000"

    def test_formatar_valor_display_a_combinar(self, formatter):
        """Deve formatar 'a combinar'."""
        vaga = {"valor_tipo": "a_combinar"}

        result = formatter.formatar_valor_display(vaga)

        assert result == "a combinar"

    def test_formatar_valor_display_sem_valor(self, formatter):
        """Deve retornar 'nao informado' quando sem valor."""
        vaga = {}

        result = formatter.formatar_valor_display(vaga)

        assert result == "nao informado"

    def test_formatar_vagas_resumo(self, formatter):
        """Deve formatar lista de vagas para resumo."""
        vagas = [
            {
                "id": "123",
                "hospitais": {"nome": "Hospital São Luiz", "cidade": "São Paulo"},
                "periodos": {"nome": "Diurno"},
                "setores": {"nome": "UTI"},
                "especialidades": {"nome": "Cardiologia"},
                "data": "2025-01-15",
                "valor": 2500,
                "valor_tipo": "fixo",
            }
        ]

        result = formatter.formatar_vagas_resumo(vagas)

        assert len(result) == 1
        assert result[0]["VAGA_ID_PARA_HANDOFF"] == "123"
        assert result[0]["hospital"] == "Hospital São Luiz"
        assert result[0]["cidade"] == "São Paulo"
        assert result[0]["periodo"] == "Diurno"
        assert result[0]["setor"] == "UTI"
        assert result[0]["especialidade"] == "Cardiologia"
        assert result[0]["valor_display"] == "R$ 2.500"
        assert result[0]["contato"] is None

    def test_formatar_vagas_resumo_com_contato(self, formatter):
        """Deve incluir contato no resumo (Sprint 57)."""
        vagas = [
            {
                "id": "123",
                "hospitais": {"nome": "Hospital São Luiz", "cidade": "São Paulo"},
                "periodos": {"nome": "Diurno"},
                "setores": None,
                "especialidades": {"nome": "Cardiologia"},
                "data": "2025-01-15",
                "valor": 2500,
                "valor_tipo": "fixo",
                "contato_nome": "Maria Silva",
            }
        ]

        result = formatter.formatar_vagas_resumo(vagas)

        assert len(result) == 1
        assert result[0]["contato"] == "Maria Silva"

    def test_formatar_vagas_resumo_com_none(self, formatter):
        """Deve lidar com objetos relacionados None."""
        vagas = [
            {
                "id": "123",
                "hospitais": None,
                "periodos": None,
                "setores": None,
                "especialidades": None,
                "data": "2025-01-15",
            }
        ]

        result = formatter.formatar_vagas_resumo(vagas, "Cardiologia")

        assert len(result) == 1
        assert result[0]["hospital"] is None
        assert result[0]["especialidade"] == "Cardiologia"

    def test_construir_instrucao_vagas(self, formatter):
        """Deve construir instrução para vagas."""
        result = formatter.construir_instrucao_vagas(
            especialidade_nome="Cardiologia"
        )

        assert "Cardiologia" in result
        assert "VAGA_ID_PARA_HANDOFF" in result
        assert "CRITICO" in result

    def test_construir_instrucao_vagas_especialidade_diferente(self, formatter):
        """Deve incluir alerta quando especialidade diferente."""
        result = formatter.construir_instrucao_vagas(
            especialidade_nome="Ortopedia",
            especialidade_diferente=True,
            especialidade_cadastrada="Cardiologia"
        )

        assert "ALERTA" in result
        assert "Ortopedia" in result
        assert "Cardiologia" in result

    def test_mensagem_sem_vagas_com_filtros(self, formatter):
        """Deve gerar mensagem quando filtros eliminaram vagas."""
        result = formatter.mensagem_sem_vagas(
            especialidade_nome="Cardiologia",
            total_sem_filtros=5,
            filtros_aplicados=["período diurno"]
        )

        assert "período diurno" in result
        assert "5 vagas" in result

    def test_mensagem_sem_vagas_especialidade_diferente(self, formatter):
        """Deve sugerir especialidade cadastrada."""
        result = formatter.mensagem_sem_vagas(
            especialidade_nome="Ortopedia",
            especialidade_diferente=True,
            especialidade_cadastrada="Cardiologia"
        )

        assert "Cardiologia" in result

    def test_mensagem_sem_vagas_padrao(self, formatter):
        """Deve gerar mensagem padrão."""
        result = formatter.mensagem_sem_vagas(
            especialidade_nome="Cardiologia"
        )

        assert "Cardiologia" in result
        assert "te aviso" in result


class TestReservaResponseFormatter:
    """Testes do formatador de respostas de reserva."""

    @pytest.fixture
    def formatter(self):
        """Fixture para o formatter."""
        return ReservaResponseFormatter()

    def test_construir_instrucao_confirmacao_valor_fixo(self, formatter):
        """Deve incluir valor fixo na instrução."""
        vaga = {"valor": 2500, "valor_tipo": "fixo"}
        hospital = {"endereco_formatado": "Rua A, 123"}

        result = formatter.construir_instrucao_confirmacao(vaga, hospital)

        assert "R$ 2500" in result
        assert "Rua A, 123" in result

    def test_construir_instrucao_confirmacao_a_combinar(self, formatter):
        """Deve mencionar negociação para 'a combinar'."""
        vaga = {"valor_tipo": "a_combinar"}
        hospital = {"endereco_formatado": "Rua A, 123"}

        result = formatter.construir_instrucao_confirmacao(vaga, hospital)

        assert "combinado" in result

    def test_construir_instrucao_ponte_externa(self, formatter):
        """Deve construir instrução para ponte externa."""
        vaga = {"valor_tipo": "fixo"}
        hospital = {}
        ponte_externa = {
            "divulgador": {
                "nome": "João Silva",
                "telefone": "11999999999",
                "empresa": "MedStaff"
            }
        }
        medico = {}

        result = formatter.construir_instrucao_ponte_externa(
            vaga, hospital, ponte_externa, medico
        )

        assert "João Silva" in result
        assert "MedStaff" in result
        assert "11999999999" in result


class TestSingletons:
    """Testes das factories singleton."""

    def test_get_vagas_formatter_singleton(self):
        """Deve retornar a mesma instância."""
        f1 = get_vagas_formatter()
        f2 = get_vagas_formatter()

        assert f1 is f2

    def test_get_reserva_formatter_singleton(self):
        """Deve retornar a mesma instância."""
        f1 = get_reserva_formatter()
        f2 = get_reserva_formatter()

        assert f1 is f2
