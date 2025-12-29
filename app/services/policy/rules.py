"""
Regras de produção do Policy Engine.

IMPORTANTE:
- Regras são funções PURAS (sem I/O)
- Primeira regra que retorna não-None vence
- rule_default é o fallback (sempre retorna)

Sprint 15 - Policy Engine
"""
from datetime import datetime
from typing import Optional

from .types import (
    DoctorState, PolicyDecision, PrimaryAction, Tone,
    PermissionState, ObjectionSeverity, LifecycleStage,
)


def rule_opted_out(state: DoctorState, **kwargs) -> Optional[PolicyDecision]:
    """
    Regra: médico fez opt-out → não contatar.

    Opt-out é TERMINAL. Não há volta automática.
    """
    if state.permission_state == PermissionState.OPTED_OUT:
        return PolicyDecision(
            primary_action=PrimaryAction.WAIT,
            allowed_actions=[],
            forbidden_actions=[],
            forbid_all=True,  # Sprint 16 Fix: usar forbid_all ao invés de ["*"]
            tone=Tone.LEVE,  # Não vai responder, mas precisa de um valor
            requires_human=False,
            constraints_text="MÉDICO FEZ OPT-OUT. NÃO RESPONDER.",
            reasoning="permission_state=opted_out (terminal)"
        )
    return None


def rule_cooling_off(state: DoctorState, **kwargs) -> Optional[PolicyDecision]:
    """
    Regra: médico em cooling off → aguardar prazo.

    Durante cooling_off, Julia ainda pode responder se médico
    iniciar contato, mas com tom cauteloso.
    """
    if state.permission_state == PermissionState.COOLING_OFF:
        if state.cooling_off_until:
            now = datetime.utcnow()
            # Converter se for string
            until = state.cooling_off_until
            if isinstance(until, str):
                try:
                    until = datetime.fromisoformat(until.replace("Z", "+00:00"))
                    if until.tzinfo:
                        until = until.replace(tzinfo=None)
                except ValueError:
                    until = now

            if now < until:
                days_left = (until - now).days
                return PolicyDecision(
                    primary_action=PrimaryAction.FOLLOWUP,
                    allowed_actions=["respond_minimal", "clarify", "apologize"],
                    forbidden_actions=["proactive_contact", "offer", "followup", "pressure"],
                    tone=Tone.CAUTELOSO,
                    requires_human=False,
                    constraints_text=(
                        f"MÉDICO EM PAUSA ({days_left} dias restantes).\n"
                        "- NÃO inicie contato proativo\n"
                        "- Se ele mandou mensagem, responda de forma mínima e cautelosa\n"
                        "- NÃO ofereça vagas"
                    ),
                    reasoning=f"cooling_off até {until.isoformat()}"
                )
    return None


def rule_grave_objection(state: DoctorState, **kwargs) -> Optional[PolicyDecision]:
    """
    Regra: objeção grave ativa → handoff para humano.
    """
    if (
        state.has_unresolved_objection()
        and state.objection_severity == ObjectionSeverity.GRAVE
    ):
        return PolicyDecision(
            primary_action=PrimaryAction.HANDOFF,
            allowed_actions=["acknowledge", "transfer", "apologize"],
            forbidden_actions=["offer", "negotiate", "insist", "pressure"],
            tone=Tone.CRISE,
            requires_human=True,
            constraints_text=(
                "SITUAÇÃO CRÍTICA. Médico tem objeção grave não resolvida.\n"
                "- Apenas reconheça a situação\n"
                "- Transfira para humano\n"
                "- NÃO tente resolver sozinha"
            ),
            reasoning=f"objection_severity=grave, tipo={state.active_objection}"
        )
    return None


def rule_high_objection(state: DoctorState, **kwargs) -> Optional[PolicyDecision]:
    """
    Regra: objeção HIGH ativa → cautela extra.
    """
    if (
        state.has_unresolved_objection()
        and state.objection_severity == ObjectionSeverity.HIGH
    ):
        return PolicyDecision(
            primary_action=PrimaryAction.FOLLOWUP,
            allowed_actions=["clarify", "apologize", "offer_help", "ask"],
            forbidden_actions=["offer", "pressure", "insist"],
            tone=Tone.CAUTELOSO,
            requires_human=False,
            constraints_text=(
                "ATENÇÃO: Médico tem objeção pendente (alta severidade).\n"
                "- Seja extra cuidadosa\n"
                "- Esclareça dúvidas antes de oferecer\n"
                "- Se escalar, transfira para humano"
            ),
            reasoning=f"objection_severity=high, tipo={state.active_objection}"
        )
    return None


