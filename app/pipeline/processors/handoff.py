"""
Processadores de handoff.

Sprint 44 T03.3: Módulo separado.
"""

import logging
from typing import Optional

from ..base import PreProcessor, ProcessorContext, ProcessorResult
from app.services.handoff_detector import detectar_trigger_handoff

logger = logging.getLogger(__name__)


class HandoffTriggerProcessor(PreProcessor):
    """
    Detecta triggers de handoff para humano.

    Prioridade: 50
    """

    name = "handoff_trigger"
    priority = 50

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        if not context.mensagem_texto:
            return ProcessorResult(success=True)

        trigger = detectar_trigger_handoff(context.mensagem_texto)

        if not trigger:
            return ProcessorResult(success=True)

        logger.info(f"Trigger de handoff detectado: {trigger['tipo']}")

        from app.services.handoff import iniciar_handoff

        await iniciar_handoff(
            conversa_id=context.conversa["id"],
            cliente_id=context.medico["id"],
            motivo=trigger["motivo"],
            trigger_type=trigger["tipo"],
        )

        return ProcessorResult(
            success=True,
            should_continue=False,  # Nao gera resposta automatica
            metadata={"handoff_trigger": trigger["tipo"]},
        )


class HandoffKeywordProcessor(PreProcessor):
    """
    Detecta keywords de confirmacao de handoff.

    Divulgadores podem responder via WhatsApp com keywords como
    "confirmado" ou "nao fechou" ao inves de clicar no link.

    Prioridade: 55 (entre HandoffTriggerProcessor e HumanControlProcessor)

    Sprint 20 - E06.
    Sprint 44 T06.6: Pre-compilar regex patterns.
    """

    name = "handoff_keyword"
    priority = 55

    # Keywords de confirmacao (case insensitive)
    # Sprint 44 T06.6: Padrões pré-compilados no nível de classe
    _PATTERNS_CONFIRMED = None
    _PATTERNS_NOT_CONFIRMED = None

    @classmethod
    def _get_compiled_patterns(cls):
        """Retorna padrões compilados (lazy initialization)."""
        import re

        if cls._PATTERNS_CONFIRMED is None:
            cls._PATTERNS_CONFIRMED = [
                re.compile(r"\bconfirmado\b", re.IGNORECASE),
                re.compile(r"\bfechou\b", re.IGNORECASE),
                re.compile(r"\bfechado\b", re.IGNORECASE),
                re.compile(r"\bconfirmo\b", re.IGNORECASE),
                re.compile(r"\bok\s*,?\s*fechou\b", re.IGNORECASE),
                re.compile(r"\bfechamos\b", re.IGNORECASE),
                re.compile(r"\bcontrato\s+fechado\b", re.IGNORECASE),
                re.compile(r"\bpode\s+confirmar\b", re.IGNORECASE),
                re.compile(r"\btudo\s+certo\b", re.IGNORECASE),
            ]
            cls._PATTERNS_NOT_CONFIRMED = [
                re.compile(r"\bnao\s+fechou\b", re.IGNORECASE),
                re.compile(r"\bn[aã]o\s+fechou\b", re.IGNORECASE),
                re.compile(r"\bnao\s+deu\b", re.IGNORECASE),
                re.compile(r"\bn[aã]o\s+deu\b", re.IGNORECASE),
                re.compile(r"\bdesistiu\b", re.IGNORECASE),
                re.compile(r"\bcancelou\b", re.IGNORECASE),
                re.compile(r"\bnao\s+vai\s+dar\b", re.IGNORECASE),
                re.compile(r"\bn[aã]o\s+vai\s+dar\b", re.IGNORECASE),
                re.compile(r"\bperdeu\b", re.IGNORECASE),
                re.compile(r"\bnao\s+confirmou\b", re.IGNORECASE),
                re.compile(r"\bn[aã]o\s+confirmou\b", re.IGNORECASE),
                re.compile(r"\bnao\s+rolou\b", re.IGNORECASE),
                re.compile(r"\bn[aã]o\s+rolou\b", re.IGNORECASE),
            ]
        return cls._PATTERNS_CONFIRMED, cls._PATTERNS_NOT_CONFIRMED

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        from app.services.external_handoff.repository import buscar_handoff_pendente_por_telefone
        from app.services.external_handoff.confirmacao import processar_confirmacao
        from app.services.business_events import emit_event, EventType, EventSource, BusinessEvent

        # Pular se nao for mensagem de texto
        if not context.mensagem_texto:
            return ProcessorResult(success=True)

        telefone = context.telefone
        mensagem = context.mensagem_texto.lower()

        # Buscar handoff pendente para este telefone
        handoff = await buscar_handoff_pendente_por_telefone(telefone)

        if not handoff:
            # Nao e divulgador com handoff pendente
            return ProcessorResult(success=True)

        logger.info(f"Telefone {telefone[-4:]} tem handoff pendente: {handoff['id'][:8]}")

        # Detectar keyword
        action = self._detectar_keyword(mensagem)

        if not action:
            # Nao detectou keyword, deixar Julia responder normalmente
            logger.debug("Nenhuma keyword detectada na mensagem do divulgador")
            return ProcessorResult(success=True)

        logger.info(f"Keyword detectada: action={action}")

        # Processar confirmacao
        try:
            await processar_confirmacao(
                handoff=handoff,
                action=action,
                confirmed_by="keyword",
            )

            # Emitir evento especifico de keyword
            event = BusinessEvent(
                event_type=EventType.HANDOFF_CONFIRM_CLICKED,
                source=EventSource.BACKEND,
                event_props={
                    "handoff_id": handoff["id"],
                    "action": action,
                    "via": "keyword",
                    "mensagem_original": context.mensagem_texto[:100],
                },
                dedupe_key=f"handoff_keyword:{handoff['id']}:{action}",
            )
            await emit_event(event)

            # Gerar resposta de agradecimento (usa template do banco)
            resposta = await self._gerar_resposta_agradecimento(action)

            logger.info(f"Handoff {handoff['id'][:8]} processado via keyword: {action}")

            return ProcessorResult(
                success=True,
                should_continue=False,  # Nao continua para o agente
                response=resposta,
                metadata={
                    "handoff_keyword": True,
                    "handoff_id": handoff["id"],
                    "action": action,
                },
            )

        except Exception as e:
            logger.error(f"Erro ao processar keyword de handoff: {e}")
            # Deixar Julia responder normalmente
            return ProcessorResult(success=True)

    def _detectar_keyword(self, mensagem: str) -> Optional[str]:
        """Detecta keyword na mensagem.

        Sprint 44 T06.6: Usa padrões pré-compilados para performance.
        """
        patterns_confirmed, patterns_not_confirmed = self._get_compiled_patterns()

        # Verificar NOT_CONFIRMED primeiro (mais especifico)
        for pattern in patterns_not_confirmed:
            if pattern.search(mensagem):
                return "not_confirmed"

        # Verificar CONFIRMED
        for pattern in patterns_confirmed:
            if pattern.search(mensagem):
                return "confirmed"

        return None

    async def _gerar_resposta_agradecimento(self, action: str) -> str:
        """
        Gera resposta de agradecimento para o divulgador.

        Usa templates do banco de dados com fallback para mensagens legadas.
        """
        from app.services.templates import get_template

        if action == "confirmed":
            template = await get_template("confirmacao_aceite")
            if template:
                return template
            return (
                "Anotado! Obrigada pela confirmacao.\n\n"
                "Ja atualizei aqui no sistema. Qualquer coisa me avisa!"
            )
        else:
            template = await get_template("confirmacao_recusa")
            if template:
                return template
            return (
                "Entendido! Ja atualizei aqui.\n\n"
                "Obrigada por avisar. Se surgir outra oportunidade, te procuro!"
            )
