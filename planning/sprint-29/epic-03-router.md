# E03: Mode Router

**Status:** Pendente
**Estimativa:** 8h
**Dependencia:** E01 (Schema), E02 (Capabilities)
**Responsavel:** Dev

---

## Objetivo

Implementar o **Mode Router** com 3 camadas:
1. **Intent Detector** - Detecta intenção do médico (não decide modo)
2. **Transition Proposer** - Propõe transição com base na intenção
3. **Transition Validator** - Valida contra matriz determinística + micro-confirmação

---

## Conceito: Intent ≠ Mode

```
┌─────────────────────────────────────────────────────────────────┐
│                     SEPARAÇÃO DE CONCEITOS                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   detected_intent (o que o médico sinaliza)                     │
│   ├── "quer_saber_vagas" → interesse em vagas                   │
│   ├── "tem_duvida" → quer entender mais                         │
│   ├── "quer_fechar" → pronto para reservar                      │
│   └── "voltou" → retomando contato                              │
│                                                                  │
│   final_mode (decisão de negócio)                               │
│   ├── discovery → conhecer o médico                             │
│   ├── oferta → apresentar vagas                                 │
│   ├── followup → acompanhar                                     │
│   └── reativacao → reativar contato                             │
│                                                                  │
│   Regra: detected_intent INFORMA, não DECIDE o modo             │
│          A decisão passa pela matriz ALLOWED_TRANSITIONS        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Arquitetura: 3 Camadas

```
┌─────────────────────────────────────────────────────────────────┐
│                         MODE ROUTER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   MENSAGEM DO MÉDICO                                            │
│        │                                                         │
│        ▼                                                         │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ CAMADA 1: INTENT DETECTOR                               │   │
│   │                                                          │   │
│   │  Entrada: mensagem, contexto                            │   │
│   │  Processo:                                               │   │
│   │    1. Aplicar keywords de interesse                     │   │
│   │    2. Aplicar keywords de dúvida                        │   │
│   │    3. Detectar sinais contextuais                       │   │
│   │  Saída: detected_intent + confidence                    │   │
│   │  NOTA: NÃO decide modo, apenas detecta intenção         │   │
│   └─────────────────────────────────────────────────────────┘   │
│        │                                                         │
│        ▼                                                         │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ CAMADA 2: TRANSITION PROPOSER                           │   │
│   │                                                          │   │
│   │  Entrada: detected_intent, modo_atual, contexto         │   │
│   │  Processo:                                               │   │
│   │    1. Mapear intent → modo sugerido                     │   │
│   │    2. Verificar se transição está em ALLOWED_TRANSITIONS│   │
│   │    3. Verificar se requer micro-confirmação             │   │
│   │  Saída: TransitionProposal (modo, needs_confirmation)   │   │
│   └─────────────────────────────────────────────────────────┘   │
│        │                                                         │
│        ▼                                                         │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ CAMADA 3: TRANSITION VALIDATOR                          │   │
│   │                                                          │   │
│   │  Entrada: TransitionProposal, pending_transition        │   │
│   │  Processo:                                               │   │
│   │    1. Se needs_confirmation: salvar pending_transition  │   │
│   │    2. Se já tem pending: verificar confirmação          │   │
│   │    3. Aplicar cooldown (evitar flip-flop)               │   │
│   │  Saída: APLICAR / PENDENTE / REJEITAR                   │   │
│   └─────────────────────────────────────────────────────────┘   │
│        │                                                         │
│        ├── APLICAR ────► atualizar conversation_mode            │
│        ├── PENDENTE ───► salvar pending_transition              │
│        └── REJEITAR ───► manter modo atual                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Matriz de Transições Permitidas (AJUSTE 1)

```python
ALLOWED_TRANSITIONS: dict[ConversationMode, set[ConversationMode]] = {
    ConversationMode.DISCOVERY: {
        ConversationMode.OFERTA,      # Com evidência + micro-confirmação
        ConversationMode.REATIVACAO,  # Silêncio > 7d (automático)
    },
    ConversationMode.OFERTA: {
        ConversationMode.FOLLOWUP,    # Reserva confirmada (automático)
        ConversationMode.DISCOVERY,   # Recuo tático (objeção)
        ConversationMode.REATIVACAO,  # Silêncio > 7d
    },
    ConversationMode.FOLLOWUP: {
        ConversationMode.OFERTA,      # Nova oportunidade
        ConversationMode.REATIVACAO,  # Silêncio > 7d
        ConversationMode.DISCOVERY,   # Mudou de perfil
    },
    ConversationMode.REATIVACAO: {
        ConversationMode.DISCOVERY,   # Médico respondeu com dúvida
        ConversationMode.OFERTA,      # Médico respondeu com interesse
        ConversationMode.FOLLOWUP,    # Médico respondeu neutro
    },
}

# Transições que NÃO requerem micro-confirmação (automáticas)
AUTOMATIC_TRANSITIONS: list[tuple[ConversationMode, ConversationMode]] = [
    (ConversationMode.OFERTA, ConversationMode.FOLLOWUP),      # Reserva confirmada
    (ConversationMode.REATIVACAO, ConversationMode.FOLLOWUP),  # Médico respondeu
    # Qualquer → REATIVACAO (silêncio 7d)
]

# Transições que REQUEREM micro-confirmação
CONFIRMATION_REQUIRED: list[tuple[ConversationMode, ConversationMode]] = [
    (ConversationMode.DISCOVERY, ConversationMode.OFERTA),  # Mais importante!
    (ConversationMode.FOLLOWUP, ConversationMode.OFERTA),   # Nova oportunidade
]
```

---

## Tipos de Intent (AJUSTE 2)

