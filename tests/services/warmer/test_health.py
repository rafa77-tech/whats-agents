"""Testes do Warmup Health Check.

Sprint 65: Testa diagnóstico do pool de warmup.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.services.warmer.health import diagnostico_warmup


@pytest.fixture
def mock_chips_warming():
    """Chips com atividade de warmup."""
    return [
        {
            "id": "chip-1",
            "telefone": "5511999990001",
            "status": "warming",
            "fase_warmup": "expansao",
            "trust_score": 60,
            "trust_level": "amarelo",
            "warming_day": 10,
            "msgs_enviadas_hoje": 5,
            "evolution_connected": True,
            "provider": "evolution",
        },
        {
            "id": "chip-2",
            "telefone": "5511999990002",
            "status": "active",
            "fase_warmup": "operacao",
            "trust_score": 80,
            "trust_level": "verde",
            "warming_day": 30,
            "msgs_enviadas_hoje": 3,
            "evolution_connected": True,
            "provider": "z-api",
        },
    ]


class TestDiagnosticoWarmup:

    @patch("app.services.warmer.health.supabase")
    async def test_healthy_quando_conversa_par_acima_80(self, mock_sb, mock_chips_warming):
        # Mock chips
        mock_sb.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=mock_chips_warming
        )

        # Mock atividades (CONVERSA_PAR com 90% sucesso)
        mock_sb.table.return_value.select.return_value.gte.return_value.execute.return_value = MagicMock(
            data=[
                {"tipo": "CONVERSA_PAR", "status": "executada"},
                {"tipo": "CONVERSA_PAR", "status": "executada"},
                {"tipo": "CONVERSA_PAR", "status": "executada"},
                {"tipo": "CONVERSA_PAR", "status": "executada"},
                {"tipo": "CONVERSA_PAR", "status": "executada"},
                {"tipo": "CONVERSA_PAR", "status": "executada"},
                {"tipo": "CONVERSA_PAR", "status": "executada"},
                {"tipo": "CONVERSA_PAR", "status": "executada"},
                {"tipo": "CONVERSA_PAR", "status": "executada"},
                {"tipo": "CONVERSA_PAR", "status": "falhou"},
            ]
        )

        # Mock alertas
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            count=0
        )

        result = await diagnostico_warmup()

        assert result["health_status"] == "healthy"
        assert result["pool"]["total"] == 2
        assert result["pool"]["warming_ou_active"] == 2
        assert result["pool"]["trust_medio"] == 70.0

    @patch("app.services.warmer.health.supabase")
    async def test_critical_quando_conversa_par_abaixo_50(self, mock_sb, mock_chips_warming):
        mock_sb.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=mock_chips_warming
        )

        # 30% sucesso
        mock_sb.table.return_value.select.return_value.gte.return_value.execute.return_value = MagicMock(
            data=[
                {"tipo": "CONVERSA_PAR", "status": "executada"},
                {"tipo": "CONVERSA_PAR", "status": "executada"},
                {"tipo": "CONVERSA_PAR", "status": "executada"},
                {"tipo": "CONVERSA_PAR", "status": "falhou"},
                {"tipo": "CONVERSA_PAR", "status": "falhou"},
                {"tipo": "CONVERSA_PAR", "status": "falhou"},
                {"tipo": "CONVERSA_PAR", "status": "falhou"},
                {"tipo": "CONVERSA_PAR", "status": "falhou"},
                {"tipo": "CONVERSA_PAR", "status": "falhou"},
                {"tipo": "CONVERSA_PAR", "status": "falhou"},
            ]
        )

        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            count=0
        )

        result = await diagnostico_warmup()

        assert result["health_status"] == "critical"

    @patch("app.services.warmer.health.supabase")
    async def test_degraded_sem_atividades_conversa_par(self, mock_sb, mock_chips_warming):
        mock_sb.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=mock_chips_warming
        )

        # Sem atividades de CONVERSA_PAR, mas com chips ativos
        mock_sb.table.return_value.select.return_value.gte.return_value.execute.return_value = MagicMock(
            data=[
                {"tipo": "MARCAR_LIDO", "status": "executada"},
            ]
        )

        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            count=0
        )

        result = await diagnostico_warmup()

        assert result["health_status"] == "degraded"

    @patch("app.services.warmer.health.supabase")
    async def test_critical_sem_chips_ativos(self, mock_sb):
        # Nenhum chip warming/active
        mock_sb.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "id": "chip-1",
                    "telefone": "5511999990001",
                    "status": "provisioned",
                    "fase_warmup": "repouso",
                    "trust_score": 0,
                    "trust_level": "vermelho",
                    "warming_day": 0,
                    "msgs_enviadas_hoje": 0,
                    "evolution_connected": False,
                    "provider": "evolution",
                },
            ]
        )

        mock_sb.table.return_value.select.return_value.gte.return_value.execute.return_value = MagicMock(
            data=[]
        )

        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            count=0
        )

        result = await diagnostico_warmup()

        assert result["health_status"] == "critical"
        assert result["pool"]["warming_ou_active"] == 0

    @patch("app.services.warmer.health.supabase")
    async def test_retorna_atividades_por_tipo(self, mock_sb, mock_chips_warming):
        mock_sb.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=mock_chips_warming
        )

        mock_sb.table.return_value.select.return_value.gte.return_value.execute.return_value = MagicMock(
            data=[
                {"tipo": "CONVERSA_PAR", "status": "executada"},
                {"tipo": "CONVERSA_PAR", "status": "falhou"},
                {"tipo": "MARCAR_LIDO", "status": "executada"},
                {"tipo": "MARCAR_LIDO", "status": "executada"},
                {"tipo": "MARCAR_LIDO", "status": "planejada"},
            ]
        )

        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            count=2
        )

        result = await diagnostico_warmup()

        assert "CONVERSA_PAR" in result["atividades_hoje"]
        assert "MARCAR_LIDO" in result["atividades_hoje"]
        assert result["atividades_hoje"]["CONVERSA_PAR"]["total"] == 2
        assert result["atividades_hoje"]["CONVERSA_PAR"]["sucesso"] == 1
        assert result["atividades_hoje"]["CONVERSA_PAR"]["falha"] == 1
        assert result["atividades_hoje"]["CONVERSA_PAR"]["taxa_sucesso"] == 50.0
        assert result["atividades_hoje"]["MARCAR_LIDO"]["pendente"] == 1
        assert result["alertas_ativos"] == 2
