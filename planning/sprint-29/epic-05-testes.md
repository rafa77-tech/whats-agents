# E05: Testes e Validação

**Status:** Pendente
**Estimativa:** 6h
**Dependencia:** E01, E02, E03, E04
**Responsavel:** Dev

---

## Objetivo

Garantir qualidade e cobertura de testes para todo o módulo Conversation Mode, incluindo:
- 3 camadas de proteção (tools, claims, behavior)
- Matriz de transições permitidas
- Micro-confirmação
- Detecção de intent

---

## Estrutura de Testes

```
tests/
└── services/
    └── conversation_mode/
        ├── __init__.py
        ├── test_types.py           # Tipos e enums
        ├── test_capabilities.py    # 3 camadas do Gate
        ├── test_intents.py         # Detecção de intent
        ├── test_proposer.py        # Proposta de transição
        ├── test_validator.py       # Validação + micro-confirmação
        ├── test_router.py          # Orquestração
        └── test_integration.py     # Testes E2E
```

---

## Testes Unitários

### `test_types.py`

```python
"""
Testes para types do Conversation Mode.
"""
import pytest
from datetime import datetime
from app.services.conversation_mode.types import (
    ConversationMode,
    ModeInfo,
    ModeTransition,
)


class TestConversationMode:
    """Testes do enum ConversationMode."""

    def test_all_modes_exist(self):
        """Verifica que todos os 4 modos existem."""
        assert ConversationMode.DISCOVERY.value == "discovery"
        assert ConversationMode.OFERTA.value == "oferta"
        assert ConversationMode.FOLLOWUP.value == "followup"
        assert ConversationMode.REATIVACAO.value == "reativacao"

    def test_mode_from_string(self):
        """Verifica conversão de string para enum."""
        assert ConversationMode("discovery") == ConversationMode.DISCOVERY
        assert ConversationMode("oferta") == ConversationMode.OFERTA


class TestModeInfo:
    """Testes do ModeInfo."""

    def test_from_row_basic(self):
        """Cria ModeInfo de row básica."""
        row = {
            "id": "conv-123",
            "conversation_mode": "discovery",
        }
        info = ModeInfo.from_row(row)
        assert info.conversa_id == "conv-123"
        assert info.mode == ConversationMode.DISCOVERY
        assert info.pending_transition is None

    def test_from_row_with_pending(self):
        """Cria ModeInfo com pending_transition."""
        row = {
            "id": "conv-123",
            "conversation_mode": "discovery",
            "pending_transition": "oferta",
            "pending_transition_at": datetime.utcnow(),
        }
        info = ModeInfo.from_row(row)
        assert info.pending_transition == ConversationMode.OFERTA
        assert info.pending_transition_at is not None

    def test_from_row_with_mode_source(self):
        """Cria ModeInfo com mode_source."""
        row = {
            "id": "conv-123",
            "conversation_mode": "oferta",
            "mode_source": "campaign:123",
        }
        info = ModeInfo.from_row(row)
        assert info.mode_source == "campaign:123"
```

### `test_capabilities.py` - 3 CAMADAS