```python
class DetectedIntent(Enum):
    """Intenção detectada na mensagem do médico."""
    INTERESSE_VAGA = "interesse_vaga"        # Quer saber de vagas
    DUVIDA_PERFIL = "duvida_perfil"          # Quer entender mais sobre Julia/Revoluna
    PRONTO_FECHAR = "pronto_fechar"          # Quer reservar agora
    VOLTANDO = "voltando"                    # Retomando contato após silêncio
    NEUTRO = "neutro"                        # Resposta sem sinal claro
    OBJECAO = "objecao"                      # Levantou objeção
    RECUSA = "recusa"                        # Não tem interesse

# Mapeamento: intent → modo sugerido (quando permitido)
INTENT_TO_MODE_SUGGESTION: dict[DetectedIntent, ConversationMode] = {
    DetectedIntent.INTERESSE_VAGA: ConversationMode.OFERTA,
    DetectedIntent.PRONTO_FECHAR: ConversationMode.OFERTA,
    DetectedIntent.DUVIDA_PERFIL: ConversationMode.DISCOVERY,
    DetectedIntent.OBJECAO: ConversationMode.DISCOVERY,
    DetectedIntent.VOLTANDO: ConversationMode.FOLLOWUP,
    DetectedIntent.NEUTRO: None,  # Não sugere mudança
    DetectedIntent.RECUSA: None,  # Não muda modo (Policy Engine cuida)
}
```

---

## Micro-Confirmação (AJUSTE 4)

**Regra crítica:** A micro-confirmação é sobre **INTRODUÇÃO/PONTE**, não sobre reserva.

- ✅ "Quer que eu te conecte ao responsável pela vaga X?"
- ✅ "Posso te colocar em contato com quem tá oferecendo?"
- ❌ ~~"Quer que eu reserve pra você?"~~ (Julia não reserva)

Quando a transição requer confirmação:

```
┌─────────────────────────────────────────────────────────────────┐
│           FLUXO DE MICRO-CONFIRMAÇÃO (INTERMEDIAÇÃO)             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   1. Médico: "Quero saber de plantões"                          │
│      └── Intent: INTERESSE_VAGA                                  │
│      └── Proposta: discovery → oferta                            │
│      └── Requer confirmação? SIM (connect_to_owner_confirm)      │
│                                                                  │
│   2. Salvar pending_transition = 'oferta'                       │
│      Julia responde com micro-confirmação de PONTE:              │
│      "Que legal! Tenho umas opções boas aqui.                   │
│       Quer que eu te coloque em contato com o responsável?"      │
│                                                                  │
│   3. Médico: "Sim, pode ser"                                    │
│      └── Intent: NEUTRO (mas confirma)                           │
│      └── pending_transition existe? SIM                          │
│      └── Resposta confirma? SIM                                  │
│      └── APLICAR transição discovery → oferta                   │
│      └── Julia mostra vagas e oferece PONTE                     │
│                                                                  │
│   OU                                                             │
│                                                                  │
│   3. Médico: "Ah não, só tava curioso"                          │
│      └── Intent: RECUSA                                          │
│      └── pending_transition existe? SIM                          │
│      └── Resposta confirma? NÃO                                  │
│      └── CANCELAR pending_transition                             │
│      └── Manter em DISCOVERY                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Tipo de Confirmação por Transição

| Transição | Tipo de Confirmação | Pergunta da Julia |
|-----------|---------------------|-------------------|
| discovery → oferta | `connect_to_owner_confirm` | "Quer que eu te coloque em contato com o responsável?" |
| followup → oferta | `new_opportunity_confirm` | "Tem uma vaga nova aqui. Quer que eu te conecte?" |

### Evidência Mínima para Transição

Para `discovery → oferta`:
- Médico pediu "tem plantão?" / "me manda opções" / "tenho interesse"
- OU respondeu positivamente a pergunta da Julia ("quer que eu te mande opções?")

---

## Implementação

### Arquivo: `app/services/conversation_mode/intents.py`

```python
"""
Intent Detector - Detecta intenção do médico (NÃO decide modo).
"""
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class DetectedIntent(Enum):
    """Intenção detectada na mensagem do médico."""
    INTERESSE_VAGA = "interesse_vaga"
    DUVIDA_PERFIL = "duvida_perfil"
    PRONTO_FECHAR = "pronto_fechar"
    VOLTANDO = "voltando"
    NEUTRO = "neutro"
    OBJECAO = "objecao"
    RECUSA = "recusa"


# Keywords por tipo de intent
INTERESSE_KEYWORDS = [
    r"\binteress",
    r"\bconta mais\b",
    r"\bquero saber\b",
    r"\btem vaga\b",
    r"\bquanto paga\b",
    r"\bvalor\b",
    r"\bonde\b.*\bhospital\b",
    r"\bqual\b.*\bplantão\b",
    r"\bquando\b.*\bvaga\b",
    r"\bpode me mandar\b",
    r"\bquero ver\b",
]

FECHAR_KEYWORDS = [
    r"\bquero\b.*\breservar\b",
    r"\bpode reservar\b",
    r"\bfecha\b",
    r"\bconfirma\b",
    r"\baceito\b",
    r"\bvou pegar\b",
    r"\bquero esse\b",
]

DUVIDA_KEYWORDS = [
    r"\bcomo funciona\b",
    r"\bo que é isso\b",
    r"\bnão entendi\b",
    r"\bexplica\b",
    r"\bquem é você\b",
    r"\bque empresa\b",
    r"\bé real\b",
    r"\bé confiável\b",
]

VOLTANDO_KEYWORDS = [
    r"^oi\b",
    r"\bvoltei\b",
    r"\blembrei\b",
    r"\bdesculpa a demora\b",
    r"\bsumido\b",
    r"\btava ocupado\b",
]

OBJECAO_KEYWORDS = [
    r"\bnão sei\b",
    r"\bpreciso pensar\b",
    r"\bdepois\b",
    r"\bagora não\b",
    r"\bestou ocupado\b",
    r"\bmuito longe\b",
    r"\bvalor baixo\b",
]

RECUSA_KEYWORDS = [
    r"\bnão quero\b",
    r"\bnão tenho interesse\b",
    r"\bpara de mandar\b",
    r"\bnão me liga\b",
    r"\btira meu numero\b",
    r"\bnão\b.*\bobrigado\b",
]


@dataclass
class IntentResult:
    """Resultado da detecção de intent."""
    intent: DetectedIntent
    confidence: float
    evidence: str


def _check_keywords(text: str, patterns: list[str]) -> tuple[bool, str]:
    """Verifica se texto contém algum dos patterns."""
    text_lower = text.lower()
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            return True, match.group()
    return False, ""


