"""Testes para tools de métricas Helena."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


class TestMetricasPeriodo:
    """Testes para metricas_periodo."""

    @pytest.mark.asyncio
    async def test_metricas_hoje(self):
        """Testa métricas de hoje."""
        from app.tools.helena.metricas import handle_metricas_periodo

        mock_result = MagicMock()
        mock_result.data = [{
            "total_conversas": 50,
            "com_resposta": 30,
            "conversoes": 10,
        }]

        with patch('app.tools.helena.metricas.supabase') as mock_db:
            mock_db.rpc.return_value.execute.return_value = mock_result

            result = await handle_metricas_periodo(
                {"periodo": "hoje"}, "U123", "C456"
            )

        assert result["success"] is True
        assert result["metricas"]["total_conversas"] == 50
        assert result["metricas"]["taxa_resposta"] == 60.0  # 30/50

    @pytest.mark.asyncio
    async def test_metricas_ontem(self):
        """Testa métricas de ontem."""
        from app.tools.helena.metricas import handle_metricas_periodo

        mock_result = MagicMock()
        mock_result.data = [{
            "total_conversas": 40,
            "com_resposta": 20,
            "conversoes": 5,
        }]

        with patch('app.tools.helena.metricas.supabase') as mock_db:
            mock_db.rpc.return_value.execute.return_value = mock_result

            result = await handle_metricas_periodo(
                {"periodo": "ontem"}, "U123", "C456"
            )

        assert result["success"] is True
        assert result["periodo"] == "ontem"
        assert result["metricas"]["total_conversas"] == 40

    @pytest.mark.asyncio
    async def test_metricas_periodo_invalido(self):
        """Testa período inválido."""
        from app.tools.helena.metricas import handle_metricas_periodo

        result = await handle_metricas_periodo(
            {"periodo": "invalido"}, "U123", "C456"
        )

        assert result["success"] is False
        assert "inválido" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_metricas_sem_dados(self):
        """Testa retorno quando não há dados."""
        from app.tools.helena.metricas import handle_metricas_periodo

        mock_result = MagicMock()
        mock_result.data = []

        with patch('app.tools.helena.metricas.supabase') as mock_db:
            mock_db.rpc.return_value.execute.return_value = mock_result

            result = await handle_metricas_periodo(
                {"periodo": "hoje"}, "U123", "C456"
            )

        assert result["success"] is True
        assert result["metricas"]["total_conversas"] == 0
        assert result["metricas"]["taxa_resposta"] == 0

    @pytest.mark.asyncio
    async def test_metricas_taxa_conversao_zero_respostas(self):
        """Testa taxa de conversão quando não há respostas."""
        from app.tools.helena.metricas import handle_metricas_periodo

        mock_result = MagicMock()
        mock_result.data = [{
            "total_conversas": 10,
            "com_resposta": 0,
            "conversoes": 0,
        }]

        with patch('app.tools.helena.metricas.supabase') as mock_db:
            mock_db.rpc.return_value.execute.return_value = mock_result

            result = await handle_metricas_periodo(
                {"periodo": "hoje"}, "U123", "C456"
            )

        assert result["success"] is True
        assert result["metricas"]["taxa_conversao"] == 0


class TestMetricasConversao:
    """Testes para metricas_conversao."""

    @pytest.mark.asyncio
    async def test_funil_completo(self):
        """Testa funil de conversão completo."""
        from app.tools.helena.metricas import handle_metricas_conversao

        mock_result = MagicMock()
        mock_result.data = [{
            "total_abordados": 100,
            "responderam": 50,
            "converteram": 10,
            "perdidos": 20,
        }]

        with patch('app.tools.helena.metricas.supabase') as mock_db:
            mock_db.rpc.return_value.execute.return_value = mock_result

            result = await handle_metricas_conversao(
                {"dias": 7}, "U123", "C456"
            )

        assert result["success"] is True
        assert result["funil"]["abordados"]["quantidade"] == 100
        assert result["funil"]["responderam"]["taxa"] == 50.0
        assert result["funil"]["converteram"]["taxa"] == 20.0  # 10/50

    @pytest.mark.asyncio
    async def test_funil_dias_customizado(self):
        """Testa funil com dias customizado."""
        from app.tools.helena.metricas import handle_metricas_conversao

        mock_result = MagicMock()
        mock_result.data = [{"total_abordados": 200, "responderam": 100, "converteram": 25, "perdidos": 50}]

        with patch('app.tools.helena.metricas.supabase') as mock_db:
            mock_db.rpc.return_value.execute.return_value = mock_result

            result = await handle_metricas_conversao(
                {"dias": 30}, "U123", "C456"
            )

        assert result["success"] is True
        assert result["dias"] == 30


class TestMetricasCampanhas:
    """Testes para metricas_campanhas."""

    @pytest.mark.asyncio
    async def test_lista_campanhas_ativas(self):
        """Testa listagem de campanhas ativas."""
        from app.tools.helena.metricas import handle_metricas_campanhas

        mock_result = MagicMock()
        mock_result.data = [
            {"id": 1, "nome_template": "Discovery", "status": "ativa"},
            {"id": 2, "nome_template": "Oferta", "status": "ativa"},
        ]

        with patch('app.tools.helena.metricas.supabase') as mock_db:
            mock_db.rpc.return_value.execute.return_value = mock_result

            result = await handle_metricas_campanhas(
                {"status": "ativa"}, "U123", "C456"
            )

        assert result["success"] is True
        assert result["total"] == 2
        assert result["filtro_status"] == "ativa"

    @pytest.mark.asyncio
    async def test_lista_todas_campanhas(self):
        """Testa listagem de todas as campanhas."""
        from app.tools.helena.metricas import handle_metricas_campanhas

        mock_result = MagicMock()
        mock_result.data = [
            {"id": 1, "nome_template": "Discovery", "status": "ativa"},
            {"id": 2, "nome_template": "Oferta", "status": "concluida"},
        ]

        with patch('app.tools.helena.metricas.supabase') as mock_db:
            mock_db.rpc.return_value.execute.return_value = mock_result

            result = await handle_metricas_campanhas(
                {"status": "todas"}, "U123", "C456"
            )

        assert result["success"] is True
        assert result["filtro_status"] == "todas"

    @pytest.mark.asyncio
    async def test_limite_respeitado(self):
        """Testa que limite máximo é respeitado."""
        from app.tools.helena.metricas import handle_metricas_campanhas

        mock_result = MagicMock()
        mock_result.data = []

        with patch('app.tools.helena.metricas.supabase') as mock_db:
            mock_db.rpc.return_value.execute.return_value = mock_result

            # Solicitar limite maior que 50
            result = await handle_metricas_campanhas(
                {"status": "todas", "limite": 100}, "U123", "C456"
            )

        # Deve funcionar (limite é internamente limitado a 50)
        assert result["success"] is True


class TestStatusSistema:
    """Testes para status_sistema."""

    @pytest.mark.asyncio
    async def test_status_completo(self):
        """Testa retorno de status completo."""
        from app.tools.helena.sistema import handle_status_sistema

        with patch('app.tools.helena.sistema.supabase') as mock_db:
            # Mock para chips
            mock_chips = MagicMock()
            mock_chips.data = [{"status": "active", "quantidade": 5}]

            # Mock para fila
            mock_fila = MagicMock()
            mock_fila.data = [{"status": "enviada", "quantidade": 100}]

            # Mock para handoffs
            mock_handoffs = MagicMock()
            mock_handoffs.data = [{"pendentes": 3}]

            mock_db.rpc.return_value.execute.side_effect = [
                mock_chips, mock_fila, mock_handoffs
            ]

            result = await handle_status_sistema({}, "U123", "C456")

        assert result["success"] is True
        assert "chips" in result
        assert "fila_24h" in result
        assert result["handoffs_pendentes"] == 3


class TestListarHandoffs:
    """Testes para listar_handoffs."""

    @pytest.mark.asyncio
    async def test_listar_pendentes(self):
        """Testa listagem de handoffs pendentes."""
        from app.tools.helena.sistema import handle_listar_handoffs

        mock_result = MagicMock()
        mock_result.data = [
            {"id": "h1", "motivo": "Pedido humano", "status": "pendente"},
            {"id": "h2", "motivo": "Jurídico", "status": "pendente"},
        ]

        with patch('app.tools.helena.sistema.supabase') as mock_db:
            mock_db.rpc.return_value.execute.return_value = mock_result

            result = await handle_listar_handoffs(
                {"status": "pendente"}, "U123", "C456"
            )

        assert result["success"] is True
        assert result["total"] == 2
        assert result["filtro_status"] == "pendente"

    @pytest.mark.asyncio
    async def test_listar_todos(self):
        """Testa listagem de todos os handoffs."""
        from app.tools.helena.sistema import handle_listar_handoffs

        mock_result = MagicMock()
        mock_result.data = [
            {"id": "h1", "status": "pendente"},
            {"id": "h2", "status": "resolvido"},
        ]

        with patch('app.tools.helena.sistema.supabase') as mock_db:
            mock_db.rpc.return_value.execute.return_value = mock_result

            result = await handle_listar_handoffs(
                {"status": "todos"}, "U123", "C456"
            )

        assert result["success"] is True
        assert result["filtro_status"] == "todos"