def rule_medium_objection(state: DoctorState, **kwargs) -> Optional[PolicyDecision]:
    """
    Regra: objeção MEDIUM ativa → tratar com cuidado.
    """
    if (
        state.has_unresolved_objection()
        and state.objection_severity == ObjectionSeverity.MEDIUM
    ):
        return PolicyDecision(
            primary_action=PrimaryAction.FOLLOWUP,
            allowed_actions=["clarify", "negotiate", "offer_alternative", "ask"],
            forbidden_actions=["pressure", "insist", "ignore_objection"],
            tone=Tone.DIRETO,
            requires_human=False,
            constraints_text=(
                f"Médico tem objeção pendente: {state.active_objection}\n"
                "- Trate a objeção antes de continuar\n"
                "- Pode negociar ou oferecer alternativas\n"
                "- NÃO pressione"
            ),
            reasoning=f"objection_severity=medium, tipo={state.active_objection}"
        )
    return None


def rule_new_doctor_first_contact(
    state: DoctorState,
    is_first_message: bool = False,
    conversa_status: str = "active",
    **kwargs
) -> Optional[PolicyDecision]:
    """
    Regra: médico novo, primeira mensagem → discovery.
    """
    if (
        state.lifecycle_stage == LifecycleStage.NOVO
        and is_first_message
        and conversa_status == "active"
    ):
        return PolicyDecision(
            primary_action=PrimaryAction.DISCOVERY,
            allowed_actions=["present_julia", "ask_specialty", "build_rapport", "ask_interest"],
            forbidden_actions=["offer_shift", "negotiate_value", "ask_docs", "pressure"],
            tone=Tone.LEVE,
            requires_human=False,
            constraints_text=(
                "PRIMEIRO CONTATO com médico novo.\n"
                "- Apresente-se de forma leve\n"
                "- Entenda o perfil e interesse\n"
                "- NÃO ofereça vagas ainda\n"
                "- NÃO peça documentos"
            ),
            reasoning="lifecycle=novo, first_message=True"
        )
    return None


def rule_silence_reactivation(
    state: DoctorState,
    conversa_status: str = "active",
    conversa_last_message_at: Optional[datetime] = None,
    **kwargs
) -> Optional[PolicyDecision]:
    """
    Regra: silêncio > 7d + temperatura quente + Julia falou por último → reativação.

    IMPORTANTE: Exige conversa ativa para evitar falso positivo.
    """
    # Só aplica se conversa está ativa
    if conversa_status != "active":
        return None

    # Precisa ter enviado mensagem
    if not state.last_outbound_at:
        return None

    # Converter se for string
    last_out = state.last_outbound_at
    if isinstance(last_out, str):
        try:
            last_out = datetime.fromisoformat(last_out.replace("Z", "+00:00"))
            if last_out.tzinfo:
                last_out = last_out.replace(tzinfo=None)
        except ValueError:
            return None

    now = datetime.utcnow()
    days_since_outbound = (now - last_out).days

    # Julia falou por último?
    julia_spoke_last = True
    if state.last_inbound_at:
        last_in = state.last_inbound_at
        if isinstance(last_in, str):
            try:
                last_in = datetime.fromisoformat(last_in.replace("Z", "+00:00"))
                if last_in.tzinfo:
                    last_in = last_in.replace(tzinfo=None)
            except ValueError:
                pass
            else:
                julia_spoke_last = last_out > last_in

    # Condições: 7+ dias, temperatura >= 0.3, Julia falou por último
    if (
        days_since_outbound >= 7
        and state.temperature >= 0.3
        and julia_spoke_last
    ):
        return PolicyDecision(
            primary_action=PrimaryAction.REACTIVATION,
            allowed_actions=["gentle_followup", "offer_new_shift", "check_in", "ask_availability"],
            forbidden_actions=["pressure", "urgent_tone", "guilt_trip"],
            tone=Tone.LEVE,
            requires_human=False,
            constraints_text=(
                f"REATIVAÇÃO: Médico não responde há {days_since_outbound} dias.\n"
                "- Seja gentil e natural\n"
                "- Ofereça algo novo/diferente\n"
                "- NÃO pressione ou cobre resposta"
            ),
            reasoning=f"silence={days_since_outbound}d, temp={state.temperature}, julia_last=True"
        )

    return None


