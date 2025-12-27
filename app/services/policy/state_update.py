"""
StateUpdate - Atualiza doctor_state baseado em eventos.

REGRAS CRÍTICAS:
1. Objeção NÃO é limpa automaticamente - persiste até resolução explícita
2. Opt-out é terminal (opted_out), não vira cooling_off
3. Cooling_off é para atrito/risco, não para quem pediu para parar

Sprint 15 - Policy Engine
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.services.classificacao.severity_mapper import (
    map_severity, is_opt_out, ObjectionSeverity
)
from .types import DoctorState, PermissionState, TemperatureTrend, LifecycleStage

logger = logging.getLogger(__name__)


class StateUpdate:
    """Atualiza doctor_state baseado em eventos."""

    def on_inbound_message(
        self,
        state: DoctorState,
        mensagem: str,
        objecao_detectada: Optional[dict],
    ) -> dict:
        """
        Atualiza estado quando médico envia mensagem.

        Args:
            state: Estado atual
            mensagem: Texto da mensagem
            objecao_detectada: ResultadoDeteccao do detector (ou None)

        Returns:
            Dict com campos a atualizar no banco
        """
        updates = {
            "last_inbound_at": datetime.utcnow().isoformat(),
        }

        # === TEMPERATURA ===
        # Médico respondeu → aquece temperatura
        new_temp = min(1.0, state.temperature + 0.1)
        if new_temp != state.temperature:
            updates["temperature"] = round(new_temp, 2)
            updates["temperature_trend"] = TemperatureTrend.WARMING.value

        # === PERMISSION STATE ===
        # Se estava em 'none' ou 'initial', promove para 'active'
        # (exceto se detectar opt-out abaixo)
        if state.permission_state in (PermissionState.NONE, PermissionState.INITIAL):
            updates["permission_state"] = PermissionState.ACTIVE.value

        # Se estava em cooling_off e voltou a falar, volta para active
        if state.permission_state == PermissionState.COOLING_OFF:
            updates["permission_state"] = PermissionState.ACTIVE.value
            updates["cooling_off_until"] = None

        # === LIFECYCLE ===
        # Se estava em 'prospecting' ou 'novo', promove para 'engaged'
        if state.lifecycle_stage in (LifecycleStage.NOVO, LifecycleStage.PROSPECTING):
            updates["lifecycle_stage"] = LifecycleStage.ENGAGED.value

        # === OBJEÇÃO ===
        if objecao_detectada and objecao_detectada.get("tem_objecao"):
            tipo = objecao_detectada.get("tipo", "")
            # Extrair valor se for Enum
            if hasattr(tipo, "value"):
                tipo = tipo.value

            subtipo = objecao_detectada.get("subtipo")

            # Calcular severidade
            severity = map_severity(tipo, subtipo, mensagem)

            # Verificar se é opt-out (terminal)
            if is_opt_out(tipo, mensagem):
                updates["permission_state"] = PermissionState.OPTED_OUT.value
                updates["active_objection"] = "opt_out"
                updates["objection_severity"] = ObjectionSeverity.GRAVE.value
                updates["objection_detected_at"] = datetime.utcnow().isoformat()
                # Limpar cooling_off se tinha
                updates["cooling_off_until"] = None
                logger.warning(f"OPT-OUT detectado para {state.cliente_id}")

            # Objeção grave (não opt-out) → cooling_off
            elif severity == ObjectionSeverity.GRAVE:
                updates["permission_state"] = PermissionState.COOLING_OFF.value
                updates["cooling_off_until"] = (datetime.utcnow() + timedelta(days=7)).isoformat()
                updates["active_objection"] = tipo
                updates["objection_severity"] = severity.value
                updates["objection_detected_at"] = datetime.utcnow().isoformat()
                logger.warning(f"Objeção GRAVE para {state.cliente_id}: {tipo}")

            # Objeção não-grave → registrar mas não mudar permission
            else:
                updates["active_objection"] = tipo
                updates["objection_severity"] = severity.value
                updates["objection_detected_at"] = datetime.utcnow().isoformat()
                logger.info(f"Objeção {severity.value} para {state.cliente_id}: {tipo}")

        # IMPORTANTE: NÃO limpar objeção se não detectou nova
        # Objeção persiste até resolução explícita via resolve_objection()
        # Apenas atualizar trend se não houver objeção nova
        elif state.has_unresolved_objection():
            # Médico respondeu sem nova objeção → trend pode melhorar
            # mas NÃO limpa a objeção
            updates["temperature_trend"] = TemperatureTrend.STABLE.value

        return updates

    def on_outbound_message(
        self,
        state: DoctorState,
        actor: str = "julia",
    ) -> dict:
        """
        Atualiza estado após Julia/humano enviar mensagem.

        Args:
            state: Estado atual
            actor: 'julia' ou 'humano'

        Returns:
            Dict com campos a atualizar
        """
        updates = {
            "last_outbound_at": datetime.utcnow().isoformat(),
            "last_outbound_actor": actor,
            "contact_count_7d": state.contact_count_7d + 1,
        }

        # Se é primeiro contato e state é NONE, promove para INITIAL
        if state.permission_state == PermissionState.NONE:
            updates["permission_state"] = PermissionState.INITIAL.value

        # Se lifecycle é NOVO e Julia iniciou contato, vira PROSPECTING
        if state.lifecycle_stage == LifecycleStage.NOVO:
            updates["lifecycle_stage"] = LifecycleStage.PROSPECTING.value

        return updates

    def decay_temperature(
        self,
        state: DoctorState,
        now: Optional[datetime] = None,
    ) -> dict:
        """
        Decai temperatura por inatividade (para job batch).

        Usa last_decay_at para ser idempotente.

        Args:
            state: Estado atual
            now: Timestamp atual (para testes)

        Returns:
            Dict com campos a atualizar (vazio se nada a fazer)
        """
        now = now or datetime.utcnow()

        # Não decair opt-out
        if state.permission_state == PermissionState.OPTED_OUT:
            return {}

        # Não decair se já está em 0
        if state.temperature <= 0:
            return {}

        # Calcular dias desde último decay OU último inbound
        reference = state.last_decay_at or state.last_inbound_at
        if not reference:
            return {}

        # Converter se for string
        if isinstance(reference, str):
            try:
                reference = datetime.fromisoformat(reference.replace("Z", "+00:00"))
            except ValueError:
                return {}

        # Remover timezone se necessário para comparação
        if reference.tzinfo is not None:
            reference = reference.replace(tzinfo=None)

        days_since = (now - reference).days

        if days_since <= 0:
            return {}

        # Decay: -0.05 por dia de inatividade
        decay_amount = min(state.temperature, days_since * 0.05)

        if decay_amount <= 0:
            return {}

        new_temp = max(0.0, state.temperature - decay_amount)

        logger.debug(
            f"Decay temperatura {state.cliente_id}: "
            f"{state.temperature} -> {new_temp} ({days_since} dias)"
        )

        return {
            "temperature": round(new_temp, 2),
            "temperature_trend": TemperatureTrend.COOLING.value,
            "last_decay_at": now.isoformat(),
        }

    def on_objection_resolved(self, state: DoctorState) -> dict:
        """
        Marca objeção como resolvida.

        Chamado quando:
        - Humano marca como resolvido via Slack/Chatwoot
        - Médico confirma resolução explicitamente
        - Ação pendente foi concluída

        NÃO limpa active_objection nem objection_severity - mantém histórico.
        """
        if not state.has_unresolved_objection():
            return {}

        logger.info(f"Objeção resolvida para {state.cliente_id}: {state.active_objection}")

        return {
            "objection_resolved_at": datetime.utcnow().isoformat(),
            # NÃO limpa active_objection - mantém histórico
            # NÃO limpa objection_severity - mantém histórico
        }

    def on_positive_signal(self, state: DoctorState, signal_type: str) -> dict:
        """
        Processa sinal positivo do médico.

        Args:
            state: Estado atual
            signal_type: Tipo de sinal (ex: 'interesse', 'pediu_vaga', 'agradeceu')

        Returns:
            Dict com campos a atualizar
        """
        updates = {}

        # Aquece temperatura
        new_temp = min(1.0, state.temperature + 0.15)
        if new_temp != state.temperature:
            updates["temperature"] = round(new_temp, 2)
            updates["temperature_trend"] = TemperatureTrend.WARMING.value

        # Atualiza lifecycle baseado no sinal
        if signal_type == "pediu_vaga" and state.lifecycle_stage not in (
            LifecycleStage.QUALIFIED, LifecycleStage.ACTIVE
        ):
            updates["lifecycle_stage"] = LifecycleStage.QUALIFIED.value

        logger.debug(f"Sinal positivo '{signal_type}' para {state.cliente_id}")

        return updates

    def on_handoff_completed(self, state: DoctorState, resolved: bool = True) -> dict:
        """
        Atualiza estado após handoff ser resolvido.

        Args:
            state: Estado atual
            resolved: Se foi resolvido positivamente

        Returns:
            Dict com campos a atualizar
        """
        updates = {}

        if resolved:
            # Handoff resolvido positivamente
            if state.has_unresolved_objection():
                updates = self.on_objection_resolved(state)

            # Se estava em cooling_off, pode voltar para active
            if state.permission_state == PermissionState.COOLING_OFF:
                updates["permission_state"] = PermissionState.ACTIVE.value
                updates["cooling_off_until"] = None
        else:
            # Handoff não resolvido - manter estado atual
            pass

        return updates


# Instância singleton para uso conveniente
state_updater = StateUpdate()