```python
"""
Testes para Capabilities Gate (3 camadas).
"""
import pytest
from app.services.conversation_mode.types import ConversationMode
from app.services.conversation_mode.capabilities import (
    CapabilitiesGate,
    CAPABILITIES_BY_MODE,
)


class TestCapabilitiesGate:
    """Testes do CapabilitiesGate."""

    # === CAMADA 1: TOOLS ===

    def test_discovery_blocks_buscar_vagas(self):
        """Discovery bloqueia buscar_vagas (CAMADA 1)."""
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        assert gate.is_tool_allowed("buscar_vagas") is False
        assert "buscar_vagas" in gate.get_forbidden_tools()

    def test_discovery_blocks_reservar_plantao(self):
        """Discovery bloqueia reservar_plantao (CAMADA 1)."""
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        assert gate.is_tool_allowed("reservar_plantao") is False

    def test_discovery_allows_salvar_memoria(self):
        """Discovery permite salvar_memoria (CAMADA 1)."""
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        assert gate.is_tool_allowed("salvar_memoria") is True

    def test_oferta_allows_buscar_vagas(self):
        """Oferta permite buscar_vagas (CAMADA 1)."""
        gate = CapabilitiesGate(ConversationMode.OFERTA)
        assert gate.is_tool_allowed("buscar_vagas") is True

    def test_reativacao_blocks_reservar_plantao(self):
        """Reativacao bloqueia reservar_plantao (CAMADA 1)."""
        gate = CapabilitiesGate(ConversationMode.REATIVACAO)
        assert gate.is_tool_allowed("reservar_plantao") is False

    def test_filter_tools_removes_forbidden(self):
        """filter_tools remove tools proibidas (CAMADA 1)."""
        tools = [
            {"name": "buscar_vagas"},
            {"name": "salvar_memoria"},
            {"name": "reservar_plantao"},
        ]
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        filtered = gate.filter_tools(tools)

        names = [t["name"] for t in filtered]
        assert "buscar_vagas" not in names
        assert "reservar_plantao" not in names
        assert "salvar_memoria" in names

    # === CAMADA 2: FORBIDDEN CLAIMS ===

    def test_discovery_has_forbidden_claims(self):
        """Discovery tem claims proibidos (CAMADA 2)."""
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        claims = gate.get_forbidden_claims()
        assert "offer_specific_shift" in claims
        assert "quote_price" in claims
        assert "confirm_booking" in claims

    def test_oferta_allows_all_claims(self):
        """Oferta permite todos os claims (CAMADA 2)."""
        gate = CapabilitiesGate(ConversationMode.OFERTA)
        claims = gate.get_forbidden_claims()
        assert claims == []  # Nenhum claim proibido

    def test_reativacao_blocks_pressure_claims(self):
        """Reativacao bloqueia claims de pressão (CAMADA 2)."""
        gate = CapabilitiesGate(ConversationMode.REATIVACAO)
        claims = gate.get_forbidden_claims()
        assert "pressure_return" in claims
        assert "offer_specific_shift" in claims

    def test_followup_blocks_urgency_claims(self):
        """Followup bloqueia claims de urgência (CAMADA 2)."""
        gate = CapabilitiesGate(ConversationMode.FOLLOWUP)
        claims = gate.get_forbidden_claims()
        assert "pressure_decision" in claims
        assert "create_urgency" in claims

    # === CAMADA 3: REQUIRED BEHAVIOR ===

    def test_discovery_has_required_behavior(self):
        """Discovery tem comportamento requerido (CAMADA 3)."""
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        behavior = gate.get_required_behavior()
        assert "DISCOVERY" in behavior
        assert "conheça o médico" in behavior.lower() or "conhecer" in behavior.lower()

    def test_oferta_has_required_behavior(self):
        """Oferta tem comportamento requerido (CAMADA 3)."""
        gate = CapabilitiesGate(ConversationMode.OFERTA)
        behavior = gate.get_required_behavior()
        assert "OFERTA" in behavior
        assert "objetiva" in behavior.lower() or "opções" in behavior.lower()

    def test_reativacao_has_required_behavior(self):
        """Reativacao tem comportamento requerido (CAMADA 3)."""
        gate = CapabilitiesGate(ConversationMode.REATIVACAO)
        behavior = gate.get_required_behavior()
        assert "REATIVAÇÃO" in behavior.upper() or "gentil" in behavior.lower()

    # === CONSTRAINTS TEXT ===

    def test_get_constraints_text_includes_all_layers(self):
        """get_constraints_text inclui as 3 camadas."""
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        text = gate.get_constraints_text()

        # Deve incluir header do modo
        assert "DISCOVERY" in text.upper()

        # Deve incluir forbidden claims
        assert "NÃO PODE" in text or "proibid" in text.lower()

        # Deve incluir tools bloqueadas
        assert "buscar_vagas" in text or "Tools bloqueadas" in text

    def test_get_tone(self):
        """get_tone retorna tom correto."""
        assert CapabilitiesGate(ConversationMode.DISCOVERY).get_tone() == "leve"
        assert CapabilitiesGate(ConversationMode.OFERTA).get_tone() == "direto"
        assert CapabilitiesGate(ConversationMode.REATIVACAO).get_tone() == "cauteloso"

    # === CONFIGURAÇÃO ===

    def test_all_modes_have_full_config(self):
        """Todos os modos têm configuração completa."""
        for mode in ConversationMode:
            config = CAPABILITIES_BY_MODE.get(mode)
            assert config is not None, f"Modo {mode} sem config"
            assert "allowed_tools" in config
            assert "forbidden_tools" in config
            assert "forbidden_claims" in config
            assert "required_behavior" in config
            assert "tone" in config
```

