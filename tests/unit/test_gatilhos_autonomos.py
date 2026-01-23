"""
Testes para serviço de gatilhos automáticos.

Sprint 32 E05 - Gatilhos Automáticos.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone


class TestBuscarMedicosNaoEnriquecidos:
    """Testes para buscar_medicos_nao_enriquecidos()."""

    @pytest.mark.asyncio
    async def test_busca_medicos_sem_especialidade(self):
        """Deve retornar médicos com telefone validado mas sem especialidade."""
        from app.services.gatilhos_autonomos import buscar_medicos_nao_enriquecidos

        with patch("app.services.gatilhos_autonomos.supabase") as mock_supabase:
            mock_execute = MagicMock()
            mock_execute.data = [
                {"id": "1", "telefone": "5511111111111", "primeiro_nome": "João", "especialidade": None},
                {"id": "2", "telefone": "5522222222222", "primeiro_nome": "Maria", "especialidade": None},
            ]

            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.is_.return_value.is_.return_value.is_.return_value.limit.return_value.execute.return_value = mock_execute

            resultado = await buscar_medicos_nao_enriquecidos(limite=10)

            assert len(resultado) == 2
            assert resultado[0]["especialidade"] is None

    @pytest.mark.asyncio
    async def test_busca_vazia_retorna_lista_vazia(self):
        """Deve retornar lista vazia quando não há médicos pendentes."""
        from app.services.gatilhos_autonomos import buscar_medicos_nao_enriquecidos

        with patch("app.services.gatilhos_autonomos.supabase") as mock_supabase:
            mock_execute = MagicMock()
            mock_execute.data = []

            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.is_.return_value.is_.return_value.is_.return_value.limit.return_value.execute.return_value = mock_execute

            resultado = await buscar_medicos_nao_enriquecidos()

            assert resultado == []


class TestExecutarDiscoveryAutomatico:
    """Testes para executar_discovery_automatico()."""

    @pytest.mark.asyncio
    async def test_retorna_none_em_modo_piloto(self):
        """Deve retornar None quando feature está desabilitada (piloto ativo)."""
        from app.services.gatilhos_autonomos import executar_discovery_automatico

        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = True
            mock_settings.is_feature_enabled.return_value = False

            resultado = await executar_discovery_automatico()

            assert resultado is None

    @pytest.mark.asyncio
    async def test_executa_quando_piloto_desabilitado(self):
        """Deve executar discovery quando feature está habilitada."""
        from app.services.gatilhos_autonomos import executar_discovery_automatico

        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = False
            mock_settings.is_feature_enabled.return_value = True

            with patch("app.services.gatilhos_autonomos.buscar_medicos_nao_enriquecidos") as mock_buscar:
                mock_buscar.return_value = []

                resultado = await executar_discovery_automatico()

                assert resultado is not None
                assert resultado["encontrados"] == 0


class TestBuscarVagasUrgentes:
    """Testes para buscar_vagas_urgentes()."""

    @pytest.mark.asyncio
    async def test_busca_vagas_dentro_threshold(self):
        """Deve retornar vagas com data < threshold dias."""
        from app.services.gatilhos_autonomos import buscar_vagas_urgentes

        with patch("app.services.gatilhos_autonomos.supabase") as mock_supabase:
            mock_execute = MagicMock()
            mock_execute.data = [
                {
                    "id": "v1",
                    "data": "2026-01-20",
                    "valor": 2500,
                    "status": "aberta",
                    "especialidade_id": "esp1",
                    "hospitais": {"nome": "Hospital A"},
                    "especialidades": {"nome": "Cardiologia"},
                },
            ]

            mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.is_.return_value.order.return_value.limit.return_value.execute.return_value = mock_execute

            resultado = await buscar_vagas_urgentes(threshold_dias=20)

            assert len(resultado) == 1
            assert resultado[0]["status"] == "aberta"

    @pytest.mark.asyncio
    async def test_busca_vazia_retorna_lista_vazia(self):
        """Deve retornar lista vazia quando não há vagas urgentes."""
        from app.services.gatilhos_autonomos import buscar_vagas_urgentes

        with patch("app.services.gatilhos_autonomos.supabase") as mock_supabase:
            mock_execute = MagicMock()
            mock_execute.data = []

            mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.is_.return_value.order.return_value.limit.return_value.execute.return_value = mock_execute

            resultado = await buscar_vagas_urgentes()

            assert resultado == []


class TestExecutarOfertaAutomatica:
    """Testes para executar_oferta_automatica()."""

    @pytest.mark.asyncio
    async def test_retorna_none_em_modo_piloto(self):
        """Deve retornar None quando feature está desabilitada (piloto ativo)."""
        from app.services.gatilhos_autonomos import executar_oferta_automatica

        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = True
            mock_settings.is_feature_enabled.return_value = False

            resultado = await executar_oferta_automatica()

            assert resultado is None

    @pytest.mark.asyncio
    async def test_executa_quando_piloto_desabilitado(self):
        """Deve executar oferta quando feature está habilitada."""
        from app.services.gatilhos_autonomos import executar_oferta_automatica

        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = False
            mock_settings.is_feature_enabled.return_value = True

            with patch("app.services.gatilhos_autonomos.buscar_vagas_urgentes") as mock_buscar:
                mock_buscar.return_value = []

                resultado = await executar_oferta_automatica()

                assert resultado is not None
                assert resultado["vagas_encontradas"] == 0


class TestBuscarMedicosInativos:
    """Testes para buscar_medicos_inativos()."""

    @pytest.mark.asyncio
    async def test_busca_medicos_inativos(self):
        """Deve retornar médicos sem interação há mais de X dias."""
        from app.services.gatilhos_autonomos import buscar_medicos_inativos

        data_antiga = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()

        with patch("app.services.gatilhos_autonomos.supabase") as mock_supabase:
            mock_execute = MagicMock()
            mock_execute.data = [
                {
                    "id": "1",
                    "telefone": "5511111111111",
                    "primeiro_nome": "João",
                    "ultima_mensagem_data": data_antiga,
                    "total_interacoes": 5,
                },
            ]

            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.is_.return_value.is_.return_value.lt.return_value.gt.return_value.order.return_value.limit.return_value.execute.return_value = mock_execute

            resultado = await buscar_medicos_inativos(dias_inativo=60)

            assert len(resultado) == 1
            assert resultado[0]["total_interacoes"] > 0


class TestExecutarReativacaoAutomatica:
    """Testes para executar_reativacao_automatica()."""

    @pytest.mark.asyncio
    async def test_retorna_none_em_modo_piloto(self):
        """Deve retornar None quando feature está desabilitada (piloto ativo)."""
        from app.services.gatilhos_autonomos import executar_reativacao_automatica

        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = True
            mock_settings.is_feature_enabled.return_value = False

            resultado = await executar_reativacao_automatica()

            assert resultado is None


class TestBuscarPlantoesRealizadosRecentes:
    """Testes para buscar_plantoes_realizados_recentes()."""

    @pytest.mark.asyncio
    async def test_busca_plantoes_recentes(self):
        """Deve retornar plantões realizados nos últimos X dias."""
        from app.services.gatilhos_autonomos import buscar_plantoes_realizados_recentes

        with patch("app.services.gatilhos_autonomos.supabase") as mock_supabase:
            mock_execute = MagicMock()
            mock_execute.data = [
                {
                    "id": "v1",
                    "data": "2026-01-14",
                    "realizada_em": datetime.now(timezone.utc).isoformat(),
                    "cliente_id": "c1",
                    "hospitais": {"nome": "Hospital A"},
                    "especialidades": {"nome": "Cardiologia"},
                    "clientes": {
                        "id": "c1",
                        "telefone": "5511111111111",
                        "primeiro_nome": "Dr. João",
                        "opt_out": False,
                        "opted_out": None,
                        "status_telefone": "validado",
                    },
                },
            ]

            mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.not_.is_.return_value.is_.return_value.order.return_value.limit.return_value.execute.return_value = mock_execute

            resultado = await buscar_plantoes_realizados_recentes(dias=2)

            assert len(resultado) == 1
            assert resultado[0]["clientes"]["status_telefone"] == "validado"


class TestExecutarFeedbackAutomatico:
    """Testes para executar_feedback_automatico()."""

    @pytest.mark.asyncio
    async def test_retorna_none_em_modo_piloto(self):
        """Deve retornar None quando feature está desabilitada (piloto ativo)."""
        from app.services.gatilhos_autonomos import executar_feedback_automatico

        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = True
            mock_settings.is_feature_enabled.return_value = False

            resultado = await executar_feedback_automatico()

            assert resultado is None


class TestExecutarTodosGatilhos:
    """Testes para executar_todos_gatilhos()."""

    @pytest.mark.asyncio
    async def test_retorna_pilot_mode_true_quando_ativo(self):
        """Deve indicar que está em modo piloto quando feature desabilitada."""
        from app.services.gatilhos_autonomos import executar_todos_gatilhos

        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = True
            mock_settings.is_feature_enabled.return_value = False

            resultado = await executar_todos_gatilhos()

            assert resultado["pilot_mode"] is True

    @pytest.mark.asyncio
    async def test_executa_todos_quando_piloto_desabilitado(self):
        """Deve executar todos os gatilhos quando features habilitadas."""
        from app.services.gatilhos_autonomos import executar_todos_gatilhos

        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = False
            mock_settings.is_feature_enabled.return_value = True

            with patch("app.services.gatilhos_autonomos.executar_discovery_automatico") as mock_discovery:
                mock_discovery.return_value = {"encontrados": 0, "enfileirados": 0, "erros": 0}

                with patch("app.services.gatilhos_autonomos.executar_oferta_automatica") as mock_oferta:
                    mock_oferta.return_value = {"vagas_encontradas": 0, "ofertas_enfileiradas": 0}

                    with patch("app.services.gatilhos_autonomos.executar_reativacao_automatica") as mock_reativacao:
                        mock_reativacao.return_value = {"encontrados": 0, "enfileirados": 0}

                        with patch("app.services.gatilhos_autonomos.executar_feedback_automatico") as mock_feedback:
                            mock_feedback.return_value = {"plantoes_encontrados": 0}

                            resultado = await executar_todos_gatilhos()

                            assert resultado["pilot_mode"] is False
                            mock_discovery.assert_called_once()
                            mock_oferta.assert_called_once()
                            mock_reativacao.assert_called_once()
                            mock_feedback.assert_called_once()


class TestObterEstatisticasGatilhos:
    """Testes para obter_estatisticas_gatilhos()."""

    @pytest.mark.asyncio
    async def test_retorna_estatisticas_completas(self):
        """Deve retornar estatísticas de todos os gatilhos."""
        from app.services.gatilhos_autonomos import obter_estatisticas_gatilhos

        with patch("app.services.gatilhos_autonomos.buscar_medicos_nao_enriquecidos") as mock_discovery:
            mock_discovery.return_value = [{"id": "1"}, {"id": "2"}]

            with patch("app.services.gatilhos_autonomos.buscar_vagas_urgentes") as mock_vagas:
                mock_vagas.return_value = [{"id": "v1"}]

                with patch("app.services.gatilhos_autonomos.buscar_medicos_inativos") as mock_inativos:
                    mock_inativos.return_value = [{"id": "3"}, {"id": "4"}, {"id": "5"}]

                    with patch("app.services.gatilhos_autonomos.buscar_plantoes_realizados_recentes") as mock_plantoes:
                        mock_plantoes.return_value = []

                        resultado = await obter_estatisticas_gatilhos()

                        assert "discovery" in resultado
                        assert resultado["discovery"]["pendentes"] == 2
                        assert resultado["oferta"]["vagas_urgentes"] == 1
                        assert resultado["reativacao"]["inativos"] == 3
                        assert resultado["feedback"]["plantoes_recentes"] == 0


class TestIdentificarCamposFaltantes:
    """Testes para _identificar_campos_faltantes()."""

    def test_identifica_especialidade_faltando(self):
        """Deve identificar quando especialidade está faltando."""
        from app.services.gatilhos_autonomos import _identificar_campos_faltantes

        medico = {"id": "1", "especialidade": None, "cidade": "São Paulo", "estado": "SP"}

        faltantes = _identificar_campos_faltantes(medico)

        assert "especialidade" in faltantes
        assert "cidade" not in faltantes

    def test_identifica_multiplos_campos_faltando(self):
        """Deve identificar múltiplos campos faltando."""
        from app.services.gatilhos_autonomos import _identificar_campos_faltantes

        medico = {"id": "1", "especialidade": None, "cidade": None, "estado": None}

        faltantes = _identificar_campos_faltantes(medico)

        assert len(faltantes) == 3

    def test_retorna_lista_vazia_quando_tudo_preenchido(self):
        """Deve retornar lista vazia quando tudo está preenchido."""
        from app.services.gatilhos_autonomos import _identificar_campos_faltantes

        medico = {"id": "1", "especialidade": "Cardiologia", "cidade": "SP", "estado": "SP"}

        faltantes = _identificar_campos_faltantes(medico)

        assert len(faltantes) == 0


class TestVerificarFeedbackJaSolicitado:
    """Testes para verificar_feedback_ja_solicitado()."""

    @pytest.mark.asyncio
    async def test_retorna_true_quando_ja_existe(self):
        """Deve retornar True quando feedback já foi solicitado."""
        from app.services.gatilhos_autonomos import verificar_feedback_ja_solicitado

        with patch("app.services.gatilhos_autonomos.supabase") as mock_supabase:
            mock_execute = MagicMock()
            mock_execute.data = [{"id": "f1"}]

            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.contains.return_value.limit.return_value.execute.return_value = mock_execute

            resultado = await verificar_feedback_ja_solicitado("c1", "v1")

            assert resultado is True

    @pytest.mark.asyncio
    async def test_retorna_false_quando_nao_existe(self):
        """Deve retornar False quando feedback ainda não foi solicitado."""
        from app.services.gatilhos_autonomos import verificar_feedback_ja_solicitado

        with patch("app.services.gatilhos_autonomos.supabase") as mock_supabase:
            mock_execute = MagicMock()
            mock_execute.data = []

            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.contains.return_value.limit.return_value.execute.return_value = mock_execute

            resultado = await verificar_feedback_ja_solicitado("c1", "v1")

            assert resultado is False
