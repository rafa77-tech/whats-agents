"""
Testes para Sprint 63: Extração de Setor + Agente de Recuperação.

Cobre:
- Épico A: Extração de setor pelo LLM
- Épico B: Validação completa (6 campos obrigatórios)
- Épico C: Safety net — hospital match sem sufixo
- Épico D: Agente de recuperação de vagas incompletas
"""

import pytest
from datetime import date, time
from uuid import uuid4, UUID
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.grupos.extrator_v2.types import VagaAtomica, DiaSemana, Periodo
from app.services.grupos.extrator_v2.extrator_llm import (
    converter_para_vagas_atomicas,
    ResultadoExtracaoLLM,
    PROMPT_EXTRACAO_UNIFICADA,
)
from app.services.grupos.normalizador import (
    ResultadoNormalizacao,
    MAPA_SETORES,
)
from app.services.grupos.recovery_agent import (
    extrair_campos_faltando,
    montar_mensagem_recovery,
    listar_vagas_incompletas,
    resolver_telefone_anunciante,
    executar_recovery,
)


# =============================================================================
# Épico A: Extração de Setor
# =============================================================================


class TestExtracaoSetor:
    """Testes para extração de setor pelo LLM."""

    def test_prompt_contem_regra_setor(self):
        """Prompt deve conter regra 8 sobre HOSPITAL vs SETOR."""
        assert "HOSPITAL vs SETOR" in PROMPT_EXTRACAO_UNIFICADA
        assert '"setor"' in PROMPT_EXTRACAO_UNIFICADA

    def test_prompt_contem_setores_comuns(self):
        """Prompt deve listar setores comuns."""
        assert "PS, pronto-socorro, UTI, centro cirúrgico" in PROMPT_EXTRACAO_UNIFICADA

    def test_vaga_atomica_tem_setor_raw(self):
        """VagaAtomica deve ter campo setor_raw."""
        vaga = VagaAtomica(
            data=date(2026, 3, 1),
            dia_semana=DiaSemana.SEGUNDA,
            periodo=Periodo.DIURNO,
            valor=2500,
            hospital_raw="Hospital São Luiz",
            setor_raw="UTI",
        )
        assert vaga.setor_raw == "UTI"

    def test_vaga_atomica_setor_raw_default_none(self):
        """VagaAtomica setor_raw deve ser None por default."""
        vaga = VagaAtomica(
            data=date(2026, 3, 1),
            dia_semana=DiaSemana.SEGUNDA,
            periodo=Periodo.DIURNO,
            valor=2500,
            hospital_raw="Hospital São Luiz",
        )
        assert vaga.setor_raw is None

    def test_vaga_atomica_to_dict_inclui_setor_raw(self):
        """to_dict deve incluir setor_raw."""
        vaga = VagaAtomica(
            data=date(2026, 3, 1),
            dia_semana=DiaSemana.SEGUNDA,
            periodo=Periodo.DIURNO,
            valor=2500,
            hospital_raw="Hospital São Luiz",
            setor_raw="PS",
        )
        d = vaga.to_dict()
        assert "setor_raw" in d
        assert d["setor_raw"] == "PS"

    def test_converter_llm_com_setor(self):
        """converter_para_vagas_atomicas deve mapear setor do LLM."""
        resultado = ResultadoExtracaoLLM(
            eh_vaga=True,
            confianca=0.9,
            vagas=[
                {
                    "hospital": "Hospital São Luiz",
                    "setor": "UTI Adulto",
                    "especialidade": "Medicina Intensiva",
                    "data": "2026-03-01",
                    "dia_semana": "segunda",
                    "periodo": "noturno",
                    "hora_inicio": "19:00",
                    "hora_fim": "07:00",
                    "valor": 3000,
                    "numero_vagas": 1,
                }
            ],
        )
        vagas = converter_para_vagas_atomicas(resultado)
        assert len(vagas) == 1
        assert vagas[0].setor_raw == "UTI Adulto"
        assert vagas[0].hospital_raw == "Hospital São Luiz"

    def test_converter_llm_sem_setor(self):
        """converter_para_vagas_atomicas deve aceitar setor None."""
        resultado = ResultadoExtracaoLLM(
            eh_vaga=True,
            confianca=0.9,
            vagas=[
                {
                    "hospital": "Hospital São Luiz",
                    "especialidade": "Clínica Médica",
                    "data": "2026-03-01",
                    "dia_semana": "segunda",
                    "periodo": "diurno",
                    "valor": 2500,
                }
            ],
        )
        vagas = converter_para_vagas_atomicas(resultado)
        assert len(vagas) == 1
        assert vagas[0].setor_raw is None

    def test_converter_llm_separa_hospital_e_setor(self):
        """LLM deve separar hospital e setor corretamente."""
        resultado = ResultadoExtracaoLLM(
            eh_vaga=True,
            confianca=0.9,
            vagas=[
                {
                    "hospital": "Hospital Cruz Azul",
                    "setor": "Ala da Prevent Senior",
                    "especialidade": "Clínica Médica",
                    "data": "2026-03-01",
                    "dia_semana": "segunda",
                    "periodo": "diurno",
                    "valor": 2000,
                }
            ],
        )
        vagas = converter_para_vagas_atomicas(resultado)
        assert vagas[0].hospital_raw == "Hospital Cruz Azul"
        assert vagas[0].setor_raw == "Ala da Prevent Senior"