### `test_intents.py` - DETECÇÃO DE INTENT

```python
"""
Testes para Intent Detector (AJUSTE 2).
"""
import pytest
from app.services.conversation_mode.intents import (
    IntentDetector,
    DetectedIntent,
)


class TestIntentDetector:
    """Testes do IntentDetector."""

    def setup_method(self):
        self.detector = IntentDetector()

    # === INTERESSE ===

    def test_detect_interesse_vaga(self):
        """Detecta interesse em vaga."""
        messages = [
            "Tem vaga de cardiologia?",
            "Quanto paga o plantão?",
            "Quero saber mais sobre as vagas",
            "Onde é o hospital?",
        ]
        for msg in messages:
            result = self.detector.detect(msg)
            assert result.intent == DetectedIntent.INTERESSE_VAGA, f"Falhou: {msg}"
            assert result.confidence >= 0.7

    # === PRONTO PARA FECHAR ===

    def test_detect_pronto_fechar(self):
        """Detecta intenção de fechar."""
        messages = [
            "Pode reservar pra mim",
            "Aceito esse plantão",
            "Quero esse, confirma",
        ]
        for msg in messages:
            result = self.detector.detect(msg)
            assert result.intent == DetectedIntent.PRONTO_FECHAR, f"Falhou: {msg}"

    # === DÚVIDA ===

    def test_detect_duvida(self):
        """Detecta dúvida sobre perfil."""
        messages = [
            "Como funciona isso?",
            "Quem é você?",
            "Que empresa é essa?",
            "É confiável?",
        ]
        for msg in messages:
            result = self.detector.detect(msg)
            assert result.intent == DetectedIntent.DUVIDA_PERFIL, f"Falhou: {msg}"

    # === OBJEÇÃO ===

    def test_detect_objecao(self):
        """Detecta objeção."""
        messages = [
            "Preciso pensar",
            "Agora não dá",
            "Muito longe pra mim",
            "Valor baixo demais",
        ]
        for msg in messages:
            result = self.detector.detect(msg)
            assert result.intent == DetectedIntent.OBJECAO, f"Falhou: {msg}"

    # === RECUSA ===

    def test_detect_recusa(self):
        """Detecta recusa."""
        messages = [
            "Não quero",
            "Não tenho interesse",
            "Para de mandar mensagem",
        ]
        for msg in messages:
            result = self.detector.detect(msg)
            assert result.intent == DetectedIntent.RECUSA, f"Falhou: {msg}"
            assert result.confidence >= 0.8  # Recusa tem alta confiança

    # === VOLTANDO ===

    def test_detect_voltando(self):
        """Detecta retorno após silêncio."""
        messages = [
            "Oi",
            "Voltei",
            "Desculpa a demora",
        ]
        for msg in messages:
            result = self.detector.detect(msg)
            assert result.intent == DetectedIntent.VOLTANDO, f"Falhou: {msg}"

    # === NEUTRO ===

    def test_detect_neutro(self):
        """Detecta mensagem neutra."""
        messages = [
            "Ok",
            "Entendi",
            "Obrigado",
        ]
        for msg in messages:
            result = self.detector.detect(msg)
            assert result.intent == DetectedIntent.NEUTRO, f"Falhou: {msg}"

    def test_empty_message_is_neutro(self):
        """Mensagem vazia é neutra."""
        result = self.detector.detect("")
        assert result.intent == DetectedIntent.NEUTRO
        assert result.confidence == 0.0

    # === PRIORIDADE ===

    def test_recusa_has_priority(self):
        """Recusa tem prioridade sobre interesse."""
        result = self.detector.detect("Não quero saber de vagas")
        assert result.intent == DetectedIntent.RECUSA
```

### `test_proposer.py` - PROPOSTA DE TRANSIÇÃO

