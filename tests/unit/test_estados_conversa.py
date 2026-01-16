"""
Testes para serviço de Estados de Conversa.

Sprint 32 E15 - Gerenciamento de estados de conversa.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestPodeJuliaResponder:
    """Testes para pode_julia_responder()."""

    @pytest.mark.asyncio
    async def test_retorna_true_para_conversa_ativa(self):
        """Deve retornar True para conversa ativa."""
        from app.services.estados_conversa import pode_julia_responder

        with patch("app.services.estados_conversa.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [{"status": "active", "controlled_by": "ai"}]
            mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result

            resultado = await pode_julia_responder("conv-123")

            assert resultado is True

    @pytest.mark.asyncio
    async def test_retorna_false_para_handoff(self):
        """Deve retornar False para conversa em handoff."""
        from app.services.estados_conversa import pode_julia_responder

        with patch("app.services.estados_conversa.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [{"status": "handoff", "controlled_by": "human"}]
            mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result

            resultado = await pode_julia_responder("conv-123")

            assert resultado is False

    @pytest.mark.asyncio
    async def test_retorna_false_para_aguardando_gestor(self):
        """Deve retornar False quando aguardando gestor."""
        from app.services.estados_conversa import pode_julia_responder

        with patch("app.services.estados_conversa.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [{"status": "aguardando_gestor", "controlled_by": "ai"}]
            mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result

            resultado = await pode_julia_responder("conv-123")

            assert resultado is False

    @pytest.mark.asyncio
    async def test_retorna_false_para_conversa_inexistente(self):
        """Deve retornar False para conversa que não existe."""
        from app.services.estados_conversa import pode_julia_responder

        with patch("app.services.estados_conversa.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = []
            mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result

            resultado = await pode_julia_responder("conv-inexistente")

            assert resultado is False


class TestPausarParaGestor:
    """Testes para pausar_para_gestor()."""

    @pytest.mark.asyncio
    async def test_pausa_conversa_com_sucesso(self):
        """Deve pausar conversa aguardando gestor."""
        from app.services.estados_conversa import pausar_para_gestor

        with patch("app.services.estados_conversa.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [{"id": "conv-123", "status": "aguardando_gestor"}]
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result

            resultado = await pausar_para_gestor(
                conversa_id="conv-123",
                pedido_ajuda_id="pedido-456",
            )

            assert resultado["success"] is True
            assert resultado["status"] == "aguardando_gestor"


class TestRetomarConversa:
    """Testes para retomar_conversa()."""

    @pytest.mark.asyncio
    async def test_retoma_conversa_com_sucesso(self):
        """Deve retomar conversa pausada."""
        from app.services.estados_conversa import retomar_conversa

        with patch("app.services.estados_conversa.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [{"id": "conv-123", "status": "active"}]
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result

            resultado = await retomar_conversa("conv-123")

            assert resultado["success"] is True
            assert resultado["status"] == "active"


class TestMarcarHandoff:
    """Testes para marcar_handoff()."""

    @pytest.mark.asyncio
    async def test_marca_handoff_com_sucesso(self):
        """Deve marcar conversa como handoff."""
        from app.services.estados_conversa import marcar_handoff

        with patch("app.services.estados_conversa.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [{"id": "conv-123", "status": "handoff"}]
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result

            resultado = await marcar_handoff(
                conversa_id="conv-123",
                motivo="Médico pediu para falar com humano",
            )

            assert resultado["success"] is True
            assert resultado["status"] == "handoff"


class TestResolverHandoff:
    """Testes para resolver_handoff()."""

    @pytest.mark.asyncio
    async def test_resolve_handoff_retornando_para_julia(self):
        """Deve resolver handoff e retornar para Julia."""
        from app.services.estados_conversa import resolver_handoff

        with patch("app.services.estados_conversa.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [{"id": "conv-123", "status": "active"}]
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result

            resultado = await resolver_handoff(
                conversa_id="conv-123",
                retornar_para_julia=True,
            )

            assert resultado["success"] is True
            assert resultado["status"] == "active"

    @pytest.mark.asyncio
    async def test_resolve_handoff_concluindo(self):
        """Deve resolver handoff e concluir conversa."""
        from app.services.estados_conversa import resolver_handoff

        with patch("app.services.estados_conversa.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [{"id": "conv-123", "status": "completed"}]
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result

            resultado = await resolver_handoff(
                conversa_id="conv-123",
                retornar_para_julia=False,
            )

            assert resultado["success"] is True
            assert resultado["status"] == "completed"


class TestConcluirConversa:
    """Testes para concluir_conversa()."""

    @pytest.mark.asyncio
    async def test_conclui_conversa_com_sucesso(self):
        """Deve concluir conversa."""
        from app.services.estados_conversa import concluir_conversa

        with patch("app.services.estados_conversa.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [{"id": "conv-123", "status": "completed"}]
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result

            resultado = await concluir_conversa("conv-123", motivo="Médico não tem interesse")

            assert resultado["success"] is True
            assert resultado["status"] == "completed"


class TestObterEstadoConversa:
    """Testes para obter_estado_conversa()."""

    @pytest.mark.asyncio
    async def test_obtem_estado_completo(self):
        """Deve obter estado completo da conversa."""
        from app.services.estados_conversa import obter_estado_conversa

        with patch("app.services.estados_conversa.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [{
                "id": "conv-123",
                "status": "aguardando_gestor",
                "controlled_by": "ai",
                "pausada_em": "2026-01-16T10:00:00Z",
                "retomada_em": None,
                "motivo_pausa": "aguardando_gestor",
                "pedido_ajuda_id": "pedido-456",
            }]
            mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result

            with patch("app.services.estados_conversa.pode_julia_responder") as mock_pode:
                mock_pode.return_value = False

                resultado = await obter_estado_conversa("conv-123")

                assert resultado is not None
                assert resultado["status"] == "aguardando_gestor"
                assert resultado["julia_pode_responder"] is False


class TestListarConversasPausadas:
    """Testes para listar_conversas_pausadas()."""

    @pytest.mark.asyncio
    async def test_lista_conversas_pausadas(self):
        """Deve listar conversas pausadas."""
        from app.services.estados_conversa import listar_conversas_pausadas

        with patch("app.services.estados_conversa.supabase") as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = [
                {"id": "c1", "status": "aguardando_gestor"},
                {"id": "c2", "status": "paused"},
            ]
            mock_supabase.table.return_value.select.return_value.in_.return_value.order.return_value.execute.return_value = mock_result

            resultado = await listar_conversas_pausadas()

            assert len(resultado) == 2


class TestContarConversasPorEstado:
    """Testes para contar_conversas_por_estado()."""

    @pytest.mark.asyncio
    async def test_conta_conversas_por_estado(self):
        """Deve contar conversas por estado."""
        from app.services.estados_conversa import contar_conversas_por_estado

        with patch("app.services.estados_conversa.supabase") as mock_supabase:
            def mock_count(estado):
                contagens = {
                    "active": 10,
                    "aguardando_gestor": 2,
                    "paused": 1,
                    "handoff": 3,
                }
                mock_result = MagicMock()
                mock_result.count = contagens.get(estado, 0)
                return mock_result

            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
                mock_count("active"),
                mock_count("aguardando_gestor"),
                mock_count("paused"),
                mock_count("handoff"),
            ]

            resultado = await contar_conversas_por_estado()

            assert resultado["active"] == 10
            assert resultado["aguardando_gestor"] == 2
            assert resultado["handoff"] == 3