class IntentDetector:
    """
    Detecta intenção do médico na mensagem.

    IMPORTANTE: Este detector NÃO decide o modo.
    Ele apenas identifica o que o médico está sinalizando.
    """

    def detect(self, mensagem: str) -> IntentResult:
        """
        Detecta intenção na mensagem.

        Args:
            mensagem: Texto da mensagem do médico

        Returns:
            IntentResult com intent detectado
        """
        if not mensagem or not mensagem.strip():
            return IntentResult(
                intent=DetectedIntent.NEUTRO,
                confidence=0.0,
                evidence="mensagem vazia",
            )

        # Ordem importa: mais específico primeiro

        # 1. Recusa (mais forte)
        found, match = _check_keywords(mensagem, RECUSA_KEYWORDS)
        if found:
            return IntentResult(
                intent=DetectedIntent.RECUSA,
                confidence=0.9,
                evidence=f"recusa: '{match}'",
            )

        # 2. Pronto para fechar
        found, match = _check_keywords(mensagem, FECHAR_KEYWORDS)
        if found:
            return IntentResult(
                intent=DetectedIntent.PRONTO_FECHAR,
                confidence=0.85,
                evidence=f"pronto para fechar: '{match}'",
            )

        # 3. Objeção
        found, match = _check_keywords(mensagem, OBJECAO_KEYWORDS)
        if found:
            return IntentResult(
                intent=DetectedIntent.OBJECAO,
                confidence=0.7,
                evidence=f"objeção: '{match}'",
            )

        # 4. Interesse em vaga
        found, match = _check_keywords(mensagem, INTERESSE_KEYWORDS)
        if found:
            return IntentResult(
                intent=DetectedIntent.INTERESSE_VAGA,
                confidence=0.75,
                evidence=f"interesse: '{match}'",
            )

        # 5. Dúvida sobre perfil
        found, match = _check_keywords(mensagem, DUVIDA_KEYWORDS)
        if found:
            return IntentResult(
                intent=DetectedIntent.DUVIDA_PERFIL,
                confidence=0.7,
                evidence=f"dúvida: '{match}'",
            )

        # 6. Voltando após silêncio
        found, match = _check_keywords(mensagem, VOLTANDO_KEYWORDS)
        if found:
            return IntentResult(
                intent=DetectedIntent.VOLTANDO,
                confidence=0.6,
                evidence=f"voltando: '{match}'",
            )

        # 7. Neutro (default)
        return IntentResult(
            intent=DetectedIntent.NEUTRO,
            confidence=0.5,
            evidence="sem sinal claro",
        )