def rule_cold_temperature(state: DoctorState, **kwargs) -> Optional[PolicyDecision]:
    """
    Regra: temperatura fria (< 0.33) → conservador.
    """
    if state.temperature < 0.33 and state.permission_state == PermissionState.ACTIVE:
        return PolicyDecision(
            primary_action=PrimaryAction.FOLLOWUP,
            allowed_actions=["respond", "clarify", "ask", "gentle_offer"],
            forbidden_actions=["pressure", "insist", "multiple_offers"],
            tone=Tone.CAUTELOSO,
            requires_human=False,
            constraints_text=(
                "TEMPERATURA FRIA: Médico pouco engajado.\n"
                "- Seja conservadora nas abordagens\n"
                "- NÃO ofereça múltiplas vagas\n"
                "- Foque em entender o que ele precisa"
            ),
            reasoning=f"temperature={state.temperature} (cold)"
        )
    return None


def rule_hot_temperature(state: DoctorState, **kwargs) -> Optional[PolicyDecision]:
    """
    Regra: temperatura quente (> 0.66) + ativo → pode oferecer.
    """
    if (
        state.temperature > 0.66
        and state.permission_state == PermissionState.ACTIVE
        and not state.has_unresolved_objection()
    ):
        return PolicyDecision(
            primary_action=PrimaryAction.OFFER,
            allowed_actions=["offer", "respond", "ask", "clarify", "negotiate"],
            forbidden_actions=["pressure", "aggressive_upsell"],
            tone=Tone.LEVE,
            requires_human=False,
            constraints_text=(
                "MÉDICO ENGAJADO: Temperatura alta, sem objeções.\n"
                "- Pode oferecer vagas\n"
                "- Seja leve e amigável\n"
                "- Pode negociar se necessário"
            ),
            reasoning=f"temperature={state.temperature} (hot), no_objection"
        )
    return None


def rule_default(state: DoctorState, **kwargs) -> PolicyDecision:
    """
    Regra default: conservadora.

    IMPORTANTE: Defaults são CONSERVADORES.
    - Offer só se permission_state == ACTIVE e sem bloqueios
    - Caso contrário, apenas followup básico
    """
    # Determinar tom baseado em temperatura
    if state.temperature >= 0.6:
        tone = Tone.LEVE
    elif state.temperature >= 0.3:
        tone = Tone.DIRETO
    else:
        tone = Tone.CAUTELOSO

    # Ações permitidas dependem do estado
    if state.permission_state == PermissionState.ACTIVE and state.is_contactable():
        # Médico ativo e sem bloqueios → pode responder e perguntar
        # Mas NÃO oferecer proativamente se não passou por regra específica
        allowed = ["respond", "ask", "clarify", "followup"]
        forbidden = ["pressure", "insist"]
        constraints = (
            "MODO PADRÃO: Médico está ativo.\n"
            "- Responda normalmente\n"
            "- Pode oferecer SE ele perguntar ou demonstrar interesse\n"
            "- NÃO pressione"
        )
    elif state.permission_state == PermissionState.INITIAL:
        # Contato inicial - ainda conhecendo
        allowed = ["respond", "clarify", "ask", "build_rapport"]
        forbidden = ["offer", "pressure", "insist", "proactive_contact"]
        constraints = (
            "CONTATO INICIAL: Ainda conhecendo o médico.\n"
            "- Responda ao que ele perguntar\n"
            "- Construa rapport\n"
            "- NÃO ofereça vagas ainda"
        )
    else:
        # Conservador: apenas responder, não oferecer proativamente
        allowed = ["respond", "clarify", "ask"]
        forbidden = ["offer", "pressure", "insist", "proactive_contact"]
        constraints = (
            "MODO CONSERVADOR: Médico não está em estado 'active' confirmado.\n"
            "- Responda ao que ele perguntar\n"
            "- NÃO ofereça vagas proativamente"
        )

    return PolicyDecision(
        primary_action=PrimaryAction.FOLLOWUP,
        allowed_actions=allowed,
        forbidden_actions=forbidden,
        tone=tone,
        requires_human=False,
        constraints_text=constraints,
        reasoning=f"default_rule, permission={state.permission_state.value}, temp={state.temperature}"
    )


# Ordem de avaliação (primeira que retorna não-None vence)
# IMPORTANTE: Ordem importa! Mais restritivas primeiro.
RULES_IN_ORDER = [
    rule_opted_out,           # Terminal
    rule_cooling_off,         # Bloqueio temporário
    rule_grave_objection,     # Crise → handoff
    rule_high_objection,      # Atenção extra
    rule_medium_objection,    # Objeção tratável
    # rule_new_doctor_first_contact precisa de parâmetros extras (avaliada separadamente)
    rule_silence_reactivation,
    rule_cold_temperature,    # Médico frio
    rule_hot_temperature,     # Médico quente
    # rule_default é fallback (avaliada separadamente)
]
