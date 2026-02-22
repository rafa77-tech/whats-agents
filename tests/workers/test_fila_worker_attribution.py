"""
Tests for fila_worker campaign attribution fix.

Validates that the new worker creates conversations BEFORE building
OutboundContext so that _finalizar_envio can call registrar_campaign_touch.
"""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from app.services.guardrails.types import SendOutcome
from app.services.circuit_breaker import CircuitState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _BreakLoop(Exception):
    """Raised to break the infinite while-True loop in processar_fila."""


def _make_mensagem(conversa_id=None, campanha_id="42"):
    """Build a fila_mensagens row dict for testing."""
    metadata = {}
    if campanha_id:
        metadata["campanha_id"] = campanha_id
    return {
        "id": "msg-attr-001",
        "cliente_id": "cliente-abc",
        "conversa_id": conversa_id,
        "conteudo": "Oi Dr Carlos!",
        "tipo": "campanha",
        "status": "processando",
        "tentativas": 0,
        "metadata": metadata,
        "clientes": {
            "telefone": "5511999999999",
            "primeiro_nome": "Carlos",
        },
    }


def _make_result(outcome=SendOutcome.SENT, provider_message_id="evo-123"):
    """Build a mock OutboundResult."""
    r = MagicMock()
    r.outcome = outcome
    r.outcome_reason_code = None
    r.provider_message_id = provider_message_id
    r.blocked = False
    r.success = True
    r.error = None
    r.chip_id = "chip-1"
    return r


def _sleep_side_effect_factory(break_after=1):
    """Create an asyncio.sleep side effect that raises _BreakLoop
    after ``break_after`` calls (to exit the while-True loop)."""
    counter = {"n": 0}

    async def _sleep(seconds):
        counter["n"] += 1
        # The first sleep is the post-send delay; break after it
        if counter["n"] >= break_after:
            raise _BreakLoop("loop break")

    return _sleep