```

### Arquivo: `app/services/conversation_mode/proposer.py`

```python
"""
Transition Proposer - Propõe transições baseado em intent + matriz.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from .types import ConversationMode
from .intents import DetectedIntent, IntentResult

logger = logging.getLogger(__name__)


# Matriz de transições permitidas (AJUSTE 1)
ALLOWED_TRANSITIONS: dict[ConversationMode, set[ConversationMode]] = {
    ConversationMode.DISCOVERY: {
        ConversationMode.OFERTA,
        ConversationMode.REATIVACAO,
    },
    ConversationMode.OFERTA: {
        ConversationMode.FOLLOWUP,
        ConversationMode.DISCOVERY,
        ConversationMode.REATIVACAO,
    },
    ConversationMode.FOLLOWUP: {
        ConversationMode.OFERTA,
        ConversationMode.REATIVACAO,
        ConversationMode.DISCOVERY,
    },
    ConversationMode.REATIVACAO: {
        ConversationMode.DISCOVERY,
        ConversationMode.OFERTA,
        ConversationMode.FOLLOWUP,
    },
}

# Transições automáticas (não requerem confirmação)
AUTOMATIC_TRANSITIONS: set[tuple[ConversationMode, ConversationMode]] = {
    (ConversationMode.OFERTA, ConversationMode.FOLLOWUP),      # Reserva OK
    (ConversationMode.REATIVACAO, ConversationMode.FOLLOWUP),  # Médico respondeu
}

# Transições que REQUEREM micro-confirmação (AJUSTE 4)
CONFIRMATION_REQUIRED: set[tuple[ConversationMode, ConversationMode]] = {
    (ConversationMode.DISCOVERY, ConversationMode.OFERTA),
    (ConversationMode.FOLLOWUP, ConversationMode.OFERTA),
}

# Mapeamento: intent → modo sugerido
INTENT_TO_MODE: dict[DetectedIntent, Optional[ConversationMode]] = {
    DetectedIntent.INTERESSE_VAGA: ConversationMode.OFERTA,
    DetectedIntent.PRONTO_FECHAR: ConversationMode.OFERTA,
    DetectedIntent.DUVIDA_PERFIL: ConversationMode.DISCOVERY,
    DetectedIntent.OBJECAO: ConversationMode.DISCOVERY,
    DetectedIntent.VOLTANDO: ConversationMode.FOLLOWUP,
    DetectedIntent.NEUTRO: None,
    DetectedIntent.RECUSA: None,
}

# Silêncio que dispara reativação
SILENCE_DAYS_FOR_REACTIVATION = 7


@dataclass
class TransitionProposal:
    """Proposta de transição de modo."""
    should_transition: bool
    from_mode: ConversationMode
    to_mode: Optional[ConversationMode]
    needs_confirmation: bool  # Se True, salvar como pending
    is_automatic: bool  # Transição automática (não precisa de evidência forte)
    trigger: str
    evidence: str
    confidence: float


class TransitionProposer:
    """
    Propõe transições baseado em intent detectado + matriz de transições.

    NÃO aplica a transição - apenas propõe.
    """

    def propose(
        self,
        intent_result: IntentResult,
        current_mode: ConversationMode,
        last_message_at: Optional[datetime] = None,
        reserva_confirmada: bool = False,
        objecao_resolvida: bool = False,
    ) -> TransitionProposal:
        """
        Propõe transição baseado no intent detectado.

        Args:
            intent_result: Resultado da detecção de intent
            current_mode: Modo atual da conversa
            last_message_at: Última mensagem do médico
            reserva_confirmada: Se reserva foi confirmada
            objecao_resolvida: Se objeção foi resolvida

        Returns:
            TransitionProposal com sugestão
        """
        # 1. Regras automáticas primeiro (alta prioridade)
        auto_proposal = self._check_automatic_rules(
            current_mode, last_message_at, reserva_confirmada
        )
        if auto_proposal.should_transition:
            return auto_proposal

        # 2. Baseado no intent detectado
        return self._propose_from_intent(
            intent_result, current_mode, objecao_resolvida
        )

    def _check_automatic_rules(
        self,
        current_mode: ConversationMode,
        last_message_at: Optional[datetime],
        reserva_confirmada: bool,
    ) -> TransitionProposal:
        """Verifica regras automáticas de transição."""

        # Regra: Silêncio >= 7 dias → REATIVACAO
        if last_message_at:
            days_since = (datetime.utcnow() - last_message_at).days
            if days_since >= SILENCE_DAYS_FOR_REACTIVATION:
                if current_mode != ConversationMode.REATIVACAO:
                    return TransitionProposal(
                        should_transition=True,
                        from_mode=current_mode,
                        to_mode=ConversationMode.REATIVACAO,
                        needs_confirmation=False,
                        is_automatic=True,
                        trigger="silencio_7d",
                        evidence=f"silêncio de {days_since} dias",
                        confidence=0.95,
                    )

        # Regra: Reserva confirmada → FOLLOWUP
        if reserva_confirmada and current_mode == ConversationMode.OFERTA:
            return TransitionProposal(
                should_transition=True,
                from_mode=current_mode,
                to_mode=ConversationMode.FOLLOWUP,
                needs_confirmation=False,
                is_automatic=True,
                trigger="reserva_confirmada",
                evidence="reserva foi confirmada",
                confidence=1.0,
            )

        # Nenhuma regra automática aplicável
        return TransitionProposal(
            should_transition=False,
            from_mode=current_mode,
            to_mode=None,
            needs_confirmation=False,
            is_automatic=False,
            trigger="none",
            evidence="",
            confidence=0.0,
        )

    def _propose_from_intent(
        self,
        intent_result: IntentResult,
        current_mode: ConversationMode,
        objecao_resolvida: bool,
    ) -> TransitionProposal:
        """Propõe transição baseado no intent."""

        # Obter modo sugerido pelo intent
        suggested_mode = INTENT_TO_MODE.get(intent_result.intent)

        # Caso especial: objeção resolvida em oferta → voltar pra discovery
        if objecao_resolvida and current_mode == ConversationMode.OFERTA:
            suggested_mode = ConversationMode.DISCOVERY

        # Se não há sugestão de modo, não transicionar
        if suggested_mode is None:
            return TransitionProposal(
                should_transition=False,
                from_mode=current_mode,
                to_mode=None,
                needs_confirmation=False,
                is_automatic=False,
                trigger="no_mode_suggestion",
                evidence=f"intent={intent_result.intent.value}",
                confidence=0.0,
            )

        # Se já está no modo sugerido, não transicionar
        if suggested_mode == current_mode:
            return TransitionProposal(
                should_transition=False,
                from_mode=current_mode,
                to_mode=None,
                needs_confirmation=False,
                is_automatic=False,
                trigger="already_in_mode",
                evidence=f"já em {current_mode.value}",
                confidence=0.0,
            )

        # Verificar se transição é permitida
        allowed = ALLOWED_TRANSITIONS.get(current_mode, set())
        if suggested_mode not in allowed:
            logger.warning(
                f"Transição não permitida: {current_mode.value} → {suggested_mode.value}"
            )
            return TransitionProposal(
                should_transition=False,
                from_mode=current_mode,
                to_mode=suggested_mode,
                needs_confirmation=False,
                is_automatic=False,
                trigger="not_allowed",
                evidence=f"transição não permitida na matriz",
                confidence=0.0,
            )

        # Verificar se requer confirmação
        transition_tuple = (current_mode, suggested_mode)
        needs_confirmation = transition_tuple in CONFIRMATION_REQUIRED
        is_automatic = transition_tuple in AUTOMATIC_TRANSITIONS

        return TransitionProposal(
            should_transition=True,
            from_mode=current_mode,
            to_mode=suggested_mode,
            needs_confirmation=needs_confirmation,
            is_automatic=is_automatic,
            trigger=f"intent_{intent_result.intent.value}",
            evidence=intent_result.evidence,
            confidence=intent_result.confidence,
        )
```

### Arquivo: `app/services/conversation_mode/validator.py`

```python
"""
Transition Validator - Valida transições com micro-confirmação.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from .types import ConversationMode
from .proposer import TransitionProposal

logger = logging.getLogger(__name__)


# Cooldown mínimo entre transições (evitar flip-flop)
TRANSITION_COOLDOWN_MINUTES = 5

# Timeout para pending_transition (se médico não confirmar)
PENDING_TRANSITION_TIMEOUT_MINUTES = 30


class TransitionDecision(Enum):
    """Decisão do validador."""
    APPLY = "apply"          # Aplicar transição imediatamente
    PENDING = "pending"      # Salvar como pending (aguardar confirmação)
    CONFIRM = "confirm"      # Confirmar pending existente
    CANCEL = "cancel"        # Cancelar pending existente
    REJECT = "reject"        # Rejeitar transição


@dataclass
class ValidationResult:
    """Resultado da validação de transição."""
    decision: TransitionDecision
    final_mode: ConversationMode  # Modo final após decisão
    reason: str
    pending_mode: Optional[ConversationMode] = None  # Se decision=PENDING


