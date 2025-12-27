"""
Testes para validações de negócio.

Sprint 14 - E05 - S05.5
"""

import pytest
from datetime import date, timedelta

from app.services.grupos.validacoes import (
    validar_valor,
    validar_data,
    validar_horario,
    validar_vaga_completa,
    validar_campo_enum,
    AlertaVaga,
    PERIODOS_VALIDOS,
    SETORES_VALIDOS,
)


class TestValidarValor:
    """Testes de validação de valor."""

    def test_valor_normal(self):
        """Valor normal não gera alertas."""
        alertas = validar_valor(1500)
        assert len(alertas) == 0

    def test_valor_baixo(self):
        """Valor baixo gera alerta."""
        alertas = validar_valor(300)

        assert len(alertas) == 1
        assert alertas[0].tipo == "valor_baixo"
        assert alertas[0].severidade == "warning"

    def test_valor_alto(self):
        """Valor alto gera alerta."""
        alertas = validar_valor(15000)

        assert len(alertas) == 1
        assert alertas[0].tipo == "valor_alto"
        assert alertas[0].severidade == "warning"

    def test_valor_none(self):
        """Valor None não gera alertas."""
        alertas = validar_valor(None)
        assert len(alertas) == 0

    def test_valor_limite_baixo(self):
        """Valor no limite baixo (500) não gera alerta."""
        alertas = validar_valor(500)
        assert len(alertas) == 0

    def test_valor_limite_alto(self):
        """Valor no limite alto (10000) não gera alerta."""
        alertas = validar_valor(10000)
        assert len(alertas) == 0


class TestValidarData:
    """Testes de validação de data."""

    def test_data_futura(self):
        """Data futura não gera alerta de erro."""
        data_futura = date.today() + timedelta(days=7)
        alertas = validar_data(data_futura)

        # Não deve ter erros
        erros = [a for a in alertas if a.severidade == "error"]
        assert len(erros) == 0

    def test_data_passada(self):
        """Data passada gera erro."""
        data_passada = date.today() - timedelta(days=1)
        alertas = validar_data(data_passada)

        assert len(alertas) == 1
        assert alertas[0].tipo == "data_passada"
        assert alertas[0].severidade == "error"

    def test_data_hoje(self):
        """Data de hoje gera info de urgência."""
        alertas = validar_data(date.today())

        assert len(alertas) == 1
        assert alertas[0].tipo == "data_hoje"
        assert alertas[0].severidade == "info"

    def test_data_distante(self):
        """Data muito distante gera info."""
        data_distante = date.today() + timedelta(days=45)
        alertas = validar_data(data_distante)

        assert len(alertas) == 1
        assert alertas[0].tipo == "data_distante"
        assert alertas[0].severidade == "info"

    def test_data_none(self):
        """Data None não gera alertas."""
        alertas = validar_data(None)
        assert len(alertas) == 0


class TestValidarHorario:
    """Testes de validação de horário."""

    def test_horario_valido(self):
        """Horário válido não gera alertas."""
        alertas = validar_horario("19:00", "07:00")
        assert len(alertas) == 0

    def test_horario_inicio_invalido(self):
        """Horário início inválido gera alerta."""
        alertas = validar_horario("25:00", "07:00")

        assert len(alertas) == 1
        assert alertas[0].tipo == "horario_invalido"

    def test_horario_fim_invalido(self):
        """Horário fim inválido gera alerta."""
        alertas = validar_horario("19:00", "28:00")

        assert len(alertas) == 1

    def test_ambos_invalidos(self):
        """Ambos inválidos gera dois alertas."""
        alertas = validar_horario("99:99", "88:88")
        assert len(alertas) == 2

    def test_horarios_none(self):
        """Horários None não geram alertas."""
        alertas = validar_horario(None, None)
        assert len(alertas) == 0

    def test_formato_sem_zero(self):
        """Horário sem zero à esquerda é válido."""
        alertas = validar_horario("7:00", "19:00")
        assert len(alertas) == 0


class TestValidarVagaCompleta:
    """Testes de validação completa."""

    def test_vaga_sem_problemas(self):
        """Vaga sem problemas não gera alertas de erro."""
        data_futura = date.today() + timedelta(days=3)
        alertas = validar_vaga_completa(
            valor=1500,
            data_vaga=data_futura,
            hora_inicio="19:00",
            hora_fim="07:00"
        )

        erros = [a for a in alertas if a.severidade == "error"]
        assert len(erros) == 0

    def test_vaga_com_multiplos_problemas(self):
        """Vaga com múltiplos problemas gera múltiplos alertas."""
        data_passada = date.today() - timedelta(days=1)
        alertas = validar_vaga_completa(
            valor=100,
            data_vaga=data_passada,
            hora_inicio="99:00",
            hora_fim="07:00"
        )

        assert len(alertas) >= 3  # valor_baixo, data_passada, horario_invalido


class TestValidarCampoEnum:
    """Testes de validação de campos enum."""

    def test_periodo_valido(self):
        """Período válido não gera alerta."""
        alertas = validar_campo_enum("Noturno", PERIODOS_VALIDOS, "periodo")
        assert len(alertas) == 0

    def test_periodo_invalido(self):
        """Período inválido gera alerta."""
        alertas = validar_campo_enum("Matutino", PERIODOS_VALIDOS, "periodo")

        assert len(alertas) == 1
        assert alertas[0].tipo == "periodo_invalido"

    def test_setor_valido(self):
        """Setor válido não gera alerta."""
        alertas = validar_campo_enum("Pronto atendimento", SETORES_VALIDOS, "setor")
        assert len(alertas) == 0

    def test_valor_none(self):
        """Valor None não gera alerta."""
        alertas = validar_campo_enum(None, PERIODOS_VALIDOS, "periodo")
        assert len(alertas) == 0


class TestAlertaVaga:
    """Testes da dataclass AlertaVaga."""

    def test_criacao_alerta(self):
        """Deve criar alerta corretamente."""
        alerta = AlertaVaga(
            tipo="valor_baixo",
            mensagem="Valor muito baixo: R$ 300",
            severidade="warning"
        )

        assert alerta.tipo == "valor_baixo"
        assert "300" in alerta.mensagem
        assert alerta.severidade == "warning"
