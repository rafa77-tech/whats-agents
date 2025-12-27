"""
Testes do módulo de métricas do pipeline de grupos.

Sprint 14 - E12 - Métricas e Monitoramento
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import date, datetime, timedelta, UTC
from uuid import uuid4

from app.services.grupos.metricas import (
    MetricasProcessamento,
    ColetorMetricas,
    obter_metricas_dia,
    obter_metricas_periodo,
    obter_top_grupos,
    obter_status_fila,
    consolidar_metricas_dia,
    coletor_metricas,
)


# =============================================================================
# Testes do Dataclass MetricasProcessamento
# =============================================================================

class TestMetricasProcessamento:
    """Testes do dataclass de métricas."""

    def test_criar_metricas_padrao(self):
        """Cria métricas com valores padrão."""
        metricas = MetricasProcessamento()

        assert metricas.mensagens_processadas == 0
        assert metricas.vagas_extraidas == 0
        assert metricas.tempo_heuristica_ms == 0
        assert metricas.tempo_llm_ms == 0
        assert metricas.tokens_input == 0
        assert metricas.tokens_output == 0
        assert metricas.fim is None

    def test_finalizar_marca_tempo(self):
        """Finalizar marca o tempo de fim."""
        metricas = MetricasProcessamento()
        metricas.finalizar()

        assert metricas.fim is not None
        assert metricas.fim > metricas.inicio

    def test_tempo_total_ms(self):
        """Calcula tempo total em ms."""
        metricas = MetricasProcessamento()
        metricas.inicio = 1000.0
        metricas.fim = 1001.5  # 1.5 segundos depois

        assert metricas.tempo_total_ms == 1500

    def test_tempo_total_ms_sem_finalizar(self):
        """Tempo total é 0 se não finalizado."""
        metricas = MetricasProcessamento()

        assert metricas.tempo_total_ms == 0

    def test_custo_estimado(self):
        """Calcula custo estimado corretamente."""
        metricas = MetricasProcessamento()
        metricas.tokens_input = 1_000_000  # 1M tokens
        metricas.tokens_output = 100_000   # 100K tokens

        # Claude Haiku: $0.25/1M input, $1.25/1M output
        # Custo esperado: (1M * 0.25/1M) + (100K * 1.25/1M)
        # = 0.25 + 0.125 = 0.375
        assert abs(metricas.custo_estimado - 0.375) < 0.001

    def test_custo_estimado_zero(self):
        """Custo é 0 sem tokens."""
        metricas = MetricasProcessamento()

        assert metricas.custo_estimado == 0


# =============================================================================
# Testes do ColetorMetricas
# =============================================================================

class TestColetorMetricas:
    """Testes do coletor de métricas."""

    def test_criar_coletor(self):
        """Cria coletor com configurações padrão."""
        coletor = ColetorMetricas()

        assert coletor.flush_threshold == 100
        assert coletor.metricas_pendentes == []

    def test_criar_coletor_custom_threshold(self):
        """Cria coletor com threshold personalizado."""
        coletor = ColetorMetricas(flush_threshold=50)

        assert coletor.flush_threshold == 50

    @pytest.mark.asyncio
    async def test_registrar_adiciona_metricas(self):
        """Registrar adiciona métricas à lista pendente."""
        coletor = ColetorMetricas()
        grupo_id = uuid4()
        metricas = MetricasProcessamento()
        metricas.vagas_extraidas = 2

        await coletor.registrar(grupo_id, metricas)

        assert len(coletor.metricas_pendentes) == 1
        assert coletor.metricas_pendentes[0]["grupo_id"] == str(grupo_id)
        assert coletor.metricas_pendentes[0]["metricas"] == metricas

    @pytest.mark.asyncio
    async def test_registrar_flush_automatico(self):
        """Flush automático quando atinge threshold."""
        coletor = ColetorMetricas(flush_threshold=3)

        with patch.object(coletor, "_upsert_metricas_grupo", new_callable=AsyncMock) as mock_upsert:
            mock_upsert.return_value = None

            for _ in range(3):
                await coletor.registrar(uuid4(), MetricasProcessamento())

            # Deve ter feito flush
            assert coletor.metricas_pendentes == []
            mock_upsert.assert_called()

    @pytest.mark.asyncio
    async def test_flush_vazio(self):
        """Flush com lista vazia retorna 0."""
        coletor = ColetorMetricas()

        result = await coletor.flush()

        assert result == 0

    @pytest.mark.asyncio
    async def test_flush_agrega_por_grupo(self):
        """Flush agrega métricas por grupo/data."""
        coletor = ColetorMetricas()
        grupo_id = uuid4()

        # Adicionar 3 métricas do mesmo grupo
        for i in range(3):
            m = MetricasProcessamento()
            m.vagas_extraidas = 1
            m.tokens_input = 100
            await coletor.registrar(grupo_id, m)

        with patch.object(coletor, "_upsert_metricas_grupo", new_callable=AsyncMock) as mock_upsert:
            mock_upsert.return_value = None

            result = await coletor.flush()

            # Deve ter chamado upsert uma vez (mesmo grupo/data)
            assert mock_upsert.call_count == 1

            # Verificar valores agregados
            call_args = mock_upsert.call_args
            valores = call_args[0][2]  # Terceiro argumento
            assert valores["mensagens_processadas"] == 3
            assert valores["tokens_input"] == 300


# =============================================================================
# Testes das Funções de Consulta
# =============================================================================

class TestObterMetricasDia:
    """Testes de obtenção de métricas do dia."""

    @pytest.mark.asyncio
    async def test_obter_metricas_hoje(self):
        """Obtém métricas de hoje."""
        with patch("app.services.grupos.metricas.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"mensagens_processadas": 100, "vagas_importadas": 10}
            )

            result = await obter_metricas_dia()

            assert result["mensagens_processadas"] == 100
            assert result["vagas_importadas"] == 10

    @pytest.mark.asyncio
    async def test_obter_metricas_dia_especifico(self):
        """Obtém métricas de data específica."""
        with patch("app.services.grupos.metricas.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data={"mensagens_processadas": 50}
            )

            data = date(2025, 12, 25)
            result = await obter_metricas_dia(data)

            # Verificar que passou a data correta
            mock_supabase.table.return_value.select.return_value.eq.assert_called_once()

    @pytest.mark.asyncio
    async def test_obter_metricas_dia_vazio(self):
        """Retorna dict vazio se não houver dados."""
        with patch("app.services.grupos.metricas.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
                data=None
            )

            result = await obter_metricas_dia()

            assert result == {}


class TestObterMetricasPeriodo:
    """Testes de obtenção de métricas de período."""

    @pytest.mark.asyncio
    async def test_obter_metricas_7_dias(self):
        """Obtém métricas dos últimos 7 dias."""
        with patch("app.services.grupos.metricas.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.gte.return_value.order.return_value.execute.return_value = MagicMock(
                data=[
                    {"mensagens_processadas": 100, "vagas_importadas": 10, "custo_total_usd": 0.5},
                    {"mensagens_processadas": 80, "vagas_importadas": 8, "custo_total_usd": 0.4},
                ]
            )

            result = await obter_metricas_periodo(dias=7)

            assert result["periodo"] == "7d"
            assert result["totais"]["mensagens"] == 180
            assert result["totais"]["vagas_importadas"] == 18
            assert result["totais"]["custo_usd"] == 0.9

    @pytest.mark.asyncio
    async def test_obter_metricas_periodo_vazio(self):
        """Retorna estrutura vazia se não houver dados."""
        with patch("app.services.grupos.metricas.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.gte.return_value.order.return_value.execute.return_value = MagicMock(
                data=[]
            )

            result = await obter_metricas_periodo(dias=7)

            assert result["periodo"] == "7d"
            assert result["dados"] == []

    @pytest.mark.asyncio
    async def test_calcula_taxa_conversao(self):
        """Calcula taxa de conversão corretamente."""
        with patch("app.services.grupos.metricas.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.gte.return_value.order.return_value.execute.return_value = MagicMock(
                data=[{"mensagens_processadas": 100, "vagas_importadas": 10}]
            )

            result = await obter_metricas_periodo(dias=7)

            assert result["totais"]["taxa_conversao"] == 0.1  # 10/100


class TestObterTopGrupos:
    """Testes de obtenção de top grupos."""

    @pytest.mark.asyncio
    async def test_obter_top_grupos(self):
        """Obtém top grupos por vagas."""
        with patch("app.services.grupos.metricas.supabase") as mock_supabase:
            mock_supabase.rpc.return_value.execute.return_value = MagicMock(
                data=[
                    {"nome_grupo": "Grupo 1", "total_vagas": 50},
                    {"nome_grupo": "Grupo 2", "total_vagas": 30},
                ]
            )

            result = await obter_top_grupos(dias=7, limite=10)

            assert len(result) == 2
            assert result[0]["total_vagas"] == 50

    @pytest.mark.asyncio
    async def test_obter_top_grupos_vazio(self):
        """Retorna lista vazia se não houver dados."""
        with patch("app.services.grupos.metricas.supabase") as mock_supabase:
            mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=None)

            result = await obter_top_grupos()

            assert result == []


class TestObterStatusFila:
    """Testes de obtenção de status da fila."""

    @pytest.mark.asyncio
    async def test_obter_status_fila(self):
        """Obtém status da fila."""
        with patch("app.services.grupos.metricas.supabase") as mock_supabase:
            mock_supabase.rpc.return_value.execute.return_value = MagicMock(
                data=[{"pendente": 10, "processando": 5, "erro": 2}]
            )

            result = await obter_status_fila()

            assert result["pendente"] == 10
            assert result["processando"] == 5

    @pytest.mark.asyncio
    async def test_obter_status_fila_vazio(self):
        """Retorna dict vazio se não houver dados."""
        with patch("app.services.grupos.metricas.supabase") as mock_supabase:
            mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=[])

            result = await obter_status_fila()

            assert result == {}


class TestConsolidarMetricasDia:
    """Testes de consolidação de métricas."""

    @pytest.mark.asyncio
    async def test_consolidar_dia_anterior(self):
        """Consolida métricas do dia anterior."""
        with patch("app.services.grupos.metricas.supabase") as mock_supabase:
            mock_supabase.rpc.return_value.execute.return_value = MagicMock()

            result = await consolidar_metricas_dia()

            assert result is True
            mock_supabase.rpc.assert_called_once()

    @pytest.mark.asyncio
    async def test_consolidar_data_especifica(self):
        """Consolida métricas de data específica."""
        with patch("app.services.grupos.metricas.supabase") as mock_supabase:
            mock_supabase.rpc.return_value.execute.return_value = MagicMock()

            data = date(2025, 12, 25)
            result = await consolidar_metricas_dia(data)

            assert result is True

    @pytest.mark.asyncio
    async def test_consolidar_erro(self):
        """Retorna False em caso de erro."""
        with patch("app.services.grupos.metricas.supabase") as mock_supabase:
            mock_supabase.rpc.return_value.execute.side_effect = Exception("Erro DB")

            result = await consolidar_metricas_dia()

            assert result is False


# =============================================================================
# Testes da Instância Global
# =============================================================================

class TestInstanciaGlobal:
    """Testes da instância global do coletor."""

    def test_coletor_metricas_existe(self):
        """Instância global existe."""
        assert coletor_metricas is not None
        assert isinstance(coletor_metricas, ColetorMetricas)