class TransitionValidator:
    """
    Valida transições com suporte a micro-confirmação.

    Se transição requer confirmação:
    1. Primeira vez: salva pending_transition, retorna PENDING
    2. Médico responde: verifica se confirma ou cancela
    3. Timeout: cancela pending automaticamente
    """

    def validate(
        self,
        proposal: TransitionProposal,
        pending_transition: Optional[ConversationMode] = None,
        pending_transition_at: Optional[datetime] = None,
        last_transition_at: Optional[datetime] = None,
        mensagem_confirma: bool = False,  # Se resposta confirma pending
    ) -> ValidationResult:
        """
        Valida proposta de transição.

        Args:
            proposal: Proposta de transição
            pending_transition: Transição pendente (se houver)
            pending_transition_at: Quando pending foi criada
            last_transition_at: Última transição (para cooldown)
            mensagem_confirma: Se mensagem atual confirma pending

        Returns:
            ValidationResult com decisão
        """
        current_mode = proposal.from_mode

        # 1. Se há pending_transition, verificar confirmação
        if pending_transition:
            return self._handle_pending(
                pending_transition,
                pending_transition_at,
                current_mode,
                mensagem_confirma,
            )

        # 2. Se proposta não sugere transição, manter modo
        if not proposal.should_transition:
            return ValidationResult(
                decision=TransitionDecision.REJECT,
                final_mode=current_mode,
                reason=proposal.trigger,
            )

        # 3. Verificar cooldown
        if last_transition_at:
            minutes_since = (datetime.utcnow() - last_transition_at).total_seconds() / 60
            if minutes_since < TRANSITION_COOLDOWN_MINUTES:
                return ValidationResult(
                    decision=TransitionDecision.REJECT,
                    final_mode=current_mode,
                    reason=f"cooldown ({minutes_since:.1f}min < {TRANSITION_COOLDOWN_MINUTES}min)",
                )

        # 4. Se transição é automática ou não requer confirmação, aplicar
        if proposal.is_automatic or not proposal.needs_confirmation:
            logger.info(
                f"Transição aplicada: {current_mode.value} → {proposal.to_mode.value} "
                f"(trigger={proposal.trigger})"
            )
            return ValidationResult(
                decision=TransitionDecision.APPLY,
                final_mode=proposal.to_mode,
                reason=f"automático: {proposal.trigger}",
            )

        # 5. Transição requer confirmação → salvar como pending
        logger.info(
            f"Transição pendente: {current_mode.value} → {proposal.to_mode.value} "
            f"(aguardando confirmação)"
        )
        return ValidationResult(
            decision=TransitionDecision.PENDING,
            final_mode=current_mode,  # Ainda não muda
            reason="aguardando micro-confirmação",
            pending_mode=proposal.to_mode,
        )

    def _handle_pending(
        self,
        pending_transition: ConversationMode,
        pending_transition_at: Optional[datetime],
        current_mode: ConversationMode,
        mensagem_confirma: bool,
    ) -> ValidationResult:
        """Trata pending_transition existente."""

        # Verificar timeout
        if pending_transition_at:
            minutes_since = (datetime.utcnow() - pending_transition_at).total_seconds() / 60
            if minutes_since > PENDING_TRANSITION_TIMEOUT_MINUTES:
                logger.info(
                    f"Pending expirada após {minutes_since:.1f}min"
                )
                return ValidationResult(
                    decision=TransitionDecision.CANCEL,
                    final_mode=current_mode,
                    reason="pending expirada por timeout",
                )

        # Se mensagem confirma, aplicar transição
        if mensagem_confirma:
            logger.info(
                f"Pending confirmada: {current_mode.value} → {pending_transition.value}"
            )
            return ValidationResult(
                decision=TransitionDecision.CONFIRM,
                final_mode=pending_transition,
                reason="confirmado pelo médico",
            )

        # Se mensagem não confirma, cancelar pending
        logger.info(
            f"Pending cancelada: médico não confirmou"
        )
        return ValidationResult(
            decision=TransitionDecision.CANCEL,
            final_mode=current_mode,
            reason="não confirmado pelo médico",
        )
```

### Arquivo: `app/services/conversation_mode/router.py`

```python
"""
Mode Router - Orquestra detecção, proposta e validação de transições.
"""
import logging
from datetime import datetime
from typing import Optional

from .types import ConversationMode, ModeInfo
from .intents import IntentDetector, DetectedIntent
from .proposer import TransitionProposer, TransitionProposal
from .validator import TransitionValidator, TransitionDecision, ValidationResult
from .repository import (
    get_conversation_mode,
    set_conversation_mode,
    set_pending_transition,
    clear_pending_transition,
)

logger = logging.getLogger(__name__)


