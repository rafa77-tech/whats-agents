"""
Testes para o repositorio de handoffs.

Cobre:
- Listar handoffs pendentes
- Listar quando nenhum pendente existe
- Obter metricas de handoff
- Verificar handoff ativo
- Verificar handoff quando nao existe
- Calculo de tempo medio de resolucao
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta


# ---- Fixtures ----


@pytest.fixture
def mock_supabase():
    """Mock do cliente Supabase."""
    return MagicMock()


# ---- Testes de listar_handoffs_pendentes ----


@pytest.mark.unit
@pytest.mark.asyncio
async def test_listar_handoffs_pendentes_com_resultados(mock_supabase):
    """Retorna handoffs pendentes com dados da conversa e cliente."""
    handoffs = [
        {"id": "hoff-1", "conversa_id": "conv-1", "motivo": "pedido_humano", "status": "pendente"},
        {"id": "hoff-2", "conversa_id": "conv-2", "motivo": "juridico", "status": "pendente"},
    ]
    conversa_1 = {
        "id": "conv-1",
        "clientes": {"id": "cli-1", "primeiro_nome": "Carlos"},
    }
    conversa_2 = {
        "id": "conv-2",
        "clientes": {"id": "cli-2", "primeiro_nome": "Ana"},
    }

    call_count = [0]

    def table_side_effect(name):
        t = MagicMock()
        if name == "handoffs":
            select = MagicMock()
            t.select.return_value = select
            eq = MagicMock()
            select.eq.return_value = eq
            order = MagicMock()
            eq.order.return_value = order
            resp = MagicMock()
            resp.data = handoffs
            order.execute.return_value = resp
        elif name == "conversations":
            select = MagicMock()
            t.select.return_value = select
            eq = MagicMock()
            select.eq.return_value = eq
            single = MagicMock()
            eq.single.return_value = single

            resp = MagicMock()
            resp.data = conversa_1 if call_count[0] == 0 else conversa_2
            call_count[0] += 1
            single.execute.return_value = resp
        return t

    mock_supabase.table.side_effect = table_side_effect

    with patch("app.services.handoff.repository.supabase", mock_supabase):
        from app.services.handoff.repository import listar_handoffs_pendentes

        result = await listar_handoffs_pendentes()

    assert len(result) == 2
    assert result[0]["id"] == "hoff-1"
    assert "conversations" in result[0]
    assert result[0]["conversations"]["clientes"]["primeiro_nome"] == "Carlos"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_listar_handoffs_pendentes_vazio(mock_supabase):
    """Retorna lista vazia quando nao ha handoffs pendentes."""
    def table_side_effect(name):
        t = MagicMock()
        select = MagicMock()
        t.select.return_value = select
        eq = MagicMock()
        select.eq.return_value = eq
        order = MagicMock()
        eq.order.return_value = order
        resp = MagicMock()
        resp.data = []
        order.execute.return_value = resp
        return t

    mock_supabase.table.side_effect = table_side_effect

    with patch("app.services.handoff.repository.supabase", mock_supabase):
        from app.services.handoff.repository import listar_handoffs_pendentes

        result = await listar_handoffs_pendentes()

    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_listar_handoffs_pendentes_erro_banco(mock_supabase):
    """Retorna lista vazia em caso de erro no banco."""
    mock_supabase.table.side_effect = Exception("Connection error")

    with patch("app.services.handoff.repository.supabase", mock_supabase):
        from app.services.handoff.repository import listar_handoffs_pendentes

        result = await listar_handoffs_pendentes()

    assert result == []


# ---- Testes de verificar_handoff_ativo ----


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verificar_handoff_ativo_true(mock_supabase):
    """Retorna True quando conversa esta sob controle humano."""
    def table_side_effect(name):
        t = MagicMock()
        select = MagicMock()
        t.select.return_value = select
        eq = MagicMock()
        select.eq.return_value = eq
        resp = MagicMock()
        resp.data = [{"controlled_by": "human"}]
        eq.execute.return_value = resp
        return t

    mock_supabase.table.side_effect = table_side_effect

    with patch("app.services.handoff.repository.supabase", mock_supabase):
        from app.services.handoff.repository import verificar_handoff_ativo

        result = await verificar_handoff_ativo("conv-123")

    assert result is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verificar_handoff_ativo_false_ai(mock_supabase):
    """Retorna False quando conversa esta sob controle da IA."""
    def table_side_effect(name):
        t = MagicMock()
        select = MagicMock()
        t.select.return_value = select
        eq = MagicMock()
        select.eq.return_value = eq
        resp = MagicMock()
        resp.data = [{"controlled_by": "ai"}]
        eq.execute.return_value = resp
        return t

    mock_supabase.table.side_effect = table_side_effect

    with patch("app.services.handoff.repository.supabase", mock_supabase):
        from app.services.handoff.repository import verificar_handoff_ativo

        result = await verificar_handoff_ativo("conv-123")

    assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verificar_handoff_ativo_conversa_inexistente(mock_supabase):
    """Retorna False quando conversa nao existe."""
    def table_side_effect(name):
        t = MagicMock()
        select = MagicMock()
        t.select.return_value = select
        eq = MagicMock()
        select.eq.return_value = eq
        resp = MagicMock()
        resp.data = []
        eq.execute.return_value = resp
        return t

    mock_supabase.table.side_effect = table_side_effect

    with patch("app.services.handoff.repository.supabase", mock_supabase):
        from app.services.handoff.repository import verificar_handoff_ativo

        result = await verificar_handoff_ativo("conv-inexistente")

    assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verificar_handoff_ativo_erro_banco(mock_supabase):
    """Retorna False em caso de erro no banco (fail-safe)."""
    mock_supabase.table.side_effect = Exception("DB error")

    with patch("app.services.handoff.repository.supabase", mock_supabase):
        from app.services.handoff.repository import verificar_handoff_ativo

        result = await verificar_handoff_ativo("conv-123")

    assert result is False


# ---- Testes de obter_metricas_handoff ----


@pytest.mark.unit
@pytest.mark.asyncio
async def test_obter_metricas_handoff_com_dados(mock_supabase):
    """Calcula metricas corretamente com handoffs variados."""
    handoffs = [
        {
            "trigger_type": "pedido_humano",
            "status": "resolvido",
            "created_at": "2026-01-10T10:00:00+00:00",
            "resolvido_em": "2026-01-10T10:30:00+00:00",
        },
        {
            "trigger_type": "pedido_humano",
            "status": "resolvido",
            "created_at": "2026-01-11T10:00:00+00:00",
            "resolvido_em": "2026-01-11T11:00:00+00:00",
        },
        {
            "trigger_type": "juridico",
            "status": "pendente",
            "created_at": "2026-01-12T10:00:00+00:00",
            "resolvido_em": None,
        },
    ]

    def table_side_effect(name):
        t = MagicMock()
        select = MagicMock()
        t.select.return_value = select
        gte = MagicMock()
        select.gte.return_value = gte
        resp = MagicMock()
        resp.data = handoffs
        gte.execute.return_value = resp
        return t

    mock_supabase.table.side_effect = table_side_effect

    with patch("app.services.handoff.repository.supabase", mock_supabase):
        from app.services.handoff.repository import obter_metricas_handoff

        result = await obter_metricas_handoff(periodo_dias=30)

    assert result["total"] == 3
    assert result["pendentes"] == 1
    assert result["resolvidos"] == 2
    assert result["por_tipo"]["pedido_humano"] == 2
    assert result["por_tipo"]["juridico"] == 1
    # Tempo medio: (30 + 60) / 2 = 45 minutos
    assert result["tempo_medio_resolucao_minutos"] == 45


@pytest.mark.unit
@pytest.mark.asyncio
async def test_obter_metricas_handoff_vazio(mock_supabase):
    """Retorna metricas zeradas quando nao ha dados."""
    def table_side_effect(name):
        t = MagicMock()
        select = MagicMock()
        t.select.return_value = select
        gte = MagicMock()
        select.gte.return_value = gte
        resp = MagicMock()
        resp.data = []
        gte.execute.return_value = resp
        return t

    mock_supabase.table.side_effect = table_side_effect

    with patch("app.services.handoff.repository.supabase", mock_supabase):
        from app.services.handoff.repository import obter_metricas_handoff

        result = await obter_metricas_handoff()

    assert result["total"] == 0
    assert result["pendentes"] == 0
    assert result["resolvidos"] == 0
    assert result["por_tipo"] == {}
    assert result["tempo_medio_resolucao_minutos"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_obter_metricas_handoff_erro_banco(mock_supabase):
    """Retorna metricas zeradas em caso de erro."""
    mock_supabase.table.side_effect = Exception("Timeout")

    with patch("app.services.handoff.repository.supabase", mock_supabase):
        from app.services.handoff.repository import obter_metricas_handoff

        result = await obter_metricas_handoff()

    assert result["total"] == 0
    assert result["tempo_medio_resolucao_minutos"] == 0


# ---- Testes de _calcular_tempo_medio ----


@pytest.mark.unit
def test_calcular_tempo_medio_lista_vazia():
    """Retorna 0 para lista vazia."""
    from app.services.handoff.repository import _calcular_tempo_medio

    assert _calcular_tempo_medio([]) == 0


@pytest.mark.unit
def test_calcular_tempo_medio_com_dados():
    """Calcula media corretamente."""
    from app.services.handoff.repository import _calcular_tempo_medio

    handoffs = [
        {
            "created_at": "2026-01-10T10:00:00+00:00",
            "resolvido_em": "2026-01-10T10:30:00+00:00",
        },
        {
            "created_at": "2026-01-10T10:00:00+00:00",
            "resolvido_em": "2026-01-10T11:30:00+00:00",
        },
    ]

    # (30 + 90) / 2 = 60
    assert _calcular_tempo_medio(handoffs) == 60


@pytest.mark.unit
def test_calcular_tempo_medio_com_dados_invalidos():
    """Ignora registros com datas invalidas."""
    from app.services.handoff.repository import _calcular_tempo_medio

    handoffs = [
        {
            "created_at": "invalid-date",
            "resolvido_em": "2026-01-10T10:30:00+00:00",
        },
        {
            "created_at": "2026-01-10T10:00:00+00:00",
            "resolvido_em": "2026-01-10T11:00:00+00:00",
        },
    ]

    # Apenas o segundo e valido: 60 min
    assert _calcular_tempo_medio(handoffs) == 60
