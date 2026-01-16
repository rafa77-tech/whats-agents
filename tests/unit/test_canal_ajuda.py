"""
Testes para serviço de Canal de Ajuda Julia.

Sprint 32 E08 - Julia pede ajuda ao gestor.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta, timezone


class TestCriarPedidoAjuda:
    """Testes para criar_pedido_ajuda()."""

    @pytest.mark.asyncio
    async def test_cria_pedido_com_sucesso(self):
        """Deve criar pedido de ajuda e notificar Slack."""
        from app.services.canal_ajuda import criar_pedido_ajuda

        with patch("app.services.canal_ajuda.supabase") as mock_supabase:
            # Mock busca cliente
            mock_cliente = MagicMock()
            mock_cliente.data = [{"primeiro_nome": "Dr. João", "telefone": "5511999999999"}]
            mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_cliente

            # Mock insert pedido
            mock_insert = MagicMock()
            mock_insert.data = [{"id": "pedido-123"}]
            mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_insert

            # Mock update conversa
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            with patch("app.services.canal_ajuda.enviar_slack") as mock_slack:
                mock_slack.return_value = True

                resultado = await criar_pedido_ajuda(
                    conversa_id="conv-123",
                    cliente_id="cliente-123",
                    pergunta="O hospital tem estacionamento?",
                    categoria="hospital",
                )

                assert resultado is not None
                assert resultado.get("id") == "pedido-123"
                mock_slack.assert_called_once()

    @pytest.mark.asyncio
    async def test_cria_pedido_com_contexto(self):
        """Deve criar pedido com contexto adicional."""
        from app.services.canal_ajuda import criar_pedido_ajuda

        with patch("app.services.canal_ajuda.supabase") as mock_supabase:
            mock_cliente = MagicMock()
            mock_cliente.data = [{"primeiro_nome": "Dr. Maria", "telefone": "5511888888888"}]
            mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_cliente

            mock_insert = MagicMock()
            mock_insert.data = [{"id": "pedido-456", "contexto": {"hospital_id": "hosp-123"}}]
            mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_insert

            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            with patch("app.services.canal_ajuda.enviar_slack") as mock_slack:
                mock_slack.return_value = True

                resultado = await criar_pedido_ajuda(
                    conversa_id="conv-456",
                    cliente_id="cliente-456",
                    pergunta="Tem refeição inclusa?",
                    categoria="hospital",
                    contexto={"hospital_id": "hosp-123", "hospital_nome": "Hospital São Luiz"},
                )

                assert resultado is not None


class TestProcessarRespostaGestor:
    """Testes para processar_resposta_gestor()."""

    @pytest.mark.asyncio
    async def test_processa_resposta_com_sucesso(self):
        """Deve processar resposta e retomar conversa."""
        from app.services.canal_ajuda import processar_resposta_gestor

        with patch("app.services.canal_ajuda.supabase") as mock_supabase:
            # Mock busca pedido
            mock_pedido = MagicMock()
            mock_pedido.data = [{
                "id": "pedido-123",
                "conversa_id": "conv-123",
                "cliente_id": "cliente-123",
                "status": "pendente",
                "categoria": "outro",
            }]
            mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_pedido

            # Mock update pedido
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            resultado = await processar_resposta_gestor(
                pedido_id="pedido-123",
                resposta="Sim, tem estacionamento gratuito",
                respondido_por="gestor-rafael",
            )

            assert resultado["success"] is True
            assert resultado["pedido_id"] == "pedido-123"

    @pytest.mark.asyncio
    async def test_rejeita_pedido_ja_respondido(self):
        """Deve rejeitar se pedido já foi respondido."""
        from app.services.canal_ajuda import processar_resposta_gestor

        with patch("app.services.canal_ajuda.supabase") as mock_supabase:
            mock_pedido = MagicMock()
            mock_pedido.data = [{
                "id": "pedido-123",
                "status": "respondido",  # Já respondido
            }]
            mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_pedido

            resultado = await processar_resposta_gestor(
                pedido_id="pedido-123",
                resposta="Resposta duplicada",
                respondido_por="gestor-rafael",
            )

            assert resultado["success"] is False
            assert "já está em status" in resultado["error"]

    @pytest.mark.asyncio
    async def test_pedido_nao_encontrado(self):
        """Deve retornar erro se pedido não existe."""
        from app.services.canal_ajuda import processar_resposta_gestor

        with patch("app.services.canal_ajuda.supabase") as mock_supabase:
            mock_pedido = MagicMock()
            mock_pedido.data = []
            mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_pedido

            resultado = await processar_resposta_gestor(
                pedido_id="pedido-inexistente",
                resposta="Resposta",
                respondido_por="gestor-rafael",
            )

            assert resultado["success"] is False
            assert "não encontrado" in resultado["error"]


class TestVerificarTimeouts:
    """Testes para verificar_timeouts()."""

    @pytest.mark.asyncio
    async def test_processa_pedidos_com_timeout(self):
        """Deve processar pedidos que deram timeout."""
        from app.services.canal_ajuda import verificar_timeouts

        with patch("app.services.canal_ajuda.supabase") as mock_supabase:
            # Mock busca pedidos pendentes com timeout
            mock_pedidos = MagicMock()
            mock_pedidos.data = [
                {"id": "pedido-1", "cliente_id": "c1", "pergunta": "Pergunta 1"},
                {"id": "pedido-2", "cliente_id": "c2", "pergunta": "Pergunta 2"},
            ]
            mock_supabase.table.return_value.select.return_value.eq.return_value.lt.return_value.execute.return_value = mock_pedidos

            # Mock update status
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            with patch("app.services.canal_ajuda._enviar_lembrete") as mock_lembrete:
                mock_lembrete.return_value = None

                resultado = await verificar_timeouts()

                assert resultado["encontrados"] == 2

    @pytest.mark.asyncio
    async def test_retorna_vazio_sem_timeouts(self):
        """Deve retornar 0 se não há timeouts."""
        from app.services.canal_ajuda import verificar_timeouts

        with patch("app.services.canal_ajuda.supabase") as mock_supabase:
            mock_pedidos = MagicMock()
            mock_pedidos.data = []
            mock_supabase.table.return_value.select.return_value.eq.return_value.lt.return_value.execute.return_value = mock_pedidos

            resultado = await verificar_timeouts()

            assert resultado["encontrados"] == 0


class TestBuscarPedidoPendente:
    """Testes para buscar_pedido_pendente()."""

    @pytest.mark.asyncio
    async def test_encontra_pedido_pendente(self):
        """Deve encontrar pedido pendente para conversa."""
        from app.services.canal_ajuda import buscar_pedido_pendente

        with patch("app.services.canal_ajuda.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [{"id": "pedido-123", "status": "pendente"}]
            mock_supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

            resultado = await buscar_pedido_pendente("conv-123")

            assert resultado is not None
            assert resultado["id"] == "pedido-123"

    @pytest.mark.asyncio
    async def test_retorna_none_sem_pedido(self):
        """Deve retornar None se não há pedido pendente."""
        from app.services.canal_ajuda import buscar_pedido_pendente

        with patch("app.services.canal_ajuda.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = []
            mock_supabase.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

            resultado = await buscar_pedido_pendente("conv-456")

            assert resultado is None


class TestJuliaPrecisaAjuda:
    """Testes para julia_precisa_ajuda()."""

    @pytest.mark.asyncio
    async def test_cria_pedido_e_retorna_sugestao(self):
        """Deve criar pedido e retornar mensagem sugerida."""
        from app.services.canal_ajuda import julia_precisa_ajuda

        with patch("app.services.canal_ajuda.criar_pedido_ajuda") as mock_criar:
            mock_criar.return_value = {"id": "pedido-789"}

            resultado = await julia_precisa_ajuda(
                conversa_id="conv-789",
                cliente_id="cliente-789",
                pergunta_medico="Tem estacionamento?",
                categoria="hospital",
            )

            assert resultado["pedido_id"] == "pedido-789"
            assert resultado["status"] == "aguardando_gestor"
            assert "Vou confirmar" in resultado["mensagem_sugerida"]


class TestVerificarRespostaPendente:
    """Testes para verificar_resposta_pendente()."""

    @pytest.mark.asyncio
    async def test_encontra_resposta_pendente(self):
        """Deve encontrar resposta do gestor."""
        from app.services.canal_ajuda import verificar_resposta_pendente

        with patch("app.services.canal_ajuda.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [{"resposta": "Sim, tem estacionamento gratuito"}]
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

            resultado = await verificar_resposta_pendente("conv-123")

            assert resultado == "Sim, tem estacionamento gratuito"

    @pytest.mark.asyncio
    async def test_retorna_none_sem_resposta(self):
        """Deve retornar None se não há resposta."""
        from app.services.canal_ajuda import verificar_resposta_pendente

        with patch("app.services.canal_ajuda.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = []
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

            resultado = await verificar_resposta_pendente("conv-456")

            assert resultado is None
