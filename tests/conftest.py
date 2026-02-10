"""
Configuração global de testes - Fixtures compartilhadas.

Este arquivo contém fixtures reutilizáveis em todos os testes do projeto.
Evita duplicação de código de mock em módulos individuais.

Usage:
    Fixtures aqui definidas são automaticamente disponíveis em todos os testes.
    Para fixtures específicas de módulo, use conftest.py local.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from typing import Any


# =============================================================================
# MOCK FACTORIES - Funções para criar mocks configuráveis
# =============================================================================


def criar_mock_supabase(dados_retorno: list[dict[str, Any]] | None = None) -> MagicMock:
    """
    Cria mock do cliente Supabase com chain de métodos configurado.

    Args:
        dados_retorno: Lista de dicts que será retornada em .execute().data

    Returns:
        MagicMock configurado para suportar chain: .table().select().eq().execute()

    Example:
        mock = criar_mock_supabase([{"id": "123", "nome": "Teste"}])
        mock.table("clientes").select("*").execute().data  # retorna os dados
    """
    mock = MagicMock()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.upsert.return_value = mock
    mock.delete.return_value = mock
    mock.eq.return_value = mock
    mock.neq.return_value = mock
    mock.gt.return_value = mock
    mock.gte.return_value = mock
    mock.lt.return_value = mock
    mock.lte.return_value = mock
    mock.like.return_value = mock
    mock.ilike.return_value = mock
    mock.is_.return_value = mock
    mock.in_.return_value = mock
    mock.not_.return_value = mock
    mock.or_.return_value = mock
    mock.filter.return_value = mock
    mock.order.return_value = mock
    mock.limit.return_value = mock
    mock.range.return_value = mock
    mock.single.return_value = mock
    mock.maybeSingle.return_value = mock
    mock.rpc.return_value = mock

    # Configurar response
    response = MagicMock()
    response.data = dados_retorno if dados_retorno is not None else []
    response.count = len(response.data) if response.data else 0
    mock.execute.return_value = response

    return mock


def criar_mock_redis() -> MagicMock:
    """
    Cria mock do cliente Redis para rate limiting e cache.

    Returns:
        MagicMock com métodos async mockados (get, set, incr, expire, etc.)
    """
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.incr = AsyncMock(return_value=1)
    mock.expire = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=0)
    mock.ttl = AsyncMock(return_value=-1)
    mock.ping = AsyncMock(return_value=True)
    return mock


def criar_mock_http_response(
    status_code: int = 200,
    json_data: dict[str, Any] | list[Any] | None = None,
    text: str = "",
) -> MagicMock:
    """
    Cria mock de resposta HTTP (httpx.Response).

    Args:
        status_code: HTTP status code
        json_data: Dados JSON a retornar
        text: Texto raw da resposta

    Returns:
        MagicMock simulando httpx.Response
    """
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data if json_data is not None else {}
    mock.text = text
    mock.is_success = 200 <= status_code < 300
    mock.is_error = status_code >= 400
    return mock


# =============================================================================
# FIXTURES DE MOCKS - Serviços Externos
# =============================================================================


@pytest.fixture
def mock_supabase():
    """
    Mock global do cliente Supabase.

    Uso:
        def test_algo(mock_supabase):
            mock_supabase.table.return_value.select.return_value.execute.return_value.data = [...]
    """
    with patch("app.services.supabase.supabase") as mock:
        configured_mock = criar_mock_supabase()
        mock.table = configured_mock.table
        mock.rpc = configured_mock.rpc
        yield mock


@pytest.fixture
def mock_supabase_factory():
    """
    Factory para criar mocks de Supabase com dados específicos.

    Uso:
        def test_algo(mock_supabase_factory):
            mock = mock_supabase_factory([{"id": "123"}])
    """
    return criar_mock_supabase


@pytest.fixture
def mock_redis():
    """
    Mock do cliente Redis para testes de rate limiting.

    Uso:
        def test_rate_limit(mock_redis):
            mock_redis.get.return_value = "5"  # 5 mensagens enviadas
    """
    with patch("app.services.rate_limiter.redis_client") as mock:
        configured_mock = criar_mock_redis()
        mock.get = configured_mock.get
        mock.set = configured_mock.set
        mock.incr = configured_mock.incr
        mock.expire = configured_mock.expire
        mock.delete = configured_mock.delete
        mock.exists = configured_mock.exists
        mock.ping = configured_mock.ping
        yield mock


@pytest.fixture
def mock_evolution_api():
    """
    Mock da Evolution API (WhatsApp).

    Uso:
        def test_envio(mock_evolution_api):
            resultado = await enviar_mensagem(...)
            mock_evolution_api.assert_called_once()
    """
    with patch("app.services.whatsapp.evolution.enviar_mensagem") as mock:
        mock.return_value = {"success": True, "message_id": f"msg-{uuid4()}"}
        yield mock


@pytest.fixture
def mock_slack():
    """
    Mock do Slack para notificações.

    Uso:
        def test_notificacao(mock_slack):
            await notificar_gestor(...)
            mock_slack.assert_called()
    """
    with patch("app.services.slack.enviar_slack") as mock:
        mock.return_value = {"ok": True, "ts": "1234567890.123456"}
        yield mock


@pytest.fixture
def mock_llm():
    """
    Mock simplificado do LLM (Claude).

    Para testes que precisam de resposta de texto simples.
    Para testes de tool calls, use mock_llm_with_tools.
    """
    with patch("app.services.llm.chamar_llm") as mock:
        mock.return_value = "Resposta do LLM para testes"
        yield mock


@pytest.fixture
def mock_httpx_client():
    """
    Mock do httpx.AsyncClient para requisições HTTP externas.

    Uso:
        def test_api_call(mock_httpx_client):
            mock_httpx_client.post.return_value = criar_mock_http_response(200, {"ok": True})
    """
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get.return_value = criar_mock_http_response()
    mock_client.post.return_value = criar_mock_http_response()
    mock_client.put.return_value = criar_mock_http_response()
    mock_client.delete.return_value = criar_mock_http_response()

    with patch("httpx.AsyncClient", return_value=mock_client):
        yield mock_client


# =============================================================================
# FIXTURES DE DADOS - Entidades do Domínio
# =============================================================================


@pytest.fixture
def medico_data():
    """Dados de médico para testes."""
    return {
        "id": str(uuid4()),
        "primeiro_nome": "Dr. Teste",
        "telefone": "5511999999999",
        "especialidade_nome": "Cardiologia",
        "crm": "123456-SP",
        "status": "ativo",
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def hospital_data():
    """Dados de hospital para testes."""
    return {
        "id": str(uuid4()),
        "nome": "Hospital Teste",
        "cidade": "São Paulo",
        "estado": "SP",
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def vaga_data(hospital_data):
    """Dados de vaga para testes."""
    return {
        "id": str(uuid4()),
        "hospital_id": hospital_data["id"],
        "hospital_nome": hospital_data["nome"],
        "especialidade": "Cardiologia",
        "data": (datetime.now() + timedelta(days=10)).date().isoformat(),
        "periodo": "noturno",
        "valor": 2500.00,
        "status": "aberta",
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def conversa_data(medico_data):
    """Dados de conversa para testes."""
    return {
        "id": str(uuid4()),
        "cliente_id": medico_data["id"],
        "telefone": medico_data["telefone"],
        "status": "ativa",
        "controlled_by": "julia",
        "campanha_id": None,
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def campanha_discovery_data():
    """Dados de campanha discovery para testes."""
    return {
        "id": str(uuid4()),
        "nome_template": "test_discovery",
        "tipo_campanha": "discovery",
        "objetivo": "Conhecer médicos e entender suas preferências",
        "regras": [
            "Nunca mencionar vagas ou oportunidades",
            "Não falar de valores",
            "Foco em conhecer o médico",
        ],
        "pode_ofertar": False,
        "status": "ativa",
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def campanha_oferta_data():
    """Dados de campanha oferta para testes."""
    return {
        "id": str(uuid4()),
        "nome_template": "test_oferta",
        "tipo_campanha": "oferta",
        "objetivo": "Ofertar vagas disponíveis",
        "regras": [
            "Consultar sistema antes de ofertar",
            "Nunca inventar vagas",
        ],
        "escopo_vagas": {},
        "pode_ofertar": True,
        "status": "ativa",
        "created_at": datetime.utcnow().isoformat(),
    }


# =============================================================================
# FIXTURES UTILITÁRIAS
# =============================================================================


@pytest.fixture
def random_uuid():
    """Gera UUID único para cada teste."""
    return uuid4()


@pytest.fixture
def random_telefone():
    """Gera telefone aleatório no formato brasileiro."""
    import random

    ddd = random.choice(["11", "21", "31", "41", "51"])
    numero = "".join([str(random.randint(0, 9)) for _ in range(9)])
    return f"55{ddd}{numero}"


@pytest.fixture
def mock_datetime_now():
    """
    Mock de datetime.now() para testes de horário.

    Uso:
        def test_horario(mock_datetime_now):
            mock_datetime_now(datetime(2024, 1, 15, 10, 0))  # Segunda 10h
            resultado = verificar_horario_comercial()
    """

    def _mock_now(dt: datetime):
        with patch("app.services.rate_limiter.datetime") as mock_dt:
            mock_dt.now.return_value = dt
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            return mock_dt

    return _mock_now


@pytest.fixture
def freeze_time():
    """
    Congela o tempo em um momento específico.

    Uso:
        def test_algo(freeze_time):
            with freeze_time(datetime(2024, 1, 15, 10, 0)):
                # Código que usa datetime.now()
    """
    from contextlib import contextmanager

    @contextmanager
    def _freeze(dt: datetime):
        with patch("datetime.datetime") as mock_dt:
            mock_dt.now.return_value = dt
            mock_dt.utcnow.return_value = dt
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            yield mock_dt

    return _freeze