```python
"""
Testes para Transition Proposer (AJUSTE 1).
"""
import pytest
from datetime import datetime, timedelta
from app.services.conversation_mode.types import ConversationMode
from app.services.conversation_mode.intents import IntentResult, DetectedIntent
from app.services.conversation_mode.proposer import (
    TransitionProposer,
    ALLOWED_TRANSITIONS,
    CONFIRMATION_REQUIRED,
)


class TestTransitionProposer:
    """Testes do TransitionProposer."""

    def setup_method(self):
        self.proposer = TransitionProposer()

    # === MATRIZ DE TRANSIÇÕES ===

    def test_discovery_to_oferta_allowed(self):
        """Discovery → oferta é permitida."""
        assert ConversationMode.OFERTA in ALLOWED_TRANSITIONS[ConversationMode.DISCOVERY]

    def test_discovery_to_followup_not_allowed(self):
        """Discovery → followup NÃO é permitida."""
        assert ConversationMode.FOLLOWUP not in ALLOWED_TRANSITIONS[ConversationMode.DISCOVERY]

    def test_all_modes_can_go_to_reativacao(self):
        """Todos os modos podem ir para reativação."""
        for mode in [ConversationMode.DISCOVERY, ConversationMode.OFERTA, ConversationMode.FOLLOWUP]:
            assert ConversationMode.REATIVACAO in ALLOWED_TRANSITIONS[mode]

    # === CONFIRMATION REQUIRED ===

    def test_discovery_to_oferta_needs_confirmation(self):
        """Discovery → oferta REQUER confirmação."""
        assert (ConversationMode.DISCOVERY, ConversationMode.OFERTA) in CONFIRMATION_REQUIRED

    def test_followup_to_oferta_needs_confirmation(self):
        """Followup → oferta REQUER confirmação."""
        assert (ConversationMode.FOLLOWUP, ConversationMode.OFERTA) in CONFIRMATION_REQUIRED

    # === PROPOSTAS ===

    def test_propose_from_interesse_vaga(self):
        """Propõe oferta quando interesse em vaga."""
        intent = IntentResult(
            intent=DetectedIntent.INTERESSE_VAGA,
            confidence=0.8,
            evidence="tem vaga"
        )
        proposal = self.proposer.propose(intent, ConversationMode.DISCOVERY)

        assert proposal.should_transition is True
        assert proposal.to_mode == ConversationMode.OFERTA
        assert proposal.needs_confirmation is True  # AJUSTE 4

    def test_propose_blocks_forbidden_transition(self):
        """Bloqueia transição não permitida."""
        intent = IntentResult(
            intent=DetectedIntent.VOLTANDO,
            confidence=0.7,
            evidence="voltei"
        )
        # VOLTANDO sugere FOLLOWUP, mas DISCOVERY → FOLLOWUP não é permitida
        proposal = self.proposer.propose(intent, ConversationMode.DISCOVERY)

        assert proposal.should_transition is False
        assert "not_allowed" in proposal.trigger

    def test_propose_automatic_silence_reativacao(self):
        """Silêncio 7d → reativação automática."""
        intent = IntentResult(
            intent=DetectedIntent.NEUTRO,
            confidence=0.5,
            evidence=""
        )
        proposal = self.proposer.propose(
            intent,
            ConversationMode.FOLLOWUP,
            last_message_at=datetime.utcnow() - timedelta(days=10)
        )

        assert proposal.should_transition is True
        assert proposal.to_mode == ConversationMode.REATIVACAO
        assert proposal.is_automatic is True
        assert proposal.needs_confirmation is False

    def test_propose_automatic_reserva_followup(self):
        """Reserva confirmada → followup automático."""
        intent = IntentResult(
            intent=DetectedIntent.NEUTRO,
            confidence=0.5,
            evidence=""
        )
        proposal = self.proposer.propose(
            intent,
            ConversationMode.OFERTA,
            reserva_confirmada=True
        )

        assert proposal.should_transition is True
        assert proposal.to_mode == ConversationMode.FOLLOWUP
        assert proposal.is_automatic is True

    def test_no_proposal_for_same_mode(self):
        """Não propõe transição para mesmo modo."""
        intent = IntentResult(
            intent=DetectedIntent.INTERESSE_VAGA,
            confidence=0.8,
            evidence="tem vaga"
        )
        # Já em oferta, interesse não muda
        proposal = self.proposer.propose(intent, ConversationMode.OFERTA)

        assert proposal.should_transition is False
        assert "already_in_mode" in proposal.trigger
```