# =============================================================================
# Épico B: Validação Completa
# =============================================================================


class TestValidacaoCompleta:
    """Testes para validação de 6 campos obrigatórios."""

    def _mock_vaga_data(self, **overrides):
        """Helper para criar dados de vaga mock."""
        base = {
            "hospital_raw": "Hospital São Luiz",
            "especialidade_raw": "Clínica Médica",
            "setor_raw": "PS",
            "data": "2026-03-01",
            "hora_inicio": "07:00",
            "hora_fim": "19:00",
            "valor": 2500,
            "grupo_origem_id": str(uuid4()),
        }
        base.update(overrides)
        return base

    @pytest.mark.asyncio
    @patch("app.services.grupos.normalizador.supabase")
    async def test_vaga_completa_normalizada(self, mock_supabase):
        """Vaga com todos os 6 campos e scores OK → normalizada."""
        from app.services.grupos.normalizador import normalizar_vaga

        vaga_id = uuid4()
        dados = self._mock_vaga_data()

        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=dados
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        hospital_id = uuid4()
        esp_id = uuid4()
        setor_id = uuid4()

        with (
            patch(
                "app.services.grupos.hospital_web.normalizar_ou_criar_hospital",
                new_callable=AsyncMock,
            ) as mock_hosp,
            patch(
                "app.services.grupos.normalizador.normalizar_especialidade",
                new_callable=AsyncMock,
            ) as mock_esp,
            patch(
                "app.services.grupos.normalizador.normalizar_periodo",
                new_callable=AsyncMock,
                return_value=uuid4(),
            ),
            patch(
                "app.services.grupos.normalizador.normalizar_setor",
                new_callable=AsyncMock,
                return_value=setor_id,
            ),
        ):
            mock_hosp.return_value = MagicMock(
                hospital_id=hospital_id, nome="Hospital São Luiz", score=0.95
            )
            mock_esp.return_value = MagicMock(
                entidade_id=esp_id, nome="Clínica Médica", score=0.90
            )

            resultado = await normalizar_vaga(vaga_id)

        assert resultado.status == "normalizada"
        assert resultado.hospital_id == hospital_id
        assert resultado.especialidade_id == esp_id
        assert resultado.setor_id == setor_id

    @pytest.mark.asyncio
    @patch("app.services.grupos.normalizador.supabase")
    async def test_vaga_sem_setor_aguardando_revisao(self, mock_supabase):
        """Vaga sem setor_raw → aguardando_revisao com match_incompleto:setor."""
        from app.services.grupos.normalizador import normalizar_vaga

        vaga_id = uuid4()
        dados = self._mock_vaga_data(setor_raw=None)

        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=dados
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with (
            patch(
                "app.services.grupos.hospital_web.normalizar_ou_criar_hospital",
                new_callable=AsyncMock,
            ) as mock_hosp,
            patch(
                "app.services.grupos.normalizador.normalizar_especialidade",
                new_callable=AsyncMock,
            ) as mock_esp,
            patch(
                "app.services.grupos.normalizador.normalizar_periodo",
                new_callable=AsyncMock,
                return_value=uuid4(),
            ),
            patch(
                "app.services.grupos.normalizador.normalizar_setor",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            mock_hosp.return_value = MagicMock(
                hospital_id=uuid4(), nome="Hospital São Luiz", score=0.95
            )
            mock_esp.return_value = MagicMock(
                entidade_id=uuid4(), nome="Clínica Médica", score=0.90
            )

            resultado = await normalizar_vaga(vaga_id)

        assert resultado.status == "aguardando_revisao"
        assert "setor" in resultado.motivo_status

    @pytest.mark.asyncio
    @patch("app.services.grupos.normalizador.supabase")
    async def test_vaga_sem_data_aguardando_revisao(self, mock_supabase):
        """Vaga sem data → aguardando_revisao com match_incompleto:data."""
        from app.services.grupos.normalizador import normalizar_vaga

        vaga_id = uuid4()
        dados = self._mock_vaga_data(data=None)

        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=dados
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with (
            patch(
                "app.services.grupos.hospital_web.normalizar_ou_criar_hospital",
                new_callable=AsyncMock,
            ) as mock_hosp,
            patch(
                "app.services.grupos.normalizador.normalizar_especialidade",
                new_callable=AsyncMock,
            ) as mock_esp,
            patch(
                "app.services.grupos.normalizador.normalizar_periodo",
                new_callable=AsyncMock,
                return_value=uuid4(),
            ),
            patch(
                "app.services.grupos.normalizador.normalizar_setor",
                new_callable=AsyncMock,
                return_value=uuid4(),
            ),
        ):
            mock_hosp.return_value = MagicMock(
                hospital_id=uuid4(), nome="Hospital São Luiz", score=0.95
            )
            mock_esp.return_value = MagicMock(
                entidade_id=uuid4(), nome="Clínica Médica", score=0.90
            )

            resultado = await normalizar_vaga(vaga_id)

        assert resultado.status == "aguardando_revisao"
        assert "data" in resultado.motivo_status

    @pytest.mark.asyncio
    @patch("app.services.grupos.normalizador.supabase")
    async def test_vaga_sem_horario_nem_periodo_aguardando_revisao(self, mock_supabase):
        """Vaga sem hora_inicio/hora_fim E sem periodo → aguardando_revisao."""
        from app.services.grupos.normalizador import normalizar_vaga

        vaga_id = uuid4()
        dados = self._mock_vaga_data(hora_inicio=None, hora_fim=None, periodo=None)

        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=dados
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with (
            patch(
                "app.services.grupos.hospital_web.normalizar_ou_criar_hospital",
                new_callable=AsyncMock,
            ) as mock_hosp,
            patch(
                "app.services.grupos.normalizador.normalizar_especialidade",
                new_callable=AsyncMock,
            ) as mock_esp,
            patch(
                "app.services.grupos.normalizador.normalizar_periodo",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.normalizador.normalizar_setor",
                new_callable=AsyncMock,
                return_value=uuid4(),
            ),
        ):
            mock_hosp.return_value = MagicMock(
                hospital_id=uuid4(), nome="Hospital São Luiz", score=0.95
            )
            mock_esp.return_value = MagicMock(
                entidade_id=uuid4(), nome="Clínica Médica", score=0.90
            )

            resultado = await normalizar_vaga(vaga_id)

        assert resultado.status == "aguardando_revisao"
        assert "horario" in resultado.motivo_status

    @pytest.mark.asyncio
    @patch("app.services.grupos.normalizador.supabase")
    async def test_vaga_com_periodo_sem_horario_normalizada(self, mock_supabase):
        """Vaga com periodo mas sem hora_inicio/hora_fim → OK (periodo substitui)."""
        from app.services.grupos.normalizador import normalizar_vaga

        vaga_id = uuid4()
        # periodo (campo do pipeline v2) substitui hora_inicio/hora_fim
        dados = self._mock_vaga_data(hora_inicio=None, hora_fim=None, periodo="noturno")

        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=dados
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        setor_id = uuid4()

        with (
            patch(
                "app.services.grupos.hospital_web.normalizar_ou_criar_hospital",
                new_callable=AsyncMock,
            ) as mock_hosp,
            patch(
                "app.services.grupos.normalizador.normalizar_especialidade",
                new_callable=AsyncMock,
            ) as mock_esp,
            patch(
                "app.services.grupos.normalizador.normalizar_periodo",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.normalizador.normalizar_setor",
                new_callable=AsyncMock,
                return_value=setor_id,
            ),
        ):
            mock_hosp.return_value = MagicMock(
                hospital_id=uuid4(), nome="Hospital São Luiz", score=0.95
            )
            mock_esp.return_value = MagicMock(
                entidade_id=uuid4(), nome="Clínica Médica", score=0.90
            )

            resultado = await normalizar_vaga(vaga_id)

        assert resultado.status == "normalizada"

    @pytest.mark.asyncio
    @patch("app.services.grupos.normalizador.supabase")
    async def test_vaga_so_hora_inicio_sem_fim_e_sem_periodo_falta_horario(self, mock_supabase):
        """Vaga com hora_inicio mas sem hora_fim e sem periodo → falta horario."""
        from app.services.grupos.normalizador import normalizar_vaga

        vaga_id = uuid4()
        dados = self._mock_vaga_data(hora_inicio="07:00", hora_fim=None, periodo=None)

        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=dados
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with (
            patch(
                "app.services.grupos.hospital_web.normalizar_ou_criar_hospital",
                new_callable=AsyncMock,
            ) as mock_hosp,
            patch(
                "app.services.grupos.normalizador.normalizar_especialidade",
                new_callable=AsyncMock,
            ) as mock_esp,
            patch(
                "app.services.grupos.normalizador.normalizar_periodo",
                new_callable=AsyncMock,
            ) as mock_periodo,
            patch(
                "app.services.grupos.normalizador.normalizar_setor",
                new_callable=AsyncMock,
                return_value=uuid4(),
            ),
        ):
            mock_hosp.return_value = MagicMock(
                hospital_id=uuid4(), nome="Hospital São Luiz", score=0.95
            )
            mock_esp.return_value = MagicMock(
                entidade_id=uuid4(), nome="Clínica Médica", score=0.90
            )
            # inferir_periodo_por_horario pode retornar algo, mas sem hora_fim
            # o normalizar_periodo pode não resolver — simular que não resolveu
            mock_periodo.return_value = None

            resultado = await normalizar_vaga(vaga_id)

        assert resultado.status == "aguardando_revisao"
        assert "horario" in resultado.motivo_status

    @pytest.mark.asyncio
    @patch("app.services.grupos.normalizador.supabase")
    async def test_vaga_sem_valor_aguardando_revisao(self, mock_supabase):
        """Vaga sem valor → aguardando_revisao com match_incompleto:valor."""
        from app.services.grupos.normalizador import normalizar_vaga

        vaga_id = uuid4()
        dados = self._mock_vaga_data(valor=None)

        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=dados
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with (
            patch(
                "app.services.grupos.hospital_web.normalizar_ou_criar_hospital",
                new_callable=AsyncMock,
            ) as mock_hosp,
            patch(
                "app.services.grupos.normalizador.normalizar_especialidade",
                new_callable=AsyncMock,
            ) as mock_esp,
            patch(
                "app.services.grupos.normalizador.normalizar_periodo",
                new_callable=AsyncMock,
                return_value=uuid4(),
            ),
            patch(
                "app.services.grupos.normalizador.normalizar_setor",
                new_callable=AsyncMock,
                return_value=uuid4(),
            ),
        ):
            mock_hosp.return_value = MagicMock(
                hospital_id=uuid4(), nome="Hospital São Luiz", score=0.95
            )
            mock_esp.return_value = MagicMock(
                entidade_id=uuid4(), nome="Clínica Médica", score=0.90
            )

            resultado = await normalizar_vaga(vaga_id)

        assert resultado.status == "aguardando_revisao"
        assert "valor" in resultado.motivo_status

    @pytest.mark.asyncio
    @patch("app.services.grupos.normalizador.supabase")
    async def test_vaga_multiplos_campos_faltando(self, mock_supabase):
        """Vaga faltando setor e valor → motivo combina corretamente."""
        from app.services.grupos.normalizador import normalizar_vaga

        vaga_id = uuid4()
        dados = self._mock_vaga_data(setor_raw=None, valor=None)

        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=dados
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with (
            patch(
                "app.services.grupos.hospital_web.normalizar_ou_criar_hospital",
                new_callable=AsyncMock,
            ) as mock_hosp,
            patch(
                "app.services.grupos.normalizador.normalizar_especialidade",
                new_callable=AsyncMock,
            ) as mock_esp,
            patch(
                "app.services.grupos.normalizador.normalizar_periodo",
                new_callable=AsyncMock,
                return_value=uuid4(),
            ),
            patch(
                "app.services.grupos.normalizador.normalizar_setor",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            mock_hosp.return_value = MagicMock(
                hospital_id=uuid4(), nome="Hospital São Luiz", score=0.95
            )
            mock_esp.return_value = MagicMock(
                entidade_id=uuid4(), nome="Clínica Médica", score=0.90
            )

            resultado = await normalizar_vaga(vaga_id)

        assert resultado.status == "aguardando_revisao"
        assert "setor" in resultado.motivo_status
        assert "valor" in resultado.motivo_status
        assert resultado.motivo_status == "match_incompleto:setor,valor"


class TestTipoVagaExtracao:
    """Testes para extração de tipo_vaga pelo LLM."""

    def test_prompt_contem_regra_tipo_vaga(self):
        """Prompt deve conter regra 9 sobre TIPO DE VAGA."""
        assert "TIPO DE VAGA" in PROMPT_EXTRACAO_UNIFICADA
        assert "ambulatorial" in PROMPT_EXTRACAO_UNIFICADA
        assert '"tipo_vaga"' in PROMPT_EXTRACAO_UNIFICADA

    def test_vaga_atomica_tem_tipo_vaga_raw(self):
        """VagaAtomica deve ter campo tipo_vaga_raw."""
        vaga = VagaAtomica(
            data=date(2026, 3, 1),
            dia_semana=DiaSemana.SEGUNDA,
            periodo=Periodo.DIURNO,
            valor=2500,
            hospital_raw="Hospital São Luiz",
            tipo_vaga_raw="ambulatorial",
        )
        assert vaga.tipo_vaga_raw == "ambulatorial"

    def test_vaga_atomica_tipo_vaga_default_none(self):
        """VagaAtomica tipo_vaga_raw deve ser None por default."""
        vaga = VagaAtomica(
            data=date(2026, 3, 1),
            dia_semana=DiaSemana.SEGUNDA,
            periodo=Periodo.DIURNO,
            valor=2500,
            hospital_raw="Hospital São Luiz",
        )
        assert vaga.tipo_vaga_raw is None

    def test_vaga_atomica_to_dict_inclui_tipo_vaga_raw(self):
        """to_dict deve incluir tipo_vaga_raw."""
        vaga = VagaAtomica(
            data=date(2026, 3, 1),
            dia_semana=DiaSemana.SEGUNDA,
            periodo=Periodo.DIURNO,
            valor=2500,
            hospital_raw="Hospital São Luiz",
            tipo_vaga_raw="cobertura",
        )
        d = vaga.to_dict()
        assert d["tipo_vaga_raw"] == "cobertura"

    def test_converter_llm_com_tipo_vaga(self):
        """converter_para_vagas_atomicas deve mapear tipo_vaga do LLM."""
        resultado = ResultadoExtracaoLLM(
            eh_vaga=True,
            confianca=0.9,
            vagas=[
                {
                    "hospital": "Clínica Santos",
                    "especialidade": "Ginecologia e Obstetrícia",
                    "data": "2026-03-01",
                    "dia_semana": "segunda",
                    "periodo": "manha",
                    "valor": 500,
                    "tipo_vaga": "ambulatorial",
                }
            ],
        )
        vagas = converter_para_vagas_atomicas(resultado)
        assert len(vagas) == 1
        assert vagas[0].tipo_vaga_raw == "ambulatorial"


class TestValidacaoAmbulatorial:
    """Testes para validação condicional de ambulatoriais."""

    def _mock_vaga_data(self, **overrides):
        base = {
            "hospital_raw": "Clínica Santos",
            "especialidade_raw": "Ginecologia e Obstetrícia",
            "setor_raw": "Consultório",
            "data": "2026-03-01",
            "hora_inicio": None,
            "hora_fim": None,
            "periodo": None,
            "periodo_raw": None,
            "valor": 500,
            "tipo_vaga_raw": "ambulatorial",
            "grupo_origem_id": str(uuid4()),
        }
        base.update(overrides)
        return base

    @pytest.mark.asyncio
    @patch("app.services.grupos.normalizador.supabase")
    async def test_ambulatorial_sem_horario_normalizada(self, mock_supabase):
        """Ambulatorial sem hora e sem periodo → normalizada (não exige horário)."""
        from app.services.grupos.normalizador import normalizar_vaga

        vaga_id = uuid4()
        dados = self._mock_vaga_data()

        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=dados
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with (
            patch(
                "app.services.grupos.hospital_web.normalizar_ou_criar_hospital",
                new_callable=AsyncMock,
            ) as mock_hosp,
            patch(
                "app.services.grupos.normalizador.normalizar_especialidade",
                new_callable=AsyncMock,
            ) as mock_esp,
            patch(
                "app.services.grupos.normalizador.normalizar_periodo",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.normalizador.normalizar_setor",
                new_callable=AsyncMock,
                return_value=uuid4(),
            ),
        ):
            mock_hosp.return_value = MagicMock(
                hospital_id=uuid4(), nome="Clínica Santos", score=0.95
            )
            mock_esp.return_value = MagicMock(
                entidade_id=uuid4(), nome="Ginecologia e Obstetrícia", score=0.90
            )

            resultado = await normalizar_vaga(vaga_id)

        assert resultado.status == "normalizada"
        assert resultado.motivo_status is None

    @pytest.mark.asyncio
    @patch("app.services.grupos.normalizador.supabase")
    async def test_plantao_sem_horario_falta_horario(self, mock_supabase):
        """Plantão sem hora e sem periodo → falta horario (exige horário)."""
        from app.services.grupos.normalizador import normalizar_vaga

        vaga_id = uuid4()
        dados = self._mock_vaga_data(tipo_vaga_raw="plantao")

        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=dados
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with (
            patch(
                "app.services.grupos.hospital_web.normalizar_ou_criar_hospital",
                new_callable=AsyncMock,
            ) as mock_hosp,
            patch(
                "app.services.grupos.normalizador.normalizar_especialidade",
                new_callable=AsyncMock,
            ) as mock_esp,
            patch(
                "app.services.grupos.normalizador.normalizar_periodo",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.normalizador.normalizar_setor",
                new_callable=AsyncMock,
                return_value=uuid4(),
            ),
        ):
            mock_hosp.return_value = MagicMock(
                hospital_id=uuid4(), nome="Clínica Santos", score=0.95
            )
            mock_esp.return_value = MagicMock(
                entidade_id=uuid4(), nome="Ginecologia e Obstetrícia", score=0.90
            )

            resultado = await normalizar_vaga(vaga_id)

        assert resultado.status == "aguardando_revisao"
        assert "horario" in resultado.motivo_status

    @pytest.mark.asyncio
    @patch("app.services.grupos.normalizador.supabase")
    async def test_sem_tipo_vaga_assume_plantao(self, mock_supabase):
        """Sem tipo_vaga_raw → assume plantão, exige horário."""
        from app.services.grupos.normalizador import normalizar_vaga

        vaga_id = uuid4()
        dados = self._mock_vaga_data(tipo_vaga_raw=None)

        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=dados
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with (
            patch(
                "app.services.grupos.hospital_web.normalizar_ou_criar_hospital",
                new_callable=AsyncMock,
            ) as mock_hosp,
            patch(
                "app.services.grupos.normalizador.normalizar_especialidade",
                new_callable=AsyncMock,
            ) as mock_esp,
            patch(
                "app.services.grupos.normalizador.normalizar_periodo",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.normalizador.normalizar_setor",
                new_callable=AsyncMock,
                return_value=uuid4(),
            ),
        ):
            mock_hosp.return_value = MagicMock(
                hospital_id=uuid4(), nome="Clínica Santos", score=0.95
            )
            mock_esp.return_value = MagicMock(
                entidade_id=uuid4(), nome="Ginecologia e Obstetrícia", score=0.90
            )

            resultado = await normalizar_vaga(vaga_id)

        assert resultado.status == "aguardando_revisao"
        assert "horario" in resultado.motivo_status


class TestMapaSetoresExpandido:
    """Testes para MAPA_SETORES expandido."""

    def test_centro_obstetrico(self):
        assert MAPA_SETORES["centro obstetrico"] == "C. Obstétrico"
        assert MAPA_SETORES["centro obstétrico"] == "C. Obstétrico"
        assert MAPA_SETORES["co"] == "C. Obstétrico"

    def test_consultorio(self):
        assert MAPA_SETORES["consultorio"] == "Consultório"
        assert MAPA_SETORES["consultório"] == "Consultório"

    def test_ala_e_unidade(self):
        assert MAPA_SETORES["ala"] == "Hospital"
        assert MAPA_SETORES["unidade"] == "Hospital"

    def test_uti_variantes(self):
        assert MAPA_SETORES["uti"] == "Hospital"
        assert MAPA_SETORES["uti adulto"] == "Hospital"
        assert MAPA_SETORES["uti pediatrica"] == "Hospital"
        assert MAPA_SETORES["uti neonatal"] == "Hospital"

    def test_maternidade(self):
        assert MAPA_SETORES["maternidade"] == "C. Obstétrico"

    def test_emergencia_com_acento(self):
        assert MAPA_SETORES["emergência"] == "Pronto atendimento"


# =============================================================================
# Épico C: Safety Net — Hospital Match sem Sufixo
# =============================================================================


class TestSafetyNetHospital:
    """Testes para match de hospital sem sufixo."""

    @pytest.mark.asyncio
    async def test_normalizar_com_sufixo_setor_encontra_alias(self):
        """Hospital com ' - Setor' deve encontrar via alias sem sufixo."""
        from app.services.grupos.hospital_web import normalizar_ou_criar_hospital

        hospital_id = uuid4()
        mock_match = MagicMock(entidade_id=hospital_id, nome="Hospital Cruz Azul", score=0.95)

        with (
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_alias",
                new_callable=AsyncMock,
            ) as mock_alias,
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_similaridade",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.hospital_web._emitir_evento_hospital",
                new_callable=AsyncMock,
            ),
        ):
            # Primeira chamada with full text: not found
            # Second call with texto_base: found
            mock_alias.side_effect = [None, mock_match]

            result = await normalizar_ou_criar_hospital("Hospital Cruz Azul - Ala da Prevent Senior")

        assert result is not None
        assert result.hospital_id == hospital_id
        assert result.fonte == "safety_net_sem_sufixo"

    @pytest.mark.asyncio
    async def test_normalizar_com_sufixo_setor_encontra_similaridade(self):
        """Hospital com ' - Setor' deve encontrar via similaridade sem sufixo."""
        from app.services.grupos.hospital_web import normalizar_ou_criar_hospital

        hospital_id = uuid4()
        mock_match = MagicMock(entidade_id=hospital_id, nome="Hospital Cruz Azul", score=0.85)

        with (
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_alias",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_similaridade",
                new_callable=AsyncMock,
            ) as mock_sim,
            patch(
                "app.services.grupos.hospital_web._emitir_evento_hospital",
                new_callable=AsyncMock,
            ),
        ):
            # First call with full text: not found
            # Second call with texto_base: found
            mock_sim.side_effect = [None, mock_match]

            result = await normalizar_ou_criar_hospital("Hospital Cruz Azul - UTI")

        assert result is not None
        assert result.hospital_id == hospital_id
        assert result.fonte == "safety_net_sem_sufixo"

    @pytest.mark.asyncio
    async def test_normalizar_sem_sufixo_nao_altera_comportamento(self):
        """Texto sem separador deve seguir fluxo normal."""
        from app.services.grupos.hospital_web import normalizar_ou_criar_hospital

        hospital_id = uuid4()
        mock_match = MagicMock(entidade_id=hospital_id, nome="Hospital São Luiz", score=0.95)

        with (
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_alias",
                new_callable=AsyncMock,
                return_value=mock_match,
            ),
            patch(
                "app.services.grupos.hospital_web._emitir_evento_hospital",
                new_callable=AsyncMock,
            ),
        ):
            result = await normalizar_ou_criar_hospital("Hospital São Luiz")

        assert result is not None
        assert result.fonte == "alias_exato"

    @pytest.mark.asyncio
    async def test_normalizar_com_parenteses(self):
        """Hospital com ' (Ala)' deve tentar match sem sufixo."""
        from app.services.grupos.hospital_web import normalizar_ou_criar_hospital

        hospital_id = uuid4()
        mock_match = MagicMock(entidade_id=hospital_id, nome="Hospital ABC", score=0.90)

        with (
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_alias",
                new_callable=AsyncMock,
            ) as mock_alias,
            patch(
                "app.services.grupos.normalizador.buscar_hospital_por_similaridade",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.grupos.hospital_web._emitir_evento_hospital",
                new_callable=AsyncMock,
            ),
        ):
            mock_alias.side_effect = [None, mock_match]

            result = await normalizar_ou_criar_hospital("Hospital ABC (Ala Norte)")

        assert result is not None
        assert result.hospital_id == hospital_id
        assert result.fonte == "safety_net_sem_sufixo"


