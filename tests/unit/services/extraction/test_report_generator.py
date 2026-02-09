"""
Testes para o gerador de relatorios Julia.

Sprint 54: Insights Dashboard & Relatorio Julia.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import json

from app.services.extraction.report_generator import (
    gerar_relatorio_campanha,
    CampaignReport,
    CampaignReportMetrics,
    MedicoDestaque,
    ObjecaoAgregada,
    _agregar_metricas,
    _agregar_objecoes,
    _extrair_preferencias_comuns,
    _gerar_relatorio_fallback,
    _dict_to_report,
)


class TestCampaignReportMetrics:
    """Testes para metricas do relatorio."""

    def test_metrics_default(self):
        """Metricas tem valores default."""
        metrics = CampaignReportMetrics()
        assert metrics.total_respostas == 0
        assert metrics.interesse_positivo == 0
        assert metrics.taxa_interesse_pct == 0.0

    def test_metrics_with_values(self):
        """Metricas com valores."""
        metrics = CampaignReportMetrics(
            total_respostas=100,
            interesse_positivo=30,
            interesse_negativo=20,
            taxa_interesse_pct=30.0,
        )
        assert metrics.total_respostas == 100
        assert metrics.taxa_interesse_pct == 30.0


class TestMedicoDestaque:
    """Testes para medicos em destaque."""

    def test_medico_destaque_minimal(self):
        """Medico com dados minimos."""
        medico = MedicoDestaque(
            cliente_id="uuid-123",
            nome="Dr. Teste",
            interesse="positivo",
            interesse_score=0.8,
            proximo_passo="enviar_vagas",
        )
        assert medico.nome == "Dr. Teste"
        assert medico.insight is None

    def test_medico_destaque_full(self):
        """Medico com todos os dados."""
        medico = MedicoDestaque(
            cliente_id="uuid-123",
            nome="Dr. Carlos",
            interesse="positivo",
            interesse_score=0.9,
            proximo_passo="enviar_vagas",
            insight="Disponivel fins de semana",
            especialidade="Cardiologia",
        )
        assert medico.especialidade == "Cardiologia"
        assert "fins de semana" in medico.insight


class TestObjecaoAgregada:
    """Testes para objecoes agregadas."""

    def test_objecao_agregada(self):
        """Objecao agregada basica."""
        objecao = ObjecaoAgregada(
            tipo="preco",
            quantidade=5,
            exemplo="Valor muito baixo",
        )
        assert objecao.tipo == "preco"
        assert objecao.quantidade == 5


class TestCampaignReport:
    """Testes para CampaignReport."""

    def test_to_dict(self):
        """Serializacao para dicionario."""
        metrics = CampaignReportMetrics(
            total_respostas=10,
            interesse_positivo=3,
            taxa_interesse_pct=30.0,
        )
        report = CampaignReport(
            campaign_id=19,
            campaign_name="Discovery Cardiologia",
            generated_at="2026-02-09T10:00:00Z",
            metrics=metrics,
            relatorio_julia="Teste de relatorio",
        )

        data = report.to_dict()

        assert data["campaign_id"] == 19
        assert data["campaign_name"] == "Discovery Cardiologia"
        assert data["metrics"]["total_respostas"] == 10
        assert data["relatorio_julia"] == "Teste de relatorio"

    def test_to_dict_with_medicos(self):
        """Serializacao com medicos."""
        metrics = CampaignReportMetrics()
        medico = MedicoDestaque(
            cliente_id="uuid-123",
            nome="Dr. Teste",
            interesse="positivo",
            interesse_score=0.8,
            proximo_passo="enviar_vagas",
        )
        report = CampaignReport(
            campaign_id=19,
            campaign_name="Teste",
            generated_at="2026-02-09T10:00:00Z",
            metrics=metrics,
            medicos_destaque=[medico],
        )

        data = report.to_dict()

        assert len(data["medicos_destaque"]) == 1
        assert data["medicos_destaque"][0]["nome"] == "Dr. Teste"

    def test_to_dict_with_objecoes(self):
        """Serializacao com objecoes."""
        metrics = CampaignReportMetrics()
        objecao = ObjecaoAgregada(
            tipo="preco",
            quantidade=3,
            exemplo="Valor baixo",
        )
        report = CampaignReport(
            campaign_id=19,
            campaign_name="Teste",
            generated_at="2026-02-09T10:00:00Z",
            metrics=metrics,
            objecoes_encontradas=[objecao],
        )

        data = report.to_dict()

        assert len(data["objecoes_encontradas"]) == 1
        assert data["objecoes_encontradas"][0]["tipo"] == "preco"


class TestAgregarMetricas:
    """Testes para funcao _agregar_metricas."""

    def test_agregar_metricas_vazio(self):
        """Retorna metricas zeradas para lista vazia."""
        metrics = _agregar_metricas([])
        assert metrics.total_respostas == 0
        assert metrics.interesse_positivo == 0

    def test_agregar_metricas_basico(self):
        """Agrega metricas de insights."""
        insights = [
            {"interesse": "positivo", "interesse_score": 0.8, "proximo_passo": "enviar_vagas"},
            {"interesse": "positivo", "interesse_score": 0.7, "proximo_passo": "agendar_followup"},
            {"interesse": "negativo", "interesse_score": 0.2, "proximo_passo": "marcar_inativo"},
        ]

        metrics = _agregar_metricas(insights)

        assert metrics.total_respostas == 3
        assert metrics.interesse_positivo == 2
        assert metrics.interesse_negativo == 1
        assert metrics.prontos_para_vagas == 1
        assert metrics.para_followup == 1

    def test_agregar_metricas_com_objecao(self):
        """Agrega metricas com objecoes."""
        insights = [
            {"interesse": "negativo", "interesse_score": 0.2, "objecao_tipo": "preco"},
            {"interesse": "negativo", "interesse_score": 0.1, "objecao_tipo": "preco"},
            {"interesse": "negativo", "interesse_score": 0.3, "objecao_tipo": "tempo"},
        ]

        metrics = _agregar_metricas(insights)

        assert metrics.total_objecoes == 3
        assert metrics.objecao_mais_comum == "preco"

    def test_agregar_metricas_taxa_interesse(self):
        """Calcula taxa de interesse corretamente."""
        insights = [
            {"interesse": "positivo", "interesse_score": 0.8},
            {"interesse": "neutro", "interesse_score": 0.5},
            {"interesse": "negativo", "interesse_score": 0.2},
            {"interesse": "neutro", "interesse_score": 0.5},
        ]

        metrics = _agregar_metricas(insights)

        assert metrics.taxa_interesse_pct == 25.0  # 1 de 4


class TestAgregarObjecoes:
    """Testes para funcao _agregar_objecoes."""

    def test_agregar_objecoes_vazio(self):
        """Lista vazia de objecoes."""
        result = _agregar_objecoes([])
        assert result == []

    def test_agregar_objecoes_sem_objecoes(self):
        """Insights sem objecoes."""
        insights = [
            {"interesse": "positivo"},
            {"interesse": "neutro"},
        ]
        result = _agregar_objecoes(insights)
        assert result == []

    def test_agregar_objecoes_basico(self):
        """Agrega objecoes por tipo."""
        insights = [
            {"objecao_tipo": "preco", "objecao_descricao": "Muito caro"},
            {"objecao_tipo": "preco", "objecao_descricao": "Valor baixo"},
            {"objecao_tipo": "tempo", "objecao_descricao": "Sem tempo"},
        ]

        result = _agregar_objecoes(insights)

        assert len(result) == 2
        preco = next(o for o in result if o.tipo == "preco")
        assert preco.quantidade == 2
        assert preco.exemplo == "Muito caro"

    def test_agregar_objecoes_ordenacao(self):
        """Objecoes ordenadas por quantidade."""
        insights = [
            {"objecao_tipo": "preco", "objecao_descricao": "Muito caro"},
            {"objecao_tipo": "tempo", "objecao_descricao": "Sem tempo 1"},
            {"objecao_tipo": "tempo", "objecao_descricao": "Sem tempo 2"},
            {"objecao_tipo": "tempo", "objecao_descricao": "Sem tempo 3"},
        ]

        result = _agregar_objecoes(insights)

        assert result[0].tipo == "tempo"
        assert result[0].quantidade == 3


class TestExtrairPreferenciasComuns:
    """Testes para funcao _extrair_preferencias_comuns."""

    def test_preferencias_vazio(self):
        """Lista vazia."""
        result = _extrair_preferencias_comuns([])
        assert result == []

    def test_preferencias_sem_dados(self):
        """Insights sem preferencias."""
        insights = [
            {"interesse": "positivo"},
            {"interesse": "neutro"},
        ]
        result = _extrair_preferencias_comuns(insights)
        assert result == []

    def test_preferencias_basico(self):
        """Extrai preferencias."""
        insights = [
            {"preferencias": ["plantoes noturnos", "uti"]},
            {"preferencias": ["plantoes noturnos", "fins de semana"]},
            {"preferencias": ["uti"]},
        ]

        result = _extrair_preferencias_comuns(insights)

        assert len(result) <= 5
        assert "plantoes noturnos" in result
        assert "uti" in result

    def test_preferencias_com_disponibilidade(self):
        """Inclui disponibilidade como preferencia."""
        insights = [
            {"disponibilidade_mencionada": "fins de semana"},
            {"disponibilidade_mencionada": "fins de semana"},
        ]

        result = _extrair_preferencias_comuns(insights)

        assert "fins de semana" in result


class TestGerarRelatorioFallback:
    """Testes para relatorio fallback."""

    def test_fallback_basico(self):
        """Gera relatorio fallback."""
        metrics = CampaignReportMetrics(
            total_respostas=10,
            interesse_positivo=3,
            interesse_negativo=2,
            taxa_interesse_pct=30.0,
            prontos_para_vagas=2,
            para_followup=3,
        )

        relatorio = _gerar_relatorio_fallback(metrics)

        assert "O que funcionou" in relatorio
        assert "Pontos de atenção" in relatorio
        assert "Próximos passos" in relatorio


class TestDictToReport:
    """Testes para conversao de dict para CampaignReport."""

    def test_dict_to_report_basico(self):
        """Converte dict basico."""
        data = {
            "campaign_id": 19,
            "campaign_name": "Teste",
            "generated_at": "2026-02-09T10:00:00Z",
            "metrics": {
                "total_respostas": 10,
                "interesse_positivo": 3,
            },
            "relatorio_julia": "Teste",
        }

        report = _dict_to_report(data)

        assert report.campaign_id == 19
        assert report.metrics.total_respostas == 10

    def test_dict_to_report_com_medicos(self):
        """Converte dict com medicos."""
        data = {
            "campaign_id": 19,
            "campaign_name": "Teste",
            "generated_at": "2026-02-09T10:00:00Z",
            "metrics": {},
            "medicos_destaque": [
                {
                    "cliente_id": "uuid-123",
                    "nome": "Dr. Teste",
                    "interesse": "positivo",
                    "interesse_score": 0.8,
                    "proximo_passo": "enviar_vagas",
                }
            ],
        }

        report = _dict_to_report(data)

        assert len(report.medicos_destaque) == 1
        assert report.medicos_destaque[0].nome == "Dr. Teste"


class TestGerarRelatorioCampanha:
    """Testes de integracao para gerar_relatorio_campanha."""

    @pytest.mark.asyncio
    @patch("app.services.extraction.report_generator._get_cached_report")
    async def test_cache_hit(self, mock_cache):
        """Retorna cache se existir."""
        cached_report = CampaignReport(
            campaign_id=19,
            campaign_name="Cached",
            generated_at="2026-02-09T10:00:00Z",
            metrics=CampaignReportMetrics(),
            cached=False,
        )
        mock_cache.return_value = cached_report

        result = await gerar_relatorio_campanha(19)

        assert result.cached is True
        mock_cache.assert_called_once_with(19)

    @pytest.mark.asyncio
    @patch("app.services.extraction.report_generator._get_cached_report")
    @patch("app.services.extraction.report_generator._buscar_campanha")
    async def test_campanha_nao_encontrada(self, mock_buscar, mock_cache):
        """Erro se campanha nao existe."""
        mock_cache.return_value = None
        mock_buscar.return_value = None

        with pytest.raises(ValueError, match="não encontrada"):
            await gerar_relatorio_campanha(999)

    @pytest.mark.asyncio
    @patch("app.services.extraction.report_generator._get_cached_report")
    @patch("app.services.extraction.report_generator._buscar_campanha")
    @patch("app.services.extraction.report_generator._buscar_insights_campanha")
    async def test_sem_insights(self, mock_insights, mock_campanha, mock_cache):
        """Retorna relatorio vazio se nao ha insights."""
        mock_cache.return_value = None
        mock_campanha.return_value = {"nome_template": "Teste"}
        mock_insights.return_value = []

        result = await gerar_relatorio_campanha(19)

        assert result.metrics.total_respostas == 0
        assert "dados suficientes" in result.relatorio_julia

    @pytest.mark.asyncio
    @patch("app.services.extraction.report_generator._get_cached_report")
    @patch("app.services.extraction.report_generator._buscar_campanha")
    @patch("app.services.extraction.report_generator._buscar_insights_campanha")
    @patch("app.services.extraction.report_generator._identificar_medicos_destaque")
    @patch("app.services.extraction.report_generator._gerar_relatorio_llm")
    @patch("app.services.extraction.report_generator._save_report_cache")
    async def test_gerar_relatorio_completo(
        self,
        mock_save_cache,
        mock_llm,
        mock_medicos,
        mock_insights,
        mock_campanha,
        mock_cache,
    ):
        """Gera relatorio completo."""
        mock_cache.return_value = None
        mock_campanha.return_value = {"nome_template": "Discovery Cardio"}
        mock_insights.return_value = [
            {"interesse": "positivo", "interesse_score": 0.8, "cliente_id": "uuid-1"},
            {"interesse": "negativo", "interesse_score": 0.2, "cliente_id": "uuid-2", "objecao_tipo": "preco"},
        ]
        mock_medicos.return_value = [
            MedicoDestaque(
                cliente_id="uuid-1",
                nome="Dr. Teste",
                interesse="positivo",
                interesse_score=0.8,
                proximo_passo="enviar_vagas",
            )
        ]
        mock_llm.return_value = ("Relatorio gerado via LLM", 500)
        mock_save_cache.return_value = None

        result = await gerar_relatorio_campanha(19)

        assert result.campaign_name == "Discovery Cardio"
        assert result.metrics.total_respostas == 2
        assert result.metrics.interesse_positivo == 1
        assert len(result.medicos_destaque) == 1
        assert result.relatorio_julia == "Relatorio gerado via LLM"
        assert result.tokens_usados == 500

    @pytest.mark.asyncio
    @patch("app.services.extraction.report_generator._get_cached_report")
    @patch("app.services.extraction.report_generator._buscar_campanha")
    @patch("app.services.extraction.report_generator._buscar_insights_campanha")
    @patch("app.services.extraction.report_generator._identificar_medicos_destaque")
    @patch("app.services.extraction.report_generator._gerar_relatorio_llm")
    @patch("app.services.extraction.report_generator._save_report_cache")
    async def test_force_refresh_ignora_cache(
        self,
        mock_save_cache,
        mock_llm,
        mock_medicos,
        mock_insights,
        mock_campanha,
        mock_cache,
    ):
        """Force refresh ignora cache."""
        mock_campanha.return_value = {"nome_template": "Teste"}
        mock_insights.return_value = [
            {"interesse": "positivo", "interesse_score": 0.8, "cliente_id": "uuid-1"},
        ]
        mock_medicos.return_value = []
        mock_llm.return_value = ("Novo relatorio", 100)
        mock_save_cache.return_value = None

        result = await gerar_relatorio_campanha(19, force_refresh=True)

        mock_cache.assert_not_called()
        assert result.relatorio_julia == "Novo relatorio"