### `test_validator.py` - VALIDAÇÃO + MICRO-CONFIRMAÇÃO

```python
"""
Testes para Transition Validator com micro-confirmação (AJUSTE 4).
"""
import pytest
from datetime import datetime, timedelta
from app.services.conversation_mode.types import ConversationMode
from app.services.conversation_mode.proposer import TransitionProposal
from app.services.conversation_mode.validator import (
    TransitionValidator,
    TransitionDecision,
    TRANSITION_COOLDOWN_MINUTES,
    PENDING_TRANSITION_TIMEOUT_MINUTES,
)


class TestTransitionValidator:
    """Testes do TransitionValidator."""

    def setup_method(self):
        self.validator = TransitionValidator()

    def _make_proposal(
        self,
        should_transition=True,
        from_mode=ConversationMode.DISCOVERY,
        to_mode=ConversationMode.OFERTA,
        needs_confirmation=False,
        is_automatic=False,
    ) -> TransitionProposal:
        return TransitionProposal(
            should_transition=should_transition,
            from_mode=from_mode,
            to_mode=to_mode,
            needs_confirmation=needs_confirmation,
            is_automatic=is_automatic,
            trigger="test",
            evidence="test",
            confidence=0.8,
        )

    # === DECISÃO APPLY ===

    def test_apply_automatic_transition(self):
        """Transição automática → APPLY."""
        proposal = self._make_proposal(is_automatic=True, needs_confirmation=False)
        result = self.validator.validate(proposal)

        assert result.decision == TransitionDecision.APPLY
        assert result.final_mode == ConversationMode.OFERTA

    def test_apply_no_confirmation_needed(self):
        """Transição sem confirmação → APPLY."""
        proposal = self._make_proposal(needs_confirmation=False)
        result = self.validator.validate(proposal)

        assert result.decision == TransitionDecision.APPLY

    # === DECISÃO PENDING ===

    def test_pending_when_confirmation_needed(self):
        """Transição com confirmação → PENDING."""
        proposal = self._make_proposal(needs_confirmation=True)
        result = self.validator.validate(proposal)

        assert result.decision == TransitionDecision.PENDING
        assert result.final_mode == ConversationMode.DISCOVERY  # Não muda ainda
        assert result.pending_mode == ConversationMode.OFERTA

    # === DECISÃO CONFIRM ===

    def test_confirm_pending_when_message_confirms(self):
        """Confirma pending quando mensagem confirma → CONFIRM."""
        proposal = self._make_proposal(should_transition=False)

        result = self.validator.validate(
            proposal=proposal,
            pending_transition=ConversationMode.OFERTA,
            pending_transition_at=datetime.utcnow(),
            mensagem_confirma=True,
        )

        assert result.decision == TransitionDecision.CONFIRM
        assert result.final_mode == ConversationMode.OFERTA

    # === DECISÃO CANCEL ===

    def test_cancel_pending_when_message_not_confirms(self):
        """Cancela pending quando mensagem não confirma → CANCEL."""
        proposal = self._make_proposal(should_transition=False)

        result = self.validator.validate(
            proposal=proposal,
            pending_transition=ConversationMode.OFERTA,
            pending_transition_at=datetime.utcnow(),
            mensagem_confirma=False,
        )

        assert result.decision == TransitionDecision.CANCEL
        assert result.final_mode == ConversationMode.DISCOVERY

    def test_cancel_pending_on_timeout(self):
        """Cancela pending após timeout → CANCEL."""
        proposal = self._make_proposal(should_transition=False)

        result = self.validator.validate(
            proposal=proposal,
            pending_transition=ConversationMode.OFERTA,
            pending_transition_at=datetime.utcnow() - timedelta(minutes=60),
            mensagem_confirma=True,  # Mesmo confirmando, timeout cancela
        )

        assert result.decision == TransitionDecision.CANCEL
        assert "timeout" in result.reason

    # === DECISÃO REJECT ===

    def test_reject_no_transition(self):
        """Rejeita quando não há transição → REJECT."""
        proposal = self._make_proposal(should_transition=False)

        result = self.validator.validate(proposal)

        assert result.decision == TransitionDecision.REJECT

    def test_reject_during_cooldown(self):
        """Rejeita durante cooldown → REJECT."""
        proposal = self._make_proposal()

        result = self.validator.validate(
            proposal=proposal,
            last_transition_at=datetime.utcnow() - timedelta(minutes=1),
        )

        assert result.decision == TransitionDecision.REJECT
        assert "cooldown" in result.reason

    def test_accept_after_cooldown(self):
        """Aceita após cooldown expirar."""
        proposal = self._make_proposal()

        result = self.validator.validate(
            proposal=proposal,
            last_transition_at=datetime.utcnow() - timedelta(
                minutes=TRANSITION_COOLDOWN_MINUTES + 1
            ),
        )

        assert result.decision == TransitionDecision.APPLY
```

