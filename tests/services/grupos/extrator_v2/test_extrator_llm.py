"""
Testes do Extrator LLM v3 - Sprint 52.

Testa a extração unificada via LLM.
"""
import pytest
from datetime import date
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.services.grupos.extrator_v2.extrator_llm import (
    _hash_texto,
    _dia_semana_from_str,
    _periodo_from_str,
    _parse_time,
    _parse_date,
    converter_para_vagas_atomicas,
    ResultadoExtracaoLLM,
    ESPECIALIDADES_VALIDAS,
)
from app.services.grupos.extrator_v2.types import DiaSemana, Periodo


class TestHashTexto:
    """Testes da função de hash."""

    def test_hash_normaliza_texto(self):
        """Hash normaliza espaços e case."""
        texto1 = "Hospital   ABC"
        texto2 = "hospital abc"
        assert _hash_texto(texto1) == _hash_texto(texto2)

    def test_hash_diferente_para_textos_diferentes(self):
        """Hash diferente para textos diferentes."""
        assert _hash_texto("Hospital A") != _hash_texto("Hospital B")


class TestDiaSemanaFromStr:
    """Testes da conversão de dia da semana."""

    def test_segunda(self):
        assert _dia_semana_from_str("segunda") == DiaSemana.SEGUNDA

    def test_terca_com_acento(self):
        assert _dia_semana_from_str("terça") == DiaSemana.TERCA

    def test_sabado_sem_acento(self):
        assert _dia_semana_from_str("sabado") == DiaSemana.SABADO

    def test_domingo(self):
        assert _dia_semana_from_str("domingo") == DiaSemana.DOMINGO

    def test_case_insensitive(self):
        assert _dia_semana_from_str("SEGUNDA") == DiaSemana.SEGUNDA


class TestPeriodoFromStr:
    """Testes da conversão de período."""

    def test_manha(self):
        assert _periodo_from_str("manha") == Periodo.MANHA

    def test_noturno(self):
        assert _periodo_from_str("noturno") == Periodo.NOTURNO

    def test_diurno(self):
        assert _periodo_from_str("diurno") == Periodo.DIURNO

    def test_cinderela(self):
        assert _periodo_from_str("cinderela") == Periodo.CINDERELA


class TestParseTime:
    """Testes da conversão de horário."""

    def test_horario_valido(self):
        result = _parse_time("07:00")
        assert result is not None
        assert result.hour == 7
        assert result.minute == 0

    def test_horario_none(self):
        assert _parse_time(None) is None

    def test_horario_invalido(self):
        assert _parse_time("invalid") is None


class TestParseDate:
    """Testes da conversão de data."""

    def test_data_valida(self):
        result = _parse_date("2026-02-10")
        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 10

    def test_data_none(self):
        assert _parse_date(None) is None

    def test_data_invalida(self):
        assert _parse_date("invalid") is None


class TestConverterParaVagasAtomicas:
    """Testes da conversão para VagaAtomica."""

    def test_conversao_basica(self):
        """Converte resultado LLM para VagaAtomica."""
        resultado = ResultadoExtracaoLLM(
            eh_vaga=True,
            confianca=0.9,
            vagas=[{
                "hospital": "Hospital ABC",
                "especialidade": "Clínica Médica",
                "data": "2026-02-10",
                "dia_semana": "segunda",
                "periodo": "diurno",
                "valor": 2500,
            }]
        )

        vagas = converter_para_vagas_atomicas(resultado)

        assert len(vagas) == 1
        assert vagas[0].hospital_raw == "Hospital ABC"
        assert vagas[0].especialidade_raw == "Clínica Médica"
        assert vagas[0].valor == 2500
        assert vagas[0].data == date(2026, 2, 10)

    def test_vaga_sem_valor(self):
        """Vaga sem valor tem valor=0."""
        resultado = ResultadoExtracaoLLM(
            eh_vaga=True,
            confianca=0.9,
            vagas=[{
                "hospital": "Hospital ABC",
                "especialidade": "Pediatria",
                "data": "2026-02-10",
                "dia_semana": "segunda",
                "periodo": "diurno",
                "valor": None,
            }]
        )

        vagas = converter_para_vagas_atomicas(resultado)

        assert len(vagas) == 1
        assert vagas[0].valor == 0

    def test_multiplas_vagas(self):
        """Converte múltiplas vagas."""
        resultado = ResultadoExtracaoLLM(
            eh_vaga=True,
            confianca=0.9,
            vagas=[
                {
                    "hospital": "Hospital A",
                    "data": "2026-02-10",
                    "dia_semana": "segunda",
                    "periodo": "diurno",
                    "valor": 1500,
                },
                {
                    "hospital": "Hospital A",
                    "data": "2026-02-11",
                    "dia_semana": "terca",
                    "periodo": "noturno",
                    "valor": 1800,
                },
            ]
        )

        vagas = converter_para_vagas_atomicas(resultado)

        assert len(vagas) == 2

    def test_vaga_sem_hospital_ignorada(self):
        """Vaga sem hospital é ignorada."""
        resultado = ResultadoExtracaoLLM(
            eh_vaga=True,
            confianca=0.9,
            vagas=[{
                "hospital": None,
                "data": "2026-02-10",
                "dia_semana": "segunda",
                "periodo": "diurno",
            }]
        )

        vagas = converter_para_vagas_atomicas(resultado)

        assert len(vagas) == 0

    def test_vaga_sem_data_ignorada(self):
        """Vaga sem data é ignorada."""
        resultado = ResultadoExtracaoLLM(
            eh_vaga=True,
            confianca=0.9,
            vagas=[{
                "hospital": "Hospital ABC",
                "data": None,
                "dia_semana": "segunda",
                "periodo": "diurno",
            }]
        )

        vagas = converter_para_vagas_atomicas(resultado)

        assert len(vagas) == 0

    def test_preserva_ids_rastreabilidade(self):
        """Preserva IDs de mensagem e grupo."""
        msg_id = uuid4()
        grupo_id = uuid4()

        resultado = ResultadoExtracaoLLM(
            eh_vaga=True,
            confianca=0.9,
            vagas=[{
                "hospital": "Hospital ABC",
                "data": "2026-02-10",
                "dia_semana": "segunda",
                "periodo": "diurno",
            }]
        )

        vagas = converter_para_vagas_atomicas(
            resultado,
            mensagem_id=msg_id,
            grupo_id=grupo_id
        )

        assert vagas[0].mensagem_id == msg_id
        assert vagas[0].grupo_id == grupo_id


