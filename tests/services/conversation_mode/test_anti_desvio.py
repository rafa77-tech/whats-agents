"""
Testes BLOQUEADORES para garantir que Julia é INTERMEDIÁRIA.

Sprint 29 - Conversation Mode

Estes testes DEVEM PASSAR para deploy. Eles protegem contra:
1. LLM tentando reservar plantões
2. LLM tentando negociar valores
3. LLM confirmando reservas sem autoridade

GUARDRAIL CRÍTICO: Julia é INTERMEDIÁRIA
- Não negocia valores
- Não confirma reservas
- Conecta médico com responsável da vaga
"""
import pytest
import re
from app.services.conversation_mode.types import ConversationMode
from app.services.conversation_mode.capabilities import (
    CapabilitiesGate,
    GLOBAL_FORBIDDEN_TOOLS,
    GLOBAL_FORBIDDEN_CLAIMS,
)


class TestAntiNegociacao:
    """Testes que garantem que Julia NUNCA negocia."""

    def test_reservar_plantao_bloqueado_em_todos_modos(self):
        """reservar_plantao DEVE estar bloqueada em TODOS os modos."""
        for mode in ConversationMode:
            gate = CapabilitiesGate(mode)
            assert gate.is_tool_allowed("reservar_plantao") is False, (
                f"CRÍTICO: reservar_plantao permitida em {mode.value}!"
            )

    def test_calcular_valor_bloqueado_em_todos_modos(self):
        """calcular_valor DEVE estar bloqueada em TODOS os modos."""
        for mode in ConversationMode:
            gate = CapabilitiesGate(mode)
            assert gate.is_tool_allowed("calcular_valor") is False, (
                f"CRÍTICO: calcular_valor permitida em {mode.value}!"
            )

    def test_global_forbidden_tools_existem(self):
        """Deve existir lista de tools globalmente proibidas."""
        assert "reservar_plantao" in GLOBAL_FORBIDDEN_TOOLS
        assert "calcular_valor" in GLOBAL_FORBIDDEN_TOOLS

    def test_filter_remove_tools_globais_proibidas(self):
        """filter_tools DEVE remover tools globalmente proibidas."""
        tools = [
            {"name": "reservar_plantao"},
            {"name": "calcular_valor"},
            {"name": "buscar_vagas"},
            {"name": "salvar_memoria"},
        ]
        # Mesmo em OFERTA (que seria o mais permissivo)
        gate = CapabilitiesGate(ConversationMode.OFERTA)
        filtered = gate.filter_tools(tools)
        names = [t["name"] for t in filtered]

        assert "reservar_plantao" not in names, "CRÍTICO: reservar_plantao não foi removida!"
        assert "calcular_valor" not in names, "CRÍTICO: calcular_valor não foi removida!"


class TestAntiConfirmacao:
    """Testes que garantem que Julia NUNCA confirma reservas."""

    def test_forbidden_claims_negociacao_em_todos_modos(self):
        """Claims de negociação devem ser proibidos em TODOS os modos."""
        for mode in ConversationMode:
            gate = CapabilitiesGate(mode)
            claims = gate.get_forbidden_claims()

            assert "confirm_booking" in claims, (
                f"CRÍTICO: confirm_booking não proibido em {mode.value}!"
            )
            assert "negotiate_terms" in claims, (
                f"CRÍTICO: negotiate_terms não proibido em {mode.value}!"
            )

    def test_constraints_text_inclui_guardrail_intermediaria(self):
        """Constraints text DEVE incluir guardrail de intermediária."""
        for mode in ConversationMode:
            gate = CapabilitiesGate(mode)
            text = gate.get_constraints_text()

            assert "INTERMEDIÁRIA" in text.upper(), (
                f"CRÍTICO: Guardrail de intermediária não está no prompt do modo {mode.value}!"
            )
            assert "NUNCA" in text, (
                f"CRÍTICO: Proibições não estão claras no prompt do modo {mode.value}!"
            )

    def test_global_forbidden_claims_existem(self):
        """Deve existir lista de claims globalmente proibidos."""
        assert "negotiate_price" in GLOBAL_FORBIDDEN_CLAIMS
        assert "confirm_booking" in GLOBAL_FORBIDDEN_CLAIMS
        assert "negotiate_terms" in GLOBAL_FORBIDDEN_CLAIMS
        assert "confirm_booking_directly" in GLOBAL_FORBIDDEN_CLAIMS