---

## Testes de Integração

### `test_integration.py`

```python
"""
Testes de integração do Conversation Mode.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.conversation_mode import (
    ConversationMode,
    ModeRouter,
    CapabilitiesGate,
    ModeInfo,
)
from app.services.conversation_mode.validator import TransitionDecision


class TestModeRouterIntegration:
    """Testes de integração do ModeRouter."""

    def _mock_supabase(self, mode="discovery", pending=None):
        """Cria mock do supabase."""
        mock = MagicMock()
        mock.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "id": "test-conv-001",
            "conversation_mode": mode,
            "mode_updated_at": None,
            "pending_transition": pending,
            "pending_transition_at": datetime.utcnow() if pending else None,
        }
        mock.table.return_value.update.return_value.eq.return_value.execute.return_value = True
        return mock

    @pytest.mark.asyncio
    async def test_discovery_to_oferta_creates_pending(self):
        """Discovery → oferta cria pending (não transiciona direto)."""
        with patch("app.services.conversation_mode.repository.supabase", self._mock_supabase("discovery")):
            router = ModeRouter()

            mode_info = await router.process(
                conversa_id="test-conv-001",
                mensagem="Tem vaga de cardiologia?",
                last_message_at=datetime.utcnow() - timedelta(hours=1),
            )

            # Deve continuar em discovery (pending foi criado)
            assert mode_info.mode == ConversationMode.DISCOVERY

    @pytest.mark.asyncio
    async def test_pending_confirmed_transitions(self):
        """Confirma pending quando médico responde positivamente."""
        with patch("app.services.conversation_mode.repository.supabase", self._mock_supabase("discovery", "oferta")):
            router = ModeRouter()

            mode_info = await router.process(
                conversa_id="test-conv-001",
                mensagem="Sim, tenho CRM ativo",
                last_message_at=datetime.utcnow() - timedelta(hours=1),
            )

            # Deve transicionar para oferta
            assert mode_info.mode == ConversationMode.OFERTA

    @pytest.mark.asyncio
    async def test_silence_triggers_reativacao(self):
        """Silêncio 7d transiciona automaticamente para reativação."""
        with patch("app.services.conversation_mode.repository.supabase", self._mock_supabase("followup")):
            router = ModeRouter()

            mode_info = await router.process(
                conversa_id="test-conv-001",
                mensagem="oi",
                last_message_at=datetime.utcnow() - timedelta(days=10),
            )

            # Deve transicionar para reativação
            assert mode_info.mode == ConversationMode.REATIVACAO


class TestCapabilitiesGateIntegration:
    """Testes de integração do CapabilitiesGate."""

    def test_gate_with_real_tools_format(self):
        """Gate funciona com formato real de tools."""
        all_tools = [
            {"name": "buscar_vagas", "description": "...", "input_schema": {}},
            {"name": "salvar_memoria", "description": "...", "input_schema": {}},
            {"name": "reservar_plantao", "description": "...", "input_schema": {}},
            {"name": "calcular_valor", "description": "...", "input_schema": {}},
        ]

        # Discovery
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        filtered = gate.filter_tools(all_tools)
        names = [t["name"] for t in filtered]

        assert "salvar_memoria" in names
        assert "buscar_vagas" not in names
        assert "reservar_plantao" not in names
        assert "calcular_valor" not in names

        # Oferta
        gate = CapabilitiesGate(ConversationMode.OFERTA)
        filtered = gate.filter_tools(all_tools)
        names = [t["name"] for t in filtered]

        assert "buscar_vagas" in names
        assert "reservar_plantao" in names
        assert "calcular_valor" in names

    def test_constraints_text_for_prompt(self):
        """Constraints text está formatado para prompt."""
        gate = CapabilitiesGate(ConversationMode.DISCOVERY)
        text = gate.get_constraints_text()

        # Deve ser legível para LLM
        assert len(text) > 50
        assert "DISCOVERY" in text
        assert "NÃO" in text or "não" in text


class TestFullConversationCycle:
    """Testes do ciclo completo de conversa."""

    @pytest.mark.asyncio
    async def test_complete_lifecycle(self):
        """Ciclo de vida: discovery → pending → oferta → followup."""
        # Este teste documenta o fluxo esperado:
        #
        # 1. Conversa começa em DISCOVERY
        # 2. Médico: "Tem vaga?" → pending_transition = oferta
        # 3. Médico: "Sim, tenho CRM" → mode = oferta
        # 4. Médico aceita → mode = followup
        #
        # Implementar com mocks apropriados
        pass
```