class TestEspecialidadesValidas:
    """Testes da lista de especialidades."""

    def test_especialidades_principais_presentes(self):
        """Especialidades principais estão na lista."""
        principais = [
            "Clínica Médica",
            "Pediatria",
            "Ginecologia e Obstetrícia",
            "Medicina Intensiva",
            "Medicina de Emergência",
            "Ortopedia e Traumatologia",
            "Cardiologia",
        ]

        for esp in principais:
            assert esp in ESPECIALIDADES_VALIDAS

    def test_total_especialidades(self):
        """Tem número razoável de especialidades."""
        assert len(ESPECIALIDADES_VALIDAS) >= 50


class TestResultadoExtracaoLLM:
    """Testes do dataclass ResultadoExtracaoLLM."""

    def test_resultado_vaga(self):
        """Resultado com vaga."""
        resultado = ResultadoExtracaoLLM(
            eh_vaga=True,
            confianca=0.9,
            vagas=[{"hospital": "ABC"}]
        )

        assert resultado.eh_vaga is True
        assert resultado.confianca == 0.9
        assert len(resultado.vagas) == 1

    def test_resultado_nao_vaga(self):
        """Resultado sem vaga."""
        resultado = ResultadoExtracaoLLM(
            eh_vaga=False,
            confianca=0.8,
            motivo_descarte="não é oferta de plantão"
        )

        assert resultado.eh_vaga is False
        assert resultado.motivo_descarte is not None


# Testes de integração (requerem API key)
@pytest.mark.skipif(
    True,  # Desabilitado por padrão - usar apenas para teste manual
    reason="Requer API key e faz chamadas reais"
)
class TestExtracaoLLMIntegracao:
    """Testes de integração com LLM real."""

    @pytest.mark.asyncio
    async def test_mensagem_com_vaga(self):
        """Extrai vaga de mensagem real."""
        from app.services.grupos.extrator_v2.extrator_llm import extrair_com_llm

        texto = """🏥 VAGA URGENTE - CLÍNICA MÉDICA

Hospital Albert Einstein
Data: 10/02/2026
Horário: 07:00 às 19:00 (SD)
Valor: R$ 2.500,00

Contato: Maria - 11999887766"""

        resultado = await extrair_com_llm(
            texto=texto,
            data_referencia=date(2026, 2, 3),
            usar_cache=False
        )

        assert resultado.eh_vaga is True
        assert len(resultado.vagas) >= 1
        assert resultado.vagas[0].get("valor") == 2500

    @pytest.mark.asyncio
    async def test_mensagem_sem_vaga(self):
        """Detecta que mensagem não é vaga."""
        from app.services.grupos.extrator_v2.extrator_llm import extrair_com_llm

        texto = """Bom dia pessoal!
Alguém sabe de vagas para ginecologista?
Obrigado!"""

        resultado = await extrair_com_llm(
            texto=texto,
            usar_cache=False
        )

        assert resultado.eh_vaga is False

    @pytest.mark.asyncio
    async def test_bug_202_corrigido(self):
        """Verifica que bug R$ 202 não ocorre mais."""
        from app.services.grupos.extrator_v2.extrator_llm import extrair_com_llm

        texto = """🏥 Hospital Dia da Rede Hora Certa M Boi Mirim II
04/02/2026	07:00 - 19:00
11/02/2026	07:00 - 19:00

Interessados chamar inbox"""

        resultado = await extrair_com_llm(
            texto=texto,
            data_referencia=date(2026, 2, 3),
            usar_cache=False
        )

        # Se extraiu vagas, nenhuma deve ter valor 202
        for vaga in resultado.vagas:
            valor = vaga.get("valor")
            if valor is not None:
                assert valor != 202, "Bug R$ 202 ainda presente!"
