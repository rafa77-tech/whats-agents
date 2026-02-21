"""
Testes para HandoffProtocol e AgentRegistry.

Sprint 70+ — Chunk 26.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestAgentRegistry:

    def test_agentes_padrao_registrados(self):
        from app.services.agents.agent_registry import AgentRegistry

        registry = AgentRegistry()
        assert registry.esta_registrado("julia")
        assert registry.esta_registrado("helena")
        assert registry.esta_registrado("human")

    def test_listar_agentes(self):
        from app.services.agents.agent_registry import AgentRegistry

        registry = AgentRegistry()
        agents = registry.listar()
        assert len(agents) >= 3

    def test_encontrar_por_capacidade(self):
        from app.services.agents.agent_registry import AgentRegistry

        registry = AgentRegistry()
        agents = registry.encontrar_por_capacidade("prospeccao")
        assert any(a.name == "julia" for a in agents)

    def test_obter_agente(self):
        from app.services.agents.agent_registry import AgentRegistry

        registry = AgentRegistry()
        julia = registry.obter("julia")
        assert julia is not None
        assert julia.name == "julia"
        assert "prospeccao" in julia.capabilities


class TestHandoffProtocol:

    @pytest.mark.asyncio
    async def test_transfer_sucesso(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch("app.services.agents.handoff_protocol.supabase", mock_sb):
            from app.services.agents.handoff_protocol import HandoffProtocol

            protocol = HandoffProtocol()
            result = await protocol.transfer("julia", "human", "conv_1", {"motivo": "irritado"})
            assert result["success"] is True
            assert result["from_agent"] == "julia"
            assert result["to_agent"] == "human"

    @pytest.mark.asyncio
    async def test_transfer_agente_invalido(self):
        with patch("app.services.agents.handoff_protocol.supabase", MagicMock()):
            from app.services.agents.handoff_protocol import HandoffProtocol

            protocol = HandoffProtocol()
            result = await protocol.transfer("inexistente", "julia", "conv_1")
            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_obter_agente_atual(self):
        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = [{"controlled_by": "julia"}]
        mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = resp

        with patch("app.services.agents.handoff_protocol.supabase", mock_sb):
            from app.services.agents.handoff_protocol import HandoffProtocol

            protocol = HandoffProtocol()
            agent = await protocol.obter_agente_atual("conv_1")
            assert agent == "julia"
