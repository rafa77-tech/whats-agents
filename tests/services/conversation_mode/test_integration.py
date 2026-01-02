"""
Testes de integração do Conversation Mode.

Sprint 29 - Verifica que:
1. Tools são filtradas por modo
2. Constraints são injetados no prompt
3. Micro-confirmação funciona
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.conversation_mode import (
    ConversationMode,
    ModeInfo,
    CapabilitiesGate,
    get_micro_confirmation_prompt,
    GLOBAL_FORBIDDEN_TOOLS,
)
from app.services.agente import JULIA_TOOLS


class TestToolsFiltering:
    """Testes de filtro de tools por modo."""

    def test_julia_tools_defined(self):
        """JULIA_TOOLS tem tools definidas."""
        assert len(JULIA_TOOLS) > 0
        tool_names = [t.get("name") for t in JULIA_TOOLS]
        assert "buscar_vagas" in tool_names
        assert "salvar_memoria" in tool_names

    def test_discovery_mode_blocks_buscar_vagas(self):
        """Modo DISCOVERY bloqueia buscar_vagas."""
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        filtered = gate.filter_tools(JULIA_TOOLS)
        tool_names = [t.get("name") for t in filtered]

        assert "buscar_vagas" not in tool_names
        assert "salvar_memoria" in tool_names

    def test_oferta_mode_allows_buscar_vagas(self):
        """Modo OFERTA permite buscar_vagas."""
        gate = CapabilitiesGate(ConversationMode.OFERTA)
        filtered = gate.filter_tools(JULIA_TOOLS)
        tool_names = [t.get("name") for t in filtered]

        assert "buscar_vagas" in tool_names

    def test_reservar_plantao_blocked_globally(self):
        """reservar_plantao bloqueada em TODOS os modos."""
        for mode in ConversationMode:
            gate = CapabilitiesGate(mode)
            filtered = gate.filter_tools(JULIA_TOOLS)
            tool_names = [t.get("name") for t in filtered]

            assert "reservar_plantao" not in tool_names, (
                f"reservar_plantao deveria estar bloqueada em {mode.value}"
            )

    def test_global_forbidden_tools_blocked_everywhere(self):
        """Tools globalmente proibidas bloqueadas em todos os modos."""
        for mode in ConversationMode:
            gate = CapabilitiesGate(mode)
            for forbidden_tool in GLOBAL_FORBIDDEN_TOOLS:
                assert gate.is_tool_allowed(forbidden_tool) is False, (
                    f"Tool {forbidden_tool} deveria estar bloqueada em {mode.value}"
                )


class TestConstraintsInjection:
    """Testes de injeção de constraints no prompt."""

    def test_discovery_constraints_include_guardrail(self):
        """Constraints de DISCOVERY incluem guardrail de intermediária."""
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        text = gate.get_constraints_text()

        assert "INTERMEDIÁRIA" in text
        assert "NUNCA" in text
        assert "DISCOVERY" in text

    def test_oferta_constraints_include_no_negotiate(self):
        """Constraints de OFERTA incluem proibição de negociar."""
        gate = CapabilitiesGate(ConversationMode.OFERTA)
        text = gate.get_constraints_text()

        assert "INTERMEDIÁRIA" in text
        assert "negocia" in text.lower() or "negociar" in text.lower()

    def test_constraints_include_forbidden_claims(self):
        """Constraints incluem claims proibidos."""
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        text = gate.get_constraints_text()

        # Deve ter seção de proibições
        assert "NÃO PODE" in text

    def test_constraints_include_behavior(self):
        """Constraints incluem comportamento requerido."""
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        text = gate.get_constraints_text()

        # Deve ter descrição do comportamento esperado
        behavior = gate.get_required_behavior()
        assert len(behavior) > 0


class TestMicroConfirmation:
    """Testes de micro-confirmação."""

    def test_discovery_to_oferta_has_prompt(self):
        """Transição discovery → oferta tem prompt de confirmação."""
        prompt = get_micro_confirmation_prompt(
            ConversationMode.DISCOVERY,
            ConversationMode.OFERTA,
        )

        assert len(prompt) > 0
        assert "MICRO-CONFIRMAÇÃO" in prompt
        assert "qualificação" in prompt.lower()

    def test_followup_to_oferta_has_prompt(self):
        """Transição followup → oferta tem prompt de confirmação."""
        prompt = get_micro_confirmation_prompt(
            ConversationMode.FOLLOWUP,
            ConversationMode.OFERTA,
        )

        assert len(prompt) > 0
        assert "MICRO-CONFIRMAÇÃO" in prompt

    def test_automatic_transitions_no_prompt(self):
        """Transições automáticas não têm prompt."""
        # oferta → followup é automático (ponte feita)
        prompt = get_micro_confirmation_prompt(
            ConversationMode.OFERTA,
            ConversationMode.FOLLOWUP,
        )

        assert prompt == ""

    def test_mode_info_has_pending(self):
        """ModeInfo.has_pending() funciona corretamente."""
        info_without = ModeInfo(
            conversa_id="test",
            mode=ConversationMode.DISCOVERY,
            pending_transition=None,
        )
        assert info_without.has_pending() is False

        info_with = ModeInfo(
            conversa_id="test",
            mode=ConversationMode.DISCOVERY,
            pending_transition=ConversationMode.OFERTA,
        )
        assert info_with.has_pending() is True


class TestIntermediationGuardrail:
    """Testes do guardrail de intermediação."""

    def test_all_modes_have_intermediation_guardrail(self):
        """Todos os modos têm guardrail de intermediária."""
        for mode in ConversationMode:
            gate = CapabilitiesGate(mode)
            text = gate.get_constraints_text()

            assert "INTERMEDIÁRIA" in text, (
                f"Modo {mode.value} não tem guardrail de intermediária"
            )

    def test_confirm_booking_claim_forbidden_globally(self):
        """confirm_booking proibido em todos os modos."""
        for mode in ConversationMode:
            gate = CapabilitiesGate(mode)
            claims = gate.get_forbidden_claims()

            assert "confirm_booking" in claims, (
                f"confirm_booking deveria ser proibido em {mode.value}"
            )

    def test_negotiate_terms_claim_forbidden_globally(self):
        """negotiate_terms proibido em todos os modos."""
        for mode in ConversationMode:
            gate = CapabilitiesGate(mode)
            claims = gate.get_forbidden_claims()

            assert "negotiate_terms" in claims, (
                f"negotiate_terms deveria ser proibido em {mode.value}"
            )


class TestAgentIntegration:
    """Testes de integração com o agente."""

    def test_gerar_resposta_julia_accepts_new_params(self):
        """gerar_resposta_julia aceita capabilities_gate e mode_info."""
        from app.services.agente import gerar_resposta_julia
        import inspect

        sig = inspect.signature(gerar_resposta_julia)
        param_names = list(sig.parameters.keys())

        assert "capabilities_gate" in param_names
        assert "mode_info" in param_names

    def test_capabilities_gate_param_is_optional(self):
        """capabilities_gate é parâmetro opcional."""
        from app.services.agente import gerar_resposta_julia
        import inspect

        sig = inspect.signature(gerar_resposta_julia)
        param = sig.parameters["capabilities_gate"]

        assert param.default is None

    def test_mode_info_param_is_optional(self):
        """mode_info é parâmetro opcional."""
        from app.services.agente import gerar_resposta_julia
        import inspect

        sig = inspect.signature(gerar_resposta_julia)
        param = sig.parameters["mode_info"]

        assert param.default is None


class TestToolsIntegrity:
    """Testes de integridade das tools."""

    def test_julia_tools_have_name_field(self):
        """Todas as tools têm campo 'name'."""
        for tool in JULIA_TOOLS:
            assert "name" in tool, f"Tool sem campo 'name': {tool}"

    def test_filter_tools_preserves_tool_structure(self):
        """filter_tools preserva estrutura da tool."""
        gate = CapabilitiesGate(ConversationMode.OFERTA)
        filtered = gate.filter_tools(JULIA_TOOLS)

        for tool in filtered:
            # Estrutura deve ser preservada
            assert "name" in tool
            # Outras propriedades também devem existir
            assert isinstance(tool, dict)
