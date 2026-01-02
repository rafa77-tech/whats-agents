"""
Testes para Capabilities Gate (3 camadas).

Sprint 29 - Conversation Mode
"""
import pytest
from app.services.conversation_mode.types import ConversationMode
from app.services.conversation_mode.capabilities import (
    CapabilitiesGate,
    CAPABILITIES_BY_MODE,
    GLOBAL_FORBIDDEN_TOOLS,
    GLOBAL_FORBIDDEN_CLAIMS,
)


class TestGlobalForbiddenTools:
    """Testes para tools globalmente proibidas."""

    def test_reservar_plantao_is_globally_forbidden(self):
        """reservar_plantao DEVE estar na lista global."""
        assert "reservar_plantao" in GLOBAL_FORBIDDEN_TOOLS

    def test_calcular_valor_is_globally_forbidden(self):
        """calcular_valor DEVE estar na lista global."""
        assert "calcular_valor" in GLOBAL_FORBIDDEN_TOOLS


class TestGlobalForbiddenClaims:
    """Testes para claims globalmente proibidos."""

    def test_negotiate_terms_is_globally_forbidden(self):
        """negotiate_terms DEVE estar na lista global."""
        assert "negotiate_terms" in GLOBAL_FORBIDDEN_CLAIMS

    def test_confirm_booking_is_globally_forbidden(self):
        """confirm_booking DEVE estar na lista global."""
        assert "confirm_booking" in GLOBAL_FORBIDDEN_CLAIMS


class TestCapabilitiesGateToolsLayer:
    """Testes da CAMADA 1: Tools."""

    def test_reservar_plantao_blocked_in_all_modes(self):
        """reservar_plantao DEVE estar bloqueada em TODOS os modos."""
        for mode in ConversationMode:
            gate = CapabilitiesGate(mode)
            assert gate.is_tool_allowed("reservar_plantao") is False, (
                f"CRÍTICO: reservar_plantao permitida em {mode.value}!"
            )

    def test_calcular_valor_blocked_in_all_modes(self):
        """calcular_valor DEVE estar bloqueada em TODOS os modos."""
        for mode in ConversationMode:
            gate = CapabilitiesGate(mode)
            assert gate.is_tool_allowed("calcular_valor") is False, (
                f"CRÍTICO: calcular_valor permitida em {mode.value}!"
            )

    def test_discovery_blocks_buscar_vagas(self):
        """Discovery bloqueia buscar_vagas."""
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        assert gate.is_tool_allowed("buscar_vagas") is False
        assert "buscar_vagas" in gate.get_forbidden_tools()

    def test_discovery_allows_salvar_memoria(self):
        """Discovery permite salvar_memoria."""
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        assert gate.is_tool_allowed("salvar_memoria") is True

    def test_oferta_allows_buscar_vagas(self):
        """Oferta permite buscar_vagas."""
        gate = CapabilitiesGate(ConversationMode.OFERTA)
        assert gate.is_tool_allowed("buscar_vagas") is True

    def test_oferta_allows_criar_handoff_externo(self):
        """Oferta permite criar_handoff_externo."""
        gate = CapabilitiesGate(ConversationMode.OFERTA)
        assert gate.is_tool_allowed("criar_handoff_externo") is True

    def test_reativacao_blocks_criar_handoff_externo(self):
        """Reativacao bloqueia criar_handoff_externo."""
        gate = CapabilitiesGate(ConversationMode.REATIVACAO)
        assert gate.is_tool_allowed("criar_handoff_externo") is False

    def test_filter_tools_removes_forbidden(self):
        """filter_tools remove tools proibidas."""
        tools = [
            {"name": "buscar_vagas"},
            {"name": "salvar_memoria"},
            {"name": "reservar_plantao"},
            {"name": "calcular_valor"},
        ]
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        filtered = gate.filter_tools(tools)

        names = [t["name"] for t in filtered]
        assert "buscar_vagas" not in names
        assert "reservar_plantao" not in names
        assert "calcular_valor" not in names
        assert "salvar_memoria" in names

    def test_filter_tools_removes_global_forbidden_even_in_oferta(self):
        """filter_tools remove globais mesmo em OFERTA."""
        tools = [
            {"name": "buscar_vagas"},
            {"name": "reservar_plantao"},
            {"name": "calcular_valor"},
        ]
        gate = CapabilitiesGate(ConversationMode.OFERTA)
        filtered = gate.filter_tools(tools)

        names = [t["name"] for t in filtered]
        assert "buscar_vagas" in names
        assert "reservar_plantao" not in names
        assert "calcular_valor" not in names


