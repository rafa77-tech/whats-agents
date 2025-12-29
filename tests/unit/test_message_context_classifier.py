"""
Testes unitarios para message_context_classifier.

Sprint 22 - Responsividade Inteligente
"""
import pytest

from app.services.message_context_classifier import (
    ContextType,
    ContextClassification,
    classificar_contexto,
    classificar_por_outbound_context,
    _detectar_aceite,
    _detectar_pergunta,
)
from app.services.guardrails.types import (
    OutboundContext,
    OutboundMethod,
    OutboundChannel,
    ActorType,
)


class TestDetectarAceite:
    """Testes de deteccao de aceite."""

    def test_detecta_aceito(self):
        """Detecta 'aceito' como aceite."""
        assert _detectar_aceite("aceito") is True
        assert _detectar_aceite("pode reservar, aceito") is True

    def test_detecta_fechado(self):
        """Detecta 'fechado' como aceite."""
        assert _detectar_aceite("fechado!") is True
        assert _detectar_aceite("Fechou, pode contar comigo") is True

    def test_detecta_pode_reservar(self):
        """Detecta 'pode reservar' como aceite."""
        assert _detectar_aceite("pode reservar pra mim") is True

    def test_detecta_bora(self):
        """Detecta 'bora', 'vamos', 'topo' como aceite."""
        assert _detectar_aceite("bora") is True
        assert _detectar_aceite("vamos nessa") is True
        assert _detectar_aceite("topo sim") is True

    def test_detecta_ok_sim(self):
        """Detecta 'ok', 'sim', 'blz' como aceite."""
        assert _detectar_aceite("ok") is True
        assert _detectar_aceite("sim") is True
        assert _detectar_aceite("blz") is True

    def test_nao_detecta_negacao(self):
        """Nao detecta aceite quando tem negacao."""
        assert _detectar_aceite("nao aceito") is False
        assert _detectar_aceite("nao posso aceitar") is False
        assert _detectar_aceite("dessa vez nao") is False

    def test_nao_detecta_texto_normal(self):
        """Nao detecta aceite em texto normal."""
        assert _detectar_aceite("qual o valor?") is False
        assert _detectar_aceite("que dia seria?") is False


class TestDetectarPergunta:
    """Testes de deteccao de pergunta."""

    def test_detecta_interrogacao(self):
        """Detecta interrogacao."""
        assert _detectar_pergunta("qual o valor?") is True
        assert _detectar_pergunta("tem vaga?") is True

    def test_detecta_palavras_pergunta(self):
        """Detecta palavras de pergunta."""
        assert _detectar_pergunta("qual hospital") is True
        assert _detectar_pergunta("quanto paga") is True
        assert _detectar_pergunta("quando seria") is True
        assert _detectar_pergunta("onde fica") is True
        assert _detectar_pergunta("como funciona") is True

    def test_detecta_me_explica(self):
        """Detecta 'me explica', 'me fala', 'me conta'."""
        assert _detectar_pergunta("me explica melhor") is True
        assert _detectar_pergunta("me fala mais") is True
        assert _detectar_pergunta("me conta detalhes") is True

    def test_nao_detecta_afirmacao(self):
        """Nao detecta pergunta em afirmacao."""
        assert _detectar_pergunta("ok pode ser") is False
        assert _detectar_pergunta("fechado") is False


class TestClassificarPorOutboundContext:
    """Testes de classificacao por OutboundContext."""

    def _criar_ctx(self, method: OutboundMethod) -> OutboundContext:
        """Helper para criar contexto."""
        return OutboundContext(
            cliente_id="test-cliente",
            actor_type=ActorType.BOT,
            channel=OutboundChannel.WHATSAPP,
            method=method,
            is_proactive=method != OutboundMethod.REPLY,
        )

    def test_reply_classifica_como_reply_direta(self):
        """REPLY deve classificar como reply_direta."""
        ctx = self._criar_ctx(OutboundMethod.REPLY)
        resultado = classificar_por_outbound_context(ctx)

        assert resultado.tipo == ContextType.REPLY_DIRETA
        assert resultado.prioridade == 1
        assert resultado.confianca >= 0.9

    def test_campaign_classifica_como_campanha_fria(self):
        """CAMPAIGN deve classificar como campanha_fria."""
        ctx = self._criar_ctx(OutboundMethod.CAMPAIGN)
        resultado = classificar_por_outbound_context(ctx)

        assert resultado.tipo == ContextType.CAMPANHA_FRIA
        assert resultado.prioridade == 5

    def test_followup_classifica_como_followup(self):
        """FOLLOWUP deve classificar como followup."""
        ctx = self._criar_ctx(OutboundMethod.FOLLOWUP)
        resultado = classificar_por_outbound_context(ctx)

        assert resultado.tipo == ContextType.FOLLOWUP
        assert resultado.prioridade == 4

    def test_reactivation_classifica_como_followup(self):
        """REACTIVATION deve classificar como followup."""
        ctx = self._criar_ctx(OutboundMethod.REACTIVATION)
        resultado = classificar_por_outbound_context(ctx)

        assert resultado.tipo == ContextType.FOLLOWUP
        assert resultado.prioridade == 4

    def test_button_classifica_como_oferta_ativa(self):
        """BUTTON/COMMAND deve classificar como oferta_ativa."""
        for method in [OutboundMethod.BUTTON, OutboundMethod.COMMAND, OutboundMethod.MANUAL]:
            ctx = self._criar_ctx(method)
            resultado = classificar_por_outbound_context(ctx)

            assert resultado.tipo == ContextType.OFERTA_ATIVA
            assert resultado.prioridade == 3


class TestClassificarContexto:
    """Testes de classificacao completa."""

    @pytest.mark.asyncio
    async def test_prioriza_outbound_ctx(self):
        """Deve priorizar OutboundContext sobre mensagem."""
        ctx = OutboundContext(
            cliente_id="test-cliente",
            actor_type=ActorType.SYSTEM,
            channel=OutboundChannel.JOB,
            method=OutboundMethod.CAMPAIGN,
            is_proactive=True,
        )
        resultado = await classificar_contexto(
            mensagem="ok pode reservar",  # Seria aceite
            outbound_ctx=ctx,
        )

        # Deve usar OutboundContext, nao mensagem
        assert resultado.tipo == ContextType.CAMPANHA_FRIA

    @pytest.mark.asyncio
    async def test_classifica_mensagem_aceite(self):
        """Deve classificar mensagem de aceite corretamente."""
        resultado = await classificar_contexto(
            mensagem="ok pode reservar",
        )

        assert resultado.tipo == ContextType.ACEITE_VAGA
        assert resultado.prioridade == 1

    @pytest.mark.asyncio
    async def test_classifica_mensagem_pergunta(self):
        """Deve classificar pergunta corretamente."""
        resultado = await classificar_contexto(
            mensagem="qual o valor do plantao?",
        )

        assert resultado.tipo == ContextType.REPLY_DIRETA
        assert resultado.prioridade == 1

    @pytest.mark.asyncio
    async def test_classifica_mensagem_curta(self):
        """Mensagem curta deve ser reply_direta."""
        resultado = await classificar_contexto(
            mensagem="oi",
        )

        assert resultado.tipo == ContextType.REPLY_DIRETA

    @pytest.mark.asyncio
    async def test_fallback_sem_contexto(self):
        """Sem contexto, deve usar fallback."""
        resultado = await classificar_contexto()

        assert resultado.tipo == ContextType.REPLY_DIRETA
        assert resultado.confianca == 0.5