class ModeRouter:
    """
    Orquestra o fluxo completo de transição de modo.

    3 camadas:
    1. IntentDetector - Detecta intenção do médico
    2. TransitionProposer - Propõe transição
    3. TransitionValidator - Valida e decide

    Suporta micro-confirmação para transições críticas.
    """

    def __init__(self):
        self.intent_detector = IntentDetector()
        self.proposer = TransitionProposer()
        self.validator = TransitionValidator()

    async def process(
        self,
        conversa_id: str,
        mensagem: str,
        last_message_at: Optional[datetime] = None,
        reserva_confirmada: bool = False,
        objecao_resolvida: bool = False,
    ) -> ModeInfo:
        """
        Processa mensagem e decide transição de modo.

        Args:
            conversa_id: ID da conversa
            mensagem: Texto da mensagem do médico
            last_message_at: Timestamp da última mensagem
            reserva_confirmada: Se reserva foi confirmada
            objecao_resolvida: Se objeção foi resolvida

        Returns:
            ModeInfo atualizado (ou atual se sem mudança)
        """
        # 1. Buscar modo atual + pending
        current_info = await get_conversation_mode(conversa_id)
        current_mode = current_info.mode

        # 2. Detectar intent (AJUSTE 2)
        intent_result = self.intent_detector.detect(mensagem)
        logger.debug(
            f"Intent detectado: {intent_result.intent.value} "
            f"(confidence={intent_result.confidence:.2f})"
        )

        # 3. Propor transição
        proposal = self.proposer.propose(
            intent_result=intent_result,
            current_mode=current_mode,
            last_message_at=last_message_at,
            reserva_confirmada=reserva_confirmada,
            objecao_resolvida=objecao_resolvida,
        )

        # 4. Verificar se mensagem confirma pending
        mensagem_confirma = self._check_confirmation(
            mensagem, intent_result, current_info.pending_transition
        )

        # 5. Validar transição
        validation = self.validator.validate(
            proposal=proposal,
            pending_transition=current_info.pending_transition,
            pending_transition_at=current_info.pending_transition_at,
            last_transition_at=current_info.updated_at,
            mensagem_confirma=mensagem_confirma,
        )

        # 6. Aplicar decisão
        return await self._apply_decision(
            conversa_id=conversa_id,
            current_info=current_info,
            validation=validation,
            proposal=proposal,
        )

    def _check_confirmation(
        self,
        mensagem: str,
        intent_result,
        pending_transition: Optional[ConversationMode],
    ) -> bool:
        """
        Verifica se mensagem confirma pending_transition.

        Confirmação acontece quando:
        - Há pending_transition
        - Mensagem não é recusa/objeção
        - Mensagem indica continuidade ou interesse
        """
        if not pending_transition:
            return False

        # Recusa ou objeção = não confirma
        if intent_result.intent in (DetectedIntent.RECUSA, DetectedIntent.OBJECAO):
            return False

        # Interesse explícito = confirma
        if intent_result.intent in (
            DetectedIntent.INTERESSE_VAGA,
            DetectedIntent.PRONTO_FECHAR,
        ):
            return True

        # Resposta neutra curta = provavelmente confirma
        # (ex: "sim", "ok", "pode ser", "tenho")
        mensagem_lower = mensagem.lower().strip()
        confirma_keywords = [
            "sim", "ok", "pode", "tenho", "blz", "beleza",
            "pode ser", "aham", "isso", "claro", "tá bom",
        ]
        for kw in confirma_keywords:
            if kw in mensagem_lower:
                return True

        return False

    async def _apply_decision(
        self,
        conversa_id: str,
        current_info: ModeInfo,
        validation: ValidationResult,
        proposal: TransitionProposal,
    ) -> ModeInfo:
        """Aplica a decisão do validador."""

        if validation.decision == TransitionDecision.APPLY:
            # Aplicar transição
            await set_conversation_mode(
                conversa_id=conversa_id,
                mode=validation.final_mode,
                reason=f"{proposal.trigger}: {proposal.evidence}",
            )
            # Limpar pending se houver
            if current_info.pending_transition:
                await clear_pending_transition(conversa_id)

            return ModeInfo(
                conversa_id=conversa_id,
                mode=validation.final_mode,
                updated_at=datetime.utcnow(),
                updated_reason=validation.reason,
            )

        elif validation.decision == TransitionDecision.PENDING:
            # Salvar pending_transition
            await set_pending_transition(
                conversa_id=conversa_id,
                pending_mode=validation.pending_mode,
            )
            return current_info  # Modo não muda ainda

        elif validation.decision == TransitionDecision.CONFIRM:
            # Confirmar pending → aplicar transição
            await set_conversation_mode(
                conversa_id=conversa_id,
                mode=validation.final_mode,
                reason="micro-confirmação aceita",
            )
            await clear_pending_transition(conversa_id)

            return ModeInfo(
                conversa_id=conversa_id,
                mode=validation.final_mode,
                updated_at=datetime.utcnow(),
                updated_reason=validation.reason,
            )

        elif validation.decision == TransitionDecision.CANCEL:
            # Cancelar pending
            await clear_pending_transition(conversa_id)
            return current_info  # Modo não muda

        else:  # REJECT
            return current_info  # Modo não muda


# Singleton para uso global
_router: Optional[ModeRouter] = None


def get_mode_router() -> ModeRouter:
    """Retorna instância singleton do ModeRouter."""
    global _router
    if _router is None:
        _router = ModeRouter()
    return _router
```

### Arquivo: `app/services/conversation_mode/logging.py` (Black Box Recorder)

```python
"""
Structured Logging para Mode Router.

Cada decisão é registrada para auditoria e debugging.
"""
import logging
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
import json

from .capabilities import CAPABILITIES_BY_MODE

logger = logging.getLogger(__name__)


@dataclass
class ModeDecisionLog:
    """Registro estruturado de decisão do Mode Router."""
    timestamp: datetime
    conversa_id: str
    current_mode: str
    detected_intent: str
    intent_confidence: float
    proposed_mode: Optional[str]
    validator_decision: str  # APPLY, PENDING, CONFIRM, CANCEL, REJECT
    transition_reason: str
    capabilities_version: str  # Hash do CAPABILITIES_BY_MODE

    def to_dict(self) -> dict:
        """Converte para dict serializável."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


def get_capabilities_version() -> str:
    """Gera hash do CAPABILITIES_BY_MODE para versionamento."""
    config_str = str(CAPABILITIES_BY_MODE)
    return hashlib.md5(config_str.encode()).hexdigest()[:8]


def log_mode_decision(
    conversa_id: str,
    current_mode: str,
    detected_intent: str,
    intent_confidence: float,
    proposed_mode: Optional[str],
    validator_decision: str,
    transition_reason: str,
) -> ModeDecisionLog:
    """
    Registra decisão do Mode Router.

    Este log é o "black box recorder" da Julia.
    Quando der ruim, explica em 30 segundos.
    """
    log_entry = ModeDecisionLog(
        timestamp=datetime.utcnow(),
        conversa_id=conversa_id,
        current_mode=current_mode,
        detected_intent=detected_intent,
        intent_confidence=intent_confidence,
        proposed_mode=proposed_mode,
        validator_decision=validator_decision,
        transition_reason=transition_reason,
        capabilities_version=get_capabilities_version(),
    )

    # Log estruturado
    logger.info(
        f"MODE_DECISION: {json.dumps(log_entry.to_dict())}"
    )

    return log_entry


def log_violation_attempt(
    conversa_id: str,
    mode: str,
    violation_type: str,  # "tool" ou "claim"
    attempted: str,
) -> None:
    """
    Registra tentativa de violação de capabilities.

    Útil para ajustar prompt ou matriz quando violação é frequente.
    """
    logger.warning(
        f"VIOLATION_ATTEMPT: conversa={conversa_id} mode={mode} "
        f"type={violation_type} attempted={attempted}"
    )
```

### Arquivo: `app/services/conversation_mode/bootstrap.py` (Modo Inicial)

```python
"""
Bootstrap de Modo - Determina modo inicial de forma determinística.

Problema que resolve: Inbound que deveria começar em OFERTA
entra como DISCOVERY, fazendo Julia parecer "lerda".