# Module-level patch targets
_MOD = "app.workers.fila_worker"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCampanhaCriaConversaAntesDoEnvio:
    """Bug 1: conversation must be created BEFORE OutboundContext."""

    @pytest.mark.asyncio
    async def test_campanha_cria_conversa_antes_do_envio(self):
        """When conversa_id is None, buscar_ou_criar_conversa is called
        BEFORE criar_contexto_campanha, and the resolved id is passed."""
        mensagem = _make_mensagem(conversa_id=None, campanha_id="20")
        result = _make_result()
        call_order = []

        async def fake_buscar(cid):
            call_order.append("buscar_conversa")
            return {"id": "conv-new-123"}

        def fake_ctx_camp(**kw):
            call_order.append("criar_ctx_camp")
            return MagicMock()

        with patch(f"{_MOD}.fila_service") as mock_fila, \
             patch(f"{_MOD}.send_outbound_message", new_callable=AsyncMock, return_value=result), \
             patch(f"{_MOD}.criar_contexto_campanha", side_effect=fake_ctx_camp), \
             patch(f"{_MOD}.buscar_ou_criar_conversa", side_effect=fake_buscar), \
             patch(f"{_MOD}.salvar_interacao", new_callable=AsyncMock), \
             patch(f"{_MOD}.supabase") as mock_sb, \
             patch(f"{_MOD}.pode_enviar", new_callable=AsyncMock, return_value=True), \
             patch(f"{_MOD}.circuit_evolution") as mock_circuit, \
             patch(f"{_MOD}.redis_client") as mock_redis, \
             patch(f"{_MOD}.asyncio") as mock_asyncio:

            mock_circuit.estado = CircuitState.CLOSED
            mock_redis.set = AsyncMock(return_value=True)
            mock_redis.delete = AsyncMock()
            mock_fila.obter_proxima = AsyncMock(return_value=mensagem)
            mock_fila.registrar_outcome = AsyncMock()
            mock_asyncio.sleep = AsyncMock(side_effect=_BreakLoop)

            from app.workers.fila_worker import processar_fila

            with pytest.raises(_BreakLoop):
                await processar_fila()

        # buscar_conversa must be called BEFORE criar_ctx_camp
        assert "buscar_conversa" in call_order
        assert "criar_ctx_camp" in call_order
        assert call_order.index("buscar_conversa") < call_order.index("criar_ctx_camp")

    @pytest.mark.asyncio
    async def test_conversa_existente_reutilizada(self):
        """When conversa_id already exists on the fila row,
        buscar_ou_criar_conversa is NOT called."""
        mensagem = _make_mensagem(conversa_id="conv-existing", campanha_id="20")
        result = _make_result()

        with patch(f"{_MOD}.fila_service") as mock_fila, \
             patch(f"{_MOD}.send_outbound_message", new_callable=AsyncMock, return_value=result), \
             patch(f"{_MOD}.criar_contexto_campanha", return_value=MagicMock()), \
             patch(f"{_MOD}.buscar_ou_criar_conversa", new_callable=AsyncMock) as mock_buscar, \
             patch(f"{_MOD}.salvar_interacao", new_callable=AsyncMock), \
             patch(f"{_MOD}.supabase"), \
             patch(f"{_MOD}.pode_enviar", new_callable=AsyncMock, return_value=True), \
             patch(f"{_MOD}.circuit_evolution") as mock_circuit, \
             patch(f"{_MOD}.redis_client") as mock_redis, \
             patch(f"{_MOD}.asyncio") as mock_asyncio:

            mock_circuit.estado = CircuitState.CLOSED
            mock_redis.set = AsyncMock(return_value=True)
            mock_redis.delete = AsyncMock()
            mock_fila.obter_proxima = AsyncMock(return_value=mensagem)
            mock_fila.registrar_outcome = AsyncMock()
            mock_asyncio.sleep = AsyncMock(side_effect=_BreakLoop)

            from app.workers.fila_worker import processar_fila

            with pytest.raises(_BreakLoop):
                await processar_fila()

        mock_buscar.assert_not_called()

    @pytest.mark.asyncio
    async def test_conversa_id_atualizada_na_fila(self):
        """When a new conversation is created, fila_mensagens.conversa_id
        is updated via supabase."""
        mensagem = _make_mensagem(conversa_id=None, campanha_id="20")
        result = _make_result()

        with patch(f"{_MOD}.fila_service") as mock_fila, \
             patch(f"{_MOD}.send_outbound_message", new_callable=AsyncMock, return_value=result), \
             patch(f"{_MOD}.criar_contexto_campanha", return_value=MagicMock()), \
             patch(f"{_MOD}.buscar_ou_criar_conversa", new_callable=AsyncMock, return_value={"id": "conv-new"}), \
             patch(f"{_MOD}.salvar_interacao", new_callable=AsyncMock), \
             patch(f"{_MOD}.supabase") as mock_sb, \
             patch(f"{_MOD}.pode_enviar", new_callable=AsyncMock, return_value=True), \
             patch(f"{_MOD}.circuit_evolution") as mock_circuit, \
             patch(f"{_MOD}.redis_client") as mock_redis, \
             patch(f"{_MOD}.asyncio") as mock_asyncio:

            mock_circuit.estado = CircuitState.CLOSED
            mock_redis.set = AsyncMock(return_value=True)
            mock_redis.delete = AsyncMock()
            mock_fila.obter_proxima = AsyncMock(return_value=mensagem)
            mock_fila.registrar_outcome = AsyncMock()
            mock_asyncio.sleep = AsyncMock(side_effect=_BreakLoop)

            from app.workers.fila_worker import processar_fila

            with pytest.raises(_BreakLoop):
                await processar_fila()

        # Verify supabase was called to update fila_mensagens with conversa_id
        mock_sb.table.assert_any_call("fila_mensagens")
        # The update chain: .update({"conversa_id": ...}).eq("id", ...).execute()
        update_call = mock_sb.table("fila_mensagens").update
        update_call.assert_called_with({"conversa_id": "conv-new"})

    @pytest.mark.asyncio
    async def test_contexto_campanha_recebe_conversa_id(self):
        """criar_contexto_campanha receives the resolved conversation_id."""
        mensagem = _make_mensagem(conversa_id=None, campanha_id="20")
        result = _make_result()

        with patch(f"{_MOD}.fila_service") as mock_fila, \
             patch(f"{_MOD}.send_outbound_message", new_callable=AsyncMock, return_value=result), \
             patch(f"{_MOD}.criar_contexto_campanha") as mock_ctx, \
             patch(f"{_MOD}.buscar_ou_criar_conversa", new_callable=AsyncMock, return_value={"id": "conv-resolved"}), \
             patch(f"{_MOD}.salvar_interacao", new_callable=AsyncMock), \
             patch(f"{_MOD}.supabase"), \
             patch(f"{_MOD}.pode_enviar", new_callable=AsyncMock, return_value=True), \
             patch(f"{_MOD}.circuit_evolution") as mock_circuit, \
             patch(f"{_MOD}.redis_client") as mock_redis, \
             patch(f"{_MOD}.asyncio") as mock_asyncio:

            mock_circuit.estado = CircuitState.CLOSED
            mock_redis.set = AsyncMock(return_value=True)
            mock_redis.delete = AsyncMock()
            mock_fila.obter_proxima = AsyncMock(return_value=mensagem)
            mock_fila.registrar_outcome = AsyncMock()
            mock_ctx.return_value = MagicMock()
            mock_asyncio.sleep = AsyncMock(side_effect=_BreakLoop)

            from app.workers.fila_worker import processar_fila

            with pytest.raises(_BreakLoop):
                await processar_fila()

        mock_ctx.assert_called_once_with(
            cliente_id="cliente-abc",
            campaign_id="20",
            conversation_id="conv-resolved",
            metadata={"campanha_id": "20"},
        )


