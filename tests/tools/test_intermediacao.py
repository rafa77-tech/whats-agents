"""
Testes para Tools de Intermediacao.

Sprint 29 - Conversation Mode

GUARDRAIL CRÍTICO: Julia é INTERMEDIÁRIA
- Nao negocia valores
- Nao confirma reservas
- Conecta medico com responsavel da vaga

Testes verificam:
1. Tool criar_handoff_externo conecta partes
2. Tool registrar_status_intermediacao atualiza status
3. Validacoes de input funcionam
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.tools.intermediacao import (
    TOOL_CRIAR_HANDOFF_EXTERNO,
    TOOL_REGISTRAR_STATUS_INTERMEDIACAO,
    TOOLS_INTERMEDIACAO,
    handle_criar_handoff_externo,
    handle_registrar_status_intermediacao,
)


class TestToolDefinitions:
    """Testes da definicao das tools."""

    def test_tools_list_has_two_tools(self):
        """Lista de tools tem as duas tools de intermediacao."""
        assert len(TOOLS_INTERMEDIACAO) == 2

    def test_criar_handoff_externo_has_name(self):
        """Tool criar_handoff_externo tem nome correto."""
        assert TOOL_CRIAR_HANDOFF_EXTERNO["name"] == "criar_handoff_externo"

    def test_registrar_status_intermediacao_has_name(self):
        """Tool registrar_status_intermediacao tem nome correto."""
        assert TOOL_REGISTRAR_STATUS_INTERMEDIACAO["name"] == "registrar_status_intermediacao"

    def test_criar_handoff_externo_has_description(self):
        """Tool criar_handoff_externo tem descricao."""
        assert len(TOOL_CRIAR_HANDOFF_EXTERNO["description"]) > 100

    def test_registrar_status_intermediacao_has_description(self):
        """Tool registrar_status_intermediacao tem descricao."""
        assert len(TOOL_REGISTRAR_STATUS_INTERMEDIACAO["description"]) > 100

    def test_criar_handoff_externo_required_params(self):
        """Tool criar_handoff_externo tem parametros obrigatorios."""
        required = TOOL_CRIAR_HANDOFF_EXTERNO["input_schema"]["required"]
        assert "vaga_id" in required
        assert "motivo" in required

    def test_registrar_status_intermediacao_required_params(self):
        """Tool registrar_status_intermediacao tem parametros obrigatorios."""
        required = TOOL_REGISTRAR_STATUS_INTERMEDIACAO["input_schema"]["required"]
        assert "vaga_id" in required
        assert "status" in required

    def test_registrar_status_has_valid_enum(self):
        """Tool registrar_status_intermediacao tem enum de status valido."""
        properties = TOOL_REGISTRAR_STATUS_INTERMEDIACAO["input_schema"]["properties"]
        status_enum = properties["status"]["enum"]
        assert "fechado" in status_enum
        assert "sem_resposta" in status_enum
        assert "desistiu" in status_enum


class TestHandleCriarHandoffExterno:
    """Testes do handler criar_handoff_externo."""

    @pytest.fixture
    def medico_mock(self):
        """Mock do medico."""
        return {
            "id": "12345678-1234-1234-1234-123456789012",
            "nome": "Dr. Teste",
            "telefone": "11999998888",
        }

    @pytest.fixture
    def conversa_mock(self):
        """Mock da conversa."""
        return {
            "id": "conv-12345678",
        }

    @pytest.mark.asyncio
    async def test_returns_error_when_no_vaga_id(self, medico_mock, conversa_mock):
        """Retorna erro quando vaga_id nao informado."""
        result = await handle_criar_handoff_externo(
            tool_input={},
            medico=medico_mock,
            conversa=conversa_mock,
        )

        assert result["success"] is False
        assert "vaga" in result["error"].lower()
        assert "mensagem_sugerida" in result

    @pytest.mark.asyncio
    async def test_returns_error_when_medico_without_id(self, conversa_mock):
        """Retorna erro quando medico sem ID."""
        result = await handle_criar_handoff_externo(
            tool_input={"vaga_id": "vaga-123", "motivo": "teste"},
            medico={},
            conversa=conversa_mock,
        )

        assert result["success"] is False
        assert "medico" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_returns_existing_handoff_when_duplicate(self, medico_mock, conversa_mock):
        """Retorna handoff existente ao tentar criar duplicado."""
        handoff_existente = {
            "id": "handoff-123",
            "status": "contacted",
            "divulgador_nome": "João",
        }

        with patch(
            "app.tools.intermediacao.buscar_handoff_existente",
            new_callable=AsyncMock,
            return_value=handoff_existente,
        ):
            result = await handle_criar_handoff_externo(
                tool_input={"vaga_id": "vaga-123", "motivo": "teste"},
                medico=medico_mock,
                conversa=conversa_mock,
            )

        assert result["success"] is True
        assert result["handoff_existente"] is True
        assert result["status"] == "contacted"

    @pytest.mark.asyncio
    async def test_returns_error_when_vaga_not_found(self, medico_mock, conversa_mock):
        """Retorna erro quando vaga nao encontrada."""
        with patch(
            "app.tools.intermediacao.buscar_handoff_existente",
            new_callable=AsyncMock,
            return_value=None,
        ):
            mock_supabase = MagicMock()
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

            with patch("app.tools.intermediacao.supabase", mock_supabase):
                result = await handle_criar_handoff_externo(
                    tool_input={"vaga_id": "vaga-inexistente", "motivo": "teste"},
                    medico=medico_mock,
                    conversa=conversa_mock,
                )

        assert result["success"] is False
        assert "nao encontrada" in result["error"].lower() or "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_handles_internal_vaga(self, medico_mock, conversa_mock):
        """Trata vaga interna (sem divulgador externo)."""
        vaga_interna = {
            "id": "vaga-123",
            "source": "interno",
            "source_id": None,
            "hospitais": {"nome": "Hospital ABC"},
        }

        with patch(
            "app.tools.intermediacao.buscar_handoff_existente",
            new_callable=AsyncMock,
            return_value=None,
        ):
            mock_supabase = MagicMock()
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[vaga_interna])

            with patch("app.tools.intermediacao.supabase", mock_supabase):
                result = await handle_criar_handoff_externo(
                    tool_input={"vaga_id": "vaga-123", "motivo": "teste"},
                    medico=medico_mock,
                    conversa=conversa_mock,
                )

        assert result["success"] is True
        assert result["tipo"] == "vaga_interna"
        assert "Hospital ABC" in result["mensagem_sugerida"]

    @pytest.mark.asyncio
    async def test_creates_external_bridge_successfully(self, medico_mock, conversa_mock):
        """Cria ponte externa com sucesso."""
        vaga_grupo = {
            "id": "vaga-123",
            "source": "grupo",
            "source_id": "grupo-abc",
            "hospitais": {"nome": "Hospital XYZ"},
        }

        ponte_resultado = {
            "success": True,
            "handoff_id": "handoff-456",
            "divulgador": {
                "nome": "Carlos",
                "telefone": "11988887777",
                "empresa": "MedStaff",
            },
            "msg_medico_enviada": True,
            "msg_divulgador_enviada": True,
        }

        with patch(
            "app.tools.intermediacao.buscar_handoff_existente",
            new_callable=AsyncMock,
            return_value=None,
        ):
            mock_supabase = MagicMock()
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[vaga_grupo])

            with patch("app.tools.intermediacao.supabase", mock_supabase):
                with patch(
                    "app.tools.intermediacao.criar_ponte_externa",
                    new_callable=AsyncMock,
                    return_value=ponte_resultado,
                ):
                    with patch(
                        "app.tools.intermediacao.emit_event",
                        new_callable=AsyncMock,
                    ):
                        result = await handle_criar_handoff_externo(
                            tool_input={"vaga_id": "vaga-123", "motivo": "interesse"},
                            medico=medico_mock,
                            conversa=conversa_mock,
                        )

        assert result["success"] is True
        assert result["handoff_id"] == "handoff-456"
        assert result["divulgador"]["nome"] == "Carlos"
        assert "Carlos" in result["mensagem_sugerida"]


class TestHandleRegistrarStatusIntermediacao:
    """Testes do handler registrar_status_intermediacao."""

    @pytest.fixture
    def medico_mock(self):
        """Mock do medico."""
        return {
            "id": "12345678-1234-1234-1234-123456789012",
            "nome": "Dr. Teste",
        }

    @pytest.fixture
    def conversa_mock(self):
        """Mock da conversa."""
        return {"id": "conv-123"}

    @pytest.mark.asyncio
    async def test_returns_error_when_no_vaga_id(self, medico_mock, conversa_mock):
        """Retorna erro quando vaga_id nao informado."""
        result = await handle_registrar_status_intermediacao(
            tool_input={"status": "fechado"},
            medico=medico_mock,
            conversa=conversa_mock,
        )

        assert result["success"] is False
        assert "vaga" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_returns_error_when_no_status(self, medico_mock, conversa_mock):
        """Retorna erro quando status nao informado."""
        result = await handle_registrar_status_intermediacao(
            tool_input={"vaga_id": "vaga-123"},
            medico=medico_mock,
            conversa=conversa_mock,
        )

        assert result["success"] is False
        assert "status" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_returns_error_when_medico_without_id(self, conversa_mock):
        """Retorna erro quando medico sem ID."""
        result = await handle_registrar_status_intermediacao(
            tool_input={"vaga_id": "vaga-123", "status": "fechado"},
            medico={},
            conversa=conversa_mock,
        )

        assert result["success"] is False
        assert "medico" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_returns_error_when_handoff_not_found(self, medico_mock, conversa_mock):
        """Retorna erro quando handoff nao encontrado."""
        with patch(
            "app.tools.intermediacao.buscar_handoff_existente",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await handle_registrar_status_intermediacao(
                tool_input={"vaga_id": "vaga-123", "status": "fechado"},
                medico=medico_mock,
                conversa=conversa_mock,
            )

        assert result["success"] is False
        assert "nao encontr" in result["error"].lower() or "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_updates_to_confirmed_successfully(self, medico_mock, conversa_mock):
        """Atualiza status para confirmado com sucesso."""
        handoff = {
            "id": "handoff-123",
            "status": "contacted",
        }

        with patch(
            "app.tools.intermediacao.buscar_handoff_existente",
            new_callable=AsyncMock,
            return_value=handoff,
        ):
            with patch(
                "app.tools.intermediacao.atualizar_status_handoff",
                new_callable=AsyncMock,
                return_value=True,
            ):
                with patch(
                    "app.tools.intermediacao.emit_event",
                    new_callable=AsyncMock,
                ):
                    result = await handle_registrar_status_intermediacao(
                        tool_input={"vaga_id": "vaga-123", "status": "fechado"},
                        medico=medico_mock,
                        conversa=conversa_mock,
                    )

        assert result["success"] is True
        assert result["status_novo"] == "confirmed"
        assert "deu certo" in result["mensagem_sugerida"].lower()

    @pytest.mark.asyncio
    async def test_updates_to_no_response(self, medico_mock, conversa_mock):
        """Atualiza status para sem resposta."""
        handoff = {
            "id": "handoff-123",
            "status": "contacted",
        }

        with patch(
            "app.tools.intermediacao.buscar_handoff_existente",
            new_callable=AsyncMock,
            return_value=handoff,
        ):
            with patch(
                "app.tools.intermediacao.atualizar_status_handoff",
                new_callable=AsyncMock,
                return_value=True,
            ):
                result = await handle_registrar_status_intermediacao(
                    tool_input={"vaga_id": "vaga-123", "status": "sem_resposta"},
                    medico=medico_mock,
                    conversa=conversa_mock,
                )

        assert result["success"] is True
        assert result["status_novo"] == "no_response"
        assert "cobrar" in result["mensagem_sugerida"].lower()

    @pytest.mark.asyncio
    async def test_updates_to_cancelled(self, medico_mock, conversa_mock):
        """Atualiza status para cancelado/desistiu."""
        handoff = {
            "id": "handoff-123",
            "status": "pending",
        }

        with patch(
            "app.tools.intermediacao.buscar_handoff_existente",
            new_callable=AsyncMock,
            return_value=handoff,
        ):
            with patch(
                "app.tools.intermediacao.atualizar_status_handoff",
                new_callable=AsyncMock,
                return_value=True,
            ):
                result = await handle_registrar_status_intermediacao(
                    tool_input={"vaga_id": "vaga-123", "status": "desistiu"},
                    medico=medico_mock,
                    conversa=conversa_mock,
                )

        assert result["success"] is True
        assert result["status_novo"] == "cancelled"

    @pytest.mark.asyncio
    async def test_blocks_update_when_already_confirmed(self, medico_mock, conversa_mock):
        """Bloqueia atualizacao quando ja confirmado."""
        handoff = {
            "id": "handoff-123",
            "status": "confirmed",
        }

        with patch(
            "app.tools.intermediacao.buscar_handoff_existente",
            new_callable=AsyncMock,
            return_value=handoff,
        ):
            result = await handle_registrar_status_intermediacao(
                tool_input={"vaga_id": "vaga-123", "status": "fechado"},
                medico=medico_mock,
                conversa=conversa_mock,
            )

        assert result["success"] is False
        assert "ja confirmada" in result["error"].lower()


class TestToolsInJulia:
    """Testes de integracao com JULIA_TOOLS."""

    def test_tools_available_in_julia(self):
        """Tools de intermediacao estao disponiveis em JULIA_TOOLS."""
        from app.services.agente import JULIA_TOOLS

        tool_names = [t["name"] for t in JULIA_TOOLS]
        assert "criar_handoff_externo" in tool_names
        assert "registrar_status_intermediacao" in tool_names

    def test_tools_have_correct_structure(self):
        """Tools tem estrutura correta para o agente."""
        from app.services.agente import JULIA_TOOLS

        for tool in JULIA_TOOLS:
            if tool["name"] in ["criar_handoff_externo", "registrar_status_intermediacao"]:
                assert "name" in tool
                assert "description" in tool
                assert "input_schema" in tool
                assert "type" in tool["input_schema"]
                assert tool["input_schema"]["type"] == "object"


class TestIntegrationWithCapabilities:
    """Testes de integracao com Capabilities Gate."""

    def test_oferta_mode_allows_criar_handoff(self):
        """Modo OFERTA permite criar_handoff_externo."""
        from app.services.conversation_mode import CapabilitiesGate, ConversationMode

        gate = CapabilitiesGate(ConversationMode.OFERTA)
        assert gate.is_tool_allowed("criar_handoff_externo") is True

    def test_discovery_mode_blocks_criar_handoff(self):
        """Modo DISCOVERY bloqueia criar_handoff_externo."""
        from app.services.conversation_mode import CapabilitiesGate, ConversationMode

        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        assert gate.is_tool_allowed("criar_handoff_externo") is False

    def test_followup_mode_allows_registrar_status(self):
        """Modo FOLLOWUP permite registrar_status_intermediacao."""
        from app.services.conversation_mode import CapabilitiesGate, ConversationMode

        gate = CapabilitiesGate(ConversationMode.FOLLOWUP)
        assert gate.is_tool_allowed("registrar_status_intermediacao") is True

    def test_reativacao_mode_blocks_criar_handoff(self):
        """Modo REATIVACAO bloqueia criar_handoff_externo."""
        from app.services.conversation_mode import CapabilitiesGate, ConversationMode

        gate = CapabilitiesGate(ConversationMode.REATIVACAO)
        assert gate.is_tool_allowed("criar_handoff_externo") is False
