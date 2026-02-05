"""
Testes do FilaService - Fila de mensagens agendadas.

Sprint 23 E01 - Rastreamento completo de resultados
Sprint 36 T01 - Timeout e cancelamento
Sprint 44 T03.5 - Dead Letter Queue
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from app.services.fila import FilaService, fila_service


@pytest.fixture
def service():
    """Instância do FilaService."""
    return FilaService()


@pytest.fixture
def mensagem_mock():
    """Mensagem mockada da fila."""
    return {
        "id": "msg-123",
        "cliente_id": "cliente-abc",
        "conversa_id": "conv-xyz",
        "conteudo": "Oi Dr Carlos!",
        "tipo": "campanha",
        "prioridade": 3,
        "status": "pendente",
        "tentativas": 0,
        "max_tentativas": 3,
        "agendar_para": datetime.now(timezone.utc).isoformat(),
        "metadata": {"campanha_id": "42"},
        "clientes": {
            "telefone": "5511999999999",
            "primeiro_nome": "Carlos"
        }
    }


class TestEnfileirar:
    """Testes do método enfileirar."""

    @pytest.mark.asyncio
    async def test_enfileirar_mensagem_simples(self, service):
        """Enfileira mensagem com campos obrigatórios."""
        with patch("app.services.fila.supabase") as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
                {"id": "msg-novo", "cliente_id": "cliente-123"}
            ]

            resultado = await service.enfileirar(
                cliente_id="cliente-123",
                conteudo="Oi! Tudo bem?",
                tipo="campanha"
            )

            assert resultado is not None
            assert resultado["id"] == "msg-novo"
            mock_supabase.table.assert_called_with("fila_mensagens")

    @pytest.mark.asyncio
    async def test_enfileirar_com_metadata(self, service):
        """Enfileira mensagem com metadata de campanha."""
        with patch("app.services.fila.supabase") as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
                {"id": "msg-novo"}
            ]

            metadata = {
                "campanha_id": "42",
                "tipo_campanha": "discovery",
                "chips_excluidos": ["chip-1"]
            }

            resultado = await service.enfileirar(
                cliente_id="cliente-123",
                conteudo="Oi!",
                tipo="campanha",
                metadata=metadata
            )

            assert resultado is not None
            # Verificar que metadata foi passado
            call_args = mock_supabase.table.return_value.insert.call_args
            assert call_args[0][0]["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_enfileirar_com_agendamento(self, service):
        """Enfileira mensagem com agendamento futuro."""
        with patch("app.services.fila.supabase") as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
                {"id": "msg-agendada"}
            ]

            agendar_para = datetime.now(timezone.utc) + timedelta(hours=2)

            resultado = await service.enfileirar(
                cliente_id="cliente-123",
                conteudo="Mensagem agendada",
                tipo="campanha",
                agendar_para=agendar_para
            )

            assert resultado is not None
            call_args = mock_supabase.table.return_value.insert.call_args
            assert agendar_para.isoformat() in call_args[0][0]["agendar_para"]

    @pytest.mark.asyncio
    async def test_enfileirar_retorna_none_em_erro(self, service):
        """Retorna None quando insert falha."""
        with patch("app.services.fila.supabase") as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = None

            resultado = await service.enfileirar(
                cliente_id="cliente-123",
                conteudo="Teste",
                tipo="campanha"
            )

            assert resultado is None


class TestObterProxima:
    """Testes do método obter_proxima."""

    @pytest.mark.asyncio
    async def test_obter_proxima_disponivel(self, service, mensagem_mock):
        """Obtém próxima mensagem disponível."""
        with patch("app.services.fila.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.lte.return_value.order.return_value.order.return_value.limit.return_value.execute.return_value.data = [mensagem_mock]
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            resultado = await service.obter_proxima()

            assert resultado is not None
            assert resultado["id"] == "msg-123"
            # Deve ter marcado como processando
            mock_supabase.table.return_value.update.assert_called()

    @pytest.mark.asyncio
    async def test_obter_proxima_fila_vazia(self, service):
        """Retorna None quando fila está vazia."""
        with patch("app.services.fila.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.lte.return_value.order.return_value.order.return_value.limit.return_value.execute.return_value.data = []

            resultado = await service.obter_proxima()

            assert resultado is None


class TestMarcarEnviada:
    """Testes do método marcar_enviada."""

    @pytest.mark.asyncio
    async def test_marcar_enviada_sucesso(self, service):
        """Marca mensagem como enviada."""
        with patch("app.services.fila.supabase") as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
                {"id": "msg-123", "status": "enviada"}
            ]

            resultado = await service.marcar_enviada("msg-123")

            assert resultado is True
            call_args = mock_supabase.table.return_value.update.call_args
            assert call_args[0][0]["status"] == "enviada"

    @pytest.mark.asyncio
    async def test_marcar_enviada_nao_encontrada(self, service):
        """Retorna False quando mensagem não existe."""
        with patch("app.services.fila.supabase") as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

            resultado = await service.marcar_enviada("msg-inexistente")

            assert resultado is False


class TestRegistrarOutcome:
    """Testes do método registrar_outcome."""

    @pytest.mark.asyncio
    async def test_registrar_outcome_sent(self, service):
        """Registra outcome SENT."""
        with patch("app.services.fila.supabase") as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
                {"id": "msg-123"}
            ]

            from app.services.guardrails import SendOutcome

            resultado = await service.registrar_outcome(
                mensagem_id="msg-123",
                outcome=SendOutcome.SENT,
                provider_message_id="evolution-msg-456"
            )

            assert resultado is True
            call_args = mock_supabase.table.return_value.update.call_args
            assert call_args[0][0]["status"] == "enviada"
            assert call_args[0][0]["outcome"] == "SENT"
            assert call_args[0][0]["provider_message_id"] == "evolution-msg-456"

    @pytest.mark.asyncio
    async def test_registrar_outcome_blocked(self, service):
        """Registra outcome BLOCKED."""
        with patch("app.services.fila.supabase") as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
                {"id": "msg-123"}
            ]

            from app.services.guardrails import SendOutcome

            resultado = await service.registrar_outcome(
                mensagem_id="msg-123",
                outcome=SendOutcome.BLOCKED_OPTED_OUT,
                outcome_reason_code="opted_out"
            )

            assert resultado is True
            call_args = mock_supabase.table.return_value.update.call_args
            assert call_args[0][0]["status"] == "bloqueada"
            assert call_args[0][0]["outcome"] == "BLOCKED_OPTED_OUT"

    @pytest.mark.asyncio
    async def test_registrar_outcome_failed(self, service):
        """Registra outcome FAILED."""
        with patch("app.services.fila.supabase") as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
                {"id": "msg-123"}
            ]

            from app.services.guardrails import SendOutcome

            resultado = await service.registrar_outcome(
                mensagem_id="msg-123",
                outcome=SendOutcome.FAILED_PROVIDER,
                outcome_reason_code="provider_error"
            )

            assert resultado is True
            call_args = mock_supabase.table.return_value.update.call_args
            assert call_args[0][0]["status"] == "erro"
            assert call_args[0][0]["outcome"] == "FAILED_PROVIDER"


class TestMarcarErro:
    """Testes do método marcar_erro."""

    @pytest.mark.asyncio
    async def test_marcar_erro_com_retry(self, service):
        """Marca erro e agenda retry quando ainda tem tentativas."""
        with patch("app.services.fila.supabase") as mock_supabase:
            # Mock busca de tentativas atuais
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
                "tentativas": 1,
                "max_tentativas": 3
            }
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            resultado = await service.marcar_erro("msg-123", "Erro temporário")

            assert resultado is True  # Retry agendado
            call_args = mock_supabase.table.return_value.update.call_args
            assert call_args[0][0]["status"] == "pendente"
            assert call_args[0][0]["tentativas"] == 2

    @pytest.mark.asyncio
    async def test_marcar_erro_esgotou_tentativas(self, service):
        """Marca como erro quando esgota tentativas."""
        with patch("app.services.fila.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
                "tentativas": 2,
                "max_tentativas": 3
            }
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
            # Mock para DLQ
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

            with patch.object(service, "_mover_para_dlq", new_callable=AsyncMock) as mock_dlq:
                mock_dlq.return_value = True

                resultado = await service.marcar_erro("msg-123", "Erro fatal")

                assert resultado is False  # Não há mais retry
                mock_dlq.assert_called_once()


class TestDLQ:
    """Testes da Dead Letter Queue."""

    @pytest.mark.asyncio
    async def test_mover_para_dlq(self, service, mensagem_mock):
        """Move mensagem falhada para DLQ."""
        with patch("app.services.fila.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = mensagem_mock
            mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

            resultado = await service._mover_para_dlq(
                mensagem_id="msg-123",
                tentativas=3,
                erro="Erro após 3 tentativas"
            )

            assert resultado is True
            # Verificar que inseriu na DLQ
            calls = mock_supabase.table.call_args_list
            dlq_calls = [c for c in calls if c[0][0] == "fila_mensagens_dlq"]
            assert len(dlq_calls) > 0

    @pytest.mark.asyncio
    async def test_listar_dlq(self, service):
        """Lista mensagens na DLQ."""
        with patch("app.services.fila.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                {"id": "dlq-1", "mensagem_original_id": "msg-123"},
                {"id": "dlq-2", "mensagem_original_id": "msg-456"},
            ]

            resultado = await service.listar_dlq(limite=50)

            assert len(resultado) == 2

    @pytest.mark.asyncio
    async def test_reprocessar_da_dlq(self, service):
        """Reprocessa mensagem da DLQ."""
        with patch("app.services.fila.supabase") as mock_supabase:
            # Mock busca da DLQ
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
                "id": "dlq-1",
                "cliente_id": "cliente-123",
                "conteudo": "Mensagem original",
                "tipo": "campanha",
                "reprocessado": False,
                "metadata": {}
            }
            # Mock insert nova mensagem
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
                {"id": "msg-nova"}
            ]
            # Mock update DLQ
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            resultado = await service.reprocessar_da_dlq("dlq-1", usuario="admin")

            assert resultado is not None
            assert resultado["id"] == "msg-nova"


class TestTimeoutECancelamento:
    """Testes de timeout e cancelamento (Sprint 36)."""

    @pytest.mark.asyncio
    async def test_resetar_mensagens_travadas(self, service):
        """Reseta mensagens travadas em processando."""
        with patch("app.services.fila.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.lt.return_value.execute.return_value.data = [
                {"id": "msg-1", "tentativas": 0, "max_tentativas": 3},
                {"id": "msg-2", "tentativas": 2, "max_tentativas": 3},
            ]
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            with patch.object(service, "_mover_para_dlq", new_callable=AsyncMock) as mock_dlq:
                mock_dlq.return_value = True

                resetadas = await service.resetar_mensagens_travadas(timeout_minutos=60)

                assert resetadas == 2

    @pytest.mark.asyncio
    async def test_cancelar_mensagens_antigas(self, service):
        """Cancela mensagens pendentes muito antigas."""
        with patch("app.services.fila.supabase") as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.lt.return_value.execute.return_value.data = [
                {"id": "msg-antiga-1"},
                {"id": "msg-antiga-2"},
            ]

            canceladas = await service.cancelar_mensagens_antigas(max_idade_horas=24)

            assert canceladas == 2
            call_args = mock_supabase.table.return_value.update.call_args
            assert call_args[0][0]["status"] == "cancelada"
            assert call_args[0][0]["outcome"] == "FAILED_EXPIRED"


class TestMetricas:
    """Testes de métricas da fila."""

    @pytest.mark.asyncio
    async def test_obter_metricas_fila(self, service):
        """Obtém métricas básicas da fila."""
        with patch("app.services.fila.supabase") as mock_supabase:
            # Mock genérico que funciona para todas as chamadas
            mock_result = MagicMock()
            mock_result.count = 10
            mock_result.data = []

            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.gte.return_value = mock_table
            mock_table.lte.return_value = mock_table
            mock_table.order.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.execute.return_value = mock_result

            mock_supabase.table.return_value = mock_table

            metricas = await service.obter_metricas_fila()

            assert "pendentes" in metricas
            assert "processando" in metricas
            assert "erros_ultimas_24h" in metricas

    @pytest.mark.asyncio
    async def test_obter_estatisticas_completas(self, service):
        """Obtém estatísticas completas da fila."""
        with patch("app.services.fila.supabase") as mock_supabase:
            mock_count = MagicMock()
            mock_count.count = 5

            mock_mais_antiga = MagicMock()
            mock_mais_antiga.data = []

            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_count
            mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = mock_count
            mock_supabase.table.return_value.select.return_value.eq.return_value.lt.return_value.execute.return_value = mock_count
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_mais_antiga

            stats = await service.obter_estatisticas_completas()

            assert "pendentes" in stats
            assert "processando" in stats
            assert "enviadas_ultima_hora" in stats
            assert "erros_ultima_hora" in stats
            assert "travadas" in stats