class TestTemporaryFailureHandling:
    """Issue #87: Temporary failures → reagendar_sem_penalidade in fila_worker."""

    @pytest.mark.asyncio
    async def test_circuit_open_reagenda_sem_penalidade(self):
        """FAILED_CIRCUIT_OPEN → reagendar_sem_penalidade, not marcar_erro."""
        mensagem = _make_mensagem(conversa_id="conv-1")
        result = _make_result(outcome=SendOutcome.FAILED_CIRCUIT_OPEN)
        result.success = False
        result.provider_message_id = None

        with patch(f"{_MOD}.fila_service") as mock_fila, \
             patch(f"{_MOD}.send_outbound_message", new_callable=AsyncMock, return_value=result), \
             patch(f"{_MOD}.criar_contexto_campanha", return_value=MagicMock()), \
             patch(f"{_MOD}.buscar_ou_criar_conversa", new_callable=AsyncMock), \
             patch(f"{_MOD}.salvar_interacao", new_callable=AsyncMock), \
             patch(f"{_MOD}.supabase"), \
             patch(f"{_MOD}.pode_enviar", new_callable=AsyncMock, return_value=True), \
             patch(f"{_MOD}.circuit_evolution") as mock_circuit, \
             patch(f"{_MOD}.redis_client") as mock_redis, \
             patch(f"{_MOD}._alertar_circuit_aberto", new_callable=AsyncMock) as mock_alert, \
             patch(f"{_MOD}.asyncio") as mock_asyncio:

            mock_circuit.estado = CircuitState.CLOSED
            mock_redis.set = AsyncMock(return_value=True)
            mock_redis.delete = AsyncMock()
            mock_fila.obter_proxima = AsyncMock(return_value=mensagem)
            mock_fila.registrar_outcome = AsyncMock()
            mock_fila.reagendar_sem_penalidade = AsyncMock()
            mock_fila.marcar_erro = AsyncMock()
            mock_asyncio.sleep = AsyncMock(side_effect=_BreakLoop)

            from app.workers.fila_worker import processar_fila

            with pytest.raises(_BreakLoop):
                await processar_fila()

        mock_fila.reagendar_sem_penalidade.assert_called_once_with("msg-attr-001")
        mock_fila.marcar_erro.assert_not_called()
        mock_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_reagenda_sem_penalidade(self):
        """FAILED_RATE_LIMIT → reagendar_sem_penalidade."""
        mensagem = _make_mensagem(conversa_id="conv-1")
        result = _make_result(outcome=SendOutcome.FAILED_RATE_LIMIT)
        result.success = False
        result.provider_message_id = None

        with patch(f"{_MOD}.fila_service") as mock_fila, \
             patch(f"{_MOD}.send_outbound_message", new_callable=AsyncMock, return_value=result), \
             patch(f"{_MOD}.criar_contexto_campanha", return_value=MagicMock()), \
             patch(f"{_MOD}.buscar_ou_criar_conversa", new_callable=AsyncMock), \
             patch(f"{_MOD}.salvar_interacao", new_callable=AsyncMock), \
             patch(f"{_MOD}.supabase"), \
             patch(f"{_MOD}.pode_enviar", new_callable=AsyncMock, return_value=True), \
             patch(f"{_MOD}.circuit_evolution") as mock_circuit, \
             patch(f"{_MOD}.redis_client") as mock_redis, \
             patch(f"{_MOD}.asyncio") as mock_asyncio:

            mock_circuit.estado = CircuitState.CLOSED
            mock_redis.set = AsyncMock(return_value=True)
            mock_redis.delete = AsyncMock()
            mock_fila.obter_proxima = AsyncMock(return_value=mensagem)
            mock_fila.registrar_outcome = AsyncMock()
            mock_fila.reagendar_sem_penalidade = AsyncMock()
            mock_fila.marcar_erro = AsyncMock()
            mock_asyncio.sleep = AsyncMock(side_effect=_BreakLoop)

            from app.workers.fila_worker import processar_fila

            with pytest.raises(_BreakLoop):
                await processar_fila()

        mock_fila.reagendar_sem_penalidade.assert_called_once_with("msg-attr-001")
        mock_fila.marcar_erro.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_capacity_reagenda_sem_penalidade(self):
        """FAILED_NO_CAPACITY → reagendar_sem_penalidade."""
        mensagem = _make_mensagem(conversa_id="conv-1")
        result = _make_result(outcome=SendOutcome.FAILED_NO_CAPACITY)
        result.success = False
        result.provider_message_id = None

        with patch(f"{_MOD}.fila_service") as mock_fila, \
             patch(f"{_MOD}.send_outbound_message", new_callable=AsyncMock, return_value=result), \
             patch(f"{_MOD}.criar_contexto_campanha", return_value=MagicMock()), \
             patch(f"{_MOD}.buscar_ou_criar_conversa", new_callable=AsyncMock), \
             patch(f"{_MOD}.salvar_interacao", new_callable=AsyncMock), \
             patch(f"{_MOD}.supabase"), \
             patch(f"{_MOD}.pode_enviar", new_callable=AsyncMock, return_value=True), \
             patch(f"{_MOD}.circuit_evolution") as mock_circuit, \
             patch(f"{_MOD}.redis_client") as mock_redis, \
             patch(f"{_MOD}.asyncio") as mock_asyncio:

            mock_circuit.estado = CircuitState.CLOSED
            mock_redis.set = AsyncMock(return_value=True)
            mock_redis.delete = AsyncMock()
            mock_fila.obter_proxima = AsyncMock(return_value=mensagem)
            mock_fila.registrar_outcome = AsyncMock()
            mock_fila.reagendar_sem_penalidade = AsyncMock()
            mock_fila.marcar_erro = AsyncMock()
            mock_asyncio.sleep = AsyncMock(side_effect=_BreakLoop)

            from app.workers.fila_worker import processar_fila

            with pytest.raises(_BreakLoop):
                await processar_fila()

        mock_fila.reagendar_sem_penalidade.assert_called_once_with("msg-attr-001")
        mock_fila.marcar_erro.assert_not_called()

    @pytest.mark.asyncio
    async def test_real_failure_calls_marcar_erro(self):
        """FAILED_PROVIDER → marcar_erro (not reagendar)."""
        mensagem = _make_mensagem(conversa_id="conv-1")
        result = _make_result(outcome=SendOutcome.FAILED_PROVIDER)
        result.success = False
        result.error = "Provider timeout"
        result.provider_message_id = None

        with patch(f"{_MOD}.fila_service") as mock_fila, \
             patch(f"{_MOD}.send_outbound_message", new_callable=AsyncMock, return_value=result), \
             patch(f"{_MOD}.criar_contexto_campanha", return_value=MagicMock()), \
             patch(f"{_MOD}.buscar_ou_criar_conversa", new_callable=AsyncMock), \
             patch(f"{_MOD}.salvar_interacao", new_callable=AsyncMock), \
             patch(f"{_MOD}.supabase"), \
             patch(f"{_MOD}.pode_enviar", new_callable=AsyncMock, return_value=True), \
             patch(f"{_MOD}.circuit_evolution") as mock_circuit, \
             patch(f"{_MOD}.redis_client") as mock_redis, \
             patch(f"{_MOD}.asyncio") as mock_asyncio:

            mock_circuit.estado = CircuitState.CLOSED
            mock_redis.set = AsyncMock(return_value=True)
            mock_redis.delete = AsyncMock()
            mock_fila.obter_proxima = AsyncMock(return_value=mensagem)
            mock_fila.registrar_outcome = AsyncMock()
            mock_fila.reagendar_sem_penalidade = AsyncMock()
            mock_fila.marcar_erro = AsyncMock()
            mock_asyncio.sleep = AsyncMock(side_effect=_BreakLoop)

            from app.workers.fila_worker import processar_fila

            with pytest.raises(_BreakLoop):
                await processar_fila()

        mock_fila.marcar_erro.assert_called_once()
        mock_fila.reagendar_sem_penalidade.assert_not_called()

    @pytest.mark.asyncio
    async def test_pre_send_rate_limit_usa_reagendar(self):
        """Pre-send rate limit check → reagendar_sem_penalidade (not marcar_erro)."""
        mensagem = _make_mensagem(conversa_id="conv-1")

        with patch(f"{_MOD}.fila_service") as mock_fila, \
             patch(f"{_MOD}.pode_enviar", new_callable=AsyncMock, return_value=False), \
             patch(f"{_MOD}.circuit_evolution") as mock_circuit, \
             patch(f"{_MOD}.redis_client") as mock_redis, \
             patch(f"{_MOD}.asyncio") as mock_asyncio:

            mock_circuit.estado = CircuitState.CLOSED
            mock_redis.set = AsyncMock(return_value=True)
            mock_redis.delete = AsyncMock()
            # Return message once, then None so loop exits on 2nd iteration
            mock_fila.obter_proxima = AsyncMock(side_effect=[mensagem, None])
            mock_fila.reagendar_sem_penalidade = AsyncMock()
            mock_fila.marcar_erro = AsyncMock()
            # break_after=3: 1st sleep (rate-limit delay at line 158),
            # 2nd sleep (empty queue wait at line 142), 3rd breaks
            mock_asyncio.sleep = AsyncMock(
                side_effect=_sleep_side_effect_factory(break_after=3)
            )

            from app.workers.fila_worker import processar_fila

            with pytest.raises(_BreakLoop):
                await processar_fila()

        mock_fila.reagendar_sem_penalidade.assert_called_once_with("msg-attr-001")
        mock_fila.marcar_erro.assert_not_called()