class TestAntiDesvioPadroesResposta:
    """Testes que detectam padrões de desvio na resposta (para validador)."""

    # Padrões que NUNCA devem aparecer nas respostas da Julia
    PADROES_PROIBIDOS = [
        r"(?i)reserv(ei|ado|a) (pra|para) voc[êe]",  # "Reservei pra você"
        r"(?i)confirm(ado|ei|o) (seu|o) plant[aã]o",  # "Confirmado seu plantão"
        r"(?i)paga\s+R?\$?\s*\d+",  # "Paga R$ 2.500"
        r"(?i)consigo\s+R?\$?\s*\d+",  # "Consigo R$ 2.500"
        r"(?i)valor\s+(é|de|seria)\s+R?\$?\s*\d+",  # "Valor é R$ 2.500"
        r"(?i)d[aá]\s+pra\s+(sub|melhora)ir",  # "Dá pra subir"
        r"(?i)consigo\s+melhorar",  # "Consigo melhorar"
        r"(?i)t[aá]\s+(fechado|confirm)",  # "Tá fechado"
        r"(?i)seu\s+plant[aã]o\s+(j[aá]|foi)\s+",  # "Seu plantão já foi..."
    ]

    def test_padroes_proibidos_regex_validos(self):
        """Verifica que os padrões regex são válidos."""
        for padrao in self.PADROES_PROIBIDOS:
            # Apenas verifica que compila sem erro
            re.compile(padrao)

    @pytest.mark.parametrize("resposta_proibida", [
        "Show! Reservei pra você, tá confirmado!",
        "Fechado! Confirmado seu plantão no São Luiz.",
        "O valor é R$ 2.500 por 12h.",
        "Consigo R$ 2.800 se vc confirmar agora.",
        "Dá pra subir o valor se precisar.",
        "Consigo melhorar as condições pra você.",
        "Tá fechado então! Te espero lá.",
        "Confirmado o plantão de cardio.",
        "Paga R$ 2500 por noite.",
    ])
    def test_detecta_resposta_proibida(self, resposta_proibida):
        """Cada resposta proibida DEVE ser detectada."""
        encontrou = False
        for padrao in self.PADROES_PROIBIDOS:
            if re.search(padrao, resposta_proibida):
                encontrou = True
                break
        assert encontrou, f"Padrão proibido não detectado: {resposta_proibida}"

    @pytest.mark.parametrize("resposta_permitida", [
        "Show! Quer que eu te coloque em contato com o responsável?",
        "Tenho uma vaga boa aqui. Posso passar seu contato pra quem tá oferecendo?",
        "Vou te conectar com o Dr. Paulo que tá com essa vaga.",
        "Passei seu contato pro responsável, ele vai te chamar.",
        "O valor você negocia direto com quem tá oferecendo.",
        "O responsável pela vaga vai te passar os detalhes.",
        "Deixa eu te colocar em contato com quem pode confirmar.",
    ])
    def test_nao_detecta_resposta_permitida(self, resposta_permitida):
        """Respostas permitidas NÃO devem disparar os padrões."""
        for padrao in self.PADROES_PROIBIDOS:
            assert not re.search(padrao, resposta_permitida), (
                f"Falso positivo: '{resposta_permitida}' casou com '{padrao}'"
            )


class TestAntiDesvioOferta:
    """Testes específicos para modo OFERTA (mais permissivo)."""

    def test_oferta_ainda_proibe_confirmar(self):
        """Mesmo em OFERTA, Julia não pode confirmar reservas."""
        gate = CapabilitiesGate(ConversationMode.OFERTA)
        claims = gate.get_forbidden_claims()

        assert "confirm_booking" in claims
        assert "quote_price" in claims
        assert "negotiate_terms" in claims

    def test_oferta_behavior_menciona_intermediaria(self):
        """Behavior de OFERTA deve mencionar papel de intermediária."""
        gate = CapabilitiesGate(ConversationMode.OFERTA)
        behavior = gate.get_required_behavior()

        assert "INTERMEDIAÇÃO" in behavior.upper() or "responsável" in behavior.lower()
        assert "NÃO negocia" in behavior or "não negocie" in behavior.lower()


class TestAntiDesvioDiscovery:
    """Testes específicos para modo DISCOVERY."""

    def test_discovery_bloqueia_buscar_vagas(self):
        """Em DISCOVERY, Julia não busca vagas ainda."""
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)

        assert gate.is_tool_allowed("buscar_vagas") is False
        assert "buscar_vagas" in gate.get_forbidden_tools()

    def test_discovery_bloqueia_oferta_especifica(self):
        """Em DISCOVERY, Julia não oferece plantão específico."""
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        claims = gate.get_forbidden_claims()

        assert "offer_specific_shift" in claims


class TestMatrizTransicoesSegura:
    """Testes que garantem que a matriz de transições é segura."""

    def test_discovery_nao_pode_ir_direto_para_followup(self):
        """DISCOVERY não pode pular para FOLLOWUP sem passar por OFERTA."""
        from app.services.conversation_mode.proposer import ALLOWED_TRANSITIONS

        allowed = ALLOWED_TRANSITIONS[ConversationMode.DISCOVERY]
        assert ConversationMode.FOLLOWUP not in allowed

    def test_transicao_para_oferta_requer_confirmacao(self):
        """Transição para OFERTA requer micro-confirmação."""
        from app.services.conversation_mode.proposer import CONFIRMATION_REQUIRED

        # De DISCOVERY para OFERTA
        assert (ConversationMode.DISCOVERY, ConversationMode.OFERTA) in CONFIRMATION_REQUIRED

        # De FOLLOWUP para OFERTA
        assert (ConversationMode.FOLLOWUP, ConversationMode.OFERTA) in CONFIRMATION_REQUIRED