---

## Testes BLOQUEADORES Anti-Desvio (CRÍTICOS)

Estes testes são **obrigatórios** pois protegem contra os riscos de negócio.

### `test_anti_desvio.py`

```python
"""
Testes BLOQUEADORES para garantir que Julia é INTERMEDIÁRIA.

Estes testes DEVEM PASSAR para deploy. Eles protegem contra:
1. LLM tentando reservar plantões
2. LLM tentando negociar valores
3. LLM confirmando reservas sem autoridade
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

    def test_forbidden_claims_negociacao_em_oferta(self):
        """Mesmo em OFERTA, claims de negociação devem ser proibidos."""
        gate = CapabilitiesGate(ConversationMode.OFERTA)
        claims = gate.get_forbidden_claims()

        assert "confirm_booking" in claims, "CRÍTICO: confirm_booking não proibido em OFERTA!"
        assert "negotiate_terms" in claims, "CRÍTICO: negotiate_terms não proibido em OFERTA!"
        assert "quote_price" in claims, "CRÍTICO: quote_price não proibido em OFERTA!"

    def test_constraints_text_inclui_guardrail_intermediaria(self):
        """Constraints text DEVE incluir guardrail de intermediária."""
        gate = CapabilitiesGate(ConversationMode.OFERTA)
        text = gate.get_constraints_text()

        assert "INTERMEDIÁRIA" in text.upper() or "intermediária" in text.lower(), (
            "CRÍTICO: Guardrail de intermediária não está no prompt!"
        )
        assert "NUNCA" in text or "NÃO" in text, (
            "CRÍTICO: Proibições não estão claras no prompt!"
        )

    def test_global_forbidden_claims_existem(self):
        """Deve existir lista de claims globalmente proibidos."""
        assert "negotiate_price" in GLOBAL_FORBIDDEN_CLAIMS or "negotiate_terms" in GLOBAL_FORBIDDEN_CLAIMS
        assert "confirm_booking_directly" in GLOBAL_FORBIDDEN_CLAIMS or "confirm_booking" in GLOBAL_FORBIDDEN_CLAIMS


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
        "Fechado! Seu plantão é dia 15 no São Luiz.",
        "O valor é R$ 2.500 por 12h.",
        "Consigo R$ 2.800 se vc confirmar agora.",
        "Dá pra subir o valor se precisar.",
        "Consigo melhorar as condições pra você.",
        "Tá fechado então! Te espero lá.",
        "Confirmado seu plantão de cardio.",
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
    ])
    def test_nao_detecta_resposta_permitida(self, resposta_permitida):
        """Respostas permitidas NÃO devem disparar os padrões."""
        for padrao in self.PADROES_PROIBIDOS:
            assert not re.search(padrao, resposta_permitida), (
                f"Falso positivo: '{resposta_permitida}' casou com '{padrao}'"
            )
```

### Função Validadora de Resposta

