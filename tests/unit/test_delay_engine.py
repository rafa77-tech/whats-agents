"""
Testes unitarios para delay_engine.

Sprint 22 - Responsividade Inteligente
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from app.services.delay_engine import (
    calcular_delay,
    calcular_delay_para_resposta,
    get_delay_seconds,
    has_valid_inbound_proof,
    DELAY_CONFIG,
    DelayResult,
)
from app.services.message_context_classifier import (
    ContextType,
    ContextClassification,
)
from app.services.guardrails.types import (
    OutboundContext,
    OutboundMethod,
    OutboundChannel,
    ActorType,
)


class TestDelayConfig:
    """Testes de configuracao de delay."""

    def test_delay_config_tem_todos_tipos(self):
        """Verifica que todos os tipos de contexto tem config."""
        for tipo in ContextType:
            assert tipo in DELAY_CONFIG, f"Tipo {tipo} sem config de delay"

    def test_reply_direta_eh_rapido(self):
        """Reply direta deve ter delay curto (0-3s)."""
        config = DELAY_CONFIG[ContextType.REPLY_DIRETA]
        assert config.min_ms == 0
        assert config.max_ms <= 3000

    def test_aceite_vaga_eh_urgente(self):
        """Aceite de vaga deve ter delay minimo (0-2s)."""
        config = DELAY_CONFIG[ContextType.ACEITE_VAGA]
        assert config.min_ms == 0
        assert config.max_ms <= 2000
        assert config.prioridade == 1

    def test_campanha_fria_eh_lenta(self):
        """Campanha fria deve ter delay longo (60-180s)."""
        config = DELAY_CONFIG[ContextType.CAMPANHA_FRIA]
        assert config.min_ms >= 60000
        assert config.max_ms <= 180000
        assert config.prioridade == 5


class TestCalcularDelay:
    """Testes de calculo de delay."""

    def test_delay_reply_direta(self):
        """Delay para reply direta deve ser 0-3s."""
        classificacao = ContextClassification(
            tipo=ContextType.REPLY_DIRETA,
            prioridade=1,
            confianca=0.9,
            razao="teste"
        )
        resultado = calcular_delay(classificacao)

        assert isinstance(resultado, DelayResult)
        assert resultado.delay_ms <= 3000
        assert resultado.tipo == ContextType.REPLY_DIRETA
        assert resultado.prioridade == 1

    def test_delay_aceite_vaga(self):
        """Delay para aceite de vaga deve ser 0-2s."""
        classificacao = ContextClassification(
            tipo=ContextType.ACEITE_VAGA,
            prioridade=1,
            confianca=0.95,
            razao="teste"
        )
        resultado = calcular_delay(classificacao)

        assert resultado.delay_ms <= 2000
        assert resultado.tipo == ContextType.ACEITE_VAGA

    def test_delay_campanha_fria(self):
        """Delay para campanha fria deve ser 60-180s."""
        classificacao = ContextClassification(
            tipo=ContextType.CAMPANHA_FRIA,
            prioridade=5,
            confianca=0.9,
            razao="teste"
        )
        resultado = calcular_delay(classificacao)

        assert resultado.delay_ms >= 50000  # Com variacao pode ser menor
        assert resultado.delay_ms <= 200000  # Com variacao pode ser maior
        assert resultado.prioridade == 5

    def test_desconta_tempo_processamento(self):
        """Deve descontar tempo de processamento do delay."""
        classificacao = ContextClassification(
            tipo=ContextType.CAMPANHA_FRIA,
            prioridade=5,
            confianca=0.9,
            razao="teste"
        )

        # Sem tempo de processamento
        resultado1 = calcular_delay(classificacao, tempo_processamento_ms=0)

        # Com 30s de processamento
        resultado2 = calcular_delay(classificacao, tempo_processamento_ms=30000)

        # Delay com processamento deve ser menor
        assert resultado2.delay_ms < resultado1.delay_ms


class TestHasValidInboundProof:
    """Testes de validacao de inbound proof."""

    def _criar_ctx(
        self,
        inbound_id: int = None,
        last_inbound: str = None,
    ) -> OutboundContext:
        """Helper para criar contexto."""
        return OutboundContext(
            cliente_id="test-cliente",
            actor_type=ActorType.BOT,
            channel=OutboundChannel.WHATSAPP,
            method=OutboundMethod.REPLY,
            is_proactive=False,
            inbound_interaction_id=inbound_id,
            last_inbound_at=last_inbound,
        )

    def test_sem_interaction_id_invalido(self):
        """Sem interaction_id, inbound proof eh invalido."""
        ctx = self._criar_ctx(
            inbound_id=None,
            last_inbound=datetime.now().isoformat(),
        )
        assert has_valid_inbound_proof(ctx) is False

    def test_sem_timestamp_invalido(self):
        """Sem timestamp, inbound proof eh invalido."""
        ctx = self._criar_ctx(
            inbound_id=123,
            last_inbound=None,
        )
        assert has_valid_inbound_proof(ctx) is False

    def test_timestamp_recente_valido(self):
        """Com interaction_id e timestamp recente, eh valido."""
        now = datetime.now()
        ctx = self._criar_ctx(
            inbound_id=123,
            last_inbound=now.isoformat(),
        )
        assert has_valid_inbound_proof(ctx) is True

    def test_timestamp_antigo_invalido(self):
        """Timestamp muito antigo (>30min) eh invalido."""
        old = datetime.now() - timedelta(minutes=35)
        ctx = self._criar_ctx(
            inbound_id=123,
            last_inbound=old.isoformat(),
        )
        assert has_valid_inbound_proof(ctx) is False

    def test_max_age_customizado(self):
        """Deve respeitar max_age_minutes customizado."""
        old = datetime.now() - timedelta(minutes=10)
        ctx = self._criar_ctx(
            inbound_id=123,
            last_inbound=old.isoformat(),
        )
        # Com 30 min (padrao), deve ser valido
        assert has_valid_inbound_proof(ctx, max_age_minutes=30) is True

        # Com 5 min, deve ser invalido
        assert has_valid_inbound_proof(ctx, max_age_minutes=5) is False


class TestCalcularDelayParaResposta:
    """Testes de calculo completo de delay."""

    @pytest.mark.asyncio
    async def test_com_mensagem(self):
        """Deve classificar e calcular delay baseado na mensagem."""
        resultado = await calcular_delay_para_resposta(
            mensagem="ok pode reservar",
        )

        assert isinstance(resultado, DelayResult)
        # Aceite de vaga deve ter prioridade 1
        assert resultado.prioridade == 1

    @pytest.mark.asyncio
    async def test_com_outbound_ctx(self):
        """Deve usar OutboundContext para classificar."""
        ctx = OutboundContext(
            cliente_id="test-cliente",
            actor_type=ActorType.SYSTEM,
            channel=OutboundChannel.JOB,
            method=OutboundMethod.CAMPAIGN,
            is_proactive=True,
        )
        resultado = await calcular_delay_para_resposta(
            outbound_ctx=ctx,
        )

        # Campanha deve ter delay longo
        assert resultado.tipo == ContextType.CAMPANHA_FRIA
        assert resultado.delay_ms >= 50000


class TestGetDelaySeconds:
    """Testes da funcao de conveniencia."""

    @pytest.mark.asyncio
    async def test_retorna_float(self):
        """Deve retornar delay em segundos como float."""
        delay = await get_delay_seconds(
            mensagem="teste",
        )

        assert isinstance(delay, float)
        assert delay >= 0

    @pytest.mark.asyncio
    async def test_desconta_processamento(self):
        """Deve descontar tempo de processamento."""
        delay1 = await get_delay_seconds(
            mensagem="teste campanha fria longa",
            tempo_processamento_s=0,
        )
        delay2 = await get_delay_seconds(
            mensagem="teste campanha fria longa",
            tempo_processamento_s=5,
        )

        # Com 5s de processamento, delay deve ser menor
        assert delay2 < delay1 or delay2 == 0
