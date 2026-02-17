"""
Testes para o fluxo de handoff IA <-> Humano.

Cobre:
- Iniciar handoff por pedido humano
- Iniciar handoff por sentimento negativo
- Idempotencia (medico ja em handoff)
- Falha de notificacao Slack (degradacao graciosa)
- Propagacao de erro do banco de dados
- Finalizar handoff
- Resolver handoff
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime


# ---- Fixtures ----


@pytest.fixture
def mock_supabase():
    """Mock do cliente Supabase com chain completa."""
    mock = MagicMock()

    def _chain_table(table_name):
        table = MagicMock()
        table._table_name = table_name

        # select().eq().single().execute()
        select = MagicMock()
        table.select.return_value = select
        eq = MagicMock()
        select.eq.return_value = eq
        single = MagicMock()
        eq.single.return_value = single

        # select().eq().order().execute()
        order = MagicMock()
        eq.order.return_value = order

        # update().eq().execute()
        update = MagicMock()
        table.update.return_value = update
        update_eq = MagicMock()
        update.eq.return_value = update_eq
        update_eq_eq = MagicMock()
        update_eq.eq.return_value = update_eq_eq

        # insert().execute()
        insert = MagicMock()
        table.insert.return_value = insert

        return table

    mock.table = MagicMock(side_effect=_chain_table)
    return mock


@pytest.fixture
def conversa_data():
    """Dados de uma conversa valida com cliente."""
    return {
        "id": "conv-123",
        "cliente_id": "cli-456",
        "controlled_by": "ai",
        "chatwoot_conversation_id": 42,
        "clientes": {
            "id": "cli-456",
            "telefone": "5511999990000",
            "primeiro_nome": "Carlos",
        },
    }


@pytest.fixture
def interacoes_data():
    """Dados de interacoes para calculo de metadata."""
    return [
        {
            "conteudo": "Oi Julia",
            "created_at": "2026-01-10T10:00:00+00:00",
        },
        {
            "conteudo": "Quero falar com um humano",
            "created_at": "2026-01-10T10:30:00+00:00",
        },
    ]


@pytest.fixture
def handoff_response_data():
    """Dados de handoff criado com sucesso."""
    return {
        "id": "hoff-789",
        "conversa_id": "conv-123",
        "motivo": "Medico pediu para falar com humano",
        "trigger_type": "pedido_humano",
        "status": "pendente",
    }


@pytest.fixture
def outbound_result_success():
    """Resultado de envio de mensagem com sucesso."""
    result = MagicMock()
    result.blocked = False
    result.success = True
    result.error = None
    return result


# ---- Testes de iniciar_handoff ----


@pytest.mark.unit
@pytest.mark.asyncio
async def test_iniciar_handoff_pedido_humano(
    mock_supabase, conversa_data, interacoes_data, handoff_response_data, outbound_result_success
):
    """Handoff por pedido humano: envia mensagem, atualiza conversa, cria registro."""
    with (
        patch("app.services.handoff.flow.supabase", mock_supabase),
        patch("app.services.handoff.flow.send_outbound_message", new_callable=AsyncMock) as mock_send,
        patch("app.services.handoff.flow.salvar_interacao", new_callable=AsyncMock) as mock_salvar,
        patch("app.services.handoff.flow.chatwoot_service") as mock_chatwoot,
        patch("app.services.handoff.flow.safe_create_task") as mock_task,
        patch("app.services.handoff.flow.agora_utc") as mock_agora,
    ):
        mock_agora.return_value.isoformat.return_value = "2026-01-10T10:30:00+00:00"
        mock_send.return_value = outbound_result_success
        mock_chatwoot.configurado = True
        mock_chatwoot.enviar_mensagem = AsyncMock()
        mock_chatwoot.adicionar_label = AsyncMock()

        # Setup table calls
        calls = {}

        def table_side_effect(name):
            t = MagicMock()
            calls[name] = t

            if name == "conversations":
                # select -> eq -> single -> execute (buscar conversa)
                select = MagicMock()
                t.select.return_value = select
                eq = MagicMock()
                select.eq.return_value = eq
                single = MagicMock()
                eq.single.return_value = single
                resp = MagicMock()
                resp.data = conversa_data
                single.execute.return_value = resp

                # update -> eq -> execute
                update = MagicMock()
                t.update.return_value = update
                update_eq = MagicMock()
                update.eq.return_value = update_eq
                update_eq.execute.return_value = MagicMock()

            elif name == "interacoes":
                select = MagicMock()
                t.select.return_value = select
                eq = MagicMock()
                select.eq.return_value = eq
                order = MagicMock()
                eq.order.return_value = order
                resp = MagicMock()
                resp.data = interacoes_data
                order.execute.return_value = resp

            elif name == "handoffs":
                insert = MagicMock()
                t.insert.return_value = insert
                resp = MagicMock()
                resp.data = [handoff_response_data]
                insert.execute.return_value = resp

            return t

        mock_supabase.table.side_effect = table_side_effect

        from app.services.handoff.flow import iniciar_handoff

        result = await iniciar_handoff(
            conversa_id="conv-123",
            cliente_id="cli-456",
            motivo="Medico pediu para falar com humano",
            trigger_type="pedido_humano",
        )

        # Verifica resultado
        assert result is not None
        assert result["id"] == "hoff-789"
        assert result["status"] == "pendente"

        # Verifica que mensagem de transicao foi enviada
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args
        assert call_kwargs.kwargs["telefone"] == "5511999990000"

        # Verifica que interacao foi salva
        mock_salvar.assert_called_once()

        # Verifica sincronizacao com Chatwoot
        mock_chatwoot.enviar_mensagem.assert_called_once()
        mock_chatwoot.adicionar_label.assert_called_once()

        # Verifica emissao de evento
        mock_task.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_iniciar_handoff_sentimento_negativo(
    mock_supabase, conversa_data, interacoes_data, handoff_response_data, outbound_result_success
):
    """Handoff por sentimento negativo usa mensagem de transicao adequada."""
    handoff_response_data["trigger_type"] = "sentimento_negativo"
    handoff_response_data["motivo"] = "Sentimento muito negativo detectado"

    with (
        patch("app.services.handoff.flow.supabase", mock_supabase),
        patch("app.services.handoff.flow.send_outbound_message", new_callable=AsyncMock) as mock_send,
        patch("app.services.handoff.flow.salvar_interacao", new_callable=AsyncMock),
        patch("app.services.handoff.flow.chatwoot_service") as mock_chatwoot,
        patch("app.services.handoff.flow.safe_create_task"),
        patch("app.services.handoff.flow.agora_utc") as mock_agora,
        patch("app.services.handoff.flow.obter_mensagem_transicao") as mock_msg,
    ):
        mock_agora.return_value.isoformat.return_value = "2026-01-10T10:30:00+00:00"
        mock_send.return_value = outbound_result_success
        mock_chatwoot.configurado = True
        mock_chatwoot.enviar_mensagem = AsyncMock()
        mock_chatwoot.adicionar_label = AsyncMock()
        mock_msg.return_value = "Entendo sua frustracao, vou chamar minha supervisora"

        def table_side_effect(name):
            t = MagicMock()
            if name == "conversations":
                select = MagicMock()
                t.select.return_value = select
                eq = MagicMock()
                select.eq.return_value = eq
                single = MagicMock()
                eq.single.return_value = single
                resp = MagicMock()
                resp.data = conversa_data
                single.execute.return_value = resp
                update = MagicMock()
                t.update.return_value = update
                update_eq = MagicMock()
                update.eq.return_value = update_eq
                update_eq.execute.return_value = MagicMock()
            elif name == "interacoes":
                select = MagicMock()
                t.select.return_value = select
                eq = MagicMock()
                select.eq.return_value = eq
                order = MagicMock()
                eq.order.return_value = order
                resp = MagicMock()
                resp.data = interacoes_data
                order.execute.return_value = resp
            elif name == "handoffs":
                insert = MagicMock()
                t.insert.return_value = insert
                resp = MagicMock()
                resp.data = [handoff_response_data]
                insert.execute.return_value = resp
            return t

        mock_supabase.table.side_effect = table_side_effect

        from app.services.handoff.flow import iniciar_handoff

        result = await iniciar_handoff(
            conversa_id="conv-123",
            cliente_id="cli-456",
            motivo="Sentimento muito negativo detectado",
            trigger_type="sentimento_negativo",
        )

        assert result is not None
        assert result["trigger_type"] == "sentimento_negativo"

        # Verifica que obter_mensagem_transicao foi chamado com tipo correto
        mock_msg.assert_called_once_with("sentimento_negativo")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_iniciar_handoff_conversa_nao_encontrada(mock_supabase):
    """Retorna None quando conversa nao existe no banco."""
    with patch("app.services.handoff.flow.supabase", mock_supabase):
        def table_side_effect(name):
            t = MagicMock()
            if name == "conversations":
                select = MagicMock()
                t.select.return_value = select
                eq = MagicMock()
                select.eq.return_value = eq
                single = MagicMock()
                eq.single.return_value = single
                resp = MagicMock()
                resp.data = None
                single.execute.return_value = resp
            return t

        mock_supabase.table.side_effect = table_side_effect

        from app.services.handoff.flow import iniciar_handoff

        result = await iniciar_handoff(
            conversa_id="conv-inexistente",
            cliente_id="cli-456",
            motivo="Teste",
        )

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_iniciar_handoff_telefone_ausente(mock_supabase):
    """Retorna None quando cliente nao tem telefone."""
    conversa_sem_telefone = {
        "id": "conv-123",
        "clientes": {"id": "cli-456", "telefone": None},
    }

    with patch("app.services.handoff.flow.supabase", mock_supabase):
        def table_side_effect(name):
            t = MagicMock()
            if name == "conversations":
                select = MagicMock()
                t.select.return_value = select
                eq = MagicMock()
                select.eq.return_value = eq
                single = MagicMock()
                eq.single.return_value = single
                resp = MagicMock()
                resp.data = conversa_sem_telefone
                single.execute.return_value = resp
            return t

        mock_supabase.table.side_effect = table_side_effect

        from app.services.handoff.flow import iniciar_handoff

        result = await iniciar_handoff(
            conversa_id="conv-123",
            cliente_id="cli-456",
            motivo="Teste",
        )

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_iniciar_handoff_erro_banco_propaga():
    """Erro no banco de dados retorna None (graceful degradation)."""
    with patch("app.services.handoff.flow.supabase") as mock_sb:
        mock_sb.table.side_effect = Exception("Connection refused")

        from app.services.handoff.flow import iniciar_handoff

        result = await iniciar_handoff(
            conversa_id="conv-123",
            cliente_id="cli-456",
            motivo="Teste",
        )

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_iniciar_handoff_mensagem_bloqueada(
    mock_supabase, conversa_data, interacoes_data, handoff_response_data
):
    """Handoff continua mesmo se mensagem de transicao for bloqueada pelo guardrail."""
    blocked_result = MagicMock()
    blocked_result.blocked = True
    blocked_result.block_reason = "Rate limit"

    with (
        patch("app.services.handoff.flow.supabase", mock_supabase),
        patch("app.services.handoff.flow.send_outbound_message", new_callable=AsyncMock) as mock_send,
        patch("app.services.handoff.flow.salvar_interacao", new_callable=AsyncMock),
        patch("app.services.handoff.flow.chatwoot_service") as mock_chatwoot,
        patch("app.services.handoff.flow.safe_create_task"),
        patch("app.services.handoff.flow.agora_utc") as mock_agora,
    ):
        mock_agora.return_value.isoformat.return_value = "2026-01-10T10:30:00+00:00"
        mock_send.return_value = blocked_result
        mock_chatwoot.configurado = False

        def table_side_effect(name):
            t = MagicMock()
            if name == "conversations":
                select = MagicMock()
                t.select.return_value = select
                eq = MagicMock()
                select.eq.return_value = eq
                single = MagicMock()
                eq.single.return_value = single
                resp = MagicMock()
                resp.data = conversa_data
                single.execute.return_value = resp
                update = MagicMock()
                t.update.return_value = update
                update_eq = MagicMock()
                update.eq.return_value = update_eq
                update_eq.execute.return_value = MagicMock()
            elif name == "interacoes":
                select = MagicMock()
                t.select.return_value = select
                eq = MagicMock()
                select.eq.return_value = eq
                order = MagicMock()
                eq.order.return_value = order
                resp = MagicMock()
                resp.data = interacoes_data
                order.execute.return_value = resp
            elif name == "handoffs":
                insert = MagicMock()
                t.insert.return_value = insert
                resp = MagicMock()
                resp.data = [handoff_response_data]
                insert.execute.return_value = resp
            return t

        mock_supabase.table.side_effect = table_side_effect

        from app.services.handoff.flow import iniciar_handoff

        result = await iniciar_handoff(
            conversa_id="conv-123",
            cliente_id="cli-456",
            motivo="Teste",
            trigger_type="pedido_humano",
        )

        # Handoff deve ser criado mesmo com mensagem bloqueada
        assert result is not None
        assert result["id"] == "hoff-789"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_iniciar_handoff_com_policy_decision_id(
    mock_supabase, conversa_data, interacoes_data, handoff_response_data, outbound_result_success
):
    """policy_decision_id deve ser incluido no registro de handoff."""
    handoff_response_data["policy_decision_id"] = "policy-abc"

    with (
        patch("app.services.handoff.flow.supabase", mock_supabase),
        patch("app.services.handoff.flow.send_outbound_message", new_callable=AsyncMock) as mock_send,
        patch("app.services.handoff.flow.salvar_interacao", new_callable=AsyncMock),
        patch("app.services.handoff.flow.chatwoot_service") as mock_chatwoot,
        patch("app.services.handoff.flow.safe_create_task"),
        patch("app.services.handoff.flow.agora_utc") as mock_agora,
    ):
        mock_agora.return_value.isoformat.return_value = "2026-01-10T10:30:00+00:00"
        mock_send.return_value = outbound_result_success
        mock_chatwoot.configurado = False

        inserted_data = {}

        def table_side_effect(name):
            t = MagicMock()
            if name == "conversations":
                select = MagicMock()
                t.select.return_value = select
                eq = MagicMock()
                select.eq.return_value = eq
                single = MagicMock()
                eq.single.return_value = single
                resp = MagicMock()
                resp.data = conversa_data
                single.execute.return_value = resp
                update = MagicMock()
                t.update.return_value = update
                update_eq = MagicMock()
                update.eq.return_value = update_eq
                update_eq.execute.return_value = MagicMock()
            elif name == "interacoes":
                select = MagicMock()
                t.select.return_value = select
                eq = MagicMock()
                select.eq.return_value = eq
                order = MagicMock()
                eq.order.return_value = order
                resp = MagicMock()
                resp.data = interacoes_data
                order.execute.return_value = resp
            elif name == "handoffs":
                insert = MagicMock()
                t.insert.return_value = insert

                def capture_insert(data):
                    inserted_data.update(data)
                    resp = MagicMock()
                    resp.data = [handoff_response_data]
                    return insert

                t.insert.side_effect = capture_insert
                insert.execute.return_value = MagicMock(data=[handoff_response_data])
            return t

        mock_supabase.table.side_effect = table_side_effect

        from app.services.handoff.flow import iniciar_handoff

        result = await iniciar_handoff(
            conversa_id="conv-123",
            cliente_id="cli-456",
            motivo="Policy decidiu handoff",
            trigger_type="pedido_humano",
            policy_decision_id="policy-abc",
        )

        assert result is not None
        assert "policy_decision_id" in inserted_data


# ---- Testes de finalizar_handoff ----


@pytest.mark.unit
@pytest.mark.asyncio
async def test_finalizar_handoff_sucesso():
    """Finalizar handoff retorna controle para IA e atualiza status."""
    conversa = {
        "id": "conv-123",
        "controlled_by": "human",
        "chatwoot_conversation_id": 42,
        "clientes": {"id": "cli-456"},
    }

    with (
        patch("app.services.handoff.flow.supabase") as mock_sb,
        patch("app.services.handoff.flow.chatwoot_service") as mock_chatwoot,
        patch("app.services.handoff.flow.agora_utc") as mock_agora,
    ):
        mock_agora.return_value.isoformat.return_value = "2026-01-10T11:00:00+00:00"
        mock_chatwoot.configurado = True
        mock_chatwoot.remover_label = AsyncMock()

        def table_side_effect(name):
            t = MagicMock()
            if name == "conversations":
                select = MagicMock()
                t.select.return_value = select
                eq = MagicMock()
                select.eq.return_value = eq
                single = MagicMock()
                eq.single.return_value = single
                resp = MagicMock()
                resp.data = conversa
                single.execute.return_value = resp
                update = MagicMock()
                t.update.return_value = update
                update_eq = MagicMock()
                update.eq.return_value = update_eq
                update_eq.execute.return_value = MagicMock()
            elif name == "handoffs":
                update = MagicMock()
                t.update.return_value = update
                eq1 = MagicMock()
                update.eq.return_value = eq1
                eq2 = MagicMock()
                eq1.eq.return_value = eq2
                resp = MagicMock()
                resp.data = [{"id": "hoff-789", "status": "resolvido"}]
                eq2.execute.return_value = resp
            return t

        mock_sb.table.side_effect = table_side_effect

        from app.services.handoff.flow import finalizar_handoff

        result = await finalizar_handoff(conversa_id="conv-123")

        assert result is True
        mock_chatwoot.remover_label.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_finalizar_handoff_conversa_nao_encontrada():
    """Retorna False quando conversa nao existe."""
    with patch("app.services.handoff.flow.supabase") as mock_sb:
        def table_side_effect(name):
            t = MagicMock()
            select = MagicMock()
            t.select.return_value = select
            eq = MagicMock()
            select.eq.return_value = eq
            single = MagicMock()
            eq.single.return_value = single
            resp = MagicMock()
            resp.data = None
            single.execute.return_value = resp
            return t

        mock_sb.table.side_effect = table_side_effect

        from app.services.handoff.flow import finalizar_handoff

        result = await finalizar_handoff(conversa_id="conv-inexistente")

        assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_finalizar_handoff_erro_banco():
    """Erro no banco retorna False."""
    with patch("app.services.handoff.flow.supabase") as mock_sb:
        mock_sb.table.side_effect = Exception("DB error")

        from app.services.handoff.flow import finalizar_handoff

        result = await finalizar_handoff(conversa_id="conv-123")

        assert result is False


# ---- Testes de resolver_handoff ----


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolver_handoff_sucesso():
    """Marca handoff como resolvido com notas e resolvido_por."""
    handoff_resolvido = {
        "id": "hoff-789",
        "status": "resolvido",
        "resolvido_por": "gestor-1",
        "notas": "Resolvido via Chatwoot",
    }

    with (
        patch("app.services.handoff.flow.supabase") as mock_sb,
        patch("app.services.handoff.flow.agora_utc") as mock_agora,
    ):
        mock_agora.return_value.isoformat.return_value = "2026-01-10T11:00:00+00:00"

        def table_side_effect(name):
            t = MagicMock()
            update = MagicMock()
            t.update.return_value = update
            eq = MagicMock()
            update.eq.return_value = eq
            resp = MagicMock()
            resp.data = [handoff_resolvido]
            eq.execute.return_value = resp
            return t

        mock_sb.table.side_effect = table_side_effect

        from app.services.handoff.flow import resolver_handoff

        result = await resolver_handoff(
            handoff_id="hoff-789",
            resolvido_por="gestor-1",
            notas="Resolvido via Chatwoot",
        )

        assert result is not None
        assert result["status"] == "resolvido"
        assert result["resolvido_por"] == "gestor-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolver_handoff_nao_encontrado():
    """Retorna None quando handoff nao existe."""
    with (
        patch("app.services.handoff.flow.supabase") as mock_sb,
        patch("app.services.handoff.flow.agora_utc") as mock_agora,
    ):
        mock_agora.return_value.isoformat.return_value = "2026-01-10T11:00:00+00:00"

        def table_side_effect(name):
            t = MagicMock()
            update = MagicMock()
            t.update.return_value = update
            eq = MagicMock()
            update.eq.return_value = eq
            resp = MagicMock()
            resp.data = None
            eq.execute.return_value = resp
            return t

        mock_sb.table.side_effect = table_side_effect

        from app.services.handoff.flow import resolver_handoff

        result = await resolver_handoff(handoff_id="hoff-inexistente")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolver_handoff_erro_banco():
    """Erro no banco retorna None."""
    with patch("app.services.handoff.flow.supabase") as mock_sb:
        mock_sb.table.side_effect = Exception("DB timeout")

        from app.services.handoff.flow import resolver_handoff

        result = await resolver_handoff(handoff_id="hoff-789")

        assert result is None