Exemplo perigoso:
"Oi, sou o Dr João, vi uma vaga de anestesia com vocês"
# Se cair como DISCOVERY por default, Julia parece desatenta.
"""
import logging
import re
from typing import Optional

from .types import ConversationMode

logger = logging.getLogger(__name__)


# Patterns que indicam interesse direto em vaga
INBOUND_INTEREST_PATTERNS = [
    r"\bvaga\b",
    r"\bplant[aã]o\b",
    r"\bescala\b",
    r"\btrabalhar\b.*\bvoc[eê]s\b",
    r"\bvi\b.*\bvaga\b",
    r"\binteress[ae]\b.*\btrabalhar\b",
]


def bootstrap_mode(
    primeira_mensagem: str,
    origem: str,
    campaign_mode: Optional[str] = None,
) -> ConversationMode:
    """
    Determina modo inicial de forma determinística.

    Args:
        primeira_mensagem: Primeira mensagem do médico
        origem: Origem da conversa ("inbound", "campaign:<id>", "manual")
        campaign_mode: Modo da campanha (se origem for campanha)

    Returns:
        ConversationMode inicial
    """
    # 1. Se veio de campanha, herda o modo da campanha
    if origem.startswith("campaign:") and campaign_mode:
        try:
            mode = ConversationMode(campaign_mode)
            logger.info(f"Bootstrap: campanha → {mode.value}")
            return mode
        except ValueError:
            logger.warning(f"Modo de campanha inválido: {campaign_mode}")

    # 2. Inbound com sinal claro de interesse → OFERTA
    if origem == "inbound":
        mensagem_lower = primeira_mensagem.lower()
        for pattern in INBOUND_INTEREST_PATTERNS:
            if re.search(pattern, mensagem_lower):
                logger.info(
                    f"Bootstrap: inbound com interesse → oferta "
                    f"(pattern: {pattern})"
                )
                return ConversationMode.OFERTA

    # 3. Default conservador → DISCOVERY
    logger.info("Bootstrap: default → discovery")
    return ConversationMode.DISCOVERY


def get_mode_source(
    origem: str,
    campaign_id: Optional[str] = None,
) -> str:
    """
    Gera string de mode_source para persistência.

    Returns:
        String no formato: "inbound", "campaign:<id>", "manual"
    """
    if origem == "campaign" and campaign_id:
        return f"campaign:{campaign_id}"
    return origem
```

### Arquivo: `app/services/conversation_mode/repository.py` (atualização)

```python
"""
Repositório para conversation_mode.
"""
import logging
from datetime import datetime
from typing import Optional

from app.services.supabase import supabase
from .types import ConversationMode, ModeInfo

logger = logging.getLogger(__name__)


async def get_conversation_mode(conversa_id: str) -> ModeInfo:
    """
    Busca modo atual da conversa.

    Returns:
        ModeInfo com modo atual (default: discovery)
    """
    try:
        response = (
            supabase.table("conversations")
            .select(
                "id, conversation_mode, mode_updated_at, mode_updated_reason, "
                "mode_source, pending_transition, pending_transition_at"
            )
            .eq("id", conversa_id)
            .single()
            .execute()
        )

        if response.data:
            return ModeInfo.from_row(response.data)

        # Conversa não encontrada - retornar default
        return ModeInfo(
            conversa_id=conversa_id,
            mode=ConversationMode.DISCOVERY,
        )

    except Exception as e:
        logger.error(f"Erro ao buscar conversation_mode: {e}")
        return ModeInfo(
            conversa_id=conversa_id,
            mode=ConversationMode.DISCOVERY,
        )


async def set_conversation_mode(
    conversa_id: str,
    mode: ConversationMode,
    reason: str,
    source: Optional[str] = None,
) -> bool:
    """
    Atualiza modo da conversa.

    Args:
        conversa_id: ID da conversa
        mode: Novo modo
        reason: Motivo da transição (para auditoria)
        source: Origem do modo (inbound, campaign:<id>, manual)

    Returns:
        True se sucesso
    """
    try:
        update_data = {
            "conversation_mode": mode.value,
            "mode_updated_at": datetime.utcnow().isoformat(),
            "mode_updated_reason": reason,
        }
        if source:
            update_data["mode_source"] = source

        response = (
            supabase.table("conversations")
            .update(update_data)
            .eq("id", conversa_id)
            .execute()
        )

        logger.info(f"Mode atualizado: {conversa_id} → {mode.value} ({reason})")
        return True

    except Exception as e:
        logger.error(f"Erro ao atualizar conversation_mode: {e}")
        return False


async def set_pending_transition(
    conversa_id: str,
    pending_mode: ConversationMode,
) -> bool:
    """
    Salva transição pendente de confirmação.

    Args:
        conversa_id: ID da conversa
        pending_mode: Modo aguardando confirmação

    Returns:
        True se sucesso
    """
    try:
        response = (
            supabase.table("conversations")
            .update({
                "pending_transition": pending_mode.value,
                "pending_transition_at": datetime.utcnow().isoformat(),
            })
            .eq("id", conversa_id)
            .execute()
        )

        logger.info(f"Pending transition salva: {conversa_id} → {pending_mode.value}")
        return True

    except Exception as e:
        logger.error(f"Erro ao salvar pending_transition: {e}")
        return False


async def clear_pending_transition(conversa_id: str) -> bool:
    """
    Limpa transição pendente.

    Args:
        conversa_id: ID da conversa

    Returns:
        True se sucesso
    """
    try:
        response = (
            supabase.table("conversations")
            .update({
                "pending_transition": None,
                "pending_transition_at": None,
            })
            .eq("id", conversa_id)
            .execute()
        )

        logger.debug(f"Pending transition limpa: {conversa_id}")
        return True

    except Exception as e:
        logger.error(f"Erro ao limpar pending_transition: {e}")
        return False
```

---

## DoD (Definition of Done)

### Implementação

- [ ] Arquivo `intents.py` criado com:
  - [ ] `DetectedIntent` enum (7 tipos)
  - [ ] Keywords por tipo de intent
  - [ ] `IntentDetector.detect()` retorna `IntentResult`

- [ ] Arquivo `proposer.py` criado com:
  - [ ] `ALLOWED_TRANSITIONS` matriz determinística
  - [ ] `CONFIRMATION_REQUIRED` para transições críticas
  - [ ] `TransitionProposer.propose()` retorna `TransitionProposal`

- [ ] Arquivo `validator.py` criado com:
  - [ ] `TransitionDecision` enum (APPLY, PENDING, CONFIRM, CANCEL, REJECT)
  - [ ] `TransitionValidator.validate()` com suporte a micro-confirmação
  - [ ] Cooldown de 5 minutos entre transições
  - [ ] Timeout de 30 minutos para pending

- [ ] Arquivo `router.py` atualizado com:
  - [ ] 3 camadas: IntentDetector → Proposer → Validator
  - [ ] `_check_confirmation()` para verificar confirmação
  - [ ] `_apply_decision()` para executar resultado

- [ ] Arquivo `repository.py` atualizado com:
  - [ ] `set_pending_transition()`
  - [ ] `clear_pending_transition()`

- [ ] Arquivo `logging.py` criado com:
  - [ ] `ModeDecisionLog` dataclass
  - [ ] `log_mode_decision()` - black box recorder
  - [ ] `log_violation_attempt()` - tentativas de violação
  - [ ] `get_capabilities_version()` - hash para versionamento

- [ ] Arquivo `bootstrap.py` criado com:
  - [ ] `INBOUND_INTEREST_PATTERNS` - patterns de interesse
  - [ ] `bootstrap_mode()` - modo inicial determinístico
  - [ ] `get_mode_source()` - gera string de origem

### Testes Unitários

- [ ] Teste: intent INTERESSE_VAGA detectado corretamente
  ```python
  def test_detect_interesse_vaga():
      detector = IntentDetector()
      result = detector.detect("Tem vaga de cardiologia?")
      assert result.intent == DetectedIntent.INTERESSE_VAGA
      assert result.confidence >= 0.7
  ```

- [ ] Teste: discovery → oferta requer confirmação
  ```python
  def test_discovery_to_oferta_needs_confirmation():
      proposer = TransitionProposer()
      intent = IntentResult(
          intent=DetectedIntent.INTERESSE_VAGA,
          confidence=0.8,
          evidence="tem vaga"
      )
      proposal = proposer.propose(intent, ConversationMode.DISCOVERY)
      assert proposal.should_transition
      assert proposal.to_mode == ConversationMode.OFERTA
      assert proposal.needs_confirmation is True
  ```

- [ ] Teste: transição não permitida é bloqueada
  ```python
  def test_forbidden_transition_blocked():
      proposer = TransitionProposer()
      intent = IntentResult(
          intent=DetectedIntent.VOLTANDO,
          confidence=0.7,
          evidence="voltei"
      )
      # DISCOVERY → FOLLOWUP não está em ALLOWED_TRANSITIONS
      proposal = proposer.propose(intent, ConversationMode.DISCOVERY)
      assert proposal.should_transition is False
      assert "not_allowed" in proposal.trigger
  ```

- [ ] Teste: pending confirmada aplica transição
  ```python
  def test_pending_confirmed_applies():
      validator = TransitionValidator()
      proposal = TransitionProposal(
          should_transition=False,  # Não importa
          from_mode=ConversationMode.DISCOVERY,
          to_mode=None,
          needs_confirmation=False,
          is_automatic=False,
          trigger="none",
          evidence="",
          confidence=0.0,
      )
      result = validator.validate(
          proposal=proposal,
          pending_transition=ConversationMode.OFERTA,
          pending_transition_at=datetime.utcnow(),
          mensagem_confirma=True,
      )
      assert result.decision == TransitionDecision.CONFIRM
      assert result.final_mode == ConversationMode.OFERTA
  ```

- [ ] Teste: pending timeout cancela
  ```python
  def test_pending_timeout_cancels():
      validator = TransitionValidator()
      result = validator.validate(
          proposal=...,
          pending_transition=ConversationMode.OFERTA,
          pending_transition_at=datetime.utcnow() - timedelta(minutes=60),
          mensagem_confirma=False,
      )
      assert result.decision == TransitionDecision.CANCEL
  ```

- [ ] Teste: bootstrap inbound com "vaga" → oferta
  ```python
  def test_bootstrap_inbound_with_vaga():
      mode = bootstrap_mode(
          primeira_mensagem="Oi, vi uma vaga de cardiologia",
          origem="inbound"
      )
      assert mode == ConversationMode.OFERTA
  ```

- [ ] Teste: bootstrap inbound sem interesse → discovery
  ```python
  def test_bootstrap_inbound_cold():
      mode = bootstrap_mode(
          primeira_mensagem="Oi, tudo bem?",
          origem="inbound"
      )
      assert mode == ConversationMode.DISCOVERY
  ```

- [ ] Teste: bootstrap campanha herda modo
  ```python
  def test_bootstrap_campaign():
      mode = bootstrap_mode(
          primeira_mensagem="qualquer coisa",
          origem="campaign:abc-123",
          campaign_mode="oferta"
      )
      assert mode == ConversationMode.OFERTA
  ```

### Validação

- [ ] Log de intent detectado em cada mensagem
- [ ] Log de proposta de transição
- [ ] Log de decisão final (APPLY, PENDING, etc)
- [ ] Cooldown evita flip-flop
- [ ] Micro-confirmação funciona corretamente
- [ ] Pending expira após 30 minutos

### Não fazer neste epic

- [ ] NÃO usar LLM para detecção de intent (V1 usa keywords)
- [ ] NÃO integrar no agente (E04)
- [ ] NÃO criar histórico de transições (log é suficiente)

---

## Exemplo de Uso

```python
from app.services.conversation_mode import get_mode_router

router = get_mode_router()

# Processar mensagem
mode_info = await router.process(
    conversa_id="abc-123",
    mensagem="Oi, tem vaga de cardiologia?",
    last_message_at=datetime.utcnow() - timedelta(hours=2),
)

# Se discovery → oferta, vai retornar PENDING na primeira vez
# Julia faz micro-confirmação
# Na próxima mensagem positiva, confirma a transição
print(f"Modo atual: {mode_info.mode.value}")
```

---

## Próximo

Após E03 concluído: [E04: Integração](./epic-04-integracao.md)