# =============================================================================
# Épico D: Recovery Agent
# =============================================================================


class TestExtrairCamposFaltando:
    """Testes para extração de campos do motivo_status."""

    def test_extrai_campo_unico(self):
        assert extrair_campos_faltando("match_incompleto:setor") == ["setor"]

    def test_extrai_multiplos_campos(self):
        assert extrair_campos_faltando("match_incompleto:setor,valor") == [
            "setor",
            "valor",
        ]

    def test_extrai_todos_campos(self):
        campos = extrair_campos_faltando(
            "match_incompleto:hospital,especialidade,setor,data,horario,valor"
        )
        assert len(campos) == 6

    def test_motivo_sem_match_incompleto(self):
        assert extrair_campos_faltando("score_baixo") == []

    def test_motivo_none(self):
        assert extrair_campos_faltando(None) == []

    def test_motivo_vazio(self):
        assert extrair_campos_faltando("") == []


class TestMontarMensagemRecovery:
    """Testes para montagem da mensagem de recuperação."""

    def test_mensagem_campo_unico_setor(self):
        msg = montar_mensagem_recovery(["setor"], "Plantões SP")
        assert "setor" in msg
        assert "Plantões SP" in msg
        assert "😊" in msg

    def test_mensagem_campo_unico_valor(self):
        msg = montar_mensagem_recovery(["valor"], "Plantões RJ")
        assert "valor do plantão" in msg

    def test_mensagem_multiplos_campos(self):
        msg = montar_mensagem_recovery(["setor", "valor"], "Plantões SP")
        assert "setor" in msg
        assert "valor" in msg
        assert " e " in msg

    def test_mensagem_com_hospital(self):
        msg = montar_mensagem_recovery(
            ["setor"], "Plantões SP", hospital_raw="Hospital São Luiz"
        )
        assert "Hospital São Luiz" in msg

    def test_mensagem_sem_hospital(self):
        msg = montar_mensagem_recovery(["data"], "Plantões SP")
        assert "Plantões SP" in msg

    def test_mensagem_campos_invalidos_retorna_vazio(self):
        msg = montar_mensagem_recovery(["campo_inexistente"], "Grupo")
        assert msg == ""


