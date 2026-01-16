"""
Testes para serviço de priorização de médicos.

Sprint 32 E07 - Algoritmo de Priorização.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone


class TestCalcularScorePriorizacao:
    """Testes para calcular_score_priorizacao()."""

    @pytest.mark.asyncio
    async def test_score_aumenta_com_historico_positivo(self):
        """Médico com histórico positivo deve ter score maior."""
        from app.services.priorizacao_medicos import calcular_score_priorizacao

        medico = {
            "id": "m1",
            "especialidade": "cardiologia",
            "qualification_score": 0.5,
            "total_interacoes": 10,
            "ultima_mensagem_data": None,
        }

        vaga = {
            "id": "v1",
            "especialidades": {"nome": "cardiologia"},
        }

        with patch("app.services.priorizacao_medicos.verificar_historico_positivo") as mock_historico:
            # Sem histórico
            mock_historico.return_value = {"tem_historico": False, "total_plantoes": 0}
            score_sem = await calcular_score_priorizacao(medico, vaga)

            # Com histórico
            mock_historico.return_value = {"tem_historico": True, "total_plantoes": 3}
            score_com = await calcular_score_priorizacao(medico, vaga)

            assert score_com > score_sem

    @pytest.mark.asyncio
    async def test_score_aumenta_com_qualification_alto(self):
        """Médico com qualification_score alto deve ter score maior."""
        from app.services.priorizacao_medicos import calcular_score_priorizacao

        medico_baixo = {
            "id": "m1",
            "especialidade": "cardiologia",
            "qualification_score": 0.1,
            "total_interacoes": 10,
        }

        medico_alto = {
            "id": "m2",
            "especialidade": "cardiologia",
            "qualification_score": 0.9,
            "total_interacoes": 10,
        }

        vaga = {"id": "v1", "especialidades": {"nome": "cardiologia"}}

        with patch("app.services.priorizacao_medicos.verificar_historico_positivo") as mock_historico:
            mock_historico.return_value = {"tem_historico": False, "total_plantoes": 0}

            score_baixo = await calcular_score_priorizacao(medico_baixo, vaga)
            score_alto = await calcular_score_priorizacao(medico_alto, vaga)

            assert score_alto > score_baixo

    @pytest.mark.asyncio
    async def test_score_bonus_para_nunca_contatado(self):
        """Médico nunca contatado deve ter bonus no score."""
        from app.services.priorizacao_medicos import calcular_score_priorizacao

        medico_novo = {
            "id": "m1",
            "especialidade": "cardiologia",
            "qualification_score": 0.5,
            "total_interacoes": 0,  # Nunca contatado
        }

        medico_antigo = {
            "id": "m2",
            "especialidade": "cardiologia",
            "qualification_score": 0.5,
            "total_interacoes": 10,  # Já contatado
        }

        vaga = {"id": "v1", "especialidades": {"nome": "cardiologia"}}

        with patch("app.services.priorizacao_medicos.verificar_historico_positivo") as mock_historico:
            mock_historico.return_value = {"tem_historico": False, "total_plantoes": 0}

            score_novo = await calcular_score_priorizacao(medico_novo, vaga)
            score_antigo = await calcular_score_priorizacao(medico_antigo, vaga)

            assert score_novo > score_antigo

    @pytest.mark.asyncio
    async def test_score_penaliza_contato_muito_recente(self):
        """Médico contatado muito recentemente deve ter penalidade."""
        from app.services.priorizacao_medicos import calcular_score_priorizacao

        data_recente = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        data_ideal = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()

        medico_recente = {
            "id": "m1",
            "especialidade": "cardiologia",
            "qualification_score": 0.5,
            "total_interacoes": 5,
            "ultima_mensagem_data": data_recente,
        }

        medico_ideal = {
            "id": "m2",
            "especialidade": "cardiologia",
            "qualification_score": 0.5,
            "total_interacoes": 5,
            "ultima_mensagem_data": data_ideal,
        }

        vaga = {"id": "v1", "especialidades": {"nome": "cardiologia"}}

        with patch("app.services.priorizacao_medicos.verificar_historico_positivo") as mock_historico:
            mock_historico.return_value = {"tem_historico": False, "total_plantoes": 0}

            score_recente = await calcular_score_priorizacao(medico_recente, vaga)
            score_ideal = await calcular_score_priorizacao(medico_ideal, vaga)

            assert score_ideal > score_recente

    @pytest.mark.asyncio
    async def test_score_bonus_especialidade_match(self):
        """Match de especialidade deve dar bonus."""
        from app.services.priorizacao_medicos import calcular_score_priorizacao

        medico_match = {
            "id": "m1",
            "especialidade": "cardiologia",
            "qualification_score": 0.5,
            "total_interacoes": 5,
        }

        medico_outro = {
            "id": "m2",
            "especialidade": "pediatria",
            "qualification_score": 0.5,
            "total_interacoes": 5,
        }

        vaga = {"id": "v1", "especialidades": {"nome": "cardiologia"}}

        with patch("app.services.priorizacao_medicos.verificar_historico_positivo") as mock_historico:
            mock_historico.return_value = {"tem_historico": False, "total_plantoes": 0}

            score_match = await calcular_score_priorizacao(medico_match, vaga)
            score_outro = await calcular_score_priorizacao(medico_outro, vaga)

            assert score_match > score_outro


class TestVerificarHistoricoPositivo:
    """Testes para verificar_historico_positivo()."""

    @pytest.mark.asyncio
    async def test_retorna_true_quando_tem_historico(self):
        """Deve retornar tem_historico=True quando médico já fez plantão."""
        from app.services.priorizacao_medicos import verificar_historico_positivo

        with patch("app.services.priorizacao_medicos.supabase") as mock_supabase:
            mock_execute = MagicMock()
            mock_execute.data = [
                {"id": "v1", "hospital_id": "h1", "status": "realizada"},
                {"id": "v2", "hospital_id": "h2", "status": "reservada"},
            ]

            mock_supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.is_.return_value.limit.return_value.execute.return_value = mock_execute

            resultado = await verificar_historico_positivo("m1")

            assert resultado["tem_historico"] is True
            assert resultado["total_plantoes"] == 2

    @pytest.mark.asyncio
    async def test_retorna_false_quando_nao_tem_historico(self):
        """Deve retornar tem_historico=False quando médico nunca fez plantão."""
        from app.services.priorizacao_medicos import verificar_historico_positivo

        with patch("app.services.priorizacao_medicos.supabase") as mock_supabase:
            mock_execute = MagicMock()
            mock_execute.data = []

            mock_supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.is_.return_value.limit.return_value.execute.return_value = mock_execute

            resultado = await verificar_historico_positivo("m1")

            assert resultado["tem_historico"] is False
            assert resultado["total_plantoes"] == 0

    @pytest.mark.asyncio
    async def test_detecta_mesmo_hospital(self):
        """Deve indicar mesmo_hospital=True quando médico fez plantão no mesmo hospital."""
        from app.services.priorizacao_medicos import verificar_historico_positivo

        with patch("app.services.priorizacao_medicos.supabase") as mock_supabase:
            mock_execute = MagicMock()
            mock_execute.data = [
                {"id": "v1", "hospital_id": "hospital-alvo", "status": "realizada"},
            ]

            mock_supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.is_.return_value.limit.return_value.execute.return_value = mock_execute

            resultado = await verificar_historico_positivo("m1", hospital_id="hospital-alvo")

            assert resultado["mesmo_hospital"] is True


class TestPriorizarMedicos:
    """Testes para priorizar_medicos()."""

    @pytest.mark.asyncio
    async def test_ordena_por_score_decrescente(self):
        """Deve ordenar médicos por score decrescente."""
        from app.services.priorizacao_medicos import priorizar_medicos

        medicos = [
            {"id": "m1", "qualification_score": 0.3, "total_interacoes": 5},
            {"id": "m2", "qualification_score": 0.9, "total_interacoes": 5},
            {"id": "m3", "qualification_score": 0.6, "total_interacoes": 5},
        ]

        vaga = {"id": "v1", "especialidades": {"nome": "cardiologia"}}

        with patch("app.services.priorizacao_medicos.verificar_historico_positivo") as mock_historico:
            mock_historico.return_value = {"tem_historico": False, "total_plantoes": 0}

            resultado = await priorizar_medicos(medicos, vaga, limite=3)

            # m2 (score 0.9) deve vir primeiro
            assert resultado[0]["id"] == "m2"

    @pytest.mark.asyncio
    async def test_respeita_limite(self):
        """Deve respeitar o limite de médicos retornados."""
        from app.services.priorizacao_medicos import priorizar_medicos

        medicos = [
            {"id": f"m{i}", "qualification_score": 0.5, "total_interacoes": i}
            for i in range(10)
        ]

        vaga = {"id": "v1", "especialidades": {"nome": "cardiologia"}}

        with patch("app.services.priorizacao_medicos.verificar_historico_positivo") as mock_historico:
            mock_historico.return_value = {"tem_historico": False, "total_plantoes": 0}

            resultado = await priorizar_medicos(medicos, vaga, limite=5)

            assert len(resultado) == 5

    @pytest.mark.asyncio
    async def test_lista_vazia_retorna_lista_vazia(self):
        """Deve retornar lista vazia quando input é vazio."""
        from app.services.priorizacao_medicos import priorizar_medicos

        resultado = await priorizar_medicos([], {"id": "v1"}, limite=5)

        assert resultado == []


class TestFiltrarMedicosContatadosRecentemente:
    """Testes para filtrar_medicos_contatados_recentemente()."""

    @pytest.mark.asyncio
    async def test_remove_medicos_contatados_recentemente(self):
        """Deve remover médicos contatados nos últimos X dias."""
        from app.services.priorizacao_medicos import filtrar_medicos_contatados_recentemente

        data_recente = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        data_antiga = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

        medicos = [
            {"id": "m1", "ultima_mensagem_data": data_recente},  # Contatado há 2 dias
            {"id": "m2", "ultima_mensagem_data": data_antiga},   # Contatado há 30 dias
            {"id": "m3", "ultima_mensagem_data": None},          # Nunca contatado
        ]

        resultado = await filtrar_medicos_contatados_recentemente(medicos, dias_minimo=7)

        # Apenas m2 e m3 devem passar
        assert len(resultado) == 2
        ids = [m["id"] for m in resultado]
        assert "m1" not in ids
        assert "m2" in ids
        assert "m3" in ids


class TestFiltrarMedicosEmConversaAtiva:
    """Testes para filtrar_medicos_em_conversa_ativa()."""

    @pytest.mark.asyncio
    async def test_remove_medicos_em_conversa_ativa(self):
        """Deve remover médicos que estão em conversa ativa."""
        from app.services.priorizacao_medicos import filtrar_medicos_em_conversa_ativa

        medicos = [
            {"id": "m1"},
            {"id": "m2"},
            {"id": "m3"},
        ]

        with patch("app.services.priorizacao_medicos.supabase") as mock_supabase:
            mock_execute = MagicMock()
            mock_execute.data = [{"cliente_id": "m2"}]  # m2 está em conversa

            mock_supabase.table.return_value.select.return_value.in_.return_value.eq.return_value.execute.return_value = mock_execute

            resultado = await filtrar_medicos_em_conversa_ativa(medicos)

            assert len(resultado) == 2
            ids = [m["id"] for m in resultado]
            assert "m2" not in ids

    @pytest.mark.asyncio
    async def test_retorna_todos_quando_nenhum_em_conversa(self):
        """Deve retornar todos quando nenhum está em conversa."""
        from app.services.priorizacao_medicos import filtrar_medicos_em_conversa_ativa

        medicos = [{"id": "m1"}, {"id": "m2"}]

        with patch("app.services.priorizacao_medicos.supabase") as mock_supabase:
            mock_execute = MagicMock()
            mock_execute.data = []

            mock_supabase.table.return_value.select.return_value.in_.return_value.eq.return_value.execute.return_value = mock_execute

            resultado = await filtrar_medicos_em_conversa_ativa(medicos)

            assert len(resultado) == 2


class TestFiltrarMedicosNaFila:
    """Testes para filtrar_medicos_na_fila()."""

    @pytest.mark.asyncio
    async def test_remove_medicos_na_fila(self):
        """Deve remover médicos que já estão na fila."""
        from app.services.priorizacao_medicos import filtrar_medicos_na_fila

        medicos = [{"id": "m1"}, {"id": "m2"}, {"id": "m3"}]

        with patch("app.services.priorizacao_medicos.supabase") as mock_supabase:
            mock_execute = MagicMock()
            mock_execute.data = [{"cliente_id": "m1"}, {"cliente_id": "m3"}]

            mock_supabase.table.return_value.select.return_value.in_.return_value.in_.return_value.eq.return_value.execute.return_value = mock_execute

            resultado = await filtrar_medicos_na_fila(medicos, tipo_mensagem="oferta")

            assert len(resultado) == 1
            assert resultado[0]["id"] == "m2"


class TestSelecionarMedicosParaOferta:
    """Testes para selecionar_medicos_para_oferta()."""

    @pytest.mark.asyncio
    async def test_selecao_completa(self):
        """Deve executar seleção completa com todos os filtros."""
        from app.services.priorizacao_medicos import selecionar_medicos_para_oferta

        vaga = {
            "id": "v1",
            "especialidades": {"nome": "cardiologia"},
        }

        with patch("app.services.gatilhos_autonomos.buscar_medicos_compativeis_para_vaga") as mock_buscar:
            mock_buscar.return_value = [
                {"id": "m1", "qualification_score": 0.8, "total_interacoes": 5},
                {"id": "m2", "qualification_score": 0.6, "total_interacoes": 3},
            ]

            with patch("app.services.priorizacao_medicos.filtrar_medicos_contatados_recentemente") as mock_f1:
                mock_f1.return_value = [
                    {"id": "m1", "qualification_score": 0.8, "total_interacoes": 5},
                    {"id": "m2", "qualification_score": 0.6, "total_interacoes": 3},
                ]

                with patch("app.services.priorizacao_medicos.filtrar_medicos_em_conversa_ativa") as mock_f2:
                    mock_f2.return_value = [
                        {"id": "m1", "qualification_score": 0.8, "total_interacoes": 5},
                    ]

                    with patch("app.services.priorizacao_medicos.filtrar_medicos_na_fila") as mock_f3:
                        mock_f3.return_value = [
                            {"id": "m1", "qualification_score": 0.8, "total_interacoes": 5},
                        ]

                        with patch("app.services.priorizacao_medicos.priorizar_medicos") as mock_priorizar:
                            mock_priorizar.return_value = [
                                {"id": "m1", "qualification_score": 0.8},
                            ]

                            resultado = await selecionar_medicos_para_oferta(vaga, limite=5)

                            assert len(resultado) == 1
                            mock_buscar.assert_called_once()
                            mock_f1.assert_called_once()
                            mock_f2.assert_called_once()
                            mock_f3.assert_called_once()

    @pytest.mark.asyncio
    async def test_retorna_vazio_sem_candidatos(self):
        """Deve retornar lista vazia quando não há candidatos."""
        from app.services.priorizacao_medicos import selecionar_medicos_para_oferta

        vaga = {"id": "v1"}

        with patch("app.services.gatilhos_autonomos.buscar_medicos_compativeis_para_vaga") as mock_buscar:
            mock_buscar.return_value = []

            resultado = await selecionar_medicos_para_oferta(vaga)

            assert resultado == []