```python
# app/services/conversation_mode/response_validator.py

"""
Validador de resposta para garantir que Julia não desvia.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

PADROES_PROIBIDOS = [
    (r"(?i)reserv(ei|ado|a) (pra|para) voc[êe]", "confirm_booking"),
    (r"(?i)confirm(ado|ei|o) (seu|o) plant[aã]o", "confirm_booking"),
    (r"(?i)paga\s+R?\$?\s*\d+", "quote_price"),
    (r"(?i)consigo\s+R?\$?\s*\d+", "quote_price"),
    (r"(?i)valor\s+(é|de|seria)\s+R?\$?\s*\d+", "quote_price"),
    (r"(?i)d[aá]\s+pra\s+(sub|melhora)ir", "negotiate_terms"),
    (r"(?i)consigo\s+melhorar", "negotiate_terms"),
    (r"(?i)t[aá]\s+(fechado|confirm)", "confirm_booking"),
]


def validar_resposta_julia(resposta: str, mode: str) -> tuple[bool, Optional[str]]:
    """
    Valida se a resposta da Julia não contém desvios.

    Args:
        resposta: Texto da resposta gerada
        mode: Modo atual da conversa

    Returns:
        (is_valid, violation_type) - Se inválida, retorna tipo de violação
    """
    for padrao, violacao in PADROES_PROIBIDOS:
        if re.search(padrao, resposta):
            logger.warning(
                f"VIOLAÇÃO DETECTADA: {violacao} em modo {mode}",
                extra={
                    "violacao": violacao,
                    "padrao": padrao,
                    "mode": mode,
                    "resposta_truncada": resposta[:100],
                }
            )
            return False, violacao

    return True, None
```

---

## DoD (Definition of Done)

### Cobertura

- [ ] Cobertura > 80% no módulo `conversation_mode`
- [ ] Todos os 4 modos testados
- [ ] Todas as transições permitidas testadas
- [ ] Todas as transições proibidas testadas
- [ ] 3 camadas do Gate testadas (tools, claims, behavior)
- [ ] Micro-confirmação testada (PENDING, CONFIRM, CANCEL)
- [ ] Cooldown e timeout testados

### Testes Específicos

- [ ] `test_types.py` - 5+ testes
- [ ] `test_capabilities.py` - 15+ testes (3 camadas)
- [ ] `test_intents.py` - 10+ testes (7 tipos de intent)
- [ ] `test_proposer.py` - 8+ testes (matriz + confirmação)
- [ ] `test_validator.py` - 10+ testes (5 decisões)
- [ ] `test_integration.py` - 5+ testes

### CI

- [ ] Todos os testes passando
- [ ] Sem warnings de deprecation
- [ ] Tempo de execução < 60s

### Validação Manual

- [ ] Teste de fluxo real via WhatsApp de teste
- [ ] Verificar logs de intent detectado
- [ ] Verificar logs de transição
- [ ] Verificar constraints no prompt
- [ ] Testar micro-confirmação na prática

---

## Comandos de Teste

```bash
# Rodar todos os testes do módulo
uv run pytest tests/services/conversation_mode/ -v

# Rodar com cobertura
uv run pytest tests/services/conversation_mode/ \
    --cov=app/services/conversation_mode \
    --cov-report=term-missing \
    --cov-report=html

# Rodar testes por arquivo
uv run pytest tests/services/conversation_mode/test_capabilities.py -v
uv run pytest tests/services/conversation_mode/test_intents.py -v
uv run pytest tests/services/conversation_mode/test_validator.py -v

# Rodar testes específicos
uv run pytest tests/services/conversation_mode/test_validator.py::TestTransitionValidator::test_pending_when_confirmation_needed -v

# Rodar testes de integração
uv run pytest tests/services/conversation_mode/test_integration.py -v

# Debug com print
uv run pytest tests/services/conversation_mode/test_intents.py -v -s
```

---

## Checklist Final da Sprint 29

- [ ] **E01** - Schema conversation_mode migrado e backfill executado
- [ ] **E02** - Capabilities Gate com 3 camadas implementado
- [ ] **E03** - Mode Router com micro-confirmação implementado
- [ ] **E04** - Integração no agente funcionando
- [ ] **E05** - Testes passando com cobertura > 80%

### Validação Pós-Deploy

- [ ] Conversa nova começa em `discovery`
- [ ] `buscar_vagas` bloqueada em discovery
- [ ] Interesse em vagas cria `pending_transition`
- [ ] Confirmação do médico transiciona para `oferta`
- [ ] Constraints das 3 camadas aparecendo no prompt
- [ ] Logs de intent, proposta e decisão aparecendo
- [ ] Micro-confirmação funcionando na prática
- [ ] Nenhum erro 500 relacionado ao módulo