class TestListarVagasIncompletas:
    """Testes para busca de vagas incompletas."""

    @pytest.mark.asyncio
    @patch("app.services.grupos.recovery_agent.supabase")
    async def test_busca_vagas_incompletas(self, mock_supabase):
        """Deve buscar vagas com status aguardando_revisao e sem DM."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.like.return_value.is_.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[
                {"id": str(uuid4()), "motivo_status": "match_incompleto:setor"},
                {"id": str(uuid4()), "motivo_status": "match_incompleto:setor,valor"},
            ]
        )

        vagas = await listar_vagas_incompletas(limite=20)
        assert len(vagas) == 2


class TestResolverTelefone:
    """Testes para resolução de telefone do anunciante."""

    @pytest.mark.asyncio
    async def test_resolve_via_divulgador(self):
        """Deve resolver telefone via buscar_divulgador_por_vaga_grupo."""
        vaga = {"id": str(uuid4()), "contato_whatsapp": None}

        with patch(
            "app.services.external_handoff.service.buscar_divulgador_por_vaga_grupo",
            new_callable=AsyncMock,
            return_value={"telefone": "5511999999999", "nome": "João"},
        ):
            telefone = await resolver_telefone_anunciante(vaga)

        assert telefone == "5511999999999"

    @pytest.mark.asyncio
    async def test_fallback_contato_whatsapp(self):
        """Deve usar contato_whatsapp como fallback quando divulgador não tem telefone."""
        vaga = {"id": str(uuid4()), "contato_whatsapp": "5511888888888"}

        with patch(
            "app.services.external_handoff.service.buscar_divulgador_por_vaga_grupo",
            new_callable=AsyncMock,
            return_value=None,
        ):
            telefone = await resolver_telefone_anunciante(vaga)

        assert telefone == "5511888888888"

    @pytest.mark.asyncio
    async def test_sem_telefone_retorna_none(self):
        """Deve retornar None quando não há telefone disponível."""
        vaga = {"id": str(uuid4()), "contato_whatsapp": None}

        with patch(
            "app.services.external_handoff.service.buscar_divulgador_por_vaga_grupo",
            new_callable=AsyncMock,
            return_value=None,
        ):
            telefone = await resolver_telefone_anunciante(vaga)

        assert telefone is None


class TestExecutarRecovery:
    """Testes para execução completa do recovery."""

    @pytest.mark.asyncio
    @patch("app.services.grupos.recovery_agent.enviar_dm_recovery", new_callable=AsyncMock)
    @patch("app.services.grupos.recovery_agent.buscar_nome_grupo", new_callable=AsyncMock)
    @patch(
        "app.services.grupos.recovery_agent.resolver_telefone_anunciante",
        new_callable=AsyncMock,
    )
    @patch(
        "app.services.grupos.recovery_agent.listar_vagas_incompletas",
        new_callable=AsyncMock,
    )
    async def test_executa_recovery_completo(
        self, mock_listar, mock_telefone, mock_grupo, mock_enviar
    ):
        """Deve enviar DMs para vagas incompletas."""
        vaga_id = str(uuid4())
        mock_listar.return_value = [
            {
                "id": vaga_id,
                "motivo_status": "match_incompleto:setor,valor",
                "hospital_raw": "Hospital ABC",
                "grupo_origem_id": str(uuid4()),
            }
        ]
        mock_telefone.return_value = "5511999999999"
        mock_grupo.return_value = "Plantões SP"
        mock_enviar.return_value = True

        stats = await executar_recovery(limite=20)

        assert stats["vagas_encontradas"] == 1
        assert stats["dms_enviados"] == 1
        mock_enviar.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        "app.services.grupos.recovery_agent.resolver_telefone_anunciante",
        new_callable=AsyncMock,
    )
    @patch(
        "app.services.grupos.recovery_agent.listar_vagas_incompletas",
        new_callable=AsyncMock,
    )
    async def test_dedup_nao_envia_dm_repetido(self, mock_listar, mock_telefone):
        """Não deve enviar DM para vagas que já têm dm_recovery_sent_at."""
        # listar_vagas_incompletas já filtra por dm_recovery_sent_at IS NULL
        # Então se retornar lista vazia, nenhum DM é enviado
        mock_listar.return_value = []

        stats = await executar_recovery()

        assert stats["vagas_encontradas"] == 0
        assert stats["dms_enviados"] == 0

    @pytest.mark.asyncio
    @patch(
        "app.services.grupos.recovery_agent.resolver_telefone_anunciante",
        new_callable=AsyncMock,
    )
    @patch(
        "app.services.grupos.recovery_agent.listar_vagas_incompletas",
        new_callable=AsyncMock,
    )
    async def test_sem_telefone_contabiliza(self, mock_listar, mock_telefone):
        """Vaga sem telefone deve ser contabilizada em sem_telefone."""
        mock_listar.return_value = [
            {
                "id": str(uuid4()),
                "motivo_status": "match_incompleto:setor",
                "hospital_raw": None,
                "grupo_origem_id": None,
            }
        ]
        mock_telefone.return_value = None

        stats = await executar_recovery()

        assert stats["sem_telefone"] == 1
        assert stats["dms_enviados"] == 0