class TestCapabilitiesGateClaimsLayer:
    """Testes da CAMADA 2: Claims."""

    def test_discovery_has_forbidden_claims(self):
        """Discovery tem claims proibidos."""
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        claims = gate.get_forbidden_claims()
        assert "offer_specific_shift" in claims
        assert "quote_price" in claims

    def test_oferta_has_forbidden_claims_even_for_intermediation(self):
        """Oferta tem claims proibidos (intermediação)."""
        gate = CapabilitiesGate(ConversationMode.OFERTA)
        claims = gate.get_forbidden_claims()
        assert "confirm_booking" in claims
        assert "negotiate_terms" in claims
        assert "quote_price" in claims

    def test_followup_blocks_pressure_claims(self):
        """Followup bloqueia claims de pressão."""
        gate = CapabilitiesGate(ConversationMode.FOLLOWUP)
        claims = gate.get_forbidden_claims()
        assert "pressure_decision" in claims
        assert "create_urgency" in claims

    def test_reativacao_blocks_pressure_return(self):
        """Reativacao bloqueia pressure_return."""
        gate = CapabilitiesGate(ConversationMode.REATIVACAO)
        claims = gate.get_forbidden_claims()
        assert "pressure_return" in claims

    def test_global_claims_included_in_all_modes(self):
        """Claims globais incluídos em todos os modos."""
        for mode in ConversationMode:
            gate = CapabilitiesGate(mode)
            claims = gate.get_forbidden_claims()
            # Pelo menos um claim global deve estar presente
            global_in_claims = any(c in claims for c in GLOBAL_FORBIDDEN_CLAIMS)
            assert global_in_claims, f"Claims globais não incluídos em {mode.value}"


class TestCapabilitiesGateBehaviorLayer:
    """Testes da CAMADA 3: Behavior."""

    def test_discovery_has_required_behavior(self):
        """Discovery tem comportamento requerido."""
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        behavior = gate.get_required_behavior()
        assert "DISCOVERY" in behavior
        assert "qualificação" in behavior.lower() or "conheça" in behavior.lower()

    def test_oferta_has_intermediation_behavior(self):
        """Oferta tem comportamento de intermediação."""
        gate = CapabilitiesGate(ConversationMode.OFERTA)
        behavior = gate.get_required_behavior()
        assert "INTERMEDIAÇÃO" in behavior.upper() or "responsável" in behavior.lower()
        assert "NÃO negocia" in behavior or "não negocie" in behavior.lower()

    def test_followup_has_required_behavior(self):
        """Followup tem comportamento requerido."""
        gate = CapabilitiesGate(ConversationMode.FOLLOWUP)
        behavior = gate.get_required_behavior()
        assert "FOLLOWUP" in behavior
        assert "responsável" in behavior.lower() or "desfecho" in behavior.lower()

    def test_reativacao_has_required_behavior(self):
        """Reativacao tem comportamento requerido."""
        gate = CapabilitiesGate(ConversationMode.REATIVACAO)
        behavior = gate.get_required_behavior()
        assert "REATIVAÇÃO" in behavior.upper() or "gentil" in behavior.lower()


class TestCapabilitiesGateConstraintsText:
    """Testes do texto de constraints para prompt."""

    def test_constraints_text_includes_guardrail(self):
        """Constraints text inclui guardrail de intermediária."""
        gate = CapabilitiesGate(ConversationMode.OFERTA)
        text = gate.get_constraints_text()
        assert "INTERMEDIÁRIA" in text.upper()
        assert "NUNCA" in text

    def test_constraints_text_includes_mode(self):
        """Constraints text inclui modo atual."""
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        text = gate.get_constraints_text()
        assert "DISCOVERY" in text.upper()

    def test_constraints_text_includes_forbidden_claims(self):
        """Constraints text inclui claims proibidos."""
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        text = gate.get_constraints_text()
        assert "NÃO PODE" in text

    def test_constraints_text_includes_tools(self):
        """Constraints text inclui tools bloqueadas."""
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        text = gate.get_constraints_text()
        assert "bloqueadas" in text.lower() or "Tools" in text


class TestCapabilitiesConfiguration:
    """Testes de configuração."""

    def test_all_modes_have_config(self):
        """Todos os modos têm configuração."""
        for mode in ConversationMode:
            assert mode in CAPABILITIES_BY_MODE, f"Modo {mode} sem config"

    def test_all_modes_have_required_fields(self):
        """Todos os modos têm campos obrigatórios."""
        required_fields = ["allowed_tools", "forbidden_tools", "forbidden_claims", "required_behavior", "tone"]
        for mode in ConversationMode:
            config = CAPABILITIES_BY_MODE[mode]
            for field in required_fields:
                assert field in config, f"Modo {mode} sem campo {field}"

    def test_get_tone_returns_valid_tone(self):
        """get_tone retorna tom válido."""
        valid_tones = ["leve", "objetiva", "cauteloso", "direto"]
        for mode in ConversationMode:
            gate = CapabilitiesGate(mode)
            tone = gate.get_tone()
            assert tone in valid_tones, f"Tom inválido '{tone}' para modo {mode}"
