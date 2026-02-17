"""Testes para gerador de vagas."""
import pytest
from datetime import date, time
from uuid import uuid4

from app.services.grupos.extrator_v2.gerador_vagas import (
    gerar_vagas,
    gerar_vagas_para_hospital,
    validar_vagas,
    deduplicar_vagas,
)
from app.services.grupos.extrator_v2.types import (
    VagaAtomica,
    HospitalExtraido,
    DataPeriodoExtraido,
    ValoresExtraidos,
    ContatoExtraido,
    DiaSemana,
    Periodo,
    GrupoDia,
    RegraValor,
)


class TestGerarVagasParaHospital:
    """Testes para geração de vagas por hospital."""

    def test_uma_data_valor_unico(self):
        """Uma data com valor único."""
        hospital = HospitalExtraido(nome="Hospital ABC", confianca=0.9)
        datas = [
            DataPeriodoExtraido(
                data=date(2026, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                confianca=0.9
            )
        ]
        valores = ValoresExtraidos(valor_unico=1700)

        vagas = gerar_vagas_para_hospital(hospital, datas, valores)

        assert len(vagas) == 1
        assert vagas[0].hospital_raw == "Hospital ABC"
        assert vagas[0].data == date(2026, 1, 26)
        assert vagas[0].valor == 1700

    def test_multiplas_datas_valor_unico(self):
        """Múltiplas datas com valor único."""
        hospital = HospitalExtraido(nome="Hospital ABC", confianca=0.9)
        datas = [
            DataPeriodoExtraido(
                data=date(2026, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                confianca=0.9
            ),
            DataPeriodoExtraido(
                data=date(2026, 1, 27),
                dia_semana=DiaSemana.TERCA,
                periodo=Periodo.NOITE,
                confianca=0.9
            ),
        ]
        valores = ValoresExtraidos(valor_unico=1700)

        vagas = gerar_vagas_para_hospital(hospital, datas, valores)

        assert len(vagas) == 2
        assert all(v.valor == 1700 for v in vagas)

    def test_multiplas_datas_valores_diferentes(self):
        """Valores diferentes por dia da semana."""
        hospital = HospitalExtraido(nome="Hospital ABC", confianca=0.9)
        datas = [
            DataPeriodoExtraido(
                data=date(2026, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                confianca=0.9
            ),
            DataPeriodoExtraido(
                data=date(2026, 1, 31),
                dia_semana=DiaSemana.SABADO,
                periodo=Periodo.DIURNO,
                confianca=0.9
            ),
        ]
        valores = ValoresExtraidos(regras=[
            RegraValor(grupo_dia=GrupoDia.SEG_SEX, valor=1700),
            RegraValor(grupo_dia=GrupoDia.SAB_DOM, valor=1800),
        ])

        vagas = gerar_vagas_para_hospital(hospital, datas, valores)

        assert len(vagas) == 2
        assert vagas[0].valor == 1700  # Segunda
        assert vagas[1].valor == 1800  # Sábado

    def test_com_contato(self):
        """Vaga com contato."""
        hospital = HospitalExtraido(nome="Hospital ABC", confianca=0.9)
        datas = [
            DataPeriodoExtraido(
                data=date(2026, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                confianca=0.9
            )
        ]
        valores = ValoresExtraidos(valor_unico=1700)
        contato = ContatoExtraido(
            nome="Eloisa",
            whatsapp="5511939050162",
            confianca=0.95
        )

        vagas = gerar_vagas_para_hospital(hospital, datas, valores, contato=contato)

        assert len(vagas) == 1
        assert vagas[0].contato_nome == "Eloisa"
        assert vagas[0].contato_whatsapp == "5511939050162"


class TestGerarVagas:
    """Testes para geração completa de vagas."""

    def test_um_hospital_multiplas_datas(self):
        """Um hospital com múltiplas datas."""
        hospitais = [HospitalExtraido(nome="Hospital ABC", confianca=0.9)]
        datas = [
            DataPeriodoExtraido(
                data=date(2026, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                confianca=0.9
            ),
            DataPeriodoExtraido(
                data=date(2026, 1, 27),
                dia_semana=DiaSemana.TERCA,
                periodo=Periodo.NOITE,
                confianca=0.9
            ),
        ]
        valores = ValoresExtraidos(valor_unico=1700)

        vagas = gerar_vagas(hospitais, datas, valores)

        assert len(vagas) == 2

    def test_multiplos_hospitais_multiplas_datas(self):
        """Múltiplos hospitais × múltiplas datas = produto cartesiano."""
        hospitais = [
            HospitalExtraido(nome="Hospital ABC", confianca=0.9),
            HospitalExtraido(nome="Hospital XYZ", confianca=0.8),
        ]
        datas = [
            DataPeriodoExtraido(
                data=date(2026, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                confianca=0.9
            ),
            DataPeriodoExtraido(
                data=date(2026, 1, 27),
                dia_semana=DiaSemana.TERCA,
                periodo=Periodo.NOITE,
                confianca=0.9
            ),
        ]
        valores = ValoresExtraidos(valor_unico=1700)

        vagas = gerar_vagas(hospitais, datas, valores)

        # 2 hospitais × 2 datas = 4 vagas
        assert len(vagas) == 4

    def test_sem_hospitais(self):
        """Sem hospitais retorna lista vazia."""
        vagas = gerar_vagas([], [], ValoresExtraidos())
        assert vagas == []

    def test_sem_datas(self):
        """Sem datas retorna lista vazia."""
        hospitais = [HospitalExtraido(nome="Hospital ABC", confianca=0.9)]
        vagas = gerar_vagas(hospitais, [], ValoresExtraidos())
        assert vagas == []


class TestValidarVagas:
    """Testes para validação de vagas."""

    def test_vaga_valida(self):
        """Vaga válida passa na validação."""
        vagas = [
            VagaAtomica(
                data=date(2030, 1, 26),  # Data futura
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                valor=1700,
                hospital_raw="Hospital ABC"
            )
        ]

        validas = validar_vagas(vagas)
        assert len(validas) == 1

    def test_vaga_sem_hospital(self):
        """Vaga sem hospital é removida."""
        vagas = [
            VagaAtomica(
                data=date(2030, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                valor=1700,
                hospital_raw=""  # Sem hospital
            )
        ]

        validas = validar_vagas(vagas)
        assert len(validas) == 0

    def test_vaga_data_passada(self):
        """Vaga com data passada é removida."""
        vagas = [
            VagaAtomica(
                data=date(2020, 1, 1),  # Passado
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                valor=1700,
                hospital_raw="Hospital ABC"
            )
        ]

        validas = validar_vagas(vagas)
        assert len(validas) == 0


class TestDeduplicarVagas:
    """Testes para deduplicação de vagas."""

    def test_sem_duplicatas(self):
        """Lista sem duplicatas permanece igual."""
        vagas = [
            VagaAtomica(
                data=date(2030, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                valor=1700,
                hospital_raw="Hospital ABC"
            ),
            VagaAtomica(
                data=date(2030, 1, 27),
                dia_semana=DiaSemana.TERCA,
                periodo=Periodo.NOITE,
                valor=1700,
                hospital_raw="Hospital ABC"
            ),
        ]

        unicas = deduplicar_vagas(vagas)
        assert len(unicas) == 2

    def test_com_duplicatas(self):
        """Duplicatas são removidas."""
        vagas = [
            VagaAtomica(
                data=date(2030, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                valor=1700,
                hospital_raw="Hospital ABC"
            ),
            VagaAtomica(
                data=date(2030, 1, 26),  # Mesma data
                dia_semana=DiaSemana.SEGUNDA,  # Mesmo dia
                periodo=Periodo.MANHA,  # Mesmo período
                valor=1700,  # Mesmo valor
                hospital_raw="Hospital ABC"  # Mesmo hospital
            ),
        ]

        unicas = deduplicar_vagas(vagas)
        assert len(unicas) == 1

    def test_mesmo_hospital_valores_diferentes(self):
        """Mesmo hospital, valores diferentes = não duplicata."""
        vagas = [
            VagaAtomica(
                data=date(2030, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                valor=1700,
                hospital_raw="Hospital ABC"
            ),
            VagaAtomica(
                data=date(2030, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.MANHA,
                valor=1800,  # Valor diferente
                hospital_raw="Hospital ABC"
            ),
        ]

        unicas = deduplicar_vagas(vagas)
        assert len(unicas) == 2


class TestCenarioCompleto:
    """Testes de cenário completo (integração)."""

    def test_cenario_exemplo_readme(self):
        """Cenário do exemplo do README."""
        # Dados de entrada conforme exemplo
        hospitais = [
            HospitalExtraido(
                nome="Hospital Campo Limpo",
                endereco="Estrada Itapecirica, 1661 - SP",
                confianca=0.95
            )
        ]

        datas = [
            DataPeriodoExtraido(
                data=date(2026, 1, 26),
                dia_semana=DiaSemana.SEGUNDA,
                periodo=Periodo.TARDE,
                hora_inicio=time(13, 0),
                hora_fim=time(19, 0),
                confianca=0.9
            ),
            DataPeriodoExtraido(
                data=date(2026, 1, 27),
                dia_semana=DiaSemana.TERCA,
                periodo=Periodo.NOITE,
                hora_inicio=time(19, 0),
                hora_fim=time(7, 0),
                confianca=0.9
            ),
            DataPeriodoExtraido(
                data=date(2026, 1, 28),
                dia_semana=DiaSemana.QUARTA,
                periodo=Periodo.MANHA,
                hora_inicio=time(7, 0),
                hora_fim=time(13, 0),
                confianca=0.9
            ),
            DataPeriodoExtraido(
                data=date(2026, 2, 1),
                dia_semana=DiaSemana.DOMINGO,
                periodo=Periodo.DIURNO,
                hora_inicio=time(7, 0),
                hora_fim=time(19, 0),
                confianca=0.9
            ),
        ]

        valores = ValoresExtraidos(regras=[
            RegraValor(grupo_dia=GrupoDia.SEG_SEX, valor=1700),
            RegraValor(grupo_dia=GrupoDia.SAB_DOM, valor=1800),
        ])

        contato = ContatoExtraido(
            nome="Eloisa",
            whatsapp="5511939050162",
            confianca=0.95
        )

        # Gerar vagas
        vagas = gerar_vagas(
            hospitais=hospitais,
            datas_periodos=datas,
            valores=valores,
            contato=contato
        )

        # Validar quantidade
        assert len(vagas) == 4

        # Validar valores
        vagas_seg_sex = [v for v in vagas if v.dia_semana in {DiaSemana.SEGUNDA, DiaSemana.TERCA, DiaSemana.QUARTA}]
        vagas_sab_dom = [v for v in vagas if v.dia_semana in {DiaSemana.SABADO, DiaSemana.DOMINGO}]

        assert all(v.valor == 1700 for v in vagas_seg_sex)
        assert all(v.valor == 1800 for v in vagas_sab_dom)

        # Validar contato
        assert all(v.contato_nome == "Eloisa" for v in vagas)
        assert all(v.contato_whatsapp == "5511939050162" for v in vagas)


class TestVagaAtomicaToDict:
    """Testes para VagaAtomica.to_dict incluindo numero_vagas."""

    def test_to_dict_inclui_numero_vagas_default(self):
        """to_dict deve incluir numero_vagas=1 por default."""
        vaga = VagaAtomica(
            data=date(2026, 1, 26),
            dia_semana=DiaSemana.SEGUNDA,
            periodo=Periodo.MANHA,
            valor=1700,
            hospital_raw="Hospital ABC",
        )

        d = vaga.to_dict()
        assert d["numero_vagas"] == 1

    def test_to_dict_inclui_numero_vagas_custom(self):
        """to_dict deve incluir numero_vagas quando definido."""
        vaga = VagaAtomica(
            data=date(2026, 1, 26),
            dia_semana=DiaSemana.SEGUNDA,
            periodo=Periodo.MANHA,
            valor=1700,
            hospital_raw="Hospital ABC",
            numero_vagas=5,
        )

        d = vaga.to_dict()
        assert d["numero_vagas"] == 5

    def test_to_dict_campos_obrigatorios(self):
        """to_dict deve incluir todos os campos esperados."""
        vaga = VagaAtomica(
            data=date(2026, 1, 26),
            dia_semana=DiaSemana.SEGUNDA,
            periodo=Periodo.MANHA,
            valor=1700,
            hospital_raw="Hospital ABC",
        )

        d = vaga.to_dict()
        assert "data" in d
        assert "dia_semana" in d
        assert "periodo" in d
        assert "valor" in d
        assert "hospital_raw" in d
        assert "numero_vagas" in d
